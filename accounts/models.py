from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


User = get_user_model()


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self) -> str:
        return self.name


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        HR = "hr", "HR"
        INSTRUCTOR = "instructor", "Instructor"
        APPROVER = "approver", "Department Head/Approver"
        TRANSPORTATION = "transportation", "Transportation"
        STAFF = "staff", "Staff"
        STUDENT = "student", "Student"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles"
    )

    def __str__(self) -> str:
        return f"{self.user.get_username()} ({self.get_role_display()})"


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    is_present = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        unique_together = ("user", "date")
        indexes = [models.Index(fields=["date", "is_present"]) ]

    def __str__(self) -> str:
        return f"{self.user.get_username()} - {self.date}"


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "start_date", "end_date"]) ]

    def __str__(self) -> str:
        return f"{self.user.get_username()} leave ({self.start_date} - {self.end_date})"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
