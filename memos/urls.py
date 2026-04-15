from django.urls import path

from . import views

app_name = "memos"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("memos/", views.memo_list, name="memo_list"),
    path("manage/memos/", views.memo_admin_list, name="memo_admin_list"),
    path("memos/create/", views.memo_create, name="memo_create"),
    path("memos/<int:pk>/edit/", views.memo_edit, name="memo_edit"),
    path("memos/<int:pk>/delete/", views.memo_delete, name="memo_delete"),
    path("memos/<int:pk>/answer/approve/", views.memo_user_approve, name="memo_user_approve"),
    path("memos/<int:pk>/answer/conflict/", views.memo_user_mark_conflict, name="memo_user_mark_conflict"),
    path("memos/<int:pk>/conflict/", views.memo_conflict, name="memo_conflict"),
    path("memos/<int:pk>/conflict/accept/", views.memo_conflict_accept, name="memo_conflict_accept"),
    path("memos/<int:pk>/conflict/delegate/", views.memo_conflict_delegate, name="memo_conflict_delegate"),
    path("memos/<int:pk>/conflict/reschedule/", views.memo_conflict_reschedule, name="memo_conflict_reschedule"),
    path("decisions/", views.decision_panel, name="decision_panel"),
    path("decisions/<int:pk>/approve/", views.decision_approve, name="decision_approve"),
    path("decisions/<int:pk>/reject/", views.decision_reject, name="decision_reject"),
]
