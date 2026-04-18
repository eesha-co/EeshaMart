// Manage pending requests and loading states
const LoaderManager = {
    pendingRequests: new Map(), // Maps requestId to { promise, description, type }
    loaderStack: [], // Stack of loader states for proper nesting

    createLoader() {
        // Do not create a new loader if one already exists (keeps compatibility with pages that inline it)
        const existing = document.getElementById('loader') || document.getElementById('pageLoader');
        if (existing) return existing;

        const loader = document.createElement('div');
        loader.id = 'loader';
        loader.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex flex-col items-center justify-center z-50';
        loader.innerHTML = `
            <div class="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-primary mb-4"></div>
            <div class="text-white text-lg mb-2" id="loaderStatus">Loading...</div>
            <div class="text-white text-sm" id="loaderProgress"></div>
        `;
        document.body.appendChild(loader);
        return loader;
    },

    updateLoaderStatus() {
        const statusEl = document.getElementById('loaderStatus');
        const progressEl = document.getElementById('loaderProgress');
        if (!statusEl || !progressEl) return;

        // Group pending requests by type
        const requests = Array.from(this.pendingRequests.values());
        const byType = requests.reduce((acc, req) => {
            if (!acc[req.type]) acc[req.type] = [];
            acc[req.type].push(req);
            return acc;
        }, {});

        if (requests.length === 0) {
            statusEl.textContent = 'Loading...';
            progressEl.textContent = '';
            return;
        }

        // Show summary of pending requests
        const summary = Object.entries(byType)
            .map(([type, reqs]) => `${reqs.length} ${type}`)
            .join(', ');
        statusEl.textContent = `Loading ${summary}...`;

        // Show descriptions of current requests
        const descriptions = requests
            .filter(req => req.description)
            .map(req => req.description);
        progressEl.textContent = descriptions.length ? descriptions.join(', ') : '';
    },

    showLoader() {
        const loader = document.getElementById('loader') || document.getElementById('pageLoader') || this.createLoader();
        this.loaderStack.push(true); // Push state to stack
        loader.style.display = 'flex';
        loader.style.opacity = '1';
        document.body.style.overflow = 'hidden';
        this.updateLoaderStatus();
    },

    hideLoader() {
        this.loaderStack.pop(); // Remove last state
        // Only hide if stack is empty and no pending requests
        if (this.loaderStack.length === 0 && this.pendingRequests.size === 0) {
            const loader = document.getElementById('loader') || document.getElementById('pageLoader');
            if (loader) {
                loader.style.opacity = '0';
                setTimeout(() => {
                    loader.style.display = 'none';
                    document.body.style.overflow = '';
                }, 300);
            }
        }
    },

    trackRequest(promise, options = {}) {
        const {
            type = 'request',
            description = '',
            id = Date.now().toString() + Math.random()
        } = options;

        this.pendingRequests.set(id, { promise, type, description });
        this.showLoader();
        this.updateLoaderStatus();

        return promise
            .then(result => {
                this.pendingRequests.delete(id);
                this.updateLoaderStatus();
                if (this.pendingRequests.size === 0) {
                    this.hideLoader();
                }
                return result;
            })
            .catch(error => {
                this.pendingRequests.delete(id);
                this.updateLoaderStatus();
                if (this.pendingRequests.size === 0) {
                    this.hideLoader();
                }
                throw error;
            });
    },

    trackMultiple(promises, options = []) {
        if (!Array.isArray(promises)) {
            promises = [promises];
        }
        if (!Array.isArray(options)) {
            options = [options];
        }

        // Ensure we have options for each promise
        while (options.length < promises.length) {
            options.push({});
        }

        // Track each promise individually
        const trackedPromises = promises.map((promise, index) => 
            this.trackRequest(promise, options[index])
        );

        // Return promise that resolves when all tracked promises resolve
        return Promise.all(trackedPromises);
    }
};

// Expose simplified interface for backward compatibility
function createLoader() {
    return LoaderManager.createLoader();
}

function showLoader() {
    return LoaderManager.showLoader();
}

function hideLoader() {
    return LoaderManager.hideLoader();
}

// Track any async request (Supabase, Firebase, fetch, etc.)
function trackRequest(promise, options = {}) {
    return LoaderManager.trackRequest(promise, options);
}

// Track multiple requests
function trackMultipleRequests(promises, options = []) {
    return LoaderManager.trackMultiple(promises, options);
}

// Initialize loader when the script loads
document.addEventListener('DOMContentLoaded', () => {
    createLoader();
    showLoader();
});