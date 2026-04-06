from .cart import Cart

class CartProxy:
    """
    Прокси-класс для корзины, чтобы избежать проблем с копированием контекста в Python 3.14
    """
    def __init__(self, request):
        self._request = request
    
    def __iter__(self):
        cart = Cart(self._request)
        return iter(cart)
    
    def __len__(self):
        cart = Cart(self._request)
        return len(cart)
    
    def get_total_price(self):
        cart = Cart(self._request)
        return cart.get_total_price()
    
    def get_delivery_cost(self):
        cart = Cart(self._request)
        return cart.get_delivery_cost()
    
    def get_final_total(self):
        cart = Cart(self._request)
        return cart.get_final_total()

def cart(request):
    return {'cart': CartProxy(request)}