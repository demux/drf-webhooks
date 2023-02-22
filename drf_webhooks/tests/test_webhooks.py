import json

import pytest
from django.contrib.auth import get_user_model
from pytest_httpx import HTTPXMock

from ..config import REGISTERED_WEBHOOK_CHOICES, conf
from ..main import ModelSerializerWebhook
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


def test_serializer_webhook_getters_not_implemented():
    with pytest.raises(NotImplementedError):

        class LevelTwoSerializerWebhook(ModelSerializerWebhook):
            serializer_class = LevelTwoSerializer
            base_name = 'test.level_two'


def test_serializer_webhook_getters_duplicate_base_name():
    with pytest.raises(RuntimeError):

        class LevelOneSideSerializerWebhook(ModelSerializerWebhook):
            serializer_class = LevelOneSideSerializer
            base_name = 'test.level'

        class LevelThreeSerializerWebhook2(ModelSerializerWebhook):
            serializer_class = LevelThreeSerializer
            base_name = 'test.level'


def test_serializer_webhook_getters_duplicate_serializer():
    with pytest.raises(RuntimeError):

        class LevelThreeSerializerWebhook(ModelSerializerWebhook):
            serializer_class = LevelThreeSerializer
            base_name = 'test.level_three'

        class LevelThreeSerializerWebhook2(ModelSerializerWebhook):
            serializer_class = LevelThreeSerializer
            base_name = 'test.level_three_2'


def test_serializer_webhook_define_success():
    class LevelTwoSerializerWebhook(ModelSerializerWebhook):
        serializer_class = LevelTwoSerializer
        base_name = 'test.level_two'

        # signal_model_instance_base_getters = {
        #     LevelOne: lambda x: x.level_two_set.all(),
        #     LevelOneSide: lambda x: x.one.level_two_set.all(),
        #     LevelThree: lambda x: [x.parent],
        #     Many: lambda x: [two for one in x.level_ones.all() for two in one.leveltwo_set.all()],
        # }

    try:
        assert REGISTERED_WEBHOOK_CHOICES['test.level_two.created'] == "Level Two Created"
        assert REGISTERED_WEBHOOK_CHOICES['test.level_two.updated'] == "Level Two Updated"
        assert REGISTERED_WEBHOOK_CHOICES['test.level_two.deleted'] == "Level Two Deleted"
    finally:
        LevelTwoSerializerWebhook.disconnect()


def test_serializer_webhook_events(db, httpx_mock: HTTPXMock):
    class LevelTwoSerializerWebhook(ModelSerializerWebhook):
        serializer_class = LevelTwoSerializer
        base_name = 'test.level_two'

        signal_model_instance_base_getters = {
            LevelOne: lambda x: x.leveltwo_set.all(),
            LevelOneSide: lambda x: x.one.leveltwo_set.all(),
            LevelThree: lambda x: [x.parent],
            Many: lambda x: [two for one in x.level_ones.all() for two in one.leveltwo_set.all()],
        }

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
        LevelTwoSerializerWebhook.disconnect()
