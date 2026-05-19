
from decimal import Decimal
from django.conf import settings
from .models import ProductVariant

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
            
        self.cart = cart

    def add(self, variant, quantity=1, override_quantity=False):
        variant_id = str(variant.id)
        
        if variant_id not in self.cart:
            self.cart[variant_id] = {
                'quantity': 0,
                'price': str(variant.price)
            }

        if override_quantity:
            self.cart[variant_id]['quantity'] = quantity
        else:
            self.cart[variant_id]['quantity'] += quantity
            
        self.save()

    def remove(self, variant):
        variant_id = str(variant.id)
        if variant_id in self.cart:
            del self.cart[variant_id]
            self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        variant_ids = self.cart.keys()
        
        variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')
        
        cart = self.cart.copy()
        for variant in variants:
            cart[str(variant.id)]['variant'] = variant
            cart[str(variant.id)]['product'] = variant.product

        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(
            Decimal(item['price']) * item['quantity'] 
            for item in self.cart.values()
        )

    def get_delivery_cost(self):
        total = self.get_total_price()
        
        if total == 0:
            return Decimal('0.00')
            
        threshold = Decimal(str(settings.FREE_DELIVERY_THRESHOLD))
        standard_delivery_cost = Decimal(str(settings.STANDARD_DELIVERY_COST))
        
        if total >= threshold:
            return Decimal('0.00')
        return standard_delivery_cost

    def get_final_total(self):
        return self.get_total_price() + self.get_delivery_cost()

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        self.save()
