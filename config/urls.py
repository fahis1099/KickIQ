"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.shortcuts import redirect
from django.contrib import admin
from django.urls import include, path
from core.views import (
    home,
    login_page, 
    player_dashboard,
    players_page,
    register_page,
    player_performance_page,
)

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("dashboard/", player_dashboard, name="player-dashboard"),
    path("login/", login_page, name="login-page"),
    path("register/", register_page, name="register-page"),
    path("players/", players_page, name="players-page"),
    path("players/<int:player_id>/",player_performance_page, name="player-performance-page"),
]