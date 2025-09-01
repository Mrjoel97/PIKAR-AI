import { useEffect } from 'react';
import { toast } from 'sonner';

export const PWAInstaller = () => {
    useEffect(() => {
        let deferredPrompt;

        const handleBeforeInstallPrompt = (e) => {
            e.preventDefault();
            deferredPrompt = e;
            
            // Show install banner after a delay
            setTimeout(() => {
                showInstallPrompt(deferredPrompt);
            }, 10000);
        };

        const showInstallPrompt = (prompt) => {
            toast("Install PIKAR AI", {
                description: "Add to your home screen for a better experience",
                action: {
                    label: "Install",
                    onClick: async () => {
                        if (prompt) {
                            prompt.prompt();
                            const { outcome } = await prompt.userChoice;
                            if (outcome === 'accepted') {
                                toast.success("PIKAR AI installed successfully!");
                            }
                        }
                    }
                },
                duration: 10000
            });
        };

        window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

        return () => {
            window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
        };
    }, []);

    return null;
};

export const ServiceWorkerRegistration = () => {
    useEffect(() => {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', async () => {
                try {
                    const registration = await navigator.serviceWorker.register('/sw.js');
                    console.log('SW registered: ', registration);
                    
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed') {
                                if (navigator.serviceWorker.controller) {
                                    toast("Update available", {
                                        description: "A new version of PIKAR AI is available",
                                        action: {
                                            label: "Update",
                                            onClick: () => window.location.reload()
                                        }
                                    });
                                }
                            }
                        });
                    });
                } catch (error) {
                    console.log('SW registration failed: ', error);
                }
            });
        }
    }, []);

    return null;
};

// Service Worker content (would be in public/sw.js)
export const serviceWorkerContent = `
const CACHE_NAME = 'pikar-ai-v1';
const urlsToCache = [
    '/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});
`;

// PWA Manifest (would be in public/manifest.json)
export const manifestContent = {
    "name": "PIKAR AI - Business Intelligence Platform",
    "short_name": "PIKAR AI",
    "description": "AI-powered business intelligence and transformation platform",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#3b82f6",
    "icons": [
        {
            "src": "/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
};