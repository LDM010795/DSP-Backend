# Generated by Django 5.1.7 on 2025-07-08 20:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='email',
            field=models.EmailField(default='temp@example.com', help_text='Geschäftliche E-Mail-Adresse des Mitarbeiters', max_length=254, unique=True, verbose_name='E-Mail-Adresse'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['email'], name='employees_e_email_8f5bbc_idx'),
        ),
    ]
