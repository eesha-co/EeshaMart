// Storage configuration for Supabase
const STORAGE_BUCKET = 'profiles';

// Function to ensure storage bucket exists
async function ensureStorageBucket() {
    try {
        // Check if we can access the bucket
        const { data: files, error: testError } = await window.supabase.storage
            .from(STORAGE_BUCKET)
            .list();

        if (testError) {
            console.error('Storage access error:', testError.message);
            return false;
        }

        return true;
    } catch (error) {
        console.error('Storage configuration error:', error.message);
        return false;
    }
}

// Export the bucket name and configuration function
window.STORAGE_BUCKET = STORAGE_BUCKET;
window.ensureStorageBucket = ensureStorageBucket;