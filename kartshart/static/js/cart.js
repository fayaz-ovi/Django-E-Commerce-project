// Cart management with localStorage and stock validation

// Initialize cart from localStorage or create empty cart
function getCart() {
    const cart = localStorage.getItem('cart');
    return cart ? JSON.parse(cart) : {};
}

// Save cart to localStorage
function saveCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
}

// Add product to cart
function addToCart(productId, productName, price, maxStock) {
    const cart = getCart();
    
    if (!cart[productId]) {
        cart[productId] = {
            id: productId,
            name: productName,
            price: price,
            quantity: 1,
            maxStock: maxStock
        };
    } else {
        if (cart[productId].quantity < maxStock) {
            cart[productId].quantity += 1;
        } else {
            showMessage('Cannot add more items. Stock limit reached.', 'warning');
            return false;
        }
    }
    
    saveCart(cart);
    return true;
}

// Update cart item quantity
function updateCartQuantity(productId, quantity, maxStock) {
    const cart = getCart();
    
    if (cart[productId]) {
        if (quantity <= 0) {
            delete cart[productId];
        } else if (quantity <= maxStock) {
            cart[productId].quantity = quantity;
            cart[productId].maxStock = maxStock;
        } else {
            showMessage('Cannot add more items. Stock limit reached.', 'warning');
            return false;
        }
    }
    
    saveCart(cart);
    return true;
}

// Remove product from cart
function removeFromCart(productId) {
    const cart = getCart();
    
    if (cart[productId]) {
        delete cart[productId];
        saveCart(cart);
    }
}

// Decrease quantity
function decreaseQuantity(productId) {
    const cart = getCart();
    
    if (cart[productId]) {
        if (cart[productId].quantity > 1) {
            cart[productId].quantity -= 1;
        } else {
            delete cart[productId];
        }
        saveCart(cart);
    }
}

// Get cart item count
function getCartItemCount() {
    const cart = getCart();
    let count = 0;
    
    for (let productId in cart) {
        count += cart[productId].quantity;
    }
    
    return count;
}

// Check stock availability for all cart items
function validateCartStock(stockData) {
    const cart = getCart();
    const warnings = {};
    let hasChanges = false;
    
    for (let productId in cart) {
        const cartItem = cart[productId];
        const stock = stockData[productId] || 0;
        
        if (stock === 0) {
            warnings[productId] = {
                type: 'out_of_stock',
                message: 'Out of Stock',
                stock: 0
            };
            // Remove item from cart if out of stock
            delete cart[productId];
            hasChanges = true;
        } else if (cartItem.quantity > stock) {
            warnings[productId] = {
                type: 'insufficient_stock',
                message: `Not enough in stock. Only ${stock} available.`,
                stock: stock
            };
            // Adjust quantity to match available stock
            cart[productId].quantity = stock;
            cart[productId].maxStock = stock;
            hasChanges = true;
        } else {
            // Update max stock for valid items
            cart[productId].maxStock = stock;
        }
    }
    
    if (hasChanges) {
        saveCart(cart);
    }
    
    return warnings;
}

// Clear entire cart
function clearCart() {
    localStorage.removeItem('cart');
}

// Sync cart with backend
function syncCartWithBackend(stockData) {
    const warnings = validateCartStock(stockData);
    return warnings;
}

// Display message to user
function showMessage(message, type = 'info') {
    // Create alert div
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="span">&times;</span>
        </button>
    `;
    
    // Insert at top of content
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

// Update cart display on page
function updateCartDisplay() {
    const cart = getCart();
    const cartCount = getCartItemCount();
    
    // Update cart count badge if exists
    const cartBadge = document.querySelector('.badge-pill');
    if (cartBadge) {
        cartBadge.textContent = cartCount;
    }
}

// Initialize cart on page load
document.addEventListener('DOMContentLoaded', function() {
    updateCartDisplay();
});
