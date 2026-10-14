from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .models import  Profile, Message,  Contact
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from .consumers import online_users

# Create your views here.


def normalize_phone(value):
    value = value.strip().replace(' ', '').replace('-', '')
    if value.startswith('0'):
        value = '+92' +value[1:]
    return value

def is_valid_phone(value):
    digits = value.lstrip('+')
    return digits.isdigit() and 10 <= len(digits) <= 15



@login_required
def chat(request, user_id=None):
    selected = None
    chat_messages = []

    if user_id:
        selected = get_object_or_404(User, id=user_id)

        # Remember this chat in the sidebar, even before any message is sent
        Contact.objects.get_or_create(owner=request.user, contact=selected)

        chat_messages = Message.objects.filter(
            Q(sender=request.user, receiver=selected) |
            Q(sender=selected, receiver=request.user)
        )

    # People I added + people I have exchanged messages with
    added = Contact.objects.filter(owner=request.user).values_list('contact_id', flat=True)
    sent = Message.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
    got = Message.objects.filter(receiver=request.user).values_list('sender_id', flat=True)
    ids = set(added) | set(sent) | set(got)

    users = User.objects.filter(id__in=ids).exclude(id=request.user.id)

    return render(request, "chat.html", {
        'users': users,
        'selected': selected,
        'chat_messages': chat_messages,
        'online_ids': list(online_users.keys()),
        'notfound': request.GET.get('notfound'),
    })




def login(request):
    if request.user.is_authenticated:
        return redirect("chat")

    error = None
    if request.method=="POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        username = None

        if '@' in email:
           username = email.lower()

        else:
            phone = normalize_phone(email)
            profile = Profile.objects.select_related('user').filter(phone = phone).first()

            if profile:
                username = profile.user.username

        user = authenticate(request, username = username, password = password ) if username else None

        if user is not None:
            auth_login(request, user)
            return redirect('chat')

        error = 'Invalid email/phone or password.'



    return render(request, "login.html", {'error': error})
  




def register(request):
    if request.user.is_authenticated:
        return redirect('login')

    error = None
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = normalize_phone(request.POST.get('phone', ''))
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm', '')

        if not name or not email:
            error = 'Name and email are required.'
        elif not is_valid_phone(phone):
            error = 'Enter  valid Phone Number.'
        elif len(password)<8:
            error = 'password must be atleast 8 characters.'
        elif password != confirm:
            error = 'Passwords do not match.'
        elif User.objects.filter(username= email).exists():
            error = 'An account with this email already exists.'   
        elif Profile.objects.filter(phone = phone).exists():
            error = 'An account with this phone number already exists.'

        else:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name= name
                )
                Profile.objects.create(user=user, phone=phone, public_key=request.POST.get('public_key', ''))
            auth_login(request, user)
            return redirect('login')
    return render(request, "register.html", {'error': error})




def logout(request):
    auth_logout(request)
    return redirect('login')



@login_required
def save_key(request):
    if request.method != "POST":
        return JsonResponse({'ok': False}, status=405)

    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        return JsonResponse({'ok': False}, status=400)

    profile.public_key = request.POST.get('public_key', '')
    profile.save()

    return JsonResponse({'ok': True})

@login_required
def get_key(request, user_id):
    profile = Profile.objects.filter(user_id=user_id).first()
    key = profile.public_key if profile else ''
    return JsonResponse({'public_key':key})



@login_required
def find_user(request):
    q = request.GET.get('q', '').strip()
    user = None

    if '@' in q:
        user = User.objects.filter(username=q.lower()).exclude(id=request.user.id).first()
    elif q:
        profile = Profile.objects.select_related('user').filter(
            phone=normalize_phone(q)
        ).exclude(user=request.user).first()
        if profile:
            user = profile.user

    if user:
        return redirect('chat_with', user_id=user.id)

    return redirect('/chat?notfound=1')