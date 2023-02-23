# Django Rest Framework - Webhooks
**Configurable webhooks for DRF Serializers**

## Goals:
- [x] Use existing DRF Serializers from REST API to serialize data in webhooks
    - [x] Consistent data formatting
    - [x] Reusable OpenAPI schemas
- [x] Configurable webhooks that simply work *(by way of django signals magic)* without the developer having to keep track of where to trigger them
    - [x] Still allow for "manual" triggering of webhooks
        - This is useful because signals aren't always triggered
        - For example: `QuerySet.update` does not trigger signals
- [x] Disable webhooks using context managers
    - This can be useful when syncing large chunks of data
    - or with a duplex sync (when two systems sync with each other) to avoid endless loops
- [x] **Webhook Signal Session**
    - [x] A context manager gathers all models signals and at the end of the session only triggers the resulting webhooks
        - [x] If a model instance is both `created` and `deleted` within the session, then no webhook is sent for that model instance
        - [x] If a model instance is `created` and then also `updated` within the session, then a `created` event is sent with the data from the last `updated` signal. Only one webhook even is sent
        - [x] If a models instance is `updated` multiple times within the session, then only one webhook event is sent
    - [x] Middleware wraps each request in **Webhook Signal Session** context
        - **NOTE:** The developer will have to call the context manager in code that runs outside of requests (for example in celery tasks) manually
- [x] Automatically determine which nested models need to be monitored for changes

## Examples:

```python
from django.db import models
from drf_webhooks import ModelSerializerWebhook, register_webhook
from rest_framework import serializers


class MyModel(models.Model):
    name = models.CharField(max_lenght=100)


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ['id', 'name']


# Automatic:
register_webhook(MyModel)()

# ---- OR ----
# If you need more configuration:
@register_webhook(MyModel)
class MyModelWebhook(ModelSerializerWebhook):
    base_name = 'core.my_model'
```

# Documentation:

## Quckstart:

### Install `drf-webhooks`
```bash
poetry add drf-webhooks
# ... or ...
pip install drf-webhooks
```

### Update `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'drf_webhooks',
]

MIDDLEWARE = [
    # ...
    'drf_webhooks.middleware.WebhooksMiddleware',
]

# This is required if you don't want your database to fill up with logs:
CELERY_BEAT_SCHEDULE = {
    'clean-webhook-log': {
        'task': 'drf_webhooks.tasks.auto_clean_log',
        'schedule': 60,
        'options': {'expires': 10},
    },
}
```

### Create a new django app
Recommended app name: `webhooks`

```python
# ----------------------------------------------------------------------
#  apps.py
# ----------------------------------------------------------------------
from django.apps import AppConfig


class WebhooksAppConfig(AppConfig):
    name = "<your module name>"
    label = "webhooks"


# ----------------------------------------------------------------------
#  models.py
# ----------------------------------------------------------------------
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from drf_webhooks.models import AbstractWebhook, AbstractWebhookLogEntry


class Webhook(AbstractWebhook):
    # This can also be a group or an organization that the user belongs to:
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return 'id=%s, events=%s, owner=%s' % (
            str(self.id),
            ', '.join(self.events),
            str(self.owner),
        )


class WebhookLogEntry(AbstractWebhookLogEntry):
    # This can also be a group or an organization that the user belongs to:
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
```
