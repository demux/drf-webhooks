from django.db import models


class WebhookOwner(models.Model):
    name = models.CharField(max_length=100) 


class LevelOne(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(WebhookOwner, on_delete=models.CASCADE)

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
