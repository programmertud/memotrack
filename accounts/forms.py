from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Department, Profile


User = get_user_model()


_TEXT_INPUT = forms.TextInput(
    attrs={
        "class": "w-full px-4 py-3 rounded-2xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)
_EMAIL_INPUT = forms.EmailInput(
    attrs={
        "class": "w-full px-4 py-3 rounded-2xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)
_PASSWORD_INPUT = forms.PasswordInput(
    attrs={
        "class": "w-full px-4 py-3 rounded-2xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)
_SELECT = forms.Select(
    attrs={
        "class": "w-full px-4 py-3 rounded-2xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)


class AdminUserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    email = forms.EmailField(required=False, widget=_EMAIL_INPUT)
    password1 = forms.CharField(widget=_PASSWORD_INPUT)
    password2 = forms.CharField(widget=_PASSWORD_INPUT)
    role = forms.ChoiceField(
        choices=[
            (Profile.Role.STAFF, Profile.Role.STAFF.label),
            (Profile.Role.INSTRUCTOR, Profile.Role.INSTRUCTOR.label),
        ],
        widget=_SELECT,
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=_SELECT,
    )
    is_active = forms.BooleanField(required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")

        username = cleaned.get("username")
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")

        return cleaned

    def save(self) -> User:
        data = self.cleaned_data
        user = User(username=data["username"], email=data.get("email") or "", is_active=data.get("is_active", True))
        user.set_password(data["password1"])
        user.save()
        profile = user.profile
        profile.role = data["role"]
        profile.department = data.get("department")
        profile.save(update_fields=["role", "department"])
        return user


class AdminUserUpdateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    email = forms.EmailField(required=False, widget=_EMAIL_INPUT)
    role = forms.ChoiceField(
        choices=[
            (Profile.Role.STAFF, Profile.Role.STAFF.label),
            (Profile.Role.INSTRUCTOR, Profile.Role.INSTRUCTOR.label),
        ],
        widget=_SELECT,
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=_SELECT,
    )
    is_active = forms.BooleanField(required=False)
    new_password = forms.CharField(widget=_PASSWORD_INPUT, required=False)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.initial.setdefault("username", user.username)
        self.initial.setdefault("email", getattr(user, "email", "") or "")
        self.initial.setdefault("is_active", user.is_active)

        profile = getattr(user, "profile", None)
        if profile is not None:
            self.initial.setdefault("role", profile.role)
            self.initial.setdefault("department", profile.department_id)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.exclude(pk=self.user.pk).filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def save(self) -> User:
        data = self.cleaned_data
        self.user.username = data["username"]
        self.user.email = data.get("email") or ""
        self.user.is_active = bool(data.get("is_active"))
        if data.get("new_password"):
            self.user.set_password(data["new_password"])
        self.user.save()

        profile = self.user.profile
        profile.role = data["role"]
        profile.department = data.get("department")
        profile.save(update_fields=["role", "department"])
        return self.user


class UserRegisterForm(UserCreationForm):
    username = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    email = forms.EmailField(required=False, widget=_EMAIL_INPUT)
    password1 = forms.CharField(widget=_PASSWORD_INPUT)
    password2 = forms.CharField(widget=_PASSWORD_INPUT)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

