from django.urls import path

from mail import views

urlpatterns = [
    path('', views.list_logs, name='list_mail_logs'),
    path('update/', views.update_email_statuses, name='update_email_statuses'),
]
