from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        DANGER = "danger", "Danger"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} -> {self.user}"
