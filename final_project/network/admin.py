from django.contrib import admin
from .models import User, Post, Follows, Like
# Register your models here.

admin.site.register(Post)
admin.site.register(User)
admin.site.register(Follows)
admin.site.register(Like)