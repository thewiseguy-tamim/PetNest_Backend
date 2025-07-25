# Generated by Django 5.2.4 on 2025-07-24 20:38

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='nid_back',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='nid_back'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='nid_front',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='nid_front'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='profile_picture',
            field=cloudinary.models.CloudinaryField(blank=True, default='default.png', max_length=255, null=True, verbose_name='profile_picture'),
        ),
        migrations.AlterField(
            model_name='verificationrequest',
            name='nid_back',
            field=cloudinary.models.CloudinaryField(max_length=255, verbose_name='verification_back'),
        ),
        migrations.AlterField(
            model_name='verificationrequest',
            name='nid_front',
            field=cloudinary.models.CloudinaryField(max_length=255, verbose_name='verification_front'),
        ),
    ]
