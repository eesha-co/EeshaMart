// Shared navbar loader with user data handling
async function loadNavbarWithUserData() {
    try {
        const container = document.getElementById('navbar-container');
        if (!container) {
            console.error('Navbar container not found');
            return;
        }

        // Load navbar HTML
        const navbarPromise = fetch('../shared/navbar.html').then(response => response.text());
        const html = await trackRequest(navbarPromise, {
            type: 'navbar',
            description: 'Loading navigation'
        });
        container.innerHTML = html;

        // Get user data
        const userPromise = window.supabase.auth.getUser();
        const { data: { user } } = await trackRequest(userPromise, {
            type: 'auth',
            description: 'Verifying authentication'
        });

        if (!user) {
            window.location.href = 'login.html';
            return;
        }

        // Load seller data
        const sellerPromise = window.supabase
            .from('sellers')
            .select('*')
            .eq('id', user.id)
            .single();

        const { data: seller, error } = await trackRequest(sellerPromise, {
            type: 'data',
            description: 'Loading seller profile'
        });

        if (error) {
            console.error('Error loading seller data:', error);
            throw error;
        }

        // Update UI elements
        if (seller) {
            // Update profile image if it exists
            const profileImage = document.getElementById('profileImage');
            if (profileImage) {
                profileImage.src = seller.profile_image || `https://ui-avatars.com/api/?name=${encodeURIComponent(seller.business_name)}`;
                profileImage.alt = seller.business_name;
            }

            // Update business name if element exists
            const businessName = document.getElementById('businessName');
            if (businessName) {
                businessName.textContent = seller.business_name || 'My Business';
            }

            // Update seller email if element exists
            const sellerEmail = document.getElementById('sellerEmail');
            if (sellerEmail) {
                sellerEmail.textContent = user.email;
            }
        }

        // Initialize any navbar-specific event listeners
        await initializeNavbarEvents();

        return { user, seller };
    } catch (error) {
        console.error('Error in loadNavbarWithUserData:', error);
        showError('Failed to load user data');
        throw error;
    }
}

async function initializeNavbarEvents() {
    // Profile dropdown toggle
    const profileBtn = document.getElementById('profileBtn');
    const dropdownMenu = document.getElementById('dropdownMenu');

    if (profileBtn && dropdownMenu) {
        profileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            dropdownMenu.classList.add('hidden');
        });
    }

    // Load and handle notifications
    if (window.supabase) {
        const notificationsPromise = window.supabase
            .from('notifications')
            .select('*', { count: 'exact' })
            .eq('seller_id', (await window.supabase.auth.getUser()).data.user.id)
            .eq('read', false);

        const { count, error } = await trackRequest(notificationsPromise, {
            type: 'notifications',
            description: 'Loading notifications'
        });

        if (!error) {
            const badge = document.getElementById('notificationCount');
            if (badge) {
                badge.textContent = count || 0;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        }
    }

    // Logout handler
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                const logoutPromise = window.supabase.auth.signOut();
                await trackRequest(logoutPromise, {
                    type: 'auth',
                    description: 'Signing out'
                });
                window.location.href = 'login.html';
            } catch (error) {
                console.error('Error signing out:', error);
            }
        });
    }
}

function showError(message) {
    // You can implement custom error display logic here
    console.error(message);
    alert(message);
}

// Export the loader function
window.loadNavbarWithUserData = loadNavbarWithUserData;
