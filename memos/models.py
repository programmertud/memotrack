from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils import timezone


class Memo(models.Model):
    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DELEGATED = "delegated", "Delegated"
        CONFLICT = "conflict", "Conflict"

    class Category(models.TextChoices):
        INTERNAL = "internal", "Internal"
        EXTERNAL = "external", "External"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_memos",
    )
    employees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="memos", blank=True
    )
    to_all = models.BooleanField(default=False)

    reference_number = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    venue = models.CharField(max_length=255, blank=True)
    destination = models.CharField(max_length=255, blank=True)

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    required = models.BooleanField(default=False)

    category = models.CharField(max_length=20, choices=Category.choices, default=Category.INTERNAL)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    delegated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_memos",
    )

    # Centralized tracking
    campus = models.ForeignKey(
        "accounts.Campus", on_delete=models.SET_NULL, null=True, blank=True, related_name="memos"
    )
    department = models.ForeignKey(
        "accounts.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="memos"
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "start_time"]
        indexes = [
            models.Index(fields=["date", "start_time", "end_time"]),
        ]

    def __str__(self) -> str:
        if self.to_all:
            emp_list = "All Faculty Members and Student"
        elif not self.pk:
            emp_list = "Unsaved Memo"
        else:
            emp_list = ", ".join([u.get_username() for u in self.employees.all()[:3]])
            if self.employees.count() > 3:
                emp_list += "..."
        return f"{self.title} ({emp_list})"

    def save(self, *args, **kwargs):
        # We handle department/campus assignment after the first save in ManyToMany
        super().save(*args, **kwargs)
        
        # After save, we can check employees and set department if not exists
        if not self.department and self.employees.exists():
            first_emp = self.employees.first()
            if hasattr(first_emp, 'profile'):
                self.department = first_emp.profile.department
                if self.department and not self.campus:
                    self.campus = self.department.campus
                # Use update to avoid infinite recursion
                Memo.objects.filter(pk=self.pk).update(department=self.department, campus=self.campus)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError("End time must be after start time.")

    def conflicts_queryset(self, user=None):
        if user:
            users = [user]
        else:
            # Note: This only works if instance is saved.
            # For pre-save checks, we might need a different approach.
            users = self.employees.all()

        qs = Memo.objects.filter(employees__in=users, date=self.date)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.filter(Q(start_time__lt=self.end_time) & Q(end_time__gt=self.start_time)).distinct()

    def has_conflicts(self) -> bool:
        # Check conflicts for every assigned employee
        for user in self.employees.all():
            if self.conflicts_queryset(user=user).exists():
                return True
        
        # Check resource conflicts
        for booking in self.resource_bookings.all():
            if booking.has_conflicts():
                return True

        # Check vehicle conflicts
        if hasattr(self, 'vehicle_booking') and self.vehicle_booking.has_conflicts():
            return True

        return False

    def get_employee_names(self) -> str:
        if self.to_all:
            return "All Faculty Members and Student"
        names = []
        for user in self.employees.all():
            if hasattr(user, 'profile') and user.profile.first_name:
                names.append(f"{user.profile.first_name} {user.profile.last_name}")
            else:
                names.append(user.get_full_name() or user.username)
        return ", ".join(names)

    def suggested_decision(self) -> str:
        if not self.has_conflicts():
            return "approve"
        
        # Policy: Critical priority and Institutional-wide (to_all) events take absolute precedence
        if self.priority == self.Priority.CRITICAL or self.to_all:
            return "accept_anyway"
            
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


class MemoRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CONVERTED = "converted", "Converted"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memo_requests"
    )
    attachment = models.FileField(upload_to="memo_requests/")
    note = models.TextField(blank=True, help_text="Optional note from the requester")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Link to the resulting memo if converted
    memo = models.OneToOneField(
        "Memo", on_delete=models.SET_NULL, null=True, blank=True, related_name="origin_request"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request from {self.requester.username} ({self.created_at.strftime('%Y-%m-%d')})"

class ActivityDesign(models.Model):
    title = models.CharField(max_length=200)
    schedule = models.DateTimeField()
    venue = models.CharField(max_length=255)
    target_participants = models.CharField(max_length=255)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    objectives = models.TextField()
    expected_outcomes = models.TextField()

    # ISO Document Controls
    doc_number = models.CharField(max_length=50, default="SNSU-F-AD-01")
    rev_number = models.CharField(max_length=10, default="00")
    effectivity_date = models.DateField(default=timezone.now)

    # Signatures / Approvals
    prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="prepared_activities")
    noted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="noted_activities")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="approved_activities")

    created_at = models.DateTimeField(auto_now_add=True)
    memo = models.OneToOneField("Memo", on_delete=models.CASCADE, null=True, blank=True, related_name="activity_design")

    def __str__(self):
        return self.title


