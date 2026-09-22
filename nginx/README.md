# Nginx source of truth

The production Nginx configuration is `../frontend/nginx.conf` because the frontend Docker build copies it into the Nginx image. It disables proxy buffering for SSE and serves the Vue history fallback.
