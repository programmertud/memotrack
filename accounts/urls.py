from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("post-login/", views.post_login, name="post_login"),
    path("dashboards/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboards/hr/", views.hr_dashboard, name="hr_dashboard"),
    path("dashboards/instructor/", views.instructor_dashboard, name="instructor_dashboard"),
    path("dashboards/approver/", views.approver_dashboard, name="approver_dashboard"),
    path(
        "dashboards/transportation/",
        views.transportation_dashboard,
        name="transportation_dashboard",
    ),

    path("admin/users/<str:role>/", views.admin_user_list, name="admin_user_list"),
    path("admin/users/<str:role>/create/", views.admin_user_create, name="admin_user_create"),
    path(
        "admin/users/<str:role>/<int:pk>/edit/",
        views.admin_user_edit,
        name="admin_user_edit",
    ),
    path(
        "admin/users/<str:role>/<int:pk>/delete/",
        views.admin_user_delete,
        name="admin_user_delete",
    ),
]