class MultiLevelApprovalRequest(models.Model):
    class Stage(models.TextChoices):
        DRAFT = "draft", "Draft"
        DEPT_HEAD = "dept_head", "Department Head"
        DEAN = "dean", "Dean/Director"
        VP = "vp", "VP"
        PRESIDENT = "president", "President"
        RELEASED = "released", "Released"

    memo_request = models.OneToOneField(MemoRequest, on_delete=models.CASCADE, related_name="approval_flow")
    current_stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.DRAFT)
    
    dept_head_approved = models.BooleanField(default=False)
    dean_approved = models.BooleanField(default=False)
    vp_approved = models.BooleanField(default=False)
    president_approved = models.BooleanField(default=False)

    def advance_stage(self):
        if self.current_stage == self.Stage.DRAFT:
            self.current_stage = self.Stage.DEPT_HEAD
        elif self.current_stage == self.Stage.DEPT_HEAD and self.dept_head_approved:
            self.current_stage = self.Stage.DEAN
        elif self.current_stage == self.Stage.DEAN and self.dean_approved:
            self.current_stage = self.Stage.VP
        elif self.current_stage == self.Stage.VP and self.vp_approved:
            self.current_stage = self.Stage.PRESIDENT
        elif self.current_stage == self.Stage.PRESIDENT and self.president_approved:
            self.current_stage = self.Stage.RELEASED
        self.save()


class InterCampusMemo(models.Model):
    memo = models.OneToOneField(Memo, on_delete=models.CASCADE, related_name="inter_campus_details")
    sender_campus = models.ForeignKey("accounts.Campus", on_delete=models.CASCADE, related_name="sent_inter_campus_memos")
    recipient_campus = models.ForeignKey("accounts.Campus", on_delete=models.CASCADE, related_name="received_inter_campus_memos")
    
    sender_director_approved = models.BooleanField(default=False)
    recipient_director_approved = models.BooleanField(default=False)


class TravelOrder(models.Model):
    memo = models.OneToOneField(Memo, on_delete=models.CASCADE, related_name="travel_order")
    traveler_name = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    purpose = models.TextField()
    duration_days = models.PositiveIntegerField()
    transportation_mode = models.CharField(max_length=100)
    estimated_expenses = models.DecimalField(max_digits=10, decimal_places=2)
    
    dept_head_approved = models.BooleanField(default=False)
    campus_director_approved = models.BooleanField(default=False)

    # ISO Document Controls
    doc_number = models.CharField(max_length=50, default="SNSU-F-TO-01")
    rev_number = models.CharField(max_length=10, default="00")
    effectivity_date = models.DateField(default=timezone.now)


class DocumentTracking(models.Model):
    class ActionTaken(models.TextChoices):
        CREATED = "created", "Created"
        FORWARDED = "forwarded", "Forwarded"
        RECEIVED = "received", "Received"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RELEASED = "released", "Released"

    memo = models.ForeignKey(Memo, on_delete=models.CASCADE, related_name="tracking_history")
    action_taken = models.CharField(max_length=20, choices=ActionTaken.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="tracking_actions")
    forwarded_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="received_documents")
    date_tracked = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)


class ActivityAccomplishmentReport(models.Model):
    activity = models.OneToOneField(ActivityDesign, on_delete=models.CASCADE, related_name="accomplishment_report")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    actual_participants = models.PositiveIntegerField()
    actual_budget_spent = models.DecimalField(max_digits=10, decimal_places=2)
    summary_of_outcomes = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)


class TravelReport(models.Model):
    travel_order = models.OneToOneField(TravelOrder, on_delete=models.CASCADE, related_name="travel_report")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    actual_expenses = models.DecimalField(max_digits=10, decimal_places=2)
    expense_liquidation_details = models.TextField()
    accomplishments = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)
