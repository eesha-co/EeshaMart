// Check if user is authenticated and has a seller profile
async function protectSellerRoute() {
    try {
        // Ensure supabase client exists
        if (typeof window.supabase === 'undefined') {
            console.error('Supabase client not found');
            window.location.href = 'login.html';
            return;
        }

        // Get the current session
        const { data: { session }, error: sessionError } = await window.supabase.auth.getSession();
        
        if (sessionError) {
            console.error('Session error:', sessionError);
            window.location.href = 'login.html';
            return;
        }

        if (!session) {
            console.log('No active session found');
            window.location.href = 'login.html';
            return;
        }

        const user = session.user;

        // Check if seller profile exists
        const { data: seller, error: sellerError } = await window.supabase
            .from('sellers')
            .select('*')
            .eq('id', user.id)
            .single();

        if (sellerError && sellerError.code !== 'PGRST116') {
            console.error('Error checking seller profile:', sellerError);
        }

        // If no seller profile exists, create one
        if (!seller) {
            // Determine a sensible default business name from user metadata or email
            const defaultBusinessName = user.user_metadata?.full_name || (user.email ? user.email.split('@')[0] : null);
            const { data: newSeller, error: createError } = await window.supabase
                .from('sellers')
                .insert([{
                    id: user.id,
                    email: user.email,
                    business_name: defaultBusinessName,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                }])
                .select()
                .single();

            if (createError) {
                console.error('Error creating seller profile:', createError);
                // Only redirect to signup if we couldn't create the profile
                window.location.href = 'signup.html';
                return;
            }

            return { user, seller: newSeller };
        }

        return { user, seller };
    } catch (error) {
        console.error('Protection error:', error);
        window.location.href = 'login.html';
        return;
    }
}

// Run protection on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const result = await protectSellerRoute();
        if (result) {
            // Store user info in localStorage for easy access
            localStorage.setItem('seller_user', JSON.stringify(result.user));
            localStorage.setItem('seller_profile', JSON.stringify(result.seller));
            
            // Dispatch event that authentication is complete
            const event = new CustomEvent('authComplete', { detail: result });
            document.dispatchEvent(event);
        }
    } finally {
        // Hide loader only after everything is done
        if (typeof hideLoader === 'function') {
            hideLoader();
        }
    }
});