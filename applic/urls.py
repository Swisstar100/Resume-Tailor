from django.contrib import admin
from django.urls import path
from . import views
from uuid import UUID

app_name = 'applications'

urlpatterns = [
    path('create/', views.create_application_view, name='create_application'),
    path("<uuid:app_id>", views.application_view, name="application"),
    path("<uuid:app_id>/optimize", views.create_ai_application, name="optimize"),
    path("<uuid:app_id>/feedback", views.student_improvements, name="feedback"),
    path('home/', views.board_view, name='board'),
    path('status/', views.application_status, name='status'),
    path('<uuid:app_id>/task-status/', views.application_task_status, name='task_status'),
]