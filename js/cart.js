/**
 * EeshaMart Shared Cart Module
 * ------------------------------------------
 * All cart operations use Supabase ONLY - NO localStorage
 * 
 * Usage:
 * 1. Include supabase.js and config/supabase.js first
 * 2. Include this file: <script src="/js/cart.js"></script>
 * 3. Use window.Cart functions for all cart operations
 */

(function() {
    'use strict';

    const supabaseClient = () => window.supabaseClient || window.supabase;

    // Get current user session
    async function getCurrentUser() {
        const client = supabaseClient();
        if (!client) {
            console.error('[Cart] Supabase client not initialized');
            return null;
        }
        
        try {
            const { data, error } = await client.auth.getSession();
            if (error) {
                console.error('[Cart] Error getting session:', error);
                return null;
            }
            console.log('[Cart] Session check:', data.session ? `User: ${data.session.user.id}` : 'No session');
            return data.session?.user || null;
        } catch (e) {
            console.error('[Cart] Exception in getCurrentUser:', e);
            return null;
        }
    }

    /**
     * Get total cart items count for current user
     * Returns the SUM of all quantities in the cart
     */
    async function getCartCount() {
        const client = supabaseClient();
        if (!client) return 0;

        const user = await getCurrentUser();
        if (!user) return 0;

        try {
            const { data: cartItems, error } = await client
                .from('cart_items')
                .select('quantity')
                .eq('user_id', user.id);

            if (error) {
                console.error('Error fetching cart count:', error);
                return 0;
            }

            // Sum up all quantities
            const totalCount = cartItems?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0;
            return totalCount;
        } catch (err) {
            console.error('Error getting cart count:', err);
            return 0;
        }
    }

    /**
     * Update all cart count elements on the page
     * Call this after any cart operation
     */
    async function updateCartCountUI() {
        const count = await getCartCount();
        
        // Update all cart count elements by common IDs
        const cartCountEl = document.getElementById('cartCount');
        const mobileCartCountEl = document.getElementById('mobileCartCount');
        
        if (cartCountEl) {
            cartCountEl.textContent = count;
            cartCountEl.style.display = count > 0 ? 'flex' : 'none';
        }
        
        if (mobileCartCountEl) {
            mobileCartCountEl.textContent = count;
            mobileCartCountEl.style.display = count > 0 ? 'flex' : 'none';
        }

        return count;
    }

    /**
     * Get all cart items with product details
     */
    async function getCartItems() {
        const client = supabaseClient();
        if (!client) {
            console.error('[Cart] getCartItems: No client');
            return [];
        }

        const user = await getCurrentUser();
        if (!user) {
            console.log('[Cart] getCartItems: No user logged in');
            return [];
        }
        
        console.log('[Cart] getCartItems: Fetching for user', user.id);

        try {
            // Use simpler select like cart.html does - this works!
            const { data: cartItems, error } = await client
                .from('cart_items')
                .select('id, quantity, product_id, products(*)')
                .eq('user_id', user.id);

            if (error) {
                console.error('[Cart] Error fetching cart items:', error);
                return [];
            }
            
            console.log('[Cart] getCartItems: Found', cartItems?.length || 0, 'items');
            return cartItems || [];
        } catch (err) {
            console.error('[Cart] Error getting cart items:', err);
            return [];
        }
    }

    /**
     * Add item to cart (requires user to be logged in)
     * Returns: { success: boolean, message: string }
     */
    async function addToCart(productId, quantity = 1) {
        const client = supabaseClient();
        
        const user = await getCurrentUser();
        if (!user) {
            return { 
                success: false, 
                requiresAuth: true,
                message: 'Please login to add items to cart' 
            };
        }

        try {
            // Check if item already exists in cart
            const { data: existingItem, error: checkError } = await client
                .from('cart_items')
                .select('id, quantity')
                .eq('user_id', user.id)
                .eq('product_id', productId)
                .single();

            if (existingItem) {
                // Update quantity
                const newQuantity = existingItem.quantity + quantity;
                const { error: updateError } = await client
                    .from('cart_items')
                    .update({ quantity: newQuantity })
                    .eq('id', existingItem.id);

                if (updateError) {
                    console.error('Error updating cart item:', updateError);
                    return { success: false, message: 'Failed to update cart' };
                }
            } else {
                // Insert new item
                const { error: insertError } = await client
                    .from('cart_items')
                    .insert({
                        user_id: user.id,
                        product_id: productId,
                        quantity: quantity
                    });

                if (insertError) {
                    console.error('Error adding to cart:', insertError);
                    return { success: false, message: 'Failed to add to cart' };
                }
            }

            // Update UI
            await updateCartCountUI();

            return { 
                success: true, 
                message: 'Added to cart!' 
            };
        } catch (err) {
            console.error('Error adding to cart:', err);
            return { success: false, message: 'An error occurred' };
        }
    }

    /**
     * Remove item from cart
     */
    async function removeFromCart(cartItemId) {
        const client = supabaseClient();
        
        const user = await getCurrentUser();
        if (!user) {
            return { success: false, message: 'Please login' };
        }

        try {
            const { error } = await client
                .from('cart_items')
                .delete()
                .eq('id', cartItemId)
                .eq('user_id', user.id);

            if (error) {
                console.error('Error removing from cart:', error);
                return { success: false, message: 'Failed to remove item' };
            }

            // Update UI
            await updateCartCountUI();

            return { success: true, message: 'Item removed' };
        } catch (err) {
            console.error('Error removing from cart:', err);
            return { success: false, message: 'An error occurred' };
        }
    }

    /**
     * Update item quantity in cart
     */
    async function updateQuantity(cartItemId, newQuantity) {
        const client = supabaseClient();
        
        const user = await getCurrentUser();
        if (!user) {
            return { success: false, message: 'Please login' };
        }

        if (newQuantity < 1) {
            // Remove item if quantity is 0
            return await removeFromCart(cartItemId);
        }

        try {
            const { error } = await client
                .from('cart_items')
                .update({ quantity: newQuantity })
                .eq('id', cartItemId)
                .eq('user_id', user.id);

            if (error) {
                console.error('Error updating quantity:', error);
                return { success: false, message: 'Failed to update quantity' };
            }

            // Update UI
            await updateCartCountUI();

            return { success: true, message: 'Quantity updated' };
        } catch (err) {
            console.error('Error updating quantity:', err);
            return { success: false, message: 'An error occurred' };
        }
    }

    /**
     * Clear entire cart
     */
    async function clearCart() {
        const client = supabaseClient();
        
        const user = await getCurrentUser();
        if (!user) {
            return { success: false, message: 'Please login' };
        }

        try {
            const { error } = await client
                .from('cart_items')
                .delete()
                .eq('user_id', user.id);

            if (error) {
                console.error('Error clearing cart:', error);
                return { success: false, message: 'Failed to clear cart' };
            }

            // Update UI
            await updateCartCountUI();

            return { success: true, message: 'Cart cleared' };
        } catch (err) {
            console.error('Error clearing cart:', err);
            return { success: false, message: 'An error occurred' };
        }
    }

    /**
     * Get cart subtotal
     */
    async function getCartSubtotal() {
        const cartItems = await getCartItems();
        return cartItems.reduce((sum, item) => {
            const price = item.products?.price || 0;
            return sum + (price * (item.quantity || 0));
        }, 0);
    }

    /**
     * Initialize cart on page load
     * Call this in DOMContentLoaded
     */
    async function initCart() {
        await updateCartCountUI();
    }

    // Expose Cart module globally
    window.Cart = {
        getCartCount,
        updateCartCountUI,
        getCartItems,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        getCartSubtotal,
        initCart,
        getCurrentUser
    };

    // Auto-initialize on DOMContentLoaded if user is logged in
    document.addEventListener('DOMContentLoaded', async () => {
        // Wait a bit for supabase to initialize
        setTimeout(async () => {
            await initCart();
        }, 100);
    });

})();
