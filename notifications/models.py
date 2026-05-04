from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        DANGER = "danger", "Danger"
        CRITICAL = "critical", "Critical"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-Application"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        PUSH = "push", "Push Notification"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    
    is_read = models.BooleanField(default=False)
    delivery_status = models.CharField(max_length=20, default="delivered")
    
    related_memo = models.ForeignKey(
        "memos.Memo", on_delete=models.SET_NULL, null=True, blank=True, related_name="related_notifications"
    )
    
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["channel", "delivery_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} -> {self.user} ({self.channel})"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Preferences for {self.user}"
