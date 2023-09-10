from django.urls import path

from dashboard import views

urlpatterns = [
    path('', views.index, name='dashboard_index'),
    path('documents/', views.documents, name='documents'),
    path('site-setup/', views.setup, name='dashboard_setup'),
    path('view_document/<int:document_id>/',
         views.frozen_document,
         name='frozen_document'),
]
