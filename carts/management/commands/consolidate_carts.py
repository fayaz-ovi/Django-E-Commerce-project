from django.core.management.base import BaseCommand
from carts.models import Cart, CartItem
from django.db.models import Count

class Command(BaseCommand):
    help = 'Consolidate duplicate carts for each user'

    def handle(self, *args, **options):
        self.stdout.write('Starting cart consolidation...')
        
        # Find users with multiple active carts
        users_with_duplicates = Cart.objects.filter(is_active=True).values('user').annotate(
            cart_count=Count('id')
        ).filter(cart_count__gt=1)
        
        consolidated = 0
        for user_data in users_with_duplicates:
            user_id = user_data['user']
            if user_id is None:
                continue
                
            # Get all carts for this user, ordered by most recent
            user_carts = Cart.objects.filter(user_id=user_id, is_active=True).order_by('-updated_at')
            
            # Keep the most recent cart
            main_cart = user_carts.first()
            duplicate_carts = user_carts[1:]
            
            # Move all items from duplicate carts to main cart
            for dup_cart in duplicate_carts:
                dup_items = CartItem.objects.filter(cart=dup_cart)
                items_moved = 0
                
                for dup_item in dup_items:
                    try:
                        # Check if item already exists in main cart
                        existing_item = CartItem.objects.get(
                            cart=main_cart,
                            product=dup_item.product,
                            user_id=user_id
                        )
                        # Merge quantities
                        existing_item.quantity += dup_item.quantity
                        existing_item.save()
                        dup_item.delete()
                        items_moved += 1
                    except CartItem.DoesNotExist:
                        # Move item to main cart
                        dup_item.cart = main_cart
                        dup_item.save()
                        items_moved += 1
                        
                self.stdout.write(f'  Moved {items_moved} items from cart {dup_cart.id} to {main_cart.id}')
                dup_cart.delete()
                consolidated += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully consolidated {consolidated} duplicate carts'))
