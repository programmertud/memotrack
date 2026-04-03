from django import forms

from .models import Vehicle, VehicleBooking


class VehicleBookingForm(forms.ModelForm):
    vehicle = forms.ModelChoiceField(queryset=Vehicle.objects.all())

    class Meta:
        model = VehicleBooking
        fields = ["vehicle"]


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["name", "plate_number", "capacity", "status"]
