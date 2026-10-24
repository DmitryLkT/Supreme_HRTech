from django.urls import path

from . import views

urlpatterns = [
    path("health/questionnaires/versions/<int:version_id>/", views.questionnaire_detail, name="questionnaire_detail"),
    path("hr/report/", views.hr_report, name="hr_report"),
    path("", views.health_entry, name="health_form"),
]
