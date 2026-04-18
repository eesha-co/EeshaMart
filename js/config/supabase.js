// Centralized Supabase client initializer
// -----------------------------------------------------------------------------
// Usage contract (tiny):
// - Pages must load the Supabase UMD script first:
//     <script src="https://unpkg.com/@supabase/supabase-js@2/dist/umd/supabase.js"></script>
// - Then include this file (path relative to the page):
//     <script src="/js/config/supabase.js"></script>
// - After this runs, a single client will be available as `window.supabaseClient` and
//   (for backward compatibility) `window.supabase`.
// - Page scripts should then use `const supabase = window.supabase;` and NOT
//   call `createClient` again. This prevents TDZ/duplicate-client issues.
//
// Failure modes:
// - If the UMD library is not present, this file will log an error and do nothing.
// - Ensure the include order above; otherwise pages may see "Cannot access 'supabase'"
//   before initialization.
// -----------------------------------------------------------------------------
(function() {
	const SUPABASE_URL = 'https://tcwdbokruvlizkxcpkzj.supabase.co';
	const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRjd2Rib2tydXZsaXpreGNwa3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDkyNjQsImV4cCI6MjA3NTY4NTI2NH0.p871FXUakrWQ7PhhZr8Ly2BxLOhwQjRJiDGd59wAhyg';

	try {
		// UMD bundle exposes a global named `supabase` which has createClient
		const lib = (typeof window !== 'undefined' && window.supabase) ? window.supabase : (typeof supabaseJs !== 'undefined' ? supabaseJs : null);
		if (lib && typeof lib.createClient === 'function') {
			// create the client and expose it as both `window.supabaseClient` and `window.supabase`
			const client = lib.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
			window.supabaseClient = client;
			// Overwrite window.supabase so existing code that expects `supabase` to be the client still works
			window.supabase = client;
		} else {
			console.error('Supabase library not found. Ensure you included the UMD script: https://unpkg.com/@supabase/supabase-js@2/dist/umd/supabase.js');
		}
	} catch (err) {
		console.error('Error initializing centralized Supabase client:', err);
	}
})();
