from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4


class User(AbstractUser):
    COUNTRIES = [
        ('US', 'United States'),
        ('CA', 'Canada'),
        ('GB', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('MX', 'Mexico'),
        ('IN', 'India'),
        ('CN', 'China'),
        ('JP', 'Japan'),
        ('BR', 'Brazil'),
        ('AU', 'Australia'),
        ('RU', 'Russia'),
        # Add more countries as needed
    ]
    country = models.CharField(max_length=2, choices=COUNTRIES, default='US')
