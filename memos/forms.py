from django import forms
from django.contrib.auth import get_user_model

from .models import Memo
from resources.models import Resource, ResourceBooking, Vehicle, VehicleBooking


User = get_user_model()


class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if hasattr(obj, 'profile') and obj.profile.first_name:
            return f"{obj.profile.first_name} {obj.profile.last_name}"
        return obj.get_full_name() or obj.username

class MemoForm(forms.ModelForm):
    employees = UserMultipleChoiceField(
        queryset=User.objects.all().select_related("profile"),
        widget=forms.CheckboxSelectMultiple,
        label="Employees"
    )
    delegated_to = forms.ModelChoiceField(
        queryset=User.objects.all().select_related("profile"),
        required=False,
        widget=forms.Select(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"})
    )
    resources = forms.ModelMultipleChoiceField(
        queryset=Resource.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select venues or equipment for this memo."
    )
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE),
        required=False,
        label="Vehicle",
        empty_label="-- Select a Vehicle --"
    )
    vehicle_days = forms.IntegerField(
        required=False, min_value=1, initial=1, label="Number of Days"
    )
    vehicle_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Vehicle Use Start Date"
    )
    vehicle_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Vehicle Use End Date"
    )

    class Meta:
        model = Memo
        fields = [
            "reference_number",
            "title",
            "description",
            "employees",
            "to_all",
            "date",
            "start_time",
            "end_time",
            "venue",
            "destination",
            "priority",
            "category",
            "required",
            "delegated_to",
        ]
        labels = {
            "to_all": "All Faculty Members and Student",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
            "priority": forms.Select(attrs={"class": "mt-2 w-full px-4 py-3 rounded-2xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-uniGold/50 focus:border-uniGold transition"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["resources"].initial = Resource.objects.filter(
                bookings__memo=self.instance
            )
            if hasattr(self.instance, 'vehicle_booking'):
                vb = self.instance.vehicle_booking
                self.fields["vehicle"].initial = vb.vehicle
                self.fields["vehicle_days"].initial = vb.days
                self.fields["vehicle_start_date"].initial = vb.start_date
                self.fields["vehicle_end_date"].initial = vb.end_date

    def save(self, commit=True):
        memo = super().save(commit=commit)
        if commit:
            # Handle resource bookings
            selected_resources = self.cleaned_data.get("resources", [])
            ResourceBooking.objects.filter(memo=memo).delete()
            for res in selected_resources:
                ResourceBooking.objects.create(memo=memo, resource=res)

            # Handle vehicle booking (external only)
            vehicle = self.cleaned_data.get("vehicle")
            if vehicle and memo.category == Memo.Category.EXTERNAL:
                vb, _ = VehicleBooking.objects.get_or_create(memo=memo, defaults={"vehicle": vehicle})
                vb.vehicle = vehicle
                vb.days = self.cleaned_data.get("vehicle_days") or 1
                vb.start_date = self.cleaned_data.get("vehicle_start_date") or memo.date
                vb.end_date = self.cleaned_data.get("vehicle_end_date") or memo.date
                vb.save()
            elif not vehicle:
                VehicleBooking.objects.filter(memo=memo).delete()
        return memo
