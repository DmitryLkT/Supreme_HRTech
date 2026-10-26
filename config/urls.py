from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("health.urls")),
    path("", include("journey.urls")),
    path("", include("onboarding.urls")),
    path("", include("users.urls")),
]
