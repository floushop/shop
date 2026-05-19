
import csv
import io
import json
import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Sum, Count, Avg, F, Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.html import format_html

from .models import Product, ProductVariant, Order, OrderItem, Category


# ─────────────────────────────────────────────
#  CATEGORY
# ─────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


# ─────────────────────────────────────────────
#  PRODUCT
# ─────────────────────────────────────────────

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    min_num = 1
    fields = ('size', 'price', 'stock_quantity', 'low_stock_threshold', 'is_available')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'color', 'is_new', 'is_active', 'created_at', 'get_min_price_display')
    list_filter = ('is_active', 'category', 'color', 'is_new', 'created_at')
    search_fields = ('name', 'description')
    inlines = [ProductVariantInline]

    # Подключаем кастомный шаблон списка товаров (с кнопкой «Экспорт»)
    change_list_template = 'admin/catalog/product/change_list.html'

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'image', 'category', 'color', 'is_new', 'is_active')
        }),
    )

    def get_min_price_display(self, obj):
        min_price = obj.get_min_price()
        return f"{min_price} ₽" if min_price else "Нет в наличии"
    get_min_price_display.short_description = "Цена от"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['export_categories'] = Category.objects.all().order_by('name')
        return super().changelist_view(request, extra_context=extra_context)

    # ── Дополнительные URL ──────────────────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-csv/',
                self.admin_site.admin_view(self.export_products_csv),
                name='catalog_product_export_csv',
            ),
            path(
                'import/',
                self.admin_site.admin_view(self.import_products_view),
                name='catalog_product_import',
            ),
        ]
        return custom_urls + urls

    # ── Экспорт в CSV ───────────────────────────────────────────────────────

    def export_products_csv(self, request):
        """
        Экспортирует товары в CSV.

        Поддерживаемые GET-параметры (фильтры):
          ?category=<id>          — фильтр по категории
          ?is_active=1|0          — фильтр по признаку активности
          ?min_price=<число>      — нижняя граница цены (по вариантам)
          ?max_price=<число>      — верхняя граница цены (по вариантам)
        """
        queryset = Product.objects.all().select_related('category').prefetch_related('variants')

        # ── Фильтр по категории ──────────────────────────────────────────
        category_id = request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # ── Фильтр по признаку активности ───────────────────────────────
        is_active = request.GET.get('is_active')
        if is_active in ('0', '1'):
            queryset = queryset.filter(is_active=bool(int(is_active)))

        # ── Фильтр по диапазону цен ─────────────────────────────────────
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(variants__price__gte=min_price).distinct()
        if max_price:
            queryset = queryset.filter(variants__price__lte=max_price).distinct()

        # ── Формируем HTTP-ответ ─────────────────────────────────────────
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'products_export_{timestamp}.csv'

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response, delimiter=';')

        # Заголовок
        writer.writerow([
            'id',
            'Название',
            'Категория',
            'Активен',
            'Цвет',
            'Размер варианта',
            'Цена (руб.)',
            'Остаток на складе',
        ])

        # Данные: по одной строке на каждый вариант товара
        for product in queryset:
            variants = product.variants.all()
            if variants.exists():
                for variant in variants:
                    writer.writerow([
                        product.id,
                        product.name,
                        product.category.name if product.category else '',
                        'Да' if product.is_active else 'Нет',
                        product.get_color_display(),
                        variant.get_size_display(),
                        variant.price,
                        variant.stock_quantity,
                    ])
            else:
                # Товар без вариантов — всё равно выгружаем
                writer.writerow([
                    product.id,
                    product.name,
                    product.category.name if product.category else '',
                    'Да' if product.is_active else 'Нет',
                    product.get_color_display(),
                    '',
                    '',
                    '',
                ])

        return response

    # ── Импорт товаров из CSV / JSON ────────────────────────────────────────

    def import_products_view(self, request):
        """
        Страница импорта товаров.
        Поддерживает CSV (разделитель «;» или «,») и JSON (массив объектов).

        Логика:
          - Если в файле есть поле «id» и товар с таким id существует → обновление.
          - Если id не указан или не найден → создание нового товара.

        Валидация каждой строки:
          - «название» (name) — обязательно, непустое.
          - «цена» (price) — обязательно, число >= 0.
          - «остаток» (stock) — число >= 0 (если указан).
          - «категория» (category) — ищется по имени; если не найдена, создаётся.

        При ошибках НЕ падает — собирает отчёт и показывает его на странице.
        """
        context = {
            **self.admin_site.each_context(request),
            'title': 'Импорт товаров',
            'opts': self.model._meta,
        }

        if request.method != 'POST':
            return TemplateResponse(request, 'admin/catalog/product/import.html', context)

        upload = request.FILES.get('import_file')
        if not upload:
            context['error'] = 'Файл не выбран.'
            return TemplateResponse(request, 'admin/catalog/product/import.html', context)

        filename = upload.name.lower()
        rows = []          # список dict-записей
        parse_error = None

        # ── Разбор файла ────────────────────────────────────────────────────
        try:
            if filename.endswith('.json'):
                raw = upload.read().decode('utf-8-sig')
                data = json.loads(raw)
                if not isinstance(data, list):
                    raise ValueError('JSON должен содержать массив объектов.')
                rows = data

            elif filename.endswith('.csv'):
                raw = upload.read().decode('utf-8-sig')
                # Автоопределение разделителя
                dialect = csv.Sniffer().sniff(raw[:1024], delimiters=';,')
                reader = csv.DictReader(io.StringIO(raw), dialect=dialect)
                rows = list(reader)

            else:
                context['error'] = 'Неподдерживаемый формат. Используйте CSV или JSON.'
                return TemplateResponse(request, 'admin/catalog/product/import.html', context)

        except Exception as exc:
            context['error'] = f'Ошибка чтения файла: {exc}'
            return TemplateResponse(request, 'admin/catalog/product/import.html', context)

        # ── Нормализация ключей (strip пробелов) ────────────────────────────
        normalized = []
        for row in rows:
            normalized.append({k.strip().lower(): str(v).strip() if v is not None else '' for k, v in row.items()})
        rows = normalized

        # ── Обработка строк ─────────────────────────────────────────────────
        created_count = 0
        updated_count = 0
        error_rows = []   # {'line': N, 'reason': '...', 'data': {...}}

        for line_num, row in enumerate(rows, start=2):   # start=2: строка 1 = заголовок
            errors = []

            # 1. Обязательное поле: название
            name = row.get('name') or row.get('название') or row.get('назва') or ''
            if not name:
                errors.append('Название (name) обязательно и не может быть пустым.')

            # 2. Обязательное поле: цена
            price_raw = row.get('price') or row.get('цена') or row.get('цена (руб.)') or ''
            price = None
            if not price_raw:
                errors.append('Цена (price) обязательна и не может быть пустой.')
            else:
                try:
                    price = Decimal(price_raw.replace(',', '.'))
                    if price < 0:
                        errors.append(f'Цена не может быть отрицательной (получено: {price_raw}).')
                        price = None
                except InvalidOperation:
                    errors.append(f'Цена должна быть числом (получено: "{price_raw}").')

            # 3. Остаток на складе
            stock_raw = row.get('stock') or row.get('stock_quantity') or row.get('остаток на складе') or row.get('остаток') or '0'
            stock = 0
            if stock_raw:
                try:
                    stock = int(stock_raw)
                    if stock < 0:
                        errors.append(f'Остаток не может быть отрицательным (получено: {stock_raw}).')
                        stock = 0
                except ValueError:
                    errors.append(f'Остаток должен быть целым числом (получено: "{stock_raw}").')

            # 4. Если есть ошибки — пропускаем строку
            if errors:
                error_rows.append({'line': line_num, 'reason': '; '.join(errors), 'data': row})
                continue

            # 5. Категория: ищем по имени, если не найдена — создаём
            category = None
            cat_name = row.get('category') or row.get('категория') or ''
            if cat_name:
                category, _ = Category.objects.get_or_create(
                    name=cat_name,
                    defaults={'slug': cat_name.lower().replace(' ', '-')[:100]}
                )

            # 5.5 Цвет:
            color_raw = row.get('color') or row.get('цвет') or ''
            color_raw = color_raw.strip().lower()
            color = 'mixed'
            if 'красн' in color_raw or 'red' in color_raw:
                color = 'red'
            elif 'розов' in color_raw or 'pink' in color_raw:
                color = 'pink'
            elif 'бел' in color_raw or 'white' in color_raw:
                color = 'white'
            elif 'желт' in color_raw or 'yellow' in color_raw:
                color = 'yellow'

            # 5.6 Размер:
            size_raw = row.get('size') or row.get('размер') or row.get('размер варианта') or 'M'
            size_raw = size_raw.strip().lower()
            size = 'M'
            if 'малый' in size_raw or 'small' in size_raw or size_raw == 's':
                size = 'S'
            elif 'большой' in size_raw or 'large' in size_raw or size_raw == 'l':
                size = 'L'

            # 6. Признак активности
            is_active_raw = row.get('is_active') or row.get('активен') or '1'
            is_active = is_active_raw.lower() not in ('0', 'false', 'нет', 'no', '')

            # 7. Update или Create
            product_id_raw = row.get('id') or ''
            product = None
            if product_id_raw:
                try:
                    product = Product.objects.filter(pk=int(product_id_raw)).first()
                except ValueError:
                    pass

            if product:
                # Обновляем существующий
                product.name = name
                product.is_active = is_active
                if color_raw:
                    product.color = color
                if category:
                    product.category = category
                product.save()
                # Обновляем или создаём вариант для указанного размера
                variant, created_var = ProductVariant.objects.get_or_create(
                    product=product,
                    size=size,
                    defaults={'price': price, 'stock_quantity': stock}
                )
                if not created_var:
                    variant.price = price
                    variant.stock_quantity = stock
                    variant.save()
                updated_count += 1
            else:
                # Создаём новый товар
                product = Product.objects.create(
                    name=name,
                    is_active=is_active,
                    category=category,
                    color=color if color_raw else 'mixed',
                )
                ProductVariant.objects.create(
                    product=product,
                    size=size,
                    price=price,
                    stock_quantity=stock,
                )
                created_count += 1

        context['result'] = {
            'total': len(rows),
            'created': created_count,
            'updated': updated_count,
            'errors': error_rows,
        }
        return TemplateResponse(request, 'admin/catalog/product/import.html', context)


