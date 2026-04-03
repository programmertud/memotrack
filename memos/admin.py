from django.contrib import admin

from .models import Memo, MemoDecision


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "assigned_user",
        "date",
        "start_time",
        "end_time",
        "priority",
        "required",
        "status",
    )
    list_filter = ("priority", "required", "status", "date")
    search_fields = ("title", "description", "venue", "destination", "assigned_user__username")
    autocomplete_fields = ("assigned_user", "delegated_to")


@admin.register(MemoDecision)
class MemoDecisionAdmin(admin.ModelAdmin):
    list_display = ("memo", "action", "decided_by", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("memo__title", "memo__assigned_user__username", "decided_by__username", "note")
    autocomplete_fields = ("memo", "decided_by")
