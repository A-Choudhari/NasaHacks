
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("like/<int:post_id>", views.like, name="like"),
    path("new_post", views.newpost, name="new_post"),
    path("profile/<int:profile_id>", views.profile, name="profile"),
    path("following", views.following, name="following"),
    path("edit/<int:edit_id>", views.edit, name="edit"),
    path("follow", views.follow_user, name="follow"),
    path("unfollow", views.unfollow_user, name="unfollow"),
]
