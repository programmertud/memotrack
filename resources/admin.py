from django.contrib import admin

from .models import Vehicle, VehicleBooking, Venue, Resource, ResourceBooking
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "venue_type", "capacity", "is_active", "department_exclusive")
    list_filter = ("venue_type", "is_active", "department_exclusive")
    search_fields = ("name", "location")

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "plate_number", "capacity", "status")
    list_filter = ("status",)
    search_fields = ("name", "plate_number")

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "resource_type", "is_active")
    list_filter = ("resource_type", "is_active")
    search_fields = ("name", "description")

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "plate_number", "capacity", "status")
    list_filter = ("status",)
    search_fields = ("name", "plate_number")

@admin.register(VehicleBooking)
class VehicleBookingAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "memo", "created_at")
    autocomplete_fields = ("vehicle", "memo")

@admin.register(ResourceBooking)
class ResourceBookingAdmin(admin.ModelAdmin):
    list_display = ("resource", "memo", "created_at")
    autocomplete_fields = ("resource", "memo")
