from django.shortcuts import render

from datetime import timedelta
import base64
import io

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.core.files.base import ContentFile

from memos.models import Memo
from memos.models import MemoDecision
from notifications.models import Notification
from resources.models import Vehicle, VehicleBooking

from .models import Attendance, LeaveRequest, Profile
from .forms import AdminUserCreateForm, AdminUserUpdateForm, UserRegisterForm


User = get_user_model()


def home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return redirect("accounts:post_login")


@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:post_login")

    login_type = (request.POST.get("login_type") or request.GET.get("login_type") or "user").strip().lower()
    if login_type not in {"user", "admin"}:
        login_type = "user"

    # Use a blank form for rendering only — we do our own auth so the form
    # never calls authenticate() with the raw identifier (which would fail for
    # school-ID / email / mobile inputs).
    form = AuthenticationForm(request)

    if request.method == "POST":
        identifier = (request.POST.get("username") or "").strip()
        password   = request.POST.get("password") or ""

        resolved_username = identifier

        if identifier:
            # Resolve school_id / email / mobile → actual Django username
            matched_user = (
                User.objects.select_related("profile")
                .filter(
                    Q(username__iexact=identifier)
                    | Q(email__iexact=identifier)
                    | Q(profile__school_id__iexact=identifier)
                    | Q(profile__mobile_number=identifier)
                )
                .first()
            )
            if matched_user is not None:
                resolved_username = matched_user.username

        user = authenticate(request, username=resolved_username, password=password)

        if user is not None:
            profile_role     = getattr(getattr(user, "profile", None), "role", None)
            is_system_admin  = profile_role == Profile.Role.ADMIN
            is_django_admin  = user.is_staff or user.is_superuser

            if login_type == "admin" and not (is_django_admin or is_system_admin):
                messages.error(request, "This account does not have admin access.")
            elif login_type == "user" and (is_django_admin or is_system_admin):
                messages.error(request, "Admin accounts must use the Admin login option.")
            else:
                login(request, user)
                return redirect("accounts:post_login")
        else:
            messages.error(request, "Invalid credentials. Please check and try again.")

    return render(request, "accounts/login.html", {"form": form, "login_type": login_type})


@csrf_protect
def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:post_login")

    admin_exists = Profile.objects.filter(role=Profile.Role.ADMIN).exists()

    form = UserRegisterForm(request.POST or None)
    admin_error = False
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created.")
        return redirect("accounts:post_login")

    # Detect if the non-field validation error is the admin-exists error
    if request.method == "POST" and not form.is_valid():
        for err in form.non_field_errors():
            if "admin account already exists" in err.lower():
                admin_error = True
                break

    return render(request, "accounts/register.html", {
        "form": form,
        "admin_exists": admin_exists,
        "admin_error": admin_error,
    })


@login_required
def post_login(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect("accounts:admin_dashboard")

    role = getattr(getattr(request.user, "profile", None), "role", None)

    if role == Profile.Role.ADMIN:
        return redirect("accounts:admin_dashboard")
    if role == Profile.Role.HR:
        return redirect("accounts:hr_dashboard")
    if role == Profile.Role.INSTRUCTOR:
        return redirect("accounts:instructor_dashboard")
    if role == Profile.Role.APPROVER:
        return redirect("accounts:approver_dashboard")
    if role == Profile.Role.TRANSPORTATION:
        return redirect("accounts:transportation_dashboard")

    return redirect("accounts:user_dashboard")


@login_required
def user_dashboard(request):
    role = getattr(getattr(request.user, "profile", None), "role", None)
    if request.user.is_staff or role == Profile.Role.ADMIN:
        return redirect("accounts:admin_dashboard")

    today = timezone.localdate()

    upcoming_memos = Memo.objects.filter(assigned_user=request.user, date__gte=today).order_by(
        "date", "start_time"
    )
    recent_memos = upcoming_memos.select_related("assigned_user")[:10]

    recent_notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    vehicles_preview = Vehicle.objects.all().order_by("name")[:6]
    available_vehicles_count = Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).count()

    return render(
        request,
        "accounts/dashboards/user_dashboard.html",
        {
            "upcoming_memos_count": upcoming_memos.count(),
            "recent_memos": recent_memos,
            "recent_notifications": recent_notifications,
            "unread_count": unread_count,
            "vehicles_preview": vehicles_preview,
            "available_vehicles_count": available_vehicles_count,
        },
    )


