from django.contrib import admin
from .models import User, Message, Type, Text, Doctor, DoctorApply
# Register your models here.

admin.site.register(User)
admin.site.register(Text)
admin.site.register(Type)
admin.site.register(Message)
admin.site.register(Doctor)
admin.site.register(DoctorApply)
