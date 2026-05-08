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
        fields = ["name", "plate_number", "capacity", "status", "driver_name", "driver_image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "plate_number": forms.TextInput(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "capacity": forms.NumberInput(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "status": forms.Select(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "driver_name": forms.TextInput(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "driver_image": forms.FileInput(attrs={"class": "mt-2 w-full block text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-uniGold/10 file:text-uniGreen hover:file:bg-uniGold/20"}),
        }
