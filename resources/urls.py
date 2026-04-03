from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    path("", views.vehicle_list, name="vehicle_list"),
    path("admin/", views.vehicle_admin_list, name="vehicle_admin_list"),
    path("admin/create/", views.vehicle_admin_create, name="vehicle_admin_create"),
    path("admin/<int:pk>/edit/", views.vehicle_admin_edit, name="vehicle_admin_edit"),
    path("admin/<int:pk>/delete/", views.vehicle_admin_delete, name="vehicle_admin_delete"),
    path("book/<int:memo_id>/", views.vehicle_book, name="vehicle_book"),
    path("trips/", views.grouped_trips, name="grouped_trips"),
]
