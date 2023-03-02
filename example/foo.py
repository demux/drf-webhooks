from celery import shared_task

from drf_webhooks import disable_webhooks, webhook_signal_session


@disable_webhooks
def some_heavy_sync_operation(data_set):
    for data in data_set:
        ...
        MyModel.objects.create(**data)
        ...


@shared_task
@webhook_signal_session
def some_background_task(id):
    instance = MyModel.objects.get(id=id)
    instance.name = "something something"
    instance.save()
