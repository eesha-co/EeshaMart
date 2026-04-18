// settings.js
class SettingsManager {
    constructor() {
        this.supabase = window.supabase;
        this.user = null;
        this.init();
    }

    async init() {
        try {
            const { data: { user } } = await this.supabase.auth.getUser();
            if (!user) {
                window.location.href = 'login.html';
                return;
            }
            this.user = user;
            await this.setupEventListeners();
            await this.loadUserData();
            this.setupNavigationHandlers();
            this.setupDarkMode();
            await this.loadNotificationSettings();
        } catch (error) {
            console.error('Initialization error:', error);
            try { if (window.showStatus) window.showStatus('Error initializing settings. Some features may be unavailable.', 'error'); } catch (e) { /* ignore */ }
        } finally {
            // Always notify the page that settings initialization is complete so loaders can hide
            try {
                window.dispatchEvent(new Event('settingsReady'));
            } catch (e) {
                console.warn('Could not dispatch settingsReady event', e);
            }
        }
    }

    setupNavigationHandlers() {
        const navLinks = document.querySelectorAll('.settings-nav a');
        const sections = document.querySelectorAll('.settings-section');

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
                
                sections.forEach(s => {
                    s.classList.remove('active');
                    if (s.id === section) {
                        s.classList.add('active');
                    }
                });

                // Update URL hash without scrolling
                history.pushState(null, null, `#${section}`);
            });
        });

        // Handle initial hash
        const hash = window.location.hash.slice(1);
        if (hash) {
            const targetLink = document.querySelector(`[data-section="${hash}"]`);
            if (targetLink) targetLink.click();
        }
    }

    async loadUserData() {
        try {
            const { data: seller, error } = await this.supabase
                .from('sellers')
                .select('*')
                .eq('id', this.user.id)
                .single();

            if (error) throw error;

            if (seller) {
                // Profile Section
                this.setFormValues('profileForm', {
                    firstName: seller.first_name,
                    lastName: seller.last_name,
                    email: seller.email || this.user.email,
                    phone: seller.phone
                });

                // Business Section
                this.setFormValues('businessForm', {
                    businessName: seller.business_name,
                    businessDescription: seller.business_description,
                    businessCategory: seller.business_category,
                    businessLocation: seller.business_location
                });

                // Profile Image (select the one inside the #profile section to avoid colliding with navbar img)
                const profileImg = document.querySelector('#profile #profileImage');
                if (profileImg) {
                    if (seller?.profile_image) {
                        // Clear any existing content
                        profileImg.innerHTML = '';
                        // Create and set the image
                        const img = document.createElement('img');
                        img.src = seller.profile_image;
                        img.alt = 'Profile';
                        img.style.width = '100%';
                        img.style.height = '100%';
                        img.style.objectFit = 'cover';
                        profileImg.appendChild(img);
                    } else {
                        // Use Font Awesome user icon as a fallback
                        profileImg.innerHTML = '<i class="fas fa-user" style="font-size: 2em; color: #666;"></i>';
                        profileImg.style.backgroundColor = '#f0f0f0';
                        profileImg.style.display = 'flex';
                        profileImg.style.alignItems = 'center';
                        profileImg.style.justifyContent = 'center';
                    }
                }

                // Preferences
                if (seller.preferences) {
                    document.getElementById('language').value = seller.preferences.language || 'en';
                    document.getElementById('timezone').value = seller.preferences.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
                    document.getElementById('darkMode').checked = seller.preferences.darkMode || false;
                }
            }
        } catch (error) {
            console.error('Error loading user data:', error);
            alert('Error loading your settings. Please refresh the page.');
        }
    }

    setFormValues(formId, values) {
        Object.entries(values).forEach(([key, value]) => {
            const element = document.getElementById(key);
            if (element && value) {
                element.value = value;
            }
        });
    }

    async setupEventListeners() {
        // Profile Image Upload
        this.setupImageUpload();

        // Update settings profile image when other parts of the app (e.g., navbar) emit updates
        window.addEventListener('profileImageUpdated', (event) => {
            try {
                const el = document.querySelector('#profile #profileImage');
                if (el && event?.detail?.url) {
                    el.innerHTML = `<img src="${event.detail.url}" alt="Profile">`;
                    el.style.backgroundColor = 'transparent';
                }
            } catch (e) {
                console.warn('Failed to update settings profile image from event', e);
            }
        });

        // Form Submissions
        this.setupFormHandlers();

        // Delete Account
        document.getElementById('deleteAccount').addEventListener('click', () => this.handleDeleteAccount());

        // Notification Toggles
        const notificationToggles = ['orderNotifications', 'reviewNotifications', 'stockAlerts'];
        notificationToggles.forEach(id => {
            document.getElementById(id).addEventListener('change', () => this.saveNotificationSettings());
        });

        // Preferences
        document.getElementById('language').addEventListener('change', () => this.savePreferences());
        document.getElementById('timezone').addEventListener('change', () => this.savePreferences());
        document.getElementById('darkMode').addEventListener('change', (e) => this.handleDarkMode(e.target.checked));
    }

    async setupImageUpload() {
    const uploadBtn = document.getElementById('uploadBtn');
    const imageInput = document.getElementById('imageInput');
    // Select the profile image container specifically inside the profile section
    const profileImage = document.querySelector('#profile #profileImage');
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(loadingOverlay);

        // Add loading indicator styles
        const style = document.createElement('style');
        style.textContent = `
            .loading-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                z-index: 9999;
                justify-content: center;
                align-items: center;
            }
            .spinner {
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #f0474a;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
        `;
        document.head.appendChild(style);
        uploadBtn.addEventListener('click', () => imageInput.click());

        imageInput.addEventListener('change', async (e) => {
            try {
                const file = e.target.files[0];
                if (!file) return;

                // Validate file type
                const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
                if (!allowedTypes.includes(file.type)) {
                    throw new Error('Please upload an image file (JPEG, PNG, GIF, or WebP)');
                }

                // Validate file size (5MB max)
                if (file.size > 5 * 1024 * 1024) {
                    throw new Error('Image size should be less than 5MB');
                }

                loadingOverlay.style.display = 'flex';

                // Check if storage bucket exists
                const bucketReady = await ensureStorageBucket();
                if (!bucketReady) {
                    throw new Error('Storage system is not properly configured');
                }

                // Create a unique filename
                const fileExt = file.name.split('.').pop().toLowerCase();
                const fileName = `${this.user.id}-${Date.now()}.${fileExt}`;
                const filePath = `${this.user.id}/${fileName}`;

                // Delete previous profile image if it exists
                try {
                    const { data: seller } = await this.supabase
                        .from('sellers')
                        .select('profile_image')
                        .eq('id', this.user.id)
                        .single();

                    if (seller?.profile_image) {
                        const oldPath = new URL(seller.profile_image).pathname.split('/').pop();
                        if (oldPath) {
                            await this.supabase.storage
                                .from(window.STORAGE_BUCKET)
                                .remove([`${this.user.id}/${oldPath}`]);
                        }
                    }
                } catch (error) {
                    console.warn('Error removing old profile image:', error);
                }

                // Upload new image
                const { error: uploadError, data: uploadData } = await this.supabase.storage
                    .from(window.STORAGE_BUCKET)
                    .upload(filePath, file, {
                        cacheControl: '3600',
                        upsert: true
                    });

                if (uploadError) {
                    console.error('Upload error:', uploadError);
                    throw new Error('Failed to upload image: ' + uploadError.message);
                }

                // Get public URL with error handling
                const { data: urlData } = await this.supabase.storage
                    .from(window.STORAGE_BUCKET)
                    .getPublicUrl(filePath);

                if (!urlData || !urlData.publicUrl) {
                    throw new Error('Failed to get public URL for uploaded image');
                }

                const publicUrl = urlData.publicUrl;

                // Update profile image in database
                const { error: updateError } = await this.supabase
                    .from('sellers')
                    .update({ 
                        profile_image: publicUrl,
                        updated_at: new Date().toISOString()
                    })
                    .eq('id', this.user.id);

                if (updateError) throw updateError;

                // Update image preview
                if (profileImage) {
                    profileImage.innerHTML = `<img src="${publicUrl}" alt="Profile">`;
                    profileImage.style.backgroundColor = 'transparent';
                } else {
                    console.warn('Profile image container not found in settings page');
                }
                showStatus('Profile image updated successfully');

                // Trigger a page refresh of areas that might show the profile image
                const event = new CustomEvent('profileImageUpdated', { detail: { url: publicUrl } });
                window.dispatchEvent(event);

            } catch (error) {
                console.error('Error uploading image:', error);
                alert(error.message || 'Error uploading image. Please try again.');
            } finally {
                loadingOverlay.style.display = 'none';
            }
        });
    }

    setupFormHandlers() {
        // Profile Form
        document.getElementById('profileForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleProfileUpdate(e);
        });

        // Business Form
        document.getElementById('businessForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleBusinessUpdate(e);
        });

        // Security Form
        document.getElementById('securityForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handlePasswordUpdate(e);
        });
    }

    async handleProfileUpdate(e) {
        try {
            // First, ensure the seller record exists
            const { data: existingSeller, error: checkError } = await this.supabase
                .from('sellers')
                .select('id')
                .eq('id', this.user.id)
                .single();

            if (checkError || !existingSeller) {
                // Create new seller record if it doesn't exist
                const { error: insertError } = await this.supabase
                    .from('sellers')
                    .insert([{ 
                        id: this.user.id,
                        first_name: document.getElementById('firstName').value,
                        last_name: document.getElementById('lastName').value,
                        email: this.user.email,
                        phone: document.getElementById('phone').value,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    }]);

                if (insertError) throw insertError;
            } else {
                // Update existing seller record
                const { error: updateError } = await this.supabase
                    .from('sellers')
                    .update({
                        first_name: document.getElementById('firstName').value,
                        last_name: document.getElementById('lastName').value,
                        phone: document.getElementById('phone').value,
                        updated_at: new Date().toISOString()
                    })
                    .eq('id', this.user.id);

                if (updateError) throw updateError;
            }

            showStatus('Profile updated successfully');
        } catch (error) {
            console.error('Error updating profile:', error);
            showStatus('Error updating profile. Please try again.', 'error');
        }
    }

    async handleBusinessUpdate(e) {
        try {
            const formData = {
                business_name: document.getElementById('businessName').value,
                business_description: document.getElementById('businessDescription').value,
                business_category: document.getElementById('businessCategory').value,
                business_location: document.getElementById('businessLocation').value,
                updated_at: new Date().toISOString()
            };

            const { error } = await this.supabase
                .from('sellers')
                .update(formData)
                .eq('id', this.user.id);

            if (error) throw error;
            alert('Business details updated successfully');
        } catch (error) {
            console.error('Error updating business details:', error);
            alert('Error updating business details. Please try again.');
        }
    }

    async handlePasswordUpdate(e) {
        try {
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            if (newPassword !== confirmPassword) {
                throw new Error('New passwords do not match');
            }

            const { error } = await this.supabase.auth.updateUser({
                password: newPassword
            });

            if (error) throw error;

            alert('Password updated successfully');
            document.getElementById('securityForm').reset();
        } catch (error) {
            console.error('Error updating password:', error);
            alert(error.message || 'Error updating password. Please try again.');
        }
    }

    async handleDeleteAccount() {
        try {
            if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
                return;
            }

            // Additional confirmation with password
            const password = prompt('Please enter your password to confirm account deletion:');
            if (!password) return;

            // Verify password
            const { error: signInError } = await this.supabase.auth.signInWithPassword({
                email: this.user.email,
                password: password
            });

            if (signInError) throw new Error('Invalid password');

            // Delete seller data
            const { error: sellerError } = await this.supabase
                .from('sellers')
                .delete()
                .eq('id', this.user.id);

            if (sellerError) throw sellerError;

            // Delete auth user
            const { error: authError } = await this.supabase.auth.admin.deleteUser(this.user.id);
            if (authError) throw authError;

            await this.supabase.auth.signOut();
            window.location.href = 'login.html';
        } catch (error) {
            console.error('Error deleting account:', error);
            alert(error.message || 'Error deleting account. Please try again.');
        }
    }

    async loadNotificationSettings() {
        try {
            const { data: settings, error } = await this.supabase
                .from('notification_settings')
                .select('*')
                .eq('user_id', this.user.id)
                .single();

            if (error && error.code !== 'PGRST116') throw error;

            if (settings) {
                document.getElementById('orderNotifications').checked = settings.order_notifications;
                document.getElementById('reviewNotifications').checked = settings.review_notifications;
                document.getElementById('stockAlerts').checked = settings.stock_alerts;
            }
        } catch (error) {
            console.error('Error loading notification settings:', error);
        }
    }

    async saveNotificationSettings() {
        try {
            const settings = {
                user_id: this.user.id,
                order_notifications: document.getElementById('orderNotifications').checked,
                review_notifications: document.getElementById('reviewNotifications').checked,
                stock_alerts: document.getElementById('stockAlerts').checked,
                updated_at: new Date().toISOString()
            };

            const { error } = await this.supabase
                .from('notification_settings')
                .upsert(settings, { onConflict: 'user_id' });

            if (error) throw error;
        } catch (error) {
            console.error('Error saving notification settings:', error);
            alert('Error saving notification preferences. Please try again.');
        }
    }

    async savePreferences() {
        try {
            const preferences = {
                language: document.getElementById('language').value,
                timezone: document.getElementById('timezone').value,
                darkMode: document.getElementById('darkMode').checked
            };

            const { error } = await this.supabase
                .from('sellers')
                .update({ preferences })
                .eq('id', this.user.id);

            if (error) throw error;
            
            this.handleDarkMode(preferences.darkMode);
        } catch (error) {
            console.error('Error saving preferences:', error);
            alert('Error saving preferences. Please try again.');
        }
    }

    setupDarkMode() {
        // Initialize dark mode from localStorage or system preference
        const darkMode = localStorage.getItem('darkMode') === 'true' || 
            (!localStorage.getItem('darkMode') && window.matchMedia('(prefers-color-scheme: dark)').matches);
        
        document.getElementById('darkMode').checked = darkMode;
        this.handleDarkMode(darkMode);

        // Listen for system dark mode changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (!localStorage.getItem('darkMode')) {
                this.handleDarkMode(e.matches);
            }
        });
    }

    handleDarkMode(enabled) {
        localStorage.setItem('darkMode', enabled);
        document.body.classList.toggle('dark-mode', enabled);
        
        // Add dark mode styles
        if (enabled) {
            document.documentElement.style.setProperty('--light-color', '#2d2d2d');
            document.documentElement.style.setProperty('--dark-color', '#f8f9fa');
            document.documentElement.style.setProperty('--primary-color', '#ff6b6e');
        } else {
            document.documentElement.style.setProperty('--light-color', '#f8f9fa');
            document.documentElement.style.setProperty('--dark-color', '#343a40');
            document.documentElement.style.setProperty('--primary-color', '#f0474a');
        }
    }

    populateTimezones() {
        const timezoneSelect = document.getElementById('timezone');
        const currentTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        Intl.supportedValuesOf('timeZone').forEach(timezone => {
            const option = document.createElement('option');
            option.value = timezone;
            option.textContent = timezone.replace(/_/g, ' ');
            if (timezone === currentTimezone) {
                option.selected = true;
            }
            timezoneSelect.appendChild(option);
        });
    }
}

// Initialize settings manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SettingsManager();
});