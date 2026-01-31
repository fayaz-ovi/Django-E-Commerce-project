from django.db import models
from django.conf import settings
from store.models import Product, Variation
from django.core.validators import MinValueValidator

# Create your models here.
class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.email}"
        return f"Cart {self.cart_id}"
    
    def get_total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.cartitem_set.filter(is_active=True))
    
    def get_cart_total(self):
        """Get total price of all items in cart"""
        return sum(item.sub_total() for item in self.cartitem_set.filter(is_active=True))
    

class CartItem(models.Model):
    # Foreign Keys
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    variations = models.ManyToManyField(Variation, blank=True)
    
    # Item Details
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_at_addition = models.IntegerField(null=True, blank=True)
    
    # Status and Tracking
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    
    # Stock Warnings
    OUT_OF_STOCK = 'out_of_stock'
    INSUFFICIENT_STOCK = 'insufficient_stock'
    AVAILABLE = 'available'
    
    STOCK_STATUS_CHOICES = [
        (OUT_OF_STOCK, 'Out of Stock'),
        (INSUFFICIENT_STOCK, 'Insufficient Stock'),
        (AVAILABLE, 'Available'),
    ]
    stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default=AVAILABLE)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = [['cart', 'product', 'user']]

    def sub_total(self):
        """Calculate subtotal for this cart item"""
        return self.product.price * self.quantity
    
    def check_stock_availability(self):
        """Check and update stock status based on current inventory"""
        current_stock = self.product.stock
        
        if current_stock == 0:
            self.stock_status = self.OUT_OF_STOCK
            self.is_available = False
            return False
        elif self.quantity > current_stock:
            self.stock_status = self.INSUFFICIENT_STOCK
            self.is_available = True
            return False
        else:
            self.stock_status = self.AVAILABLE
            self.is_available = True
            return True
    
    def get_stock_message(self):
        """Get user-friendly stock status message"""
        if self.stock_status == self.OUT_OF_STOCK:
            return "Out of Stock"
        elif self.stock_status == self.INSUFFICIENT_STOCK:
            return f"Not enough in stock. Only {self.product.stock} available."
        return "In Stock"
    
    def adjust_quantity_to_stock(self):
        """Adjust quantity to match available stock"""
        current_stock = self.product.stock
        if self.quantity > current_stock and current_stock > 0:
            self.quantity = current_stock
            self.save()
            return True
        return False
    
    def update_price_snapshot(self):
        """Update price snapshot to current product price"""
        self.price_at_addition = self.product.price
        self.save()
    
    def update_stock_snapshot(self):
        """Update stock snapshot to current product stock"""
        self.stock_at_addition = self.product.stock
        self.save()
    
    def get_variations_display(self):
        """Get formatted string of all variations"""
        return ", ".join([f"{v.variation_category}: {v.variation_value}" for v in self.variations.all()])

    def __str__(self):
        user_info = self.user.email if self.user else "Anonymous"
        return f"{self.product.product_name} x{self.quantity} - {user_info}"
    
    def save(self, *args, **kwargs):
        """Override save to update snapshots and check stock"""
        # Save price and stock snapshots on creation
        if not self.pk:
            self.price_at_addition = self.product.price
            self.stock_at_addition = self.product.stock
        
        # Check stock availability before saving
        self.check_stock_availability()
        
        super().save(*args, **kwargs)