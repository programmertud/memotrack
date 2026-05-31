from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.text import slugify
import random
import string
try:
    from email_validator import validate_email as lib_validate_email, EmailNotValidError
except ImportError:
    lib_validate_email = None

from .models import Department, Profile


User = get_user_model()


_TEXT_INPUT = forms.TextInput(
    attrs={
        "class": "w-full px-3 py-1.5 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)
_EMAIL_INPUT = forms.EmailInput(
    attrs={
        "class": "w-full px-3 py-1.5 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)
_PASSWORD_INPUT = forms.PasswordInput(
    attrs={
        "class": "w-full pl-3 pr-10 py-1.5 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)
_SELECT = forms.Select(
    attrs={
        "class": "w-full px-3 py-1.5 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60",
    }
)


class AdminUserCreateForm(forms.Form):
    first_name = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    middle_name = forms.CharField(max_length=150, widget=_TEXT_INPUT, required=False)
    last_name = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    email = forms.EmailField(required=True, widget=_EMAIL_INPUT)
    employee_id = forms.CharField(max_length=50, widget=_TEXT_INPUT, label="Employee ID")
    mobile_number = forms.CharField(max_length=30, widget=_TEXT_INPUT, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"class": "w-full px-3 py-1.5 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60", "rows": 2}), required=False)
    password1 = forms.CharField(widget=_PASSWORD_INPUT, label="Password")
    password2 = forms.CharField(widget=_PASSWORD_INPUT, label="Confirm Password")

    def __init__(self, *args, **kwargs):
        self.initial_role = None
        initial = kwargs.get('initial')
        if initial and 'role' in initial:
            roles = initial['role']
            if isinstance(roles, list) and roles:
                self.initial_role = roles[0]
            elif isinstance(roles, str):
                self.initial_role = roles
        super().__init__(*args, **kwargs)

    def _generate_unique_username(self) -> str:
        first_name = self.cleaned_data.get("first_name") or ""
        last_name = self.cleaned_data.get("last_name") or ""
        full_name = f"{first_name} {last_name}".strip()
        name_slug = slugify(full_name, allow_unicode=False).replace("-", "")
        
        if not name_slug:
            email  = (self.cleaned_data.get("email") or "").strip()
            if email:
                name_slug = slugify(email.split("@", 1)[0], allow_unicode=False).replace("-", "")
        
        if not name_slug:
            name_slug = "user"

        for _ in range(20):
            suffix = str(random.randint(1000, 9999))
            candidate = f"{name_slug}{suffix}"
            if not User.objects.filter(username=candidate).exists():
                return candidate

        return name_slug + "".join(random.choices(string.digits, k=6))

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        
        if email.endswith("@ssct.edu.ph"):
            pass # Explicitly allow university domain
        elif lib_validate_email:
            try:
                valid = lib_validate_email(email, check_deliverability=True)
                email = valid.normalized
            except EmailNotValidError as e:
                raise forms.ValidationError(f"Please enter a valid, real email address ({str(e)}).")
        
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_employee_id(self):
        employee_id = (self.cleaned_data.get("employee_id") or "").strip()
        if employee_id and Profile.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError("ID Number already exists.")
        return employee_id

    def clean_mobile_number(self):
        mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        if not mobile:
            return mobile
        if len(mobile) != 11 or not mobile.isdigit() or not mobile.startswith("09"):
            raise forms.ValidationError("Mobile number must be 11 digits and start with '09'.")
        if Profile.objects.filter(mobile_number=mobile).exists():
            raise forms.ValidationError("This contact number is already registered.")
        return mobile

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")

        cleaned["username"] = self._generate_unique_username()
        return cleaned

    def save(self) -> User:
        data = self.cleaned_data
        user = User(username=data["username"], email=data.get("email") or "", is_active=True)
        user.set_password(data["password1"])
        user.save()
        profile = user.profile
        
        role_val = Profile.Role.EMPLOYEE
        if self.initial_role:
            role_val = self.initial_role

        profile.role = role_val
        profile.first_name = data.get("first_name") or ""
        profile.middle_name = data.get("middle_name") or ""
        profile.last_name = data.get("last_name") or ""
        profile.employee_id = data.get("employee_id") or ""
        profile.mobile_number = data.get("mobile_number") or ""
        profile.address = data.get("address") or ""
        profile.save()
        return user


class AdminUserUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    middle_name = forms.CharField(max_length=150, widget=_TEXT_INPUT, required=False)
    last_name = forms.CharField(max_length=150, widget=_TEXT_INPUT)
    email = forms.EmailField(required=True, widget=_EMAIL_INPUT)
    employee_id = forms.CharField(max_length=50, widget=_TEXT_INPUT, label="Employee ID")
    mobile_number = forms.CharField(max_length=30, widget=_TEXT_INPUT, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"class": "w-full px-3 py-1.5 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-2 focus:ring-uniGold/60", "rows": 2}), required=False)
    is_active = forms.BooleanField(required=False)
    new_password = forms.CharField(widget=_PASSWORD_INPUT, required=False)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.initial.setdefault("email", getattr(user, "email", "") or "")
        self.initial.setdefault("is_active", user.is_active)

        profile = getattr(user, "profile", None)
        if profile is not None:
            self.initial.setdefault("first_name", profile.first_name)
            self.initial.setdefault("middle_name", profile.middle_name)
            self.initial.setdefault("last_name", profile.last_name)
            self.initial.setdefault("employee_id", profile.employee_id)
            self.initial.setdefault("mobile_number", profile.mobile_number)
            self.initial.setdefault("address", profile.address)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        
        if email.endswith("@ssct.edu.ph"):
            pass # Explicitly allow university domain
        elif lib_validate_email:
            try:
                valid = lib_validate_email(email, check_deliverability=True)
                email = valid.normalized
            except EmailNotValidError as e:
                raise forms.ValidationError(f"Please enter a valid, real email address ({str(e)}).")

        qs = User.objects.filter(email__iexact=email)
        if getattr(self, 'user', None):
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_employee_id(self):
        employee_id = (self.cleaned_data.get("employee_id") or "").strip()
        if employee_id:
            qs = Profile.objects.filter(employee_id=employee_id)
            if getattr(self.user, 'profile', None):
                qs = qs.exclude(pk=self.user.profile.pk)
            if qs.exists():
                raise forms.ValidationError("ID Number already exists.")
        return employee_id

    def clean_mobile_number(self):
        mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        if not mobile:
            return mobile
        if len(mobile) != 11 or not mobile.isdigit() or not mobile.startswith("09"):
            raise forms.ValidationError("Mobile number must be 11 digits and start with '09'.")
        qs = Profile.objects.filter(mobile_number=mobile)
        if getattr(self.user, 'profile', None):
            qs = qs.exclude(pk=self.user.profile.pk)
        if qs.exists():
            raise forms.ValidationError("This contact number is already registered.")
        return mobile

    def save(self) -> User:
        data = self.cleaned_data
        self.user.email = data.get("email") or ""
        self.user.is_active = bool(data.get("is_active"))
        if data.get("new_password"):
            self.user.set_password(data["new_password"])
        self.user.save()

        profile = self.user.profile
        profile.first_name = data.get("first_name") or ""
        profile.middle_name = data.get("middle_name") or ""
        profile.last_name = data.get("last_name") or ""
        profile.employee_id = data.get("employee_id") or ""
        profile.mobile_number = data.get("mobile_number") or ""
        profile.address = data.get("address") or ""
        profile.save()
        return self.user


class UserRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=255, widget=_TEXT_INPUT, label="Full Name")
    employee_id = forms.CharField(max_length=50, widget=_TEXT_INPUT, label="ID Number")
    mobile_number = forms.CharField(max_length=30, widget=_TEXT_INPUT, label="Contact Number")
    email = forms.EmailField(required=True, widget=_EMAIL_INPUT)
    username = forms.CharField(max_length=150, required=False, widget=forms.HiddenInput())
    role = forms.ChoiceField(
        choices=[
            ("admin", "Admin"),
            ("instructor", "Employee"),
            ("staff", "Staff"),
        ],
        widget=_SELECT,
        label="User Type"
    )
    password1 = forms.CharField(widget=_PASSWORD_INPUT, label="Password")
    password2 = forms.CharField(widget=_PASSWORD_INPUT, label="Confirm Password")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_employee_id(self):
        employee_id = (self.cleaned_data.get("employee_id") or "").strip()
        if not employee_id:
            raise forms.ValidationError("ID Number is required.")
        if Profile.objects.filter(employee_id=employee_id).exists():
            raise forms.ValidationError("ID Number already exists.")
        return employee_id

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        
        if email.endswith("@ssct.edu.ph"):
            pass # Explicitly allow university domain
        elif lib_validate_email:
            try:
                valid = lib_validate_email(email, check_deliverability=True)
                email = valid.normalized
            except EmailNotValidError as e:
                raise forms.ValidationError(f"Please enter a valid, real email address ({str(e)}).")

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_mobile_number(self):
        mobile = (self.cleaned_data.get("mobile_number") or "").strip()
        if not mobile:
            raise forms.ValidationError("Contact number is required.")
        if len(mobile) != 11 or not mobile.isdigit() or not mobile.startswith("09"):
            raise forms.ValidationError("Mobile number must be 11 digits and start with '09'.")
        if Profile.objects.filter(mobile_number=mobile).exists():
            raise forms.ValidationError("This contact number is already registered.")
        return mobile

    def _generate_unique_username(self) -> str:
        full_name = self.cleaned_data.get("full_name") or ""
        name_slug = slugify(full_name, allow_unicode=False).replace("-", "")
        
        if not name_slug:
            email  = (self.cleaned_data.get("email") or "").strip()
            if email:
                name_slug = slugify(email.split("@", 1)[0], allow_unicode=False).replace("-", "")
        
        if not name_slug:
            name_slug = "user"

        for _ in range(20):
            suffix = str(random.randint(1000, 9999))
            candidate = f"{name_slug}{suffix}"
            if not User.objects.filter(username=candidate).exists():
                return candidate

        return name_slug + "".join(random.choices(string.digits, k=6))

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("username"):
            cleaned["username"] = self._generate_unique_username()

        if cleaned.get("role") == "admin":
            if Profile.objects.filter(role=Profile.Role.ADMIN).exists():
                raise forms.ValidationError(
                    "An admin account already exists. Only one admin is allowed in this system."
                )

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        user.email = self.cleaned_data.get("email")
        role = self.cleaned_data["role"]
        full_name = self.cleaned_data.get("full_name", "").strip()
        
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        if commit:
            user.save(update_fields=["email"])
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = Profile.Role.ADMIN if role == "admin" else role
            profile.first_name = first_name
            profile.last_name = last_name
            profile.employee_id = self.cleaned_data["employee_id"]
            profile.mobile_number = self.cleaned_data["mobile_number"]
            profile.save(
                update_fields=[
                    "role",
                    "first_name",
                    "last_name",
                    "employee_id",
                    "mobile_number",
                ]
            )
        return user

