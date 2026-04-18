// Use the centralized Supabase client created in js/config/supabase.js

// Check authentication status
async function checkAuth() {
    const { data: { user } } = await window.supabase.auth.getUser();
    if (!user) {
        // Redirect to login if not authenticated
        window.location.href = 'login.html';
        return null;
    }
    return user;
}

// Create seller profile after registration
async function createSellerProfile(userId) {
    const { data, error } = await window.supabase
        .from('sellers')
        .insert([
            {
                id: userId,
                created_at: new Date().toISOString(),
                status: 'active'
            }
        ]);

    if (error) {
        console.error('Error creating seller profile:', error);
        throw error;
    }
    return data;
}

// Protect seller routes
async function protectSellerRoute() {
    const user = await checkAuth();
    if (!user) return;

    // Check if seller profile exists
    const { data: seller, error } = await supabase
        .from('sellers')
        .select('*')
        .eq('id', user.id)
        .single();

    if (error || !seller) {
        // Redirect to signup if no seller profile exists
        window.location.href = 'signup.html';
        return;
    }

    return user;
}

// Initialize protection on seller pages
if (!window.location.pathname.includes('signup.html') && 
    !window.location.pathname.includes('login.html')) {
    protectSellerRoute();
}