from django import forms
from django.contrib.auth import get_user_model

from .models import Memo


User = get_user_model()


class MemoForm(forms.ModelForm):
    assigned_user = forms.ModelChoiceField(queryset=User.objects.all())
    delegated_to = forms.ModelChoiceField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Memo
        fields = [
            "title",
            "description",
            "assigned_user",
            "date",
            "start_time",
            "end_time",
            "venue",
            "destination",
            "priority",
            "required",
            "delegated_to",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