@login_required
def admin_dashboard(request):
    is_admin = request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.Role.ADMIN
    if not is_admin:
        return redirect("accounts:post_login")

    today = timezone.localdate()
    upcoming_until = today + timedelta(days=7)
    week_start = today - timedelta(days=6)

    # ── User counts ──
    total_instructors = Profile.objects.filter(role=Profile.Role.INSTRUCTOR).count()
    total_students    = Profile.objects.filter(role=Profile.Role.STUDENT).count()
    total_staff       = Profile.objects.filter(role=Profile.Role.STAFF).count()
    total_vehicles    = Vehicle.objects.count()
    available_vehicles = Vehicle.objects.filter(status="available").count()

    # ── Memo stats ──
    all_memos        = Memo.objects.all()
    pending_requests = all_memos.filter(status=Memo.Status.PENDING).count()
    approved_requests= all_memos.filter(status=Memo.Status.APPROVED).count()
    rejected_requests= all_memos.filter(status=Memo.Status.REJECTED).count()
    conflict_alerts  = all_memos.filter(status=Memo.Status.CONFLICT).count()
    total_memos      = all_memos.count()

    # ── Today's schedule sorted by time ──
    today_schedules = (
        Memo.objects.filter(date=today)
        .select_related("assigned_user")
        .prefetch_related("assigned_user__profile")
        .order_by("start_time")
    )
    today_count = today_schedules.count()

    # ── Upcoming (next 7 days, excluding today) ──
    upcoming_events = (
        Memo.objects.filter(date__gt=today, date__lte=upcoming_until)
        .select_related("assigned_user")
        .prefetch_related("assigned_user__profile")
        .order_by("date", "start_time")
    )[:8]

    # ── Conflicts ──
    conflict_memos = (
        Memo.objects.filter(status=Memo.Status.CONFLICT)
        .select_related("assigned_user")
        .prefetch_related("assigned_user__profile")
        .order_by("-date")
    )[:5]

    # ── Recent activity ──
    recent_memos = (
        Memo.objects.select_related("assigned_user", "created_by")
        .prefetch_related("assigned_user__profile", "created_by__profile")
        .order_by("-created_at")
    )[:8]

    # ── Weekly activity: memo counts per day for the past 7 days ──
    from django.db.models import Count as _Count
    daily_counts_qs = (
        Memo.objects.filter(date__gte=week_start, date__lte=today)
        .values("date")
        .annotate(cnt=_Count("id"))
        .order_by("date")
    )
    daily_map = {row["date"].isoformat(): row["cnt"] for row in daily_counts_qs}
    weekly_labels = []
    weekly_data   = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        weekly_labels.append(d.strftime("%b %d"))
        weekly_data.append(daily_map.get(d.isoformat(), 0))

    # ── High priority pending memos (action required) ──
    urgent_memos = (
        Memo.objects.filter(status=Memo.Status.PENDING, priority=Memo.Priority.HIGH)
        .select_related("assigned_user")
        .prefetch_related("assigned_user__profile")
        .order_by("date", "start_time")
    )[:5]

    return render(
        request,
        "accounts/dashboards/admin_dashboard.html",
        {
            "total_instructors":  total_instructors,
            "total_students":     total_students,
            "total_staff":        total_staff,
            "total_vehicles":     total_vehicles,
            "available_vehicles": available_vehicles,
            "pending_requests":   pending_requests,
            "approved_requests":  approved_requests,
            "rejected_requests":  rejected_requests,
            "conflict_alerts":    conflict_alerts,
            "total_memos":        total_memos,
            "today_count":        today_count,
            "today_schedules":    today_schedules,
            "upcoming_events":    upcoming_events,
            "conflict_memos":     conflict_memos,
            "recent_memos":       recent_memos,
            "urgent_memos":       urgent_memos,
            "weekly_labels":      weekly_labels,
            "weekly_data":        weekly_data,
            "today":              today,
        },
    )



def _normalize_admin_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role not in {Profile.Role.STAFF, Profile.Role.INSTRUCTOR}:
        return ""
    return role


