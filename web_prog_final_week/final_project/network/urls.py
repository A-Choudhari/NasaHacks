
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("apply", views.doctor_app, name="doctor_app"),
    path("new_doctor", views.add_doctor, name="new_doctor"),
    path("find_doctor", views.find_doctor, name="find_doctor"),
    path("chat", views.chat_doctor, name="doctor_chat"),
    path("send_message/<int:message_id>", views.send_message, name="send_message"),
    path("old_message/<int:convo_id>", views.old_message, name="old_message"),
    path("end_chat", views.end_chat, name="end_chat"),
]
