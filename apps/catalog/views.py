"""
Views для приложения Catalog.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib import messages
from django.db import transaction
from .models import Product, ProductVariant, Order, OrderItem
from .cart import Cart
from .forms import OrderCreateForm

class ProductListView(ListView):
    """
    Представление для списка товаров (каталог).
    """
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        """
        Показываем только активные товары с доступными вариантами.
        """
        return Product.objects.filter(
            is_active=True,
            variants__is_available=True
        ).distinct().prefetch_related('variants')

class ProductDetailView(DetailView):
    """
    Представление для детальной страницы товара.
    """
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        """
        Предзагружаем варианты для оптимизации запросов.
        """
        return Product.objects.prefetch_related('variants')

class CartAddView(View):
    """
    Представление для добавления товара в корзину.
    """
    def post(self, request, variant_id):
        """
        Обработка POST-запроса на добавление в корзину.
        """
        cart = Cart(request)
        variant = get_object_or_404(ProductVariant, id=variant_id, is_available=True)
        
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
    """
    Представление для удаления товара из корзины.
    """
    def post(self, request, variant_id):
        """
        Обработка POST-запроса на удаление из корзины.
        """
        cart = Cart(request)
        variant = get_object_or_404(ProductVariant, id=variant_id)
        cart.remove(variant)
        messages.info(request, 'Товар удалён из корзины.')
        return redirect('catalog:cart_detail')

class CartUpdateView(View):
    """
    Представление для обновления количества товара в корзине.
    """
    def post(self, request, variant_id):
        """
        Обработка POST-запроса на изменение количества.
        """
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
    """
    Представление для отображения корзины.
    """
    def get(self, request):
        """
        Отображение страницы корзины.
        """
        cart = Cart(request)
        return render(request, 'catalog/cart_detail.html', {'cart': cart})

class OrderCreateView(View):
    """
    Представление для создания заказа (оформления предзаказа).
    """
    def get(self, request):
        """
        Отображение формы оформления заказа.
        """
        cart = Cart(request)
        
        if len(cart) == 0:
            messages.warning(request, 'Ваша корзина пуста. Добавьте товары для оформления заказа.')
            return redirect('catalog:product_list')
        
        form = OrderCreateForm()
        return render(request, 'catalog/order_create.html', {
            'cart': cart,
            'form': form
        })
    
    def post(self, request):
        """
        Обработка формы оформления заказа.
        """
        cart = Cart(request)
        
        if len(cart) == 0:
            messages.warning(request, 'Ваша корзина пуста.')
            return redirect('catalog:product_list')
        
        form = OrderCreateForm(request.POST)
        
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
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
    """
    Представление для страницы успешного оформления заказа.
    """
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
    """
    Представление для страницы информации о доставке.
    """
    template_name = 'catalog/delivery_info.html'

class ContactsView(TemplateView):
    """
    Представление для страницы контактов.
    """
    template_name = 'catalog/contacts.html'
