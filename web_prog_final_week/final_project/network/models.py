from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Type(models.Model):
    titles = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.titles}"


class DoctorApply(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="doctor_apply_id")
    type = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="doctor_type")
    degree = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        return f"{self.user} is a {self.type}"


class Doctor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="doctor_id")
    type = models.ForeignKey(Type, on_delete=models.CASCADE, related_name="type")
    degree = models.CharField(max_length=1024, blank=True)
    doctor_message = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        return f"{self.user} is a {self.type}"


class Text(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender_id")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="receiver_id")
    text = models.CharField(max_length=512)
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    def __str__(self):
        return f"{self.sender} sent to {self.receiver}: {self.text}"

    def serialize(self):
        return {
            "id": self.id,
            "sender":self.sender.username,
            "receiver": self.receiver.username,
            "text": self.text,
            "timestamp": self.timestamp.strftime("%b %d %Y, %I:%M %p")
        }



class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="doctor")
    messages = models.ManyToManyField(Text, blank=True, null=True, related_name="messages")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} and {self.doctor} are talking."

    def serialize(self):
        return {
            "id": self.id,
            "user":self.user,
            "doctor": self.doctor.user.username,
            "messages": [user.text for user in self.messages.all()],
            "is_active": self.is_active,
        }


