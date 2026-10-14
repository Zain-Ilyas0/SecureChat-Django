from django.urls import path
from . import views

urlpatterns = [

    path("chat", views.chat, name="chat"),
    path('chat/<int:user_id>/', views.chat, name='chat_with'),

    path("", views.login, name="login" ),
    path("register/", views.register, name="register"),
    path("logout/", views.logout, name="logout"),
    path('save-key/', views.save_key, name='save_key'),
    path('key/<int:user_id>/', views.get_key, name='get_key'),
    path('find/', views.find_user, name='find_user'),

]


