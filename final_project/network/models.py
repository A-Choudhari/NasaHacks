from django.contrib.auth.models import AbstractUser
from django.db import models


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


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_id")
    likes = models.IntegerField(default=0)
    text = models.CharField(max_length=500)
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    def __str__(self):
        return f"{self.user} posted {self.text} at {self.timestamp}"


class Follows(models.Model):
    following = models.ForeignKey(User, blank=True, on_delete=models.CASCADE, related_name="user_following")
    followed = models.ForeignKey(User, blank=True, on_delete=models.CASCADE, related_name="user_followed")

    def __str__(self):
        return f"{self.following} follows {self.followed}"


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_liked")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_name")

    def __str__(self):
        return f"{self.user} liked {self.post}"

