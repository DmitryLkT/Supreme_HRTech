from django.urls import path
from . import views, hr_views

urlpatterns = [
    path("", views.home, name="home"),
    path("hr/", hr_views.hr_dashboard, name="hr_dashboard"),
    path("hr/employees/<int:user_id>/", hr_views.hr_employee_detail, name="hr_employee_detail"),
    path("hr/answers/", hr_views.hr_answers, name="hr_answers"),
    path("modules/<int:module_id>/", views.module_detail, name="module_detail"),
    path("modules/<int:module_id>/complete/", views.complete_module, name="complete_module"),
    path("questions/<int:question_id>/answer/", views.answer_question, name="answer_question"),
]
