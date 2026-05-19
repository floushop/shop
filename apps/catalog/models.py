
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Название"))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("Slug"))
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name=_("Родительская категория")
    )

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")
        ordering = ['name']

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    name = models.CharField(
        max_length=255, 
        verbose_name=_("Название букета")
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Описание")
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name=_("Категория")
    )
    color = models.CharField(
        max_length=50,
        choices=[
            ('red', 'Красный'),
            ('pink', 'Розовый'),
            ('white', 'Белый'),
            ('yellow', 'Желтый'),
            ('mixed', 'Микс'),
        ],
        default='mixed',
        verbose_name=_("Основной цвет")
    )
    is_new = models.BooleanField(
        default=False,
        verbose_name=_("Новинка")
    )
    image = models.ImageField(
        upload_to='products/',
        verbose_name=_("Изображение"),
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Активен"),
        help_text=_("Снимите галочку, чтобы скрыть товар из каталога полностью.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("Дата создания")
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_("Дата обновления")
    )

    class Meta:
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'pk': self.pk})
    
    def get_min_price(self):
        available_variants = self.variants.filter(is_available=True)
        if available_variants.exists():
            return min(variant.price for variant in available_variants)
        return None

class ProductVariant(models.Model):
    SIZE_CHOICES = (
        ('S', 'Малый (Small)'),
        ('M', 'Средний (Medium)'),
        ('L', 'Большой (Large)'),
    )

    product = models.ForeignKey(
        Product, 
        related_name='variants', 
        on_delete=models.CASCADE, 
        verbose_name=_("Товар")
    )
    size = models.CharField(
        max_length=1, 
        choices=SIZE_CHOICES, 
        verbose_name=_("Размер")
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_("Цена")
    )
    stock_quantity = models.IntegerField(
        default=0,
        verbose_name=_("Остаток на складе")
    )
    low_stock_threshold = models.IntegerField(
        default=5,
        verbose_name=_("Порог малого остатка"),
        help_text=_("Если остаток меньше или равен этому значению, товар считается с малым остатком.")
    )
    is_available = models.BooleanField(
        default=True, 
        verbose_name=_("Доступен для предзаказа"),
        help_text=_("Снимите галочку, если цветы для данного размера временно недоступны.")
    )

    class Meta:
        verbose_name = _("Вариант товара")
        verbose_name_plural = _("Варианты товаров")
        unique_together = ('product', 'size')
        ordering = ["product", "size"]

    def save(self, *args, **kwargs):
        if self.stock_quantity > 0:
            self.is_available = True
        else:
            self.is_available = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.price} руб.)"

class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('confirmed', 'Подтверждён'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнен'),
        ('cancelled', 'Отменён'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Клиент")
    )
    first_name = models.CharField(max_length=100, verbose_name=_("Имя"))
    phone = models.CharField(max_length=20, verbose_name=_("Телефон"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    address = models.TextField(verbose_name=_("Адрес доставки"))
    delivery_date = models.DateField(verbose_name=_("Дата доставки"))
    comment = models.TextField(blank=True, verbose_name=_("Комментарий"))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    is_paid = models.BooleanField(default=False, verbose_name=_("Оплачен"))
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Дата и время оплаты"))
    stock_deducted = models.BooleanField(default=False, verbose_name=_("Списано со склада"))
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new',
        verbose_name=_("Статус")
    )
    
    total_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_("Сумма заказа")
    )
    delivery_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name=_("Стоимость доставки")
    )

    class Meta:
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.stock_deducted:
            for item in self.items.all():
                if item.product_variant:
                    variant = item.product_variant
                    variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                    variant.save() # Это также обновит флаг is_available
            self.stock_deducted = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Заказ #{self.pk} - {self.first_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, 
        related_name='items', 
        on_delete=models.CASCADE,
        verbose_name=_("Заказ")
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Вариант товара")
    )
    product_name = models.CharField(
        max_length=255, 
        verbose_name=_("Название товара")
    )
    size = models.CharField(max_length=10, verbose_name=_("Размер"))
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name=_("Цена")
    )
    quantity = models.PositiveIntegerField(
        default=1, 
        verbose_name=_("Количество")
    )

    class Meta:
        verbose_name = _("Элемент заказа")
        verbose_name_plural = _("Элементы заказа")

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def get_cost(self):
        return self.price * self.quantity
