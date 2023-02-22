from .sessions import webhook_signal_session


class WebhooksMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with webhook_signal_session():
            return self.get_response(request)
