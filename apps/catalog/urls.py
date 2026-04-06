"""
URL-конфигурация для приложения Catalog.
"""

from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product_list'),
    
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'),
    path('cart/add/<int:variant_id>/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/remove/<int:variant_id>/', views.CartRemoveView.as_view(), name='cart_remove'),
    path('cart/update/<int:variant_id>/', views.CartUpdateView.as_view(), name='cart_update'),
    
    path('order/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('order/success/', views.OrderSuccessView.as_view(), name='order_success'),
    
    path('delivery/', views.DeliveryInfoView.as_view(), name='delivery_info'),
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
]
