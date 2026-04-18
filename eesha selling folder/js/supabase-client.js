// DEPRECATED: legacy per-page Supabase client helper.
//
// All pages now use the centralized initializer at `js/config/supabase.js`.
// This file remains temporarily to avoid 404s for older deployments.
// Safe to delete after verifying no script tags reference it.

/* eslint-disable no-console */
console.info('[DEPRECATED] eesha selling folder/js/supabase-client.js loaded - legacy placeholder.');

// Optional runtime check (non-throwing) to help debug missing includes during migration.
if (typeof window !== 'undefined' && typeof window.supabase === 'undefined') {
    console.warn('Centralized Supabase client not found. Include js/config/supabase.js after the UMD supabase script.');
}
