from .models import Cart, CartItem
from .views import _cart_id
import logging

logger = logging.getLogger(__name__)

def counter(request):
    cart_count = 0
    
    if request.user.is_authenticated:
        # For authenticated users, get their cart items directly
        try:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
            cart_count = sum(item.quantity for item in cart_items)
            logger.debug(f"Cart count for {request.user.email}: {cart_count}")
        except Exception as e:
            logger.error(f"Cart counter error for authenticated user: {e}")
            cart_count = 0
    else:
        # For anonymous users, use session cart
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            cart_count = sum(item.quantity for item in cart_items)
            logger.debug(f"Cart count for anonymous user: {cart_count}")
        except Cart.DoesNotExist:
            cart_count = 0
        except Exception as e:
            logger.error(f"Cart counter error for anonymous user: {e}")
            cart_count = 0
    
    return {'cart_count': cart_count}