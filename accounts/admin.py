from django.contrib import admin

from .models import Attendance, Department, LeaveRequest, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "is_present")
    list_filter = ("date", "is_present")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date", "end_date", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "reason")
    autocomplete_fields = ("user",)
