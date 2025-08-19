// Service Worker for Pi Monitor PWA
const CACHE_NAME = 'pi-monitor-v2.0.0';
const STATIC_CACHE = 'pi-monitor-static-v2.0.0';
const DYNAMIC_CACHE = 'pi-monitor-dynamic-v2.0.0';

// Files to cache for offline use
const STATIC_FILES = [
  '/',
  '/index.html',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json',
  '/favicon.ico'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('Opened static cache');
        return cache.addAll(STATIC_FILES);
      })
      .catch((error) => {
        console.log('Cache install failed:', error);
      })
  );
  // Ensure the new SW activates immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  // Aggressively clear ALL caches to avoid stale assets after deploys
  event.waitUntil((async () => {
    try {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map((name) => caches.delete(name)));
    } catch (e) {
      console.log('Cache cleanup failed:', e);
    }
    // Take control of existing clients immediately
    await self.clients.claim();
  })());
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip non-HTTP requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Handle API requests differently
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Handle static assets
  if (request.destination === 'script' || 
      request.destination === 'style' || 
      request.destination === 'image') {
    event.respondWith(handleStaticRequest(request));
    return;
  }

  // Handle navigation requests
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request));
    return;
  }
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
  const url = new URL(request.url);
  const isRealtimeMetrics = url.pathname === '/api/system';
  const isMetricsHistory = url.pathname.startsWith('/api/metrics/history');
  try {
    // Try network first
    const networkResponse = await fetch(request);
    
    // Cache successful responses only when allowed
    if (networkResponse.ok) {
      const cacheControl = (networkResponse.headers.get('Cache-Control') || '').toLowerCase();
      const shouldSkipCache = cacheControl.includes('no-store') || cacheControl.includes('no-cache') || isRealtimeMetrics || isMetricsHistory;
      if (!shouldSkipCache) {
        const cache = await caches.open(DYNAMIC_CACHE);
        cache.put(request, networkResponse.clone());
      }
    }
    
    return networkResponse;
  } catch (error) {
    // For highly dynamic endpoints, do NOT serve stale cached data
    if (isRealtimeMetrics || isMetricsHistory) {
      return new Response(
        JSON.stringify({ error: 'Offline - API not available' }),
        {
          status: 503,
          statusText: 'Service Unavailable',
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // Fallback to cache for other API requests if available
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline response for API requests
    return new Response(
      JSON.stringify({ error: 'Offline - API not available' }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle static assets with cache-first strategy
async function handleStaticRequest(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // Return offline response for static assets
    return new Response('Offline', { status: 503 });
  }
}

// Handle navigation requests with network-first strategy to avoid stale HTML
async function handleNavigationRequest(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.ok) {
      try {
        const cache = await caches.open(DYNAMIC_CACHE);
        cache.put(request, networkResponse.clone());
      } catch (_) {}
      return networkResponse;
    }
    // If network failed or not ok, try cache
    const cachedResponse = await caches.match('/index.html');
    if (cachedResponse) return cachedResponse;
  } catch (_) {
    const cachedResponse = await caches.match('/index.html');
    if (cachedResponse) return cachedResponse;
  }
  // Fallback offline response
  return new Response(
    `
    <!DOCTYPE html>
    <html>
      <head>
        <title>Pi Monitor - Offline</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            padding: 50px; 
            background: #f5f5f5; 
          }
          .offline-message { 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
          }
        </style>
      </head>
      <body>
        <div class="offline-message">
          <h1>🥧 Pi Monitor</h1>
          <p>You're currently offline.</p>
          <p>Please check your internet connection and try again.</p>
          <button onclick="window.location.reload()">Retry</button>
        </div>
      </body>
    </html>
    `,
    {
      status: 200,
      headers: { 'Content-Type': 'text/html' }
    }
  );
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  try {
    // Perform background sync tasks
    console.log('Background sync completed');
  } catch (error) {
    console.log('Background sync failed:', error);
  }
}

// Push notification handling
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'Pi Monitor notification',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      tag: 'pi-monitor-notification',
      data: data.data || {},
      actions: data.actions || [],
      requireInteraction: data.requireInteraction || false
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'Pi Monitor', options)
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action) {
    // Handle specific action clicks
    console.log('Notification action clicked:', event.action);
  } else {
    // Default click behavior
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
