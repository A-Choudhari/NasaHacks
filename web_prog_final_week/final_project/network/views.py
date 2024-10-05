import json
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.core.paginator import Paginator
from .models import User, Type, Doctor, Text, Message, DoctorApply


def index(request):
    is_doctor = ''
    page_obj = ''
    if request.user.is_authenticated:
        try:
            is_doctor = Doctor.objects.get(user=request.user)
            all_posts = Message.objects.filter(doctor=is_doctor, is_active=False).reverse()
        except:
            all_posts = Message.objects.filter(user=request.user, is_active=False).reverse()

        p = Paginator(all_posts, 10)
        page_number = request.GET.get('page')
        page_obj = p.get_page(page_number)
    return render(request, "network/index.html", {"posts": page_obj, "is_doctor":is_doctor})


def old_message(request, convo_id):
    all_posts = Message.objects.get(pk=convo_id)
    return JsonResponse([post.serialize() for post in all_posts.messages.all()], safe=False)


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")


def doctor_app(request):
    types = Type.objects.all()
    return render(request, "network/doctor_apply.html", {"types": types})


def add_doctor(request):
    if request.method == "POST":
        types = Type.objects.all()
        title = request.POST["title"]
        type= Type.objects.get(titles=title)
        filename = request.POST["filename"]
        if title is not None and filename is not None:
            new_doctor = DoctorApply(user=request.user, type=type, degree=filename)
            new_doctor.save()
            return render(request, "network/index.html", {"message":"Your application is currently under review"})
        else:
            return render(request, "network/doctor_apply.html", {"types": types, "message":"Please fill in all required"
                                                                                           " portions appropriately"})


def end_chat(request):
    if request.method == "POST":
        message_id = request.POST["end_chat"]
        message = Message.objects.get(pk=message_id)
        message.is_active = False
        message.save()
        return HttpResponseRedirect(reverse("index"))


def chat_doctor(request):
    doctor = ""
    try:
        is_doctor = Doctor.objects.get(user=request.user)
        patient_message = Message.objects.filter(doctor=is_doctor)
    except:
        patient_message = Message.objects.filter(user=request.user)
    doctor_type = Type.objects.all()
    no_chat = True
    chat_message = []
    for patient in patient_message:
        if patient.is_active:
            no_chat = False
            doctor = patient
            chat_message = patient.messages.all()
            break
    return render(request, "network/doctor_chat.html", {"doctor": doctor, "no_chat": no_chat,
                                                        "chat_messages": chat_message, "doctor_type": doctor_type})


def find_doctor(request):
    if request.method == "PUT":
        data = json.loads(request.body)
        if data.get("doctor_type") is not None:
            types = data["doctor_type"]
            model_type = Type.objects.get(titles=types)
            doctors = Doctor.objects.filter(type=model_type)
            for doctor in doctors:
                messages = Message.objects.filter(doctor=doctor).reverse()
                if request.user != doctor.user:
                    if not messages:
                        new_message = Message(user=request.user, doctor=doctor)
                        new_message.doctor.doctor_message = "Patient is waiting in chat room"
                        new_message.save()
                        message_id = new_message.pk
                        return JsonResponse({"doctor": "Doctor " + doctor.user.username, "type": types,
                                             "id":message_id})
                    for message in messages:
                        if not message.is_active:
                            new_message = Message(user=request.user, doctor=doctor)
                            new_message.doctor.doctor_message = "Patient is waiting in chat room"
                            new_message.save()
                            message_id = new_message.pk
                            return JsonResponse({"doctor": "Doctor " + doctor.user.username, "type": types,
                                                 "id": message_id})
            return JsonResponse({"message": "Doctor for this field is not available"})


def send_message(request, message_id):
    if request.method == "PUT":
        data = json.loads(request.body)
        if data.get("text") is not None:
            new_text = data["text"]
            print(new_text)
            conversation = Message.objects.get(pk=message_id)

            if conversation.user == request.user:
                new_message = Text(sender=request.user, receiver=conversation.doctor.user, text=new_text)
            else:
                new_message = Text(sender=request.user, receiver=conversation.user, text=new_text)
            new_message.save()
            conversation.messages.add(new_message)
            conversation.save()
            return JsonResponse([post.serialize() for post in conversation.messages.all()], safe=False)