@login_required
def admin_user_list(request, role: str):
    if not (request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.Role.ADMIN):
        return redirect('accounts:post_login')
    role = _normalize_admin_role(role)
    if not role:
        messages.error(request, "Invalid role.")
        return redirect("accounts:admin_dashboard")

    users = (
        User.objects.select_related("profile")
        .filter(profile__role=role)
        .order_by("username")
    )
    return render(
        request,
        "accounts/admin/user_list.html",
        {"users": users, "role": role},
    )


@login_required
def admin_user_create(request, role: str):
    if not (request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.Role.ADMIN):
        return redirect('accounts:post_login')
    role = _normalize_admin_role(role)
    if not role:
        messages.error(request, "Invalid role.")
        return redirect("accounts:admin_dashboard")

    initial = {"role": role}
    form = AdminUserCreateForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"User '{user.get_username()}' created.")
        return redirect("accounts:admin_user_list", role=role)

    return render(
        request,
        "accounts/admin/user_form.html",
        {"form": form, "role": role, "mode": "create"},
    )


@login_required
def admin_user_edit(request, role: str, pk: int):
    if not (request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.Role.ADMIN):
        return redirect('accounts:post_login')
    role = _normalize_admin_role(role)
    if not role:
        messages.error(request, "Invalid role.")
        return redirect("accounts:admin_dashboard")

    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    form = AdminUserUpdateForm(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "User updated.")
        return redirect("accounts:admin_user_list", role=role)

    return render(
        request,
        "accounts/admin/user_form.html",
        {"form": form, "role": role, "mode": "edit", "managed_user": user},
    )


@login_required
def admin_user_delete(request, role: str, pk: int):
    if not (request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', None) == Profile.Role.ADMIN):
        return redirect('accounts:post_login')
    role = _normalize_admin_role(role)
    if not role:
        messages.error(request, "Invalid role.")
        return redirect("accounts:admin_dashboard")

    user = get_object_or_404(User.objects.select_related("profile"), pk=pk)
    if request.method == "POST":
        username = user.get_username()
        user.delete()
        messages.success(request, f"User '{username}' deleted.")
        return redirect("accounts:admin_user_list", role=role)

    return render(
        request,
        "accounts/admin/user_confirm_delete.html",
        {"role": role, "managed_user": user},
    )


@login_required
def hr_dashboard(request):
    role = getattr(request.user.profile, "role", None)
    if role != Profile.Role.HR and not request.user.is_staff:
        return redirect("accounts:post_login")

    today = timezone.localdate()

    employee_records = Profile.objects.exclude(role=Profile.Role.STUDENT).count()
    attendance = Attendance.objects.filter(date=today)
    attendance_present = attendance.filter(is_present=True).count()
    attendance_absent = attendance.filter(is_present=False).count()
    attendance_total = attendance.count()
    leave_pending = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count()

    busy_today = (
        Memo.objects.filter(date=today).values_list("assigned_user_id", flat=True).distinct()
    )
    available_staff = (
        Profile.objects.exclude(role=Profile.Role.STUDENT)
        .exclude(user_id__in=busy_today)
        .count()
    )
    unavailable_staff = (
        Profile.objects.exclude(role=Profile.Role.STUDENT)
        .filter(user_id__in=busy_today)
        .count()
    )

    department_assignments = Profile.objects.exclude(department=None).count()

    workload_summary = (
        Memo.objects.filter(date=today)
        .values("assigned_user__username")
        .order_by("assigned_user__username")
    )

    return render(
        request,
        "accounts/dashboards/hr_dashboard.html",
        {
            "employee_records": employee_records,
            "attendance_present": attendance_present,
            "attendance_absent": attendance_absent,
            "attendance_total": attendance_total,
            "leave_pending": leave_pending,
            "available_staff": available_staff,
            "unavailable_staff": unavailable_staff,
            "department_assignments": department_assignments,
            "workload_summary": workload_summary,
        },
    )


@login_required
def instructor_dashboard(request):
    role = getattr(request.user.profile, "role", None)
    if role != Profile.Role.INSTRUCTOR and not request.user.is_staff:
        return redirect("accounts:post_login")

    today = timezone.localdate()

    personal_schedule = (
        Memo.objects.filter(assigned_user=request.user, date__gte=today)
        .order_by("date", "start_time")
        .select_related("assigned_user")[:15]
    )
    class_assignments = Memo.objects.filter(assigned_user=request.user, venue__icontains="class").order_by(
        "-date"
    )[:10]
    travel_assignments = (
        Memo.objects.filter(assigned_user=request.user)
        .exclude(destination="")
        .order_by("-date")[:10]
    )
    event_participation = Memo.objects.filter(assigned_user=request.user, priority=Memo.Priority.HIGH).order_by(
        "-date"
    )[:10]

    leave_requests = LeaveRequest.objects.filter(user=request.user).order_by("-created_at")[:10]
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]

    return render(
        request,
        "accounts/dashboards/instructor_dashboard.html",
        {
            "personal_schedule": personal_schedule,
            "class_assignments": class_assignments,
            "travel_assignments": travel_assignments,
            "event_participation": event_participation,
            "leave_requests": leave_requests,
            "notifications": notifications,
            "chart_counts": {
                "schedule": personal_schedule.count() if hasattr(personal_schedule, "count") else len(personal_schedule),
                "class": class_assignments.count() if hasattr(class_assignments, "count") else len(class_assignments),
                "travel": travel_assignments.count() if hasattr(travel_assignments, "count") else len(travel_assignments),
                "events": event_participation.count() if hasattr(event_participation, "count") else len(event_participation),
            },
        },
    )


