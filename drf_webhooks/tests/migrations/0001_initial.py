# Generated by Django 4.1.7 on 2023-02-21 15:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LevelOne',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Many',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('level_ones', models.ManyToManyField(blank=True, null=True, related_name='many', to='tests.levelone')),
            ],
        ),
        migrations.CreateModel(
            name='LevelTwo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tests.levelone')),
            ],
        ),
        migrations.CreateModel(
            name='LevelThree',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tests.leveltwo')),
            ],
        ),
        migrations.CreateModel(
            name='LevelOneSide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                (
                    'one',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name='side', to='tests.levelone'
                    ),
                ),
            ],
        ),
    ]
