// Supabase client is already initialized in supabase.js

// Get product ID from URL
function getProductIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('id');
}

// Load product details from Supabase
async function loadProductDetails() {
    const productId = getProductIdFromUrl();
    if (!productId) {
        window.location.href = '/index.html';
        return;
    }

    try {
        // Show loading states
        document.getElementById('loadingSkeleton').classList.remove('hidden');
        document.getElementById('loadingText').classList.remove('hidden');
        document.getElementById('productImagesContainer').classList.add('hidden');
        document.getElementById('productInfo').classList.add('hidden');
        document.getElementById('priceSection').classList.add('hidden');
        document.getElementById('descriptionSection').classList.add('hidden');

        // Fetch product from Supabase
        const { data: product, error } = await supabase
            .from('products')
            .select('*')
            .eq('id', productId)
            .single();

        if (error || !product) {
            console.error('Error loading product:', error);
            window.location.href = '/index.html';
            return;
        }

        // Hide loading states
        document.getElementById('loadingSkeleton').classList.add('hidden');
        document.getElementById('loadingText').classList.add('hidden');
        document.getElementById('productImagesContainer').classList.remove('hidden');
        document.getElementById('productInfo').classList.remove('hidden');
        document.getElementById('priceSection').classList.remove('hidden');
        document.getElementById('descriptionSection').classList.remove('hidden');

        // Update the UI with product details
        document.getElementById('mainImage').src = product.image_url;
        document.getElementById('productName').textContent = product.name;
        document.getElementById('productCategory').textContent = product.category || 'General';
        document.getElementById('productPrice').textContent = `₦${product.price.toFixed(2)}`;
        document.getElementById('productDescription').textContent = product.description;
        
        // Handle optional fields
        if (product.original_price) {
            document.getElementById('originalPrice').textContent = `₦${product.original_price.toFixed(2)}`;
            const discount = Math.round(((product.original_price - product.price) / product.original_price) * 100);
            document.getElementById('discountBadge').textContent = `-${discount}%`;
        } else {
            document.getElementById('originalPrice').classList.add('hidden');
            document.getElementById('discountBadge').classList.add('hidden');
        }
        
        // Update page title
        document.title = `${product.name} - Eesha`;
        
        // Handle product images
        const thumbnailContainer = document.getElementById('thumbnailContainer');
        thumbnailContainer.innerHTML = ''; // Clear existing thumbnails
        
        // Add main image to thumbnails
        const mainThumbnail = createThumbnail(product.image_url, product.name, true);
        thumbnailContainer.appendChild(mainThumbnail);
        
        // Add additional images if available
        if (product.additional_images && Array.isArray(product.additional_images)) {
            product.additional_images.forEach(imgUrl => {
                const thumbnail = createThumbnail(imgUrl, product.name);
                thumbnailContainer.appendChild(thumbnail);
            });
        }

        // Handle rating if available
        if (product.rating) {
            const ratingDiv = document.getElementById('productRating');
            const stars = '★'.repeat(Math.floor(product.rating)) + '☆'.repeat(5 - Math.floor(product.rating));
            ratingDiv.innerHTML = `
                <div class="text-yellow-400">${stars}</div>
                <span class="text-gray-600">(${product.rating_count || 0} reviews)</span>
            `;
        }

    } catch (error) {
        console.error('Error loading product:', error);
        alert('Error loading product details. Please try again.');
    }
}

// Quantity management
let quantity = 1;

function increaseQty() {
    quantity++;
    updateQuantityDisplay();
}

function decreaseQty() {
    if (quantity > 1) {
        quantity--;
        updateQuantityDisplay();
    }
}

function updateQuantityDisplay() {
    document.getElementById('quantity').textContent = quantity;
}

