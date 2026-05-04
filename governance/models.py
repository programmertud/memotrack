from django.db import models
from django.conf import settings
from django.utils import timezone


class Policy(models.Model):
    class Type(models.TextChoices):
        PRIORITY = "priority", "Priority Hierarchy"
        RESTRICTION = "restriction", "Departmental Restriction"
        ALLOCATION = "allocation", "Venue Allocation Rule"

    name = models.CharField(max_length=200)
    policy_type = models.CharField(max_length=20, choices=Type.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    rule_definition = models.JSONField(help_text="JSON representation of the policy logic.")
    
    priority_weight = models.PositiveIntegerField(default=0, help_text="Used to resolve conflicts between policies.")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Policies"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_policy_type_display()})"


class SchedulingAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        OVERRIDE = "override", "Policy Override"
        CONFLICT_RESOLVED = "conflict_resolved", "Conflict Resolved"

    memo = models.ForeignKey("memos.Memo", on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.action} on {self.memo} by {self.actor}"
