# Generated by Django 5.1.1 on 2024-11-16 21:32

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Time_Banking", "0003_listing_status_alter_listing_creator_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Skill",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.AlterField(
            model_name="listing",
            name="creator",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="services",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="listing_type",
            field=models.CharField(
                choices=[("Offer", "Offer"), ("Request", "Request")],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="skills",
            field=models.ManyToManyField(blank=True, to="Time_Banking.skill"),
        ),
    ]
