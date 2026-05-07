from django.contrib import admin

from .models import Memo, MemoDecision


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "get_employees",
        "date",
        "start_time",
        "end_time",
        "priority",
        "required",
        "status",
    )
    list_filter = ("priority", "required", "status", "date")
    search_fields = ("title", "description", "venue", "destination", "employees__username", "employees__profile__first_name", "employees__profile__last_name")
    autocomplete_fields = ("employees", "delegated_to")
    filter_horizontal = ("employees",)

    def get_employees(self, obj):
        return ", ".join([f"{u.profile.first_name} {u.profile.last_name}" if hasattr(u, 'profile') and u.profile.first_name else u.username for u in obj.employees.all()])
    get_employees.short_description = "Employees"


@admin.register(MemoDecision)
class MemoDecisionAdmin(admin.ModelAdmin):
    list_display = ("memo", "action", "decided_by", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("memo__title", "memo__employees__username", "decided_by__username", "note")
    autocomplete_fields = ("memo", "decided_by")



