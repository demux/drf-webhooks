from django.contrib.auth import get_user_model
from django.db import models


class LevelOne(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"LevelOne(id={self.id}, name={self.name})"


class LevelOneSide(models.Model):
    name = models.CharField(max_length=100)
    one = models.OneToOneField(LevelOne, related_name='side', on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"LevelOneSide(id={self.id}, name={self.name})"


class LevelTwo(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(LevelOne, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"LevelTwo(id={self.id}, name={self.name})"


class LevelThree(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(LevelTwo, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"LevelThree(id={self.id}, name={self.name})"


class Many(models.Model):
    name = models.CharField(max_length=100)
    level_ones = models.ManyToManyField(LevelOne, blank=True, null=True, related_name="many")

    def __str__(self) -> str:
        return f"Many(id={self.id}, name={self.name})"
