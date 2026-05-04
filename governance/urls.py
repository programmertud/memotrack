from django.urls import path
from . import views

app_name = 'governance'

urlpatterns = [
    path('policies/', views.policy_list, name='policy_list'),
    path('policies/create/', views.policy_create, name='policy_create'),
    path('policies/<int:pk>/edit/', views.policy_edit, name='policy_edit'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
]
