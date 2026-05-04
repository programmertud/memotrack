from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('preferences/', views.notification_preferences, name='preferences'),
    path('list/', views.notification_list, name='notification_list'),
    path('<int:pk>/read/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_read_all, name='mark_all_read'),
]
