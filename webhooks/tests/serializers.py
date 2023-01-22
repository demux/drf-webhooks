from rest_framework import serializers

from .models import LevelOne, LevelOneSide, LevelThree, LevelTwo


class LevelThreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelThree
        fields = ('id', 'name',)


class LevelOneSideSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelOneSide
        fields = ('id', 'name',)


class LevelOneSerializer(serializers.ModelSerializer):
    side = LevelOneSideSerializer(many=False)

    class Meta:
        model = LevelOne
        fields = ('id', 'name', 'side')


class LevelTwoSerializer(serializers.ModelSerializer):
    parent = LevelOneSerializer(many=False)
    levelthree_set = LevelThreeSerializer(many=True)

    class Meta:
        model = LevelTwo
        fields = ('id', 'name', 'parent', 'levelthree_set')
