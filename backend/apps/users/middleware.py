from urllib.parse import urlparse

from django.conf import settings


class OAuthCallbackHostMiddleware:
    """
    Forces allauth to build OAuth callback URLs using BACKEND_URL.
    Without this, Vite's changeOrigin proxy makes Django see Host: localhost:4500
    and allauth sends redirect_uri=http://localhost:4500/... which GitHub rejects.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        backend_url = getattr(settings, 'BACKEND_URL', '')
        if backend_url:
            parsed = urlparse(backend_url)
            self._host = parsed.netloc
            self._scheme = parsed.scheme
        else:
            self._host = None
            self._scheme = None

    def __call__(self, request):
        if self._host and request.path.startswith('/accounts/'):
            request.META['HTTP_HOST'] = self._host
            if self._scheme == 'https':
                request.META['wsgi.url_scheme'] = 'https'
                request.META['HTTP_X_FORWARDED_PROTO'] = 'https'
        return self.get_response(request)
