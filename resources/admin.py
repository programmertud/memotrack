from django.contrib import admin

from .models import Vehicle, VehicleBooking


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "plate_number", "capacity", "status")
    list_filter = ("status",)
    search_fields = ("name", "plate_number")


@admin.register(VehicleBooking)
class VehicleBookingAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "memo", "created_at")
    autocomplete_fields = ("vehicle", "memo")
