// shared/navbar.js
// Navbar runtime: exposes window.initSellerNavbar() which pages call after inserting navbar HTML
(function () {
    window.initSellerNavbar = async function initSellerNavbar() {
        // Set active tab based on current page
        const currentPage = window.location.pathname.split('/').pop().split('.')[0];
        const tabs = document.querySelectorAll('.nav-tab');
        tabs.forEach(tab => {
            if (tab.dataset.page === currentPage) {
                tab.classList.add('active');
            }
        });

        // Profile Dropdown Toggle
        const profileBtn = document.getElementById('profileBtn');
        const dropdownMenu = document.getElementById('dropdownMenu');

        profileBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            dropdownMenu?.classList.add('hidden');
        });

        // Fetch Seller Info
        async function loadSellerInfo() {
            // Ensure supabase client exists
            if (!window.supabase) return;
            const { data: { user } } = await window.supabase.auth.getUser();
            if (!user) return;

            const { data: seller, error } = await window.supabase
                .from('sellers')
                .select('*')
                .eq('id', user.id)
                .single();

            if (error) {
                console.error('Error loading seller:', error);
                return;
            }

            if (seller) {
                const businessNameEl = document.getElementById('businessName');
                const sellerEmailEl = document.getElementById('sellerEmail');
                const profileImageEl = document.getElementById('profileImage');
                if (businessNameEl) businessNameEl.textContent = seller.business_name || 'My Business';
                if (sellerEmailEl) sellerEmailEl.textContent = (user && user.email) || '';
                if (profileImageEl) profileImageEl.src = seller.profile_image || 
                    `https://ui-avatars.com/api/?name=${encodeURIComponent(seller.business_name)}`;
            }
        }

        // Helper: show a small error banner near the navbar if something fails
        function showNavbarError(message) {
            try {
                let banner = document.getElementById('navbarErrorBanner');
                if (!banner) {
                    banner = document.createElement('div');
                    banner.id = 'navbarErrorBanner';
                    banner.style.position = 'fixed';
                    banner.style.top = '76px';
                    banner.style.right = '16px';
                    banner.style.zIndex = '60';
                    banner.style.background = '#fff3f2';
                    banner.style.color = '#6b1e1e';
                    banner.style.border = '1px solid #f5c6cb';
                    banner.style.padding = '8px 12px';
                    banner.style.borderRadius = '6px';
                    banner.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)';
                    document.body.appendChild(banner);
                }
                banner.textContent = message;
                // auto-hide after 6s
                setTimeout(() => { if (banner) banner.remove(); }, 6000);
            } catch (e) {
                console.warn('Could not show navbar error banner', e);
            }
        }

        // Load notifications count
        async function loadNotifications() {
            if (!window.supabase) return;
            try {
                const { data: { user } } = await window.supabase.auth.getUser();
                if (!user) return;

                const { count, error } = await window.supabase
                    .from('notifications')
                    .select('*', { count: 'exact' })
                    .eq('seller_id', user.id)
                    .eq('read', false);

                if (error) {
                    console.error('Error loading notification count:', error);
                    showNavbarError('Notifications unavailable: ' + (error.message || error.code || 'server error'));
                    return;
                }

                const badge = document.getElementById('notificationCount');
                if (badge) {
                    badge.textContent = count || 0;
                    badge.style.display = count > 0 ? 'flex' : 'none';
                }
            } catch (err) {
                console.error('Error loading notification count (unexpected):', err);
                showNavbarError('Notifications error');
            }
        }

        // Logout functionality
        document.getElementById('logoutBtn')?.addEventListener('click', async () => {
            if (!window.supabase) return;
            const { error } = await window.supabase.auth.signOut();
            if (!error) {
                window.location.href = 'login.html';
            }
        });

        // Run initial loads
        try {
            await loadSellerInfo();
            await loadNotifications();
        } catch (err) {
            console.error('Error initializing navbar:', err);
        }

        // Listen for notification updates (if supabase real-time is available)
        if (window.supabase && window.supabase.channel) {
            try {
                window.supabase
                    .channel('notifications')
                    .on('postgres_changes', { 
                        event: '*', 
                        schema: 'public', 
                        table: 'notifications' 
                    }, loadNotifications)
                    .subscribe();
            } catch (err) {
                console.warn('Realtime subscription failed:', err);
            }
        }
    };
})();
