# Generated by Django 4.1.5 on 2023-02-20 15:31

import uuid

import django.db.models.deletion
import swapper
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                (
                    'events',
                    ArrayField(base_field=models.CharField(db_index=True, max_length=128), size=None),
                ),
                ('target_url', models.URLField(max_length=255)),
                (
                    'target_method',
                    models.CharField(
                        choices=[
                            ('get', 'GET'),
                            ('put', 'PUT'),
                            ('post', 'POST'),
                            ('patch', 'PATCH'),
                            ('delete', 'DELETE'),
                        ],
                        default='post',
                        max_length=6,
                    ),
                ),
                (
                    'target_content_type',
                    models.CharField(
                        choices=[('application/json', 'JSON'), ('application/xml', 'XML')],
                        default='application/json',
                        max_length=64,
                    ),
                ),
                ('target_headers', models.JSONField(default=dict)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'swappable': swapper.swappable_setting('webhooks', 'Webhook'),
                'verbose_name': 'webhook',
                'verbose_name_plural': 'webhooks',
            },
        ),
        migrations.CreateModel(
            name='WebhookLogEntry',
            fields=[
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('event', models.CharField(db_index=True, max_length=64)),
                ('req_dt', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('req_url', models.URLField(db_index=True, max_length=255)),
                ('req_method', models.CharField(db_index=True, max_length=6)),
                ('req_headers', models.JSONField()),
                ('req_data', models.JSONField(blank=True, null=True)),
                ('req_content', models.TextField(blank=True)),
                ('res_dt', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('res_data', models.JSONField(blank=True, null=True)),
                ('res_content', models.TextField(blank=True)),
                ('res_headers', models.JSONField(blank=True, null=True)),
                ('res_status', models.PositiveSmallIntegerField(blank=True, db_index=True, null=True)),
                ('error_code', models.CharField(blank=True, db_index=True, max_length=100)),
                ('error_message', models.TextField(blank=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                (
                    'webhook',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='log_entries',
                        to=settings.WEBHOOKS_WEBHOOK_MODEL,
                    ),
                ),
            ],
            options={
                'swappable': swapper.swappable_setting('webhooks', 'WebhookLogEntry'),
                'verbose_name': 'webhook log entry',
                'verbose_name_plural': 'webhook log',
            },
        ),
    ]
