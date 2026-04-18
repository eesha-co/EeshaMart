# Eesha Shop

A modern e-commerce platform built with HTML, CSS, and JavaScript, featuring both buyer and seller interfaces.

## Features

- Modern UI with Tailwind CSS
- Responsive design
- Interactive splash screen with animations
- Buyer and seller interfaces
- Product showcase
- Shopping cart functionality
- AI shopping assistant
- User authentication

## Getting Started

1. Clone the repository
2. Open `index.html` in your browser
3. Navigate through the buyer or seller interface

## Structure

- `/Eesha buying folder` - Buyer interface and assets
- `/eesha selling folder` - Seller interface
- `/css` - Stylesheets
- `/js` - JavaScript files
- `/shared` - Shared resources

## Development

This project uses:
- Tailwind CSS for styling
- Font Awesome for icons
- Custom animations
- Responsive design principles

## Deployment

The site is deployed on Netlify with continuous deployment from the main branch.
"# Eesha-shop-Buying-and-Selling" 

## Supabase integration — script order & centralized initializer

Short note for future edits and new pages that use Supabase (important — follow this order):

1. Include the Supabase UMD browser bundle (CDN or locally) before anything that touches `supabase` in the page.
	- Example CDN: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js/dist/umd/supabase.js"></script>
2. Include the centralized initializer: `js/config/supabase.js`.
	- This file creates a single client and exposes it as `window.supabaseClient` and `window.supabase`.
	- Do NOT call `createClient(...)` again in page scripts — that caused duplicate clients and initialization timing errors.
3. Include page-specific scripts that use Supabase (these scripts should read the global client via `const supabase = window.supabase;`).

Notes / helpful pointers:
- Server-side code should use `lib/supabaseClient.js` (exports an ES module client via `createClient`).
- If you need to check for the client at runtime in a script, use a non-throwing check like `if (window.supabase) { /* use it */ }`.
- Guest cart key (used across buyer pages): `guest_cart` in localStorage. Logged-in cart items are stored in the `cart_items` table.
- If you find any legacy per-page `supabase-client.js` files, prefer replacing their script tag with the two includes above and remove the legacy file once no references remain.

Keeping this order prevents errors like "Cannot access 'supabase' before initialization" and avoids duplicated client instances.

