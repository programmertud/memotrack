from django.shortcuts import render

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

from memos.models import Memo
from memos.models import MemoDecision
from notifications.models import Notification
from resources.models import Vehicle, VehicleBooking

from .models import Attendance, LeaveRequest, Profile
from .forms import AdminUserCreateForm, AdminUserUpdateForm


User = get_user_model()


def home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return redirect("accounts:post_login")


@login_required
def post_login(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect("accounts:admin_dashboard")

    role = getattr(getattr(request.user, "profile", None), "role", None)

    if role == Profile.Role.HR:
        return redirect("accounts:hr_dashboard")
    if role == Profile.Role.INSTRUCTOR:
        return redirect("accounts:instructor_dashboard")
    if role == Profile.Role.APPROVER:
        return redirect("accounts:approver_dashboard")
    if role == Profile.Role.TRANSPORTATION:
        return redirect("accounts:transportation_dashboard")

    return redirect("memos:memo_list")


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("accounts:post_login")

    today = timezone.localdate()
    upcoming_until = today + timedelta(days=7)

    total_instructors = Profile.objects.filter(role=Profile.Role.INSTRUCTOR).count()
    total_staff = Profile.objects.exclude(role=Profile.Role.STUDENT).exclude(
        role=Profile.Role.INSTRUCTOR
    ).count()
    total_vehicles = Vehicle.objects.count()

    pending_requests = Memo.objects.filter(status=Memo.Status.PENDING).count()
    approved_requests = Memo.objects.filter(status=Memo.Status.APPROVED).count()
    rejected_requests = Memo.objects.filter(status=Memo.Status.REJECTED).count()
    today_schedules = Memo.objects.filter(date=today).order_by("start_time")
    conflict_alerts = Memo.objects.filter(status=Memo.Status.CONFLICT).count()
    upcoming_events = Memo.objects.filter(date__gt=today, date__lte=upcoming_until).order_by(
        "date", "start_time"
    )[:10]

    return render(
        request,
        "accounts/dashboards/admin_dashboard.html",
        {
            "total_instructors": total_instructors,
            "total_staff": total_staff,
            "total_vehicles": total_vehicles,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "today_schedules": today_schedules,
            "conflict_alerts": conflict_alerts,
            "upcoming_events": upcoming_events,
        },
    )


def _normalize_admin_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role not in {Profile.Role.STAFF, Profile.Role.INSTRUCTOR}:
        return ""
    return role


@staff_member_required
def admin_user_list(request, role: str):
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


@staff_member_required
def admin_user_create(request, role: str):
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


@staff_member_required
def admin_user_edit(request, role: str, pk: int):
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


@staff_member_required
def admin_user_delete(request, role: str, pk: int):
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
