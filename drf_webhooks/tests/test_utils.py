from django.contrib.auth import get_user_model

from drf_webhooks.utils import get_serializer_query_names

from .models import LevelOne, LevelOneSide, LevelThree, LevelTwo, Many
from .serializers import LevelTwoSerializer


def test_get_serializer_model_fields(db):
    owner = get_user_model().objects.create()
    one = LevelOne.objects.create(name="one", owner=owner)
    side = LevelOneSide.objects.create(name="side", one=one)
    two = LevelTwo.objects.create(name="two", parent=one)
    three = LevelThree.objects.create(name="three", parent=two)
    many = Many.objects.create(name="Many")
    many.level_ones.add(one)

    two.refresh_from_db()
    serializer = LevelTwoSerializer(two)

    fields = list(get_serializer_query_names(serializer))

    expected = [
        (LevelOne, 'parent'),
        (LevelOneSide, 'parent__side'),
        (Many, 'parent__many'),
        (LevelThree, 'levelthree'),
    ]

    assert fields == expected
