from django.utils.cache import add_never_cache_headers


class AdminNoCacheMiddleware:
    """
    Prevent Django Admin pages from being cached by the browser.

    This ensures that after logout, using the browser Back button
    cannot display a previously cached Admin page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/admin/"):
            add_never_cache_headers(response)

        return response