from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4


class User(AbstractUser):
    country = models.CharField(max_length=16, default = uuid4, null=False, blank=False)
