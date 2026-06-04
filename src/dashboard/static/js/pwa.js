const PWA = {
    deferredPrompt: null,

    init() {
        // Register Service Worker
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        console.log('SW registered:', registration);
                    })
                    .catch(registrationError => {
                        console.log('SW registration failed:', registrationError);
                    });
            });
        }

        // Install prompt handling
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            const installSection = document.getElementById('install-app-section');
            const installBtn = document.getElementById('install-app-btn');
            
            if (installSection && installBtn) {
                installSection.style.display = 'flex';
                installBtn.addEventListener('click', async () => {
                    this.deferredPrompt.prompt();
                    const { outcome } = await this.deferredPrompt.userChoice;
                    console.log(`User response to install prompt: ${outcome}`);
                    this.deferredPrompt = null;
                    installSection.style.display = 'none';
                });
            }
        });

        window.addEventListener('appinstalled', (evt) => {
            console.log('EduIG Dashboard was installed as a PWA');
            Toast.show('Dashboard installed successfully!', 'success');
            const installSection = document.getElementById('install-app-section');
            if (installSection) installSection.style.display = 'none';
        });

        // Online/Offline detection
        window.addEventListener('online', () => this.updateOnlineStatus());
        window.addEventListener('offline', () => this.updateOnlineStatus());
        
        // Initial check
        this.updateOnlineStatus();
        this.updateCacheStatusText();
    },

    updateOnlineStatus() {
        const isOnline = navigator.onLine;
        const banner = document.getElementById('offline-banner');
        const statusText = document.getElementById('connection-status-text');
        const statusIndicator = document.getElementById('connection-status-indicator');

        if (isOnline) {
            if (banner) banner.classList.add('hidden');
            if (statusText) statusText.textContent = 'Online';
            if (statusIndicator) {
                statusIndicator.classList.remove('bg-red-500');
                statusIndicator.classList.add('bg-green-500');
            }
        } else {
            if (banner) banner.classList.remove('hidden');
            if (statusText) statusText.textContent = 'Offline (Cached)';
            if (statusIndicator) {
                statusIndicator.classList.remove('bg-green-500');
                statusIndicator.classList.add('bg-red-500');
            }
            Toast.show('You are offline. Viewing cached data.', 'warning');
        }
    },

    updateCacheStatusText() {
        const cacheText = document.getElementById('cache-status-text');
        if (cacheText) {
            cacheText.textContent = `Last updated: ${new Date().toLocaleString()}`;
        }
    },

    async clearCache() {
        if ('caches' in window) {
            try {
                const cacheNames = await caches.keys();
                await Promise.all(
                    cacheNames.map(cache => caches.delete(cache))
                );
                
                // Clear Service Worker registration to force complete refresh
                const registrations = await navigator.serviceWorker.getRegistrations();
                for (let registration of registrations) {
                    await registration.unregister();
                }

                Toast.show('Cache cleared. Reloading...', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } catch (err) {
                console.error('Error clearing cache:', err);
                Toast.show('Failed to clear cache', 'error');
            }
        } else {
            Toast.show('Caching not supported in this browser', 'info');
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    PWA.init();
});