@login_required
def approver_dashboard(request):
    role = getattr(request.user.profile, "role", None)
    if role != Profile.Role.APPROVER and not request.user.is_staff:
        return redirect("accounts:post_login")

    today = timezone.localdate()

    pending_approvals = Memo.objects.filter(status=Memo.Status.PENDING).order_by(
        "date", "start_time"
    )[:25]
    schedule_conflicts = Memo.objects.filter(status=Memo.Status.CONFLICT).order_by(
        "date", "start_time"
    )[:25]

    dept = request.user.profile.department
    if dept:
        dept_user_ids = dept.profiles.values_list("user_id", flat=True)
        department_schedules = Memo.objects.filter(
            assigned_user_id__in=dept_user_ids, date__gte=today
        ).order_by("date", "start_time")[:25]
    else:
        department_schedules = Memo.objects.none()

    request_history = Memo.objects.exclude(status=Memo.Status.PENDING).order_by("-updated_at")[:15]

    decision_history = (
        MemoDecision.objects.select_related("memo", "decided_by")
        .order_by("-created_at")[:20]
    )

    return render(
        request,
        "accounts/dashboards/approver_dashboard.html",
        {
            "pending_approvals": pending_approvals,
            "schedule_conflicts": schedule_conflicts,
            "department_schedules": department_schedules,
            "request_history": request_history,
            "decision_history": decision_history,
        },
    )


@login_required
def transportation_dashboard(request):
    role = getattr(request.user.profile, "role", None)
    if role != Profile.Role.TRANSPORTATION and not request.user.is_staff:
        return redirect("accounts:post_login")

    today = timezone.localdate()

    available_vehicles = Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE)
    booked_today = VehicleBooking.objects.filter(memo__date=today).select_related("vehicle", "memo")
    booked_vehicle_ids = booked_today.values_list("vehicle_id", flat=True).distinct()
    booked_vehicles = Vehicle.objects.filter(id__in=booked_vehicle_ids)

    trip_schedules = booked_today.order_by("memo__start_time")

    double_booking_warnings = 0
    by_vehicle = {}
    for b in trip_schedules:
        by_vehicle.setdefault(b.vehicle_id, []).append(b)
    for _, bookings in by_vehicle.items():
        for i in range(len(bookings)):
            for j in range(i + 1, len(bookings)):
                a, c = bookings[i], bookings[j]
                if a.memo.start_time < c.memo.end_time and a.memo.end_time > c.memo.start_time:
                    double_booking_warnings += 1

    overcapacity_alerts = 0

    return render(
        request,
        "accounts/dashboards/transportation_dashboard.html",
        {
            "available_vehicles": available_vehicles,
            "booked_vehicles": booked_vehicles,
            "trip_schedules": trip_schedules,
            "double_booking_warnings": double_booking_warnings,
            "overcapacity_alerts": overcapacity_alerts,
            "chart_counts": {
                "available": available_vehicles.count(),
                "booked": booked_vehicles.count(),
            },
        },
    )


