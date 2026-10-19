from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from onboarding.auth_views import RoleLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", RoleLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("health.urls")),
    path("", include("onboarding.urls")),
]