// Add to cart functionality - Supabase ONLY (requires login)
async function addToCart() {
    const productId = getProductIdFromUrl();
    if (!productId) return;

    try {
        // Check if user is logged in
        const { data: { session } } = await supabase.auth.getSession();
        const user = session?.user;

        if (!user) {
            // Redirect to login
            if (confirm('Please login to add items to your cart. Go to login page?')) {
                window.location.href = `login.html?redirect=product&id=${productId}`;
            }
            return;
        }

        // Check if item already exists in cart
        const { data: existingItem, error: fetchError } = await supabase
            .from('cart_items')
            .select('*')
            .eq('user_id', user.id)
            .eq('product_id', productId)
            .single();

        if (fetchError && fetchError.code !== 'PGRST116') {
            throw fetchError;
        }

        if (existingItem) {
            // Update quantity
            const { error: updateError } = await supabase
                .from('cart_items')
                .update({ quantity: existingItem.quantity + quantity })
                .eq('id', existingItem.id);
            if (updateError) throw updateError;
        } else {
            // Insert new item
            const { error: insertError } = await supabase
                .from('cart_items')
                .insert([{ user_id: user.id, product_id: productId, quantity }]);
            if (insertError) throw insertError;
        }

        // Update cart count UI using shared Cart module
        if (window.Cart) {
            await window.Cart.updateCartCountUI();
        } else {
            await updateCartCount();
        }

        // Visual feedback
        const addBtn = document.querySelector('button[onclick="addToCart()"]');
        if (addBtn) {
            const orig = addBtn.innerHTML;
            addBtn.innerHTML = '<i class="fas fa-check"></i> Added!';
            addBtn.classList.add('bg-green-500');
            setTimeout(() => {
                addBtn.innerHTML = orig;
                addBtn.classList.remove('bg-green-500');
            }, 1500);
        }

    } catch (error) {
        console.error('Add to cart failed:', error);
        alert('Failed to add to cart. Please try again.');
    }
}

// Update cart count in header - Supabase ONLY
async function updateCartCount() {
    try {
        const { data: { session } } = await supabase.auth.getSession();
        const user = session?.user;
        
        let total = 0;

        if (user) {
            const { data: cartItems, error } = await supabase
                .from('cart_items')
                .select('quantity')
                .eq('user_id', user.id);
            if (!error && Array.isArray(cartItems)) {
                total = cartItems.reduce((s, it) => s + (it.quantity || 0), 0);
            }
        }

        const cartCountEl = document.getElementById('cartCount');
        if (cartCountEl) {
            cartCountEl.textContent = total;
            cartCountEl.style.display = total > 0 ? 'flex' : 'none';
        }
    } catch (err) {
        console.error('Error updating cart count:', err);
    }
}

// Image gallery functionality
function createThumbnail(imageUrl, altText, isActive = false) {
    const div = document.createElement('div');
    div.className = `cursor-pointer rounded-lg overflow-hidden border-2 ${isActive ? 'border-brand-500' : 'border-transparent'}`;
    
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = altText;
    img.className = 'w-full h-full object-cover aspect-square';
    
    div.appendChild(img);
    
    div.addEventListener('click', () => {
        // Update main image
        updateMainImage(imageUrl);
        
        // Update active state of thumbnails
        document.querySelectorAll('#thumbnailContainer > div').forEach(thumb => {
            thumb.classList.remove('border-brand-500');
            thumb.classList.add('border-transparent');
        });
        div.classList.remove('border-transparent');
        div.classList.add('border-brand-500');
    });
    
    return div;
}

function updateMainImage(imageUrl) {
    const mainImage = document.getElementById('mainImage');
    mainImage.src = imageUrl;
}

// Global user state
let currentUser = null;

// Merge guest cart into user cart after sign-in
async function mergeGuestCartAfterSignIn(user) {
    try {
        const guestCart = JSON.parse(localStorage.getItem('cart') || '[]');
        if (!guestCart || guestCart.length === 0) return;

        for (const item of guestCart) {
            const { data: existingItem, error: fetchError } = await supabase
                .from('cart_items')
                .select('*')
                .eq('user_id', user.id)
                .eq('product_id', item.productId)
                .single();

            if (fetchError && fetchError.code !== 'PGRST116') {
                console.error('Error checking existing cart item:', fetchError);
                continue;
            }

            if (existingItem) {
                const { error: updateError } = await supabase
                    .from('cart_items')
                    .update({ quantity: existingItem.quantity + item.quantity })
                    .eq('id', existingItem.id);
                if (updateError) console.error('Error updating existing cart item:', updateError);
            } else {
                const { error: insertError } = await supabase
                    .from('cart_items')
                    .insert([{ user_id: user.id, product_id: item.productId, quantity: item.quantity }]);
                if (insertError) console.error('Error inserting guest cart item:', insertError);
            }
        }

        // Clear canonical cart and refresh count
        localStorage.removeItem('cart');
        await updateCartCount();
    } catch (err) {
        console.error('Error merging guest cart:', err);
    }
}

