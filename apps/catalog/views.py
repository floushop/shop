
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db import transaction
from django.db.models import Q, Min, Max
from django.http import JsonResponse
from .models import Product, ProductVariant, Order, OrderItem, Category
from .cart import Cart
from .forms import OrderCreateForm

class ProductListView(ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).distinct()
        
        # Поиск
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | 
                Q(description__icontains=q) |
                Q(category__name__icontains=q)
            )

        # Фильтрация по категории
        cat_slug = self.request.GET.get('category')
        if cat_slug:
            category = get_object_or_404(Category, slug=cat_slug)
            # Включаем подкатегории
            queryset = queryset.filter(
                Q(category=category) | Q(category__parent=category)
            )

        # Фильтрация по цене
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(variants__price__gte=min_price)
        if max_price:
            queryset = queryset.filter(variants__price__lte=max_price)

        # Фильтрация по наличию и новинкам
        if self.request.GET.get('in_stock'):
            queryset = queryset.filter(variants__stock_quantity__gt=0)
        if self.request.GET.get('is_new'):
            queryset = queryset.filter(is_new=True)

        # Сортировка
        sort = self.request.GET.get('sort', 'newest')
        if sort == 'price_asc':
            queryset = queryset.annotate(min_p=Min('variants__price')).order_by('min_p')
        elif sort == 'price_desc':
            queryset = queryset.annotate(min_p=Min('variants__price')).order_by('-min_p')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        
        return queryset.distinct().prefetch_related('variants')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent__isnull=True).prefetch_related('children')
        
        # Получаем диапазон цен для слайдера (опционально)
        price_range = ProductVariant.objects.aggregate(min_p=Min('price'), max_p=Max('price'))
        context['min_price_all'] = price_range['min_p'] or 0
        context['max_price_all'] = price_range['max_p'] or 10000
        
        # Для отображения текущих фильтров
        context['current_filters'] = self.request.GET
        
        # Если поиск пустой, добавим популярные/похожие
        if self.request.GET.get('q') and not context['products'].exists():
            context['similar_products'] = Product.objects.filter(is_active=True)[:6]
            
        return context

class ProductAutocompleteView(View):
    def get(self, request):
        q = request.GET.get('q', '')
        if len(q) < 3:
            return JsonResponse([], safe=False)
            
        products = Product.objects.filter(
            Q(name__icontains=q) | Q(category__name__icontains=q),
            is_active=True
        )[:5]
        
        results = [
            {'id': p.id, 'name': p.name, 'url': p.get_absolute_url()} 
            for p in products
        ]
        return JsonResponse(results, safe=False)

class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return Product.objects.prefetch_related('variants')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_variants'] = self.object.variants.filter(is_available=True)
        context['all_variants'] = self.object.variants.all()
        return context

class CartAddView(View):
    def post(self, request, variant_id=None):
        cart = Cart(request)
        # Форма на фронтенде отправляет выбранный variant_id в теле запроса,
        # а в URL может быть оставлен дефолтный. Используем приоритетно POST.
        actual_variant_id = request.POST.get('variant_id') or variant_id
        
        variant = get_object_or_404(ProductVariant, id=actual_variant_id, is_available=True)
        
        quantity = int(request.POST.get('quantity', 1))
        
        cart.add(variant=variant, quantity=quantity)
        
        messages.success(
            request, 
            f'"{variant.product.name}" ({variant.get_size_display()}) добавлен в корзину.'
        )
        
        next_url = request.POST.get('next', 'catalog:product_detail')
        if next_url == 'catalog:cart_detail':
            return redirect('catalog:cart_detail')
        return redirect('catalog:product_detail', pk=variant.product.pk)

class CartRemoveView(View):
    def post(self, request, variant_id):
        cart = Cart(request)
        variant = get_object_or_404(ProductVariant, id=variant_id)
        cart.remove(variant)
        messages.info(request, 'Товар удалён из корзины.')
        return redirect('catalog:cart_detail')

class CartUpdateView(View):
    def post(self, request, variant_id):
        cart = Cart(request)
        variant = get_object_or_404(ProductVariant, id=variant_id)
        
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart.add(variant=variant, quantity=quantity, override_quantity=True)
            messages.success(request, 'Количество обновлено.')
        else:
            cart.remove(variant)
            messages.info(request, 'Товар удалён из корзины.')
        
        return redirect('catalog:cart_detail')

class CartDetailView(View):
    def get(self, request):
        cart = Cart(request)
        return render(request, 'catalog/cart_detail.html', {'cart': cart})

class OrderCreateView(View):
    def get(self, request):
        cart = Cart(request)
        
        if len(cart) == 0:
            messages.warning(request, 'Ваша корзина пуста. Добавьте товары для оформления заказа.')
            return redirect('catalog:product_list')
        
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'first_name': request.user.first_name,
                'email': request.user.email,
            }
            if not initial['first_name'] and request.user.username:
                initial['first_name'] = request.user.username

        form = OrderCreateForm(initial=initial)
        return render(request, 'catalog/order_create.html', {
            'cart': cart,
            'form': form
        })
    
    def post(self, request):
        cart = Cart(request)
        
        if len(cart) == 0:
            messages.warning(request, 'Ваша корзина пуста.')
            return redirect('catalog:product_list')
        
        form = OrderCreateForm(request.POST)
        
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                order.total_cost = cart.get_total_price()
                order.delivery_cost = cart.get_delivery_cost()
                order.save()
                
                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        product_variant=item['variant'],
                        product_name=item['product'].name,
                        size=item['variant'].get_size_display(),
                        price=item['price'],
                        quantity=item['quantity']
                    )
                
                cart.clear()
                
                request.session['last_order_id'] = order.id
                
                messages.success(request, 'Ваш заказ успешно оформлен!')
                return redirect('catalog:order_success')
        
        return render(request, 'catalog/order_create.html', {
            'cart': cart,
            'form': form
        })

class OrderSuccessView(TemplateView):
    template_name = 'catalog/order_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = self.request.session.get('last_order_id')
        if order_id:
            try:
                context['order'] = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                pass
        return context

class DeliveryInfoView(TemplateView):
    template_name = 'catalog/delivery_info.html'

class ContactsView(TemplateView):
    template_name = 'catalog/contacts.html'

class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:product_list')
        form = UserCreationForm()
        return render(request, 'catalog/register.html', {'form': form})
        
    def post(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:product_list')
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Поздравляем с успешной регистрацией!')
            return redirect('catalog:product_list')
        return render(request, 'catalog/register.html', {'form': form})
