from django.db import models
from django.db.models import Q
from django.utils import timezone


class Venue(models.Model):
    class Type(models.TextChoices):
        AUDITORIUM = "auditorium", "Auditorium"
        CONFERENCE = "conference", "Conference Room"
        CLASSROOM = "classroom", "Classroom"
        LABORATORY = "laboratory", "Laboratory"
        OUTDOOR = "outdoor", "Outdoor Space"

    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    capacity = models.PositiveIntegerField(default=50)
    venue_type = models.CharField(max_length=20, choices=Type.choices, default=Type.CLASSROOM)
    is_active = models.BooleanField(default=True)
    department_exclusive = models.ForeignKey(
        "accounts.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="exclusive_venues", help_text="If set, only this department can book this venue."
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.get_venue_type_display()})"


class Vehicle(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        MAINTENANCE = "maintenance", "Maintenance"
        UNAVAILABLE = "unavailable", "Unavailable"

    name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    
    driver_name = models.CharField(max_length=100, blank=True)
    driver_image = models.ImageField(upload_to="drivers/", null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.plate_number})"

    @property
    def is_booked_today(self):
        from django.utils import timezone
        from django.db.models import Q
        today = timezone.now().date()
        # A vehicle is booked if there's a booking spanning today, 
        # or if it's linked to an approved memo for today.
        return self.bookings.filter(
            Q(start_date__lte=today, end_date__gte=today) |
            Q(start_date__isnull=True, memo__date=today)
        ).exists()


class VehicleBooking(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="bookings")
    memo = models.OneToOneField("memos.Memo", on_delete=models.CASCADE, related_name="vehicle_booking")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    days = models.PositiveIntegerField(default=1, help_text="Number of days for vehicle use")
    start_date = models.DateField(null=True, blank=True, help_text="Start date of vehicle use")
    end_date = models.DateField(null=True, blank=True, help_text="End date of vehicle use")

    class Meta:
        indexes = [
            models.Index(fields=["vehicle"]),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle} for {self.memo}"

    def overlaps_queryset(self):
        start = self.start_date or self.memo.date
        end = self.end_date or self.memo.date
        
        qs = VehicleBooking.objects.filter(vehicle=self.vehicle)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
            
        return qs.filter(
            Q(start_date__lte=end) & Q(end_date__gte=start)
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


class Resource(models.Model):
    class Type(models.TextChoices):
        VENUE = "venue", "Venue"
        EQUIPMENT = "equipment", "Equipment"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100)
    resource_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.VENUE
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.get_resource_type_display()})"


class ResourceBooking(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="bookings")
    memo = models.ForeignKey("memos.Memo", on_delete=models.CASCADE, related_name="resource_bookings")
    
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["resource", "memo"]),
        ]

    def __str__(self) -> str:
        return f"{self.resource} for {self.memo}"

    def overlaps_queryset(self):
        qs = ResourceBooking.objects.filter(resource=self.resource, memo__date=self.memo.date)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.filter(
            Q(memo__start_time__lt=self.memo.end_time) & Q(memo__end_time__gt=self.memo.start_time)
        )

    def has_conflicts(self) -> bool:
        return self.overlaps_queryset().exists()