@login_required
def profile_update(request):
    """GET: returns profile info as JSON. POST: updates profile fields and photo."""
    profile = request.user.profile

    if request.method == "GET":
        pic_url = ""
        if profile.profile_picture:
            pic_url = request.build_absolute_uri(profile.profile_picture.url)
        full_name = " ".join(
            filter(None, [profile.first_name, profile.middle_name, profile.last_name])
        ) or request.user.username
        data = {
            "username": request.user.username,
            "email": request.user.email or "",
            "first_name": profile.first_name,
            "middle_name": profile.middle_name,
            "last_name": profile.last_name,
            "full_name": full_name,
            "school_id": profile.school_id or "",
            "mobile_number": profile.mobile_number,
            "role": profile.get_role_display(),
            "department": str(profile.department) if profile.department else "",
            "profile_picture": pic_url,
        }
        return JsonResponse(data)

    if request.method == "POST":
        profile.first_name = request.POST.get("first_name", profile.first_name).strip()
        profile.middle_name = request.POST.get("middle_name", profile.middle_name).strip()
        profile.last_name = request.POST.get("last_name", profile.last_name).strip()
        profile.mobile_number = request.POST.get("mobile_number", profile.mobile_number).strip()

        # Remove picture if requested
        if request.POST.get("remove_picture") == "1":
            if profile.profile_picture:
                profile.profile_picture.delete(save=False)
            profile.profile_picture = None

        else:
            # Handle cropped image data URI sent from Cropper.js
            cropped_data = request.POST.get("cropped_image", "")
            if cropped_data and cropped_data.startswith("data:image"):
                try:
                    header, b64data = cropped_data.split(",", 1)
                    ext = header.split("/")[1].split(";")[0]  # png / jpeg
                    img_bytes = base64.b64decode(b64data)
                    file_name = f"profile_{request.user.pk}.{ext}"
                    # Delete old file first to avoid orphans
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                    profile.profile_picture.save(file_name, ContentFile(img_bytes), save=False)
                except Exception:
                    pass

        profile.save(update_fields=["first_name", "middle_name", "last_name", "mobile_number", "profile_picture"])
        request.user.email = request.POST.get("email", request.user.email).strip()
        request.user.save(update_fields=["email"])

        pic_url = ""
        if profile.profile_picture:
            pic_url = request.build_absolute_uri(profile.profile_picture.url)
        return JsonResponse({"success": True, "profile_picture": pic_url})

    return JsonResponse({"error": "Method not allowed"}, status=405)


# ─────────────────────────────────────────────────────────────────
#  AI CHAT ENDPOINT  —  MemoBot local AI (no external API)
#  POST /accounts/ai-chat/
#  Body (JSON): { "message": "...", "history": [{role, content}, ...] }
#  Returns JSON: { "reply": "..." }
# ─────────────────────────────────────────────────────────────────
import json as _json

@login_required
@csrf_protect
def ai_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body    = _json.loads(request.body)
        message = (body.get("message") or "").strip()
        history = body.get("history") or []
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if not message:
        return JsonResponse({"error": "Empty message"}, status=400)

    # Build user's display name
    profile   = getattr(request.user, "profile", None)
    fn        = getattr(profile, "first_name", "") or request.user.first_name
    mn        = getattr(profile, "middle_name", "")
    ln        = getattr(profile, "last_name",  "") or request.user.last_name
    mid_init  = (mn[0] + ".") if mn else ""
    full_name = " ".join(filter(None, [fn, mid_init, ln])) or request.user.username

    # Sanitise history
    clean_history = []
    for turn in history[-14:]:
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant") and isinstance(turn.get("content"), str):
            clean_history.append({"role": turn["role"], "content": turn["content"][:2000]})

    try:
        from accounts.ai_engine import get_response
        reply = get_response(message, user_name=full_name, history=clean_history)
        return JsonResponse({"reply": reply})
    except Exception as exc:
        return JsonResponse({"error": f"AI engine error: {exc}"}, status=500)

