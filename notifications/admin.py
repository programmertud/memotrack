from django.contrib import admin

from .models import Notification, NotificationPreference

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_enabled", "sms_enabled", "push_enabled", "in_app_enabled")
    search_fields = ("user__username", "user__email")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "severity", "channel", "is_read", "delivery_status", "created_at")
    list_filter = ("severity", "channel", "is_read", "delivery_status")
    search_fields = ("title", "message", "user__username", "user__email")
    autocomplete_fields = ("user", "related_memo")