function updateUIforAuthState(user) {
    const loginLink = document.getElementById('login-link');
    const signupLink = document.getElementById('signup-link');
    const userMenu = document.getElementById('user-menu');
    const userEmail = document.getElementById('user-email');
    const mobileLogin = document.querySelector('#mobile-auth-links a[href="login.html"]') || document.querySelector('#mobile-auth-links a[href="Eesha buying folder/login.html"]');
    const mobileSignup = document.querySelector('#mobile-auth-links a[href="signup.html"]') || document.querySelector('#mobile-auth-links a[href="Eesha buying folder/signup.html"]');
    const mobileLogout = document.getElementById('mobile-logout-button');

    if (user) {
        if (loginLink) loginLink.style.display = 'none';
        if (signupLink) signupLink.style.display = 'none';
        if (userMenu) userMenu.style.display = 'block';
        if (userEmail) userEmail.textContent = user.email || '';
        if (mobileLogin) mobileLogin.style.display = 'none';
        if (mobileSignup) mobileSignup.style.display = 'none';
        if (mobileLogout) mobileLogout.style.display = 'block';
    } else {
        if (loginLink) loginLink.style.display = 'block';
        if (signupLink) signupLink.style.display = 'block';
        if (userMenu) userMenu.style.display = 'none';
        if (mobileLogin) mobileLogin.style.display = 'block';
        if (mobileSignup) mobileSignup.style.display = 'block';
        if (mobileLogout) mobileLogout.style.display = 'none';
    }
}

// Initialize page and auth handling
document.addEventListener('DOMContentLoaded', async () => {
    // Setup auth state listener
    try {
        const { data: { session } } = await supabase.auth.getSession();
        currentUser = session?.user || null;
        updateUIforAuthState(currentUser);
        await updateCartCount();
    } catch (err) {
        console.error('Error checking initial session:', err);
    }

    supabase.auth.onAuthStateChange(async (event, session) => {
        console.log('Auth event:', event);
        currentUser = session?.user || null;
        updateUIforAuthState(currentUser);

        if (event === 'SIGNED_IN' && session?.user) {
            // Merge guest cart into user cart on sign in
            await mergeGuestCartAfterSignIn(session.user);
        }
        await updateCartCount();
    });

    // Wire up logout buttons if present
    const logoutButton = document.getElementById('logout-button');
    const mobileLogoutButton = document.getElementById('mobile-logout-button');
    if (logoutButton) logoutButton.addEventListener('click', async (e) => { e.preventDefault(); await supabase.auth.signOut(); });
    if (mobileLogoutButton) mobileLogoutButton.addEventListener('click', async (e) => { e.preventDefault(); await supabase.auth.signOut(); });

    // User menu toggle
    const userMenuButton = document.getElementById('user-menu-button');
    const userMenuDropdown = document.getElementById('user-menu-dropdown');
    if (userMenuButton && userMenuDropdown) {
        userMenuButton.addEventListener('click', () => userMenuDropdown.classList.toggle('hidden'));
        document.addEventListener('click', (e) => {
            if (!document.getElementById('user-menu').contains(e.target)) {
                userMenuDropdown.classList.add('hidden');
            }
        });
    }

    // Mobile menu
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenuBtn && mobileMenu) mobileMenuBtn.addEventListener('click', () => mobileMenu.classList.toggle('hidden'));

    // Finally load product details and update cart count
    await loadProductDetails();
    await updateCartCount();
});

// Search bar behavior (navigate to search-result.html with query)
(function setupSearch() {
    try {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;

        const goToSearch = () => {
            const q = (searchInput.value || '').trim();
            if (!q) return;
            // keep relative path consistent with index/product location
            window.location.href = `../search-result.html?q=${encodeURIComponent(q)}`;
        };

        // Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') goToSearch();
        });

        // If there's an adjacent button (search icon) try to attach click
        const btn = searchInput.parentElement?.querySelector('button');
        if (btn) btn.addEventListener('click', goToSearch);
    } catch (err) {
        console.error('Search setup failed:', err);
    }
})();