from django.urls import path

from . import views

urlpatterns = [
    path("path/", views.path, name="path"),
    path("path/steps/<int:step_id>/toggle/", views.toggle_step, name="toggle_step"),
    path("mentor/", views.mentor, name="mentor"),
    path("hr/path/", views.hr_path, name="hr_path"),
    path("hr/mentor/", views.hr_mentor, name="hr_mentor"),
    path("hr/mentor/<int:question_id>/answer/", views.hr_mentor_answer, name="hr_mentor_answer"),
]
