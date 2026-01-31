from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
import json
from store.models import Product
from .models import Cart, CartItem



# Create your views here.
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

@login_required(login_url='login')
def add_cart(request, product_id):
    if request.method == 'POST':

        for item in request.POST:
            key = item
            value = request.POST[key]


    product=Product.objects.get(id=product_id)
    current_user = request.user
    
    # Check if product is in stock
    if product.stock == 0:
        messages.error(request, f'{product.product_name} is out of stock.')
        return redirect('cart')

    # Get or create user's cart (handle multiple carts by getting the latest)
    cart = Cart.objects.filter(user=current_user, is_active=True).order_by('-updated_at').first()
    
    if not cart:
        cart = Cart.objects.create(
            cart_id=_cart_id(request),
            user=current_user,
            is_active=True
        )
    else:
        # Consolidate if multiple carts exist
        duplicate_carts = Cart.objects.filter(user=current_user, is_active=True).exclude(id=cart.id)
        if duplicate_carts.exists():
            for dup_cart in duplicate_carts:
                # Move items from duplicate carts to main cart
                dup_items = CartItem.objects.filter(cart=dup_cart)
                for dup_item in dup_items:
                    try:
                        # Check if item already exists in main cart
                        existing_item = CartItem.objects.get(
                            cart=cart,
                            product=dup_item.product,
                            user=current_user
                        )
                        # Merge quantities
                        existing_item.quantity += dup_item.quantity
                        existing_item.save()
                        dup_item.delete()
                    except CartItem.DoesNotExist:
                        # Move item to main cart
                        dup_item.cart = cart
                        dup_item.save()
                dup_cart.delete()

    try:
        cart_item=CartItem.objects.get(product=product, cart=cart, user=current_user)
        
        # Check if adding one more exceeds stock
        if cart_item.quantity + 1 > product.stock:
            messages.warning(request, f'Cannot add more. Only {product.stock} items available in stock.')
            return redirect('cart')
        
        cart_item.quantity += 1
        cart_item.check_stock_availability()
        cart_item.save()
    except CartItem.DoesNotExist:
        cart_item=CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
            user=current_user
        )
        cart_item.save()
    
    messages.success(request, f'{product.product_name} added to cart.')
    return redirect('cart')

@login_required(login_url='login')
def remove_cart(request, product_id):
    current_user = request.user
    product=get_object_or_404(Product, id=product_id)
    try:
        cart = Cart.objects.filter(user=current_user, is_active=True).order_by('-updated_at').first()
        if not cart:
            return redirect('cart')
        cart_item=CartItem.objects.get(product=product, cart=cart, user=current_user)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.check_stock_availability()
            cart_item.save()
        else:
            cart_item.delete()
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass
    return redirect('cart')


@login_required(login_url='login')
def remove_cart_item(request, product_id):
    current_user = request.user
    product=get_object_or_404(Product, id=product_id)
    try:
        cart = Cart.objects.filter(user=current_user, is_active=True).order_by('-updated_at').first()
        if not cart:
            return redirect('cart')
        cart_item=CartItem.objects.get(product=product, cart=cart, user=current_user)
        cart_item.delete()
        messages.info(request, f'{product.product_name} removed from cart.')
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass
    return redirect('cart')

@login_required(login_url='login')
def cart(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0
    stock_warnings = {}
    stock_data = {}
    current_user = request.user
    
    try:
        # Get user's active cart (handle multiple by getting latest)
        cart = Cart.objects.filter(user=current_user, is_active=True).order_by('-updated_at').first()
        
        if not cart:
            raise Cart.DoesNotExist
        
        # Consolidate duplicate carts if they exist
        duplicate_carts = Cart.objects.filter(user=current_user, is_active=True).exclude(id=cart.id)
        if duplicate_carts.exists():
            for dup_cart in duplicate_carts:
                dup_items = CartItem.objects.filter(cart=dup_cart)
                for dup_item in dup_items:
                    try:
                        # Check if item already exists in main cart
                        existing_item = CartItem.objects.get(
                            cart=cart,
                            product=dup_item.product,
                            user=current_user
                        )
                        # Merge quantities
                        existing_item.quantity += dup_item.quantity
                        existing_item.save()
                        dup_item.delete()
                    except CartItem.DoesNotExist:
                        # Move item to main cart
                        dup_item.cart = cart
                        dup_item.save()
                dup_cart.delete()
        
        cart_items = CartItem.objects.filter(user=current_user, is_active=True).select_related('product').order_by('-created_at')
        
        # Validate stock for each cart item
        for cart_item in cart_items:
            # Update stock status
            cart_item.check_stock_availability()
            
            product_stock = cart_item.product.stock
            stock_data[str(cart_item.product.id)] = product_stock
            
            # Check if product is out of stock
            if product_stock == 0:
                stock_warnings[cart_item.product.id] = {
                    'type': 'out_of_stock',
                    'message': cart_item.get_stock_message()
                }
                # Mark as inactive but don't delete yet
                cart_item.is_active = False
                cart_item.save()
            # Check if requested quantity exceeds stock
            elif cart_item.quantity > product_stock:
                stock_warnings[cart_item.product.id] = {
                    'type': 'insufficient_stock',
                    'message': cart_item.get_stock_message()
                }
                # Adjust quantity to available stock
                cart_item.adjust_quantity_to_stock()
                messages.warning(request, f'{cart_item.product.product_name}: {cart_item.get_stock_message()}')
            
            # Calculate totals only for items with available stock
            if product_stock > 0 and cart_item.is_active:
                total += cart_item.sub_total()
                quantity += cart_item.quantity
        
        tax= (2 * total)/100
        grand_total= total + tax

    except Cart.DoesNotExist:
        pass #just ignore

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
        'stock_warnings': stock_warnings,
        'stock_data': json.dumps(stock_data),
    }

    return render(request, 'store/cart.html', context)

@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0
    current_user = request.user
    
    try:
        cart = Cart.objects.filter(user=current_user, is_active=True).order_by('-updated_at').first()
        if not cart:
            raise Cart.DoesNotExist
        cart_items = CartItem.objects.filter(cart=cart, user=current_user, is_active=True, is_available=True)
        
        # Validate stock before checkout
        for cart_item in cart_items:
            cart_item.check_stock_availability()
            if not cart_item.is_available:
                messages.error(request, f'{cart_item.product.product_name} is no longer available.')
                return redirect('cart')
            
            total += cart_item.sub_total()
            quantity += cart_item.quantity
            
        tax = (2 * total) / 100
        grand_total = total + tax

    except Cart.DoesNotExist:
        pass

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/checkout.html', context)
