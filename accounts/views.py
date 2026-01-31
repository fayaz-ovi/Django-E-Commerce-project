from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from .forms import RegistrationForm
from .models import Account
from orders.models import Order, OrderProduct
from carts.models import Cart, CartItem
from carts.views import _cart_id


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]
            
            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password
            )
            user.phone_number = phone_number
            user.save()
            
            messages.success(request, 'Registration successful! You can now login.')
            return redirect('login')
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)


def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            # Get or merge cart before login
            try:
                # Check if user has existing cart
                user_cart = Cart.objects.filter(user=user, is_active=True).first()
                
                # Check for session cart
                session_cart = Cart.objects.filter(cart_id=_cart_id(request), user__isnull=True).first()
                
                if session_cart and user_cart:
                    # Merge session cart items with user cart
                    session_items = CartItem.objects.filter(cart=session_cart)
                    
                    for session_item in session_items:
                        try:
                            # Check if product already exists in user cart
                            user_item = CartItem.objects.get(
                                cart=user_cart,
                                product=session_item.product,
                                user=user
                            )
                            # Add quantities together (respecting stock limits)
                            new_quantity = user_item.quantity + session_item.quantity
                            if new_quantity <= session_item.product.stock:
                                user_item.quantity = new_quantity
                            else:
                                user_item.quantity = session_item.product.stock
                                messages.warning(request, f'{session_item.product.product_name}: Maximum stock limit reached.')
                            user_item.check_stock_availability()
                            user_item.save()
                        except CartItem.DoesNotExist:
                            # Move session item to user cart
                            session_item.cart = user_cart
                            session_item.user = user
                            session_item.check_stock_availability()
                            session_item.save()
                    
                    # Delete session cart after merge
                    session_cart.delete()
                    messages.info(request, 'Your cart has been updated with previous items.')
                    
                elif session_cart and not user_cart:
                    # Assign session cart to user
                    session_cart.user = user
                    session_cart.save()
                    
                    # Update all cart items with user
                    CartItem.objects.filter(cart=session_cart).update(user=user)
                    
                elif user_cart and not session_cart:
                    # User has existing cart, just load it
                    cart_count = user_cart.get_total_items()
                    if cart_count > 0:
                        messages.info(request, f'Welcome back! You have {cart_count} item(s) in your cart.')
                        
            except Exception as e:
                # If any error occurs, just continue with login
                print(f"Cart merge error: {e}")
                pass
            
            auth.login(request, user)
            messages.success(request, 'You are now logged in.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')
    return render(request, 'accounts/login.html')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    orders_count = orders.count()
    
    context = {
        'orders_count': orders_count,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'accounts/my_orders.html', context)


@login_required(login_url='login')
def order_detail(request, order_id):
    order_detail = get_object_or_404(Order, id=order_id, user=request.user, is_ordered=True)
    order_products = OrderProduct.objects.filter(order_id=order_id)
    
    subtotal = 0
    for i in order_products:
        subtotal += i.product_price * i.quantity
    
    context = {
        'order_detail': order_detail,
        'order_products': order_products,
        'subtotal': subtotal,
    }
    return render(request, 'accounts/order_detail.html', context)


@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone_number = request.POST.get('phone_number')
        user.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('dashboard')
    
    return render(request, 'accounts/edit_profile.html')


@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated successfully.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Current password is incorrect')
                return redirect('change_password')
        else:
            messages.error(request, 'Passwords do not match!')
            return redirect('change_password')
    return render(request, 'accounts/change_password.html')
