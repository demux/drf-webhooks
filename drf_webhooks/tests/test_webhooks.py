import json
from atexit import unregister

import pytest
from django.contrib.auth import get_user_model
from pytest_httpx import HTTPXMock

from ..config import REGISTERED_WEBHOOK_CHOICES, conf
from ..main import ModelSerializerWebhook, register_webhook, unregister_webhook
from ..sessions import webhook_signal_session
from .models import LevelOne, LevelOneSide, LevelThree, LevelTwo, Many
from .serializers import (
    LevelOneSideSerializer,
    LevelThreeSerializer,
    LevelTwoSerializer,
)

Webhook = conf.WEBHOOK_MODEL


@pytest.fixture(scope='session')
def celery_config():
    return {'task_always_eager': True}


def test_serializer_webhook_getters_duplicate_base_name():
    with pytest.raises(RuntimeError):

        @register_webhook(LevelOneSideSerializer)
        class LevelOneSideSerializerWebhook(ModelSerializerWebhook):
            base_name = 'test.level'

        @register_webhook(LevelThreeSerializer)
        class LevelThreeSerializerWebhook2(ModelSerializerWebhook):
            base_name = 'test.level'


def test_serializer_webhook_getters_duplicate_serializer():
    with pytest.raises(RuntimeError):
        register_webhook(LevelThreeSerializer)()
        register_webhook(LevelThreeSerializer)()


def test_serializer_webhook_define_success():
    register_webhook(LevelTwoSerializer)()

    try:
        assert REGISTERED_WEBHOOK_CHOICES['test.level_two.created'] == "Level Two Created"
        assert REGISTERED_WEBHOOK_CHOICES['test.level_two.updated'] == "Level Two Updated"
        assert REGISTERED_WEBHOOK_CHOICES['test.level_two.deleted'] == "Level Two Deleted"
    finally:
        unregister_webhook(LevelTwoSerializer)


def test_serializer_webhook_events(db, httpx_mock: HTTPXMock):
    @register_webhook(LevelTwoSerializer)
    class LevelTwoSerializerWebhook(ModelSerializerWebhook):
        base_name = 'test.level_two'

        def get_owner(self, instance):
            return instance.parent.owner

    try:
        with webhook_signal_session():
            owner = get_user_model().objects.create()

            httpx_mock.add_response()

            target_url = "http://reon.mock/webhook/level_two/"
            webhook = Webhook.objects.create(
                owner=owner,
                events=[
                    'test.level_two.created',
                    'test.level_two.updated',
                    'test.level_two.deleted',
                ],
                target_url=target_url,
            )

            one = LevelOne.objects.create(name="one", owner=owner)
            one_id = one.id
            two = LevelTwo.objects.create(name="two", parent=one)
            side = LevelOneSide.objects.create(name="side", one=one)
            side_id = side.id
            three = LevelThree.objects.create(name="three", parent=two)
            three.delete()

            two.name = "two!"
            two.save()

            two2 = LevelTwo.objects.create(name="more two", parent=one)

        with webhook_signal_session():
            two.name = "updated name"
            two.save()

            three2 = LevelThree.objects.create(name="three2", parent=two2)
            three2_id = three2.id

        with webhook_signal_session():
            many = Many.objects.create(name="Many")
            many.level_ones.add(one)
            many_id = many.id

        with webhook_signal_session():
            one.delete()

        # for req in httpx_mock.get_requests():
        #     print(json.dumps(json.loads((req.content)), indent=2))

        assert len(httpx_mock.get_requests()) == 8

        (
            level_two__created,
            level_two2__created,
            level_two__updated,
            level_two2__updated,
            m2m__updated,
            m2m_2__updated,
            level_two__deleted,
            level_two2__deleted,
        ) = [json.loads(r.content) for r in httpx_mock.get_requests()]

        assert level_two__created["event"] == "test.level_two.created"
        assert level_two__created["objectId"] == str(two.id)
        assert level_two__created["payload"]["name"] == "two!"
        assert level_two__created["payload"]["parent"]["id"] == one_id
        assert level_two__created["payload"]["parent"]["side"]["id"] == side_id

        assert level_two2__created["event"] == "test.level_two.created"
        assert level_two2__created["objectId"] == str(two2.id)
        assert level_two2__created["payload"]["name"] == "more two"
        assert level_two2__created["payload"]["parent"]["id"] == one_id
        assert level_two2__created["payload"]["parent"]["side"]["id"] == side_id

        assert level_two__updated["event"] == "test.level_two.updated"
        assert level_two__updated["objectId"] == str(two.id)
        assert level_two__updated["payload"]["name"] == "updated name"
        assert level_two__updated["payload"]["parent"]["id"] == one_id
        assert level_two__updated["payload"]["parent"]["many"] == []
        assert level_two__updated["payload"]["parent"]["side"]["id"] == side_id

        assert level_two2__updated["event"] == "test.level_two.updated"
        assert level_two2__updated["objectId"] == str(two2.id)
        assert level_two2__updated["payload"]["name"] == "more two"
        assert level_two2__updated["payload"]["parent"]["id"] == one_id
        assert level_two2__updated["payload"]["parent"]["many"] == []
        assert level_two2__updated["payload"]["parent"]["side"]["id"] == side_id
        assert level_two2__updated["payload"]["levelthreeSet"][0]["id"] == three2_id

        assert m2m__updated["event"] == "test.level_two.updated"
        assert m2m__updated["objectId"] == str(two.id)
        assert m2m__updated["payload"]["parent"]["many"][0]["id"] == many_id
        assert len(m2m__updated["payload"]["parent"]["many"]) == 1

        assert m2m_2__updated["event"] == "test.level_two.updated"
        assert m2m_2__updated["objectId"] == str(two2.id)
        assert m2m_2__updated["payload"]["parent"]["many"][0]["id"] == many_id
        assert len(m2m_2__updated["payload"]["parent"]["many"]) == 1

        assert level_two__deleted["event"] == "test.level_two.deleted"
        assert level_two__deleted["objectId"] == str(two.id)
        assert not level_two__deleted["payload"]

        assert level_two2__deleted["event"] == "test.level_two.deleted"
        assert level_two2__deleted["objectId"] == str(two2.id)
        assert not level_two2__deleted["payload"]
    finally:
        unregister_webhook(LevelTwoSerializer)
