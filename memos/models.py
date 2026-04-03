from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils import timezone


class Memo(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DELEGATED = "delegated", "Delegated"
        CONFLICT = "conflict", "Conflict"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memos"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    venue = models.CharField(max_length=255, blank=True)
    destination = models.CharField(max_length=255, blank=True)

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    required = models.BooleanField(default=False)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    delegated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_memos",
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "start_time"]
        indexes = [
            models.Index(fields=["assigned_user", "date", "start_time", "end_time"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.assigned_user})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def conflicts_queryset(self):
        qs = Memo.objects.filter(assigned_user=self.assigned_user, date=self.date)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.filter(Q(start_time__lt=self.end_time) & Q(end_time__gt=self.start_time))

    def has_conflicts(self) -> bool:
        return self.conflicts_queryset().exists()

    def suggested_decision(self) -> str:
        if not self.has_conflicts():
            return "approve"
        if self.required and self.priority in {self.Priority.HIGH, self.Priority.MEDIUM}:
            return "accept_anyway"
        if self.priority == self.Priority.LOW and not self.required:
            return "reschedule"
        return "delegate"


class MemoDecision(models.Model):
    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"

    memo = models.ForeignKey(Memo, on_delete=models.CASCADE, related_name="decisions")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["memo", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]
