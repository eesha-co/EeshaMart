// Function to load products from Supabase
async function loadProducts() {
    try {
        const { data: products, error } = await supabase
            .from('products')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) {
            console.error('Error loading products:', error);
            return [];
        }

        if (!products || products.length === 0) {
            console.log('No products found');
            return [];
        }

        console.log('Products loaded successfully:', products.length);
        return products;
    } catch (err) {
        console.error('Unexpected error loading products:', err);
        return [];
    }
}

// Function to display products. Renders into #categoryTabContent if present, otherwise #featuredProducts
async function displayProducts(targetSelector) {
    const categoryContainer = document.getElementById('categoryTabs');
    const productGridWrapper = document.getElementById('categoryTabContent') || document.getElementById('featuredProducts');
    if (!productGridWrapper) return;

    const products = await loadProducts();
    if (!products || products.length === 0) {
        productGridWrapper.innerHTML = '<p class="text-center text-gray-600">No products available at the moment.</p>';
        return;
    }

    // Prepare categories if tabs container exists
    let categories = ['All'];
    if (categoryContainer) {
        const cats = Array.from(new Set(products.map(p => p.category || 'Uncategorized')));
        categories = ['All', ...cats];
        categoryContainer.innerHTML = categories.map((c, i) => `
            <button data-category="${c}" class="tab-btn px-3 py-1 rounded-md mr-2 ${i===0? 'bg-yellow-400 text-black':'bg-white text-gray-700'}">${c}</button>
        `).join('');
    }

    // render function
    const render = (list) => {
        productGridWrapper.innerHTML = '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">' + list.map(prod => `
            <div class="bg-white rounded-lg shadow hover:shadow-lg transition overflow-hidden cursor-pointer" onclick="handleProductClick(event, ${prod.id})">
                <div class="w-full h-48 bg-gray-100">
                    <img src="${prod.image_url || prod.image || 'https://via.placeholder.com/600x400?text=No+Image'}" alt="${(prod.name||'').replace(/"/g,'') }" class="w-full h-full object-cover" onerror="this.onerror=null;this.src='https://via.placeholder.com/600x400?text=No+Image'">
                </div>
                <div class="p-4">
                    <h3 class="font-semibold text-lg text-gray-800">${prod.name || ''}</h3>
                    <p class="text-sm text-gray-500 mt-1 truncate">${(prod.description || '').substring(0, 80)}</p>
                    <div class="mt-3 flex items-center justify-between">
                        <span class="font-bold text-yellow-500">$${(prod.price || 0)}</span>
                        <button onclick="event.stopPropagation(); addToCart(${prod.id})" class="bg-yellow-400 text-black px-3 py-1 rounded">Add</button>
                    </div>
                </div>
            </div>
        `).join('') + '</div>';
    };

    // initial render (All)
    render(products);

    // wire up tab clicks
    if (categoryContainer) {
        const tabButtons = categoryContainer.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('ring-2'));
            btn.classList.add('ring-2', 'ring-yellow-300');
            const cat = btn.dataset.category;
            const list = cat === 'All' ? products : products.filter(p => (p.category || 'Uncategorized') === cat);
            render(list);
        }));
    }
}

// Initialize products when the page loads
document.addEventListener('DOMContentLoaded', displayProducts);