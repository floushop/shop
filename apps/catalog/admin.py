"""
Настройки админ-панели для приложения Catalog.
Используется TabularInline для удобного редактирования цен и размеров 
прямо на странице создания/редактирования букета.
"""

from django.contrib import admin
from .models import Product, ProductVariant, Order, OrderItem

class ProductVariantInline(admin.TabularInline):
    """
    Встроенный интерфейс для вариантов товара.
    Позволяет администратору управлять размерами (S, M, L) прямо в карточке продукта.
    """
    model = ProductVariant
    extra = 0
    min_num = 1 
    fields = ('size', 'price', 'is_available')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Админ-класс для модели Product.
    """
    list_display = ('name', 'is_active', 'created_at', 'get_min_price_display')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    
    inlines = [ProductVariantInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'image', 'is_active')
        }),
    )
    
    def get_min_price_display(self, obj):
        """Отображает минимальную цену в списке товаров."""
        min_price = obj.get_min_price()
        return f"{min_price} ₽" if min_price else "Нет в наличии"
    get_min_price_display.short_description = "Цена от"

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Админ-класс для модели ProductVariant (опционально, для расширенного управления).
    """
    list_display = ('product', 'size', 'price', 'is_available')
    list_filter = ('size', 'is_available', 'product')
    search_fields = ('product__name',)

class OrderItemInline(admin.TabularInline):
    """
    Встроенный интерфейс для элементов заказа.
    """
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
    """
    Админ-класс для модели Order.
    """
    list_display = ('id', 'first_name', 'phone', 'status', 'total_cost', 'delivery_cost', 'created_at')
    list_filter = ('status', 'created_at', 'delivery_date')
    search_fields = ('first_name', 'phone', 'email', 'address')
    readonly_fields = ('created_at', 'updated_at', 'total_cost', 'delivery_cost')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Информация о клиенте', {
            'fields': ('first_name', 'phone', 'email')
        }),
        ('Доставка', {
            'fields': ('address', 'delivery_date', 'comment')
        }),
        ('Оплата', {
            'fields': ('total_cost', 'delivery_cost')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