# ─────────────────────────────────────────────
#  PRODUCT VARIANT
# ─────────────────────────────────────────────

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'price', 'stock_quantity', 'is_available')
    list_filter = ('size', 'is_available', 'product')
    search_fields = ('product__name',)


# ─────────────────────────────────────────────
#  ORDER
# ─────────────────────────────────────────────

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'size', 'price', 'quantity', 'get_cost')
    fields = ('product_name', 'size', 'price', 'quantity', 'get_cost')

    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = "Сумма"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'phone', 'status', 'total_cost', 'is_paid', 'created_at')
    list_filter = ('status', 'is_paid', 'created_at', 'delivery_date')
    search_fields = ('first_name', 'phone', 'email', 'address', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'total_cost', 'delivery_cost', 'stock_deducted')
    inlines = [OrderItemInline]

    fieldsets = (
        ('Информация о клиенте', {
            'fields': ('user', 'first_name', 'phone', 'email')
        }),
        ('Доставка', {
            'fields': ('address', 'delivery_date', 'comment')
        }),
        ('Оплата', {
            'fields': ('total_cost', 'delivery_cost', 'is_paid', 'paid_at')
        }),
        ('Статус', {
            'fields': ('status', 'stock_deducted')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reports/', self.admin_site.admin_view(self.reports_view), name='catalog_order_reports'),
        ]
        return custom_urls + urls

    def reports_view(self, request):
        User = get_user_model()
        today = timezone.now().date()

        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else today - datetime.timedelta(days=30)
        except ValueError:
            start_date = today - datetime.timedelta(days=30)

        try:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else today
        except ValueError:
            end_date = today

        recent_orders = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        sales_summary = recent_orders.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_cost'),
            avg_check=Avg('total_cost'),
            paid_orders=Count('id', filter=Q(is_paid=True)),
            cancelled_orders=Count('id', filter=Q(status='cancelled'))
        )

        status_counts = recent_orders.values('status').annotate(count=Count('id')).order_by('status')
        status_dict = {
            'new': 0, 'confirmed': 0, 'in_progress': 0, 'completed': 0, 'cancelled': 0
        }
        for item in status_counts:
            status_dict[item['status']] = item['count']

        low_stock_variants = ProductVariant.objects.filter(stock_quantity__lte=F('low_stock_threshold')).select_related('product')
        all_variants_stock = ProductVariant.objects.all().select_related('product').order_by('stock_quantity')

        new_users_count = User.objects.filter(
            date_joined__date__gte=start_date,
            date_joined__date__lte=end_date
        ).count()
        new_users_with_orders = User.objects.filter(
            date_joined__date__gte=start_date,
            date_joined__date__lte=end_date,
            orders__isnull=False
        ).distinct().count()

        best_customers = User.objects.annotate(
            total_spent=Sum('orders__total_cost'),
            orders_count=Count('orders')
        ).filter(total_spent__gt=0).order_by('-total_spent')[:10]

        context = {
            **self.admin_site.each_context(request),
            'title': 'Отчёты магазина',
            'opts': self.model._meta,
            'sales_summary': sales_summary,
            'status_dict': status_dict,
            'low_stock_variants': low_stock_variants,
            'all_variants_stock': all_variants_stock,
            'new_users_count': new_users_count,
            'new_users_with_orders': new_users_with_orders,
            'best_customers': best_customers,
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
        }
        return TemplateResponse(request, "admin/catalog/order/reports.html", context)
