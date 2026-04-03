from django.db import models
from django.db.models import Q
from django.utils import timezone


class Vehicle(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        MAINTENANCE = "maintenance", "Maintenance"
        UNAVAILABLE = "unavailable", "Unavailable"

    name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    def __str__(self) -> str:
        return f"{self.name} ({self.plate_number})"


class VehicleBooking(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="bookings")
    memo = models.OneToOneField("memos.Memo", on_delete=models.CASCADE, related_name="vehicle_booking")

    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["vehicle"]),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle} for {self.memo}"

    def overlaps_queryset(self):
        qs = VehicleBooking.objects.filter(vehicle=self.vehicle, memo__date=self.memo.date)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.filter(
            Q(memo__start_time__lt=self.memo.end_time) & Q(memo__end_time__gt=self.memo.start_time)
        )

    def has_conflicts(self) -> bool:
        return self.overlaps_queryset().exists()

    def shared_trip_suggestions(self):
        dest = (self.memo.destination or "").strip()
        if not dest:
            return self.memo.__class__.objects.none()

        return (
            self.memo.__class__.objects.filter(date=self.memo.date, destination__iexact=dest)
            .exclude(pk=self.memo.pk)
            .order_by("start_time")
        )
