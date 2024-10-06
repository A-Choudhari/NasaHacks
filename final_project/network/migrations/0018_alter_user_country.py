# Generated by Django 5.1.1 on 2024-10-06 21:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0017_alter_user_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='country',
            field=models.CharField(choices=[('US', 'United States'), ('CA', 'Canada'), ('GB', 'United Kingdom'), ('DE', 'Germany'), ('FR', 'France'), ('IT', 'Italy'), ('ES', 'Spain'), ('MX', 'Mexico'), ('IN', 'India'), ('CN', 'China'), ('JP', 'Japan'), ('BR', 'Brazil'), ('AU', 'Australia'), ('RU', 'Russia')], default='US', max_length=2),
        ),
    ]
