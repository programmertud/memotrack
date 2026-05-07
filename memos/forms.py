from django import forms
from django.contrib.auth import get_user_model

from .models import Memo
from resources.models import Resource, ResourceBooking


User = get_user_model()


class MemoForm(forms.ModelForm):
    assigned_user = forms.ModelChoiceField(queryset=User.objects.all())
    delegated_to = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    resources = forms.ModelMultipleChoiceField(
        queryset=Resource.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select venues or equipment for this memo."
    )

    class Meta:
        model = Memo
        fields = [
            "title",
            "reference_number",
            "description",
            "assigned_user",
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
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["resources"].initial = Resource.objects.filter(
                bookings__memo=self.instance
            )

    def save(self, commit=True):
        memo = super().save(commit=commit)
        if commit:
            # Handle resource bookings
            selected_resources = self.cleaned_data.get("resources", [])
            # Clear existing and add new
            ResourceBooking.objects.filter(memo=memo).delete()
            for res in selected_resources:
                ResourceBooking.objects.create(memo=memo, resource=res)
        return memo
