"""
Модели приложения Catalog.
Здесь определены сущности для товаров и их вариантов (размеров).
Поскольку мы работаем по предзаказу, мы не отслеживаем точные остатки (stock), 
а используем флаг `is_available` для управления доступностью.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

class Product(models.Model):
    """
    Базовая модель товара (Букета/Композиции).
    Содержит общую информацию, которая не зависит от конкретного размера.
    """
    name = models.CharField(
        max_length=255, 
        verbose_name=_("Название букета")
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Описание")
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
        """Возвращает минимальную цену среди доступных вариантов."""
        available_variants = self.variants.filter(is_available=True)
        if available_variants.exists():
            return min(variant.price for variant in available_variants)
        return None

class ProductVariant(models.Model):
    """
    Модель вариации товара.
    Позволяет задавать разные цены для разных размеров одного и того же букета.
    """
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

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.price} руб.)"

class Order(models.Model):
    """
    Модель заказа (предзаказа).
    """
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('confirmed', 'Подтверждён'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнен'),
        ('cancelled', 'Отменён'),
    )
    
    first_name = models.CharField(max_length=100, verbose_name=_("Имя"))
    phone = models.CharField(max_length=20, verbose_name=_("Телефон"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    address = models.TextField(verbose_name=_("Адрес доставки"))
    delivery_date = models.DateField(verbose_name=_("Дата доставки"))
    comment = models.TextField(blank=True, verbose_name=_("Комментарий"))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    
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

    def __str__(self):
        return f"Заказ #{self.pk} - {self.first_name}"

class OrderItem(models.Model):
    """
    Элемент заказа (конкретный товар и его количество).
    """
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
