from django.urls import path

from . import views

app_name = "memos"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("memos/", views.memo_list, name="memo_list"),
    path("manage/memos/", views.memo_admin_list, name="memo_admin_list"),
    path("requests/", views.memo_request_list, name="memo_request_list"),
    path("requests/create/", views.memo_request_create, name="memo_request_create"),
    path("requests/<int:pk>/", views.memo_request_detail, name="memo_request_detail"),
    path("requests/<int:pk>/approve/", views.memo_request_approve, name="memo_request_approve"),
    path("requests/<int:pk>/reject/", views.memo_request_reject, name="memo_request_reject"),
    path("memos/create/", views.memo_create, name="memo_create"),
    path("activity-designs/create/", views.activity_design_create, name="activity_design_create"),
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
    path("memos/parse-ai/", views.memo_parse_ai, name="memo_parse_ai"),
    path("memos/parse-ai-file/", views.memo_parse_ai_file, name="memo_parse_ai_file"),
    path("check-conflicts/", views.memo_check_conflicts, name="memo_check_conflicts"),
    path("recommend-slots/", views.memo_recommendations, name="memo_recommendations_new"),
    path("recommend-slots/<int:pk>/", views.memo_recommendations, name="memo_recommendations"),
]

