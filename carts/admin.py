from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('price_at_addition', 'stock_at_addition', 'created_at', 'updated_at', 'stock_status')
    fields = ('product', 'variations', 'quantity', 'price_at_addition', 'stock_at_addition', 
              'stock_status', 'is_active', 'is_available')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart_id', 'user', 'get_total_items', 'is_active', 'date_added', 'updated_at')
    list_filter = ('is_active', 'date_added', 'updated_at')
    search_fields = ('cart_id', 'user__email', 'user__username')
    readonly_fields = ('date_added', 'updated_at', 'get_total_items', 'get_cart_total')
    inlines = [CartItemInline]
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Total Items'
    
    def get_cart_total(self, obj):
        return f"${obj.get_cart_total():.2f}"
    get_cart_total.short_description = 'Cart Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'cart', 'quantity', 'price_at_addition', 
                    'stock_status', 'is_active', 'is_available', 'created_at')
    list_filter = ('stock_status', 'is_active', 'is_available', 'created_at')
    search_fields = ('product__product_name', 'user__email', 'cart__cart_id')
    readonly_fields = ('price_at_addition', 'stock_at_addition', 'created_at', 'updated_at', 
                       'stock_status', 'get_stock_message', 'sub_total')
    filter_horizontal = ('variations',)
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product', 'variations', 'quantity')
        }),
        ('Cart & User', {
            'fields': ('cart', 'user')
        }),
        ('Price & Stock Snapshots', {
            'fields': ('price_at_addition', 'stock_at_addition', 'sub_total'),
            'classes': ('collapse',)
        }),
        ('Stock Status', {
            'fields': ('stock_status', 'get_stock_message', 'is_available')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_stock_message(self, obj):
        return obj.get_stock_message()
    get_stock_message.short_description = 'Stock Message'
    
    def sub_total(self, obj):
        return f"${obj.sub_total():.2f}"
    sub_total.short_description = 'Subtotal'
    
    actions = ['check_stock_for_selected']
    
    def check_stock_for_selected(self, request, queryset):
        """Admin action to check stock for selected items"""
        updated = 0
        for item in queryset:
            if item.check_stock_availability():
                item.save()
                updated += 1
        self.message_user(request, f'{updated} items updated with current stock status.')
    check_stock_for_selected.short_description = 'Check stock availability'
