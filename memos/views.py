from django.shortcuts import render

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from .models import Memo, MemoDecision
from .forms import MemoForm

from notifications.models import Notification


User = get_user_model()


try:
    from accounts.models import Profile
except Exception:  # pragma: no cover
    Profile = None


def _is_approver(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    role = getattr(getattr(user, "profile", None), "role", None)
    if Profile is not None:
        return role in (Profile.Role.APPROVER, Profile.Role.ADMIN)
    return role in ("approver", "admin")


def _is_admin(user) -> bool:
    """Returns True for Django staff/superusers AND system admins (profile.role='admin')."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    role = getattr(getattr(user, "profile", None), "role", None)
    if Profile is not None:
        return role == Profile.Role.ADMIN
    return role == "admin"


@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect("memos:memo_list")

    recent_memos = Memo.objects.all()[:5]
    conflicts_count = Memo.objects.filter(status=Memo.Status.CONFLICT).count()
    pending_decisions_count = Memo.objects.filter(status=Memo.Status.PENDING).count()
    return render(
        request,
        "memos/dashboard.html",
        {
            "recent_memos": recent_memos,
            "conflicts_count": conflicts_count,
            "pending_decisions_count": pending_decisions_count,
        },
    )


def memo_list(request):
    if request.user.is_authenticated and not request.user.is_staff:
        memos = Memo.objects.filter(assigned_user=request.user).select_related("created_by")
    else:
        memos = Memo.objects.all().select_related("created_by")
    return render(request, "memos/memo_list.html", {"memos": memos})


@login_required
def memo_admin_list(request):
    if not _is_admin(request.user):
        messages.error(request, "You do not have permission to view this page.")
        return redirect("accounts:post_login")
    memos = Memo.objects.all().select_related("assigned_user", "created_by").order_by("-date", "start_time")
    return render(request, "memos/memo_admin_list.html", {"memos": memos})


@require_http_methods(["GET", "POST"])
def memo_create(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if not _is_admin(request.user):
        messages.error(request, "You do not have permission to create memos.")
        return redirect("accounts:post_login")

    form = MemoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        memo = form.save(commit=False)
        memo.created_by = request.user
        if memo.has_conflicts():
            memo.status = Memo.Status.CONFLICT
            memo.save()
            messages.warning(request, "Conflict detected. Review options before finalizing.")
            _notify_conflict(request, memo)
            return redirect("memos:memo_conflict", pk=memo.pk)

        memo.status = Memo.Status.PENDING
        memo.save()
        messages.success(request, "Memo created successfully.")
        return redirect("memos:memo_list")

    return render(request, "memos/memo_form.html", {"form": form, "mode": "create"})


@require_http_methods(["GET", "POST"])
def memo_edit(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)

    if request.user.is_authenticated and not request.user.is_staff:
        if memo.created_by and (memo.created_by.is_staff or memo.created_by.is_superuser):
            messages.error(request, "You cannot edit this memo.")
            return redirect("memos:memo_list")

    form = MemoForm(request.POST or None, instance=memo)
    if request.method == "POST" and form.is_valid():
        memo = form.save(commit=False)
        if memo.has_conflicts():
            memo.status = Memo.Status.CONFLICT
            memo.save()
            messages.warning(request, "Conflict detected. Review options before finalizing.")
            _notify_conflict(request, memo)
            return redirect("memos:memo_conflict", pk=memo.pk)

        if memo.status == Memo.Status.CONFLICT:
            memo.status = Memo.Status.PENDING
        memo.save()
        messages.success(request, "Memo updated successfully.")
        return redirect("memos:memo_list")

    return render(
        request,
        "memos/memo_form.html",
        {"form": form, "mode": "edit", "memo": memo},
    )


@require_http_methods(["GET", "POST"])
def memo_delete(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)

    if request.user.is_authenticated and not request.user.is_staff:
        if memo.created_by and (memo.created_by.is_staff or memo.created_by.is_superuser):
            messages.error(request, "You cannot delete this memo.")
            return redirect("memos:memo_list")

    if request.method == "POST":
        memo.delete()
        messages.success(request, "Memo deleted.")
        return redirect("memos:memo_list")
    return render(request, "memos/memo_confirm_delete.html", {"memo": memo})


@login_required
@require_http_methods(["POST"])
def memo_user_approve(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)
    if memo.assigned_user_id != request.user.id or request.user.is_staff:
        messages.error(request, "You cannot perform this action.")
        return redirect("accounts:post_login")

    if memo.created_by and not (memo.created_by.is_staff or memo.created_by.is_superuser):
        messages.error(request, "This memo cannot be answered.")
        return redirect("memos:memo_list")

    memo.status = Memo.Status.APPROVED
    memo.save(update_fields=["status"])
    messages.success(request, "Memo marked as approved.")
    return redirect("memos:memo_list")


@login_required
@require_http_methods(["POST"])
def memo_user_mark_conflict(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)
    if memo.assigned_user_id != request.user.id or request.user.is_staff:
        messages.error(request, "You cannot perform this action.")
        return redirect("accounts:post_login")

    if memo.created_by and not (memo.created_by.is_staff or memo.created_by.is_superuser):
        messages.error(request, "This memo cannot be answered.")
        return redirect("memos:memo_list")

    memo.status = Memo.Status.CONFLICT
    memo.save(update_fields=["status"])
    messages.warning(request, "Memo marked as conflict.")
    return redirect("memos:memo_list")


def memo_conflict(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)
    conflicts = memo.conflicts_queryset()
    suggestion = memo.suggested_decision()
    users = User.objects.all().order_by("username")
    return render(
        request,
        "memos/memo_conflict.html",
        {"memo": memo, "conflicts": conflicts, "suggestion": suggestion, "users": users},
    )


@require_http_methods(["POST"])
def memo_conflict_accept(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)
    if not memo.required:
        messages.error(request, "Accept anyway is only allowed for required memos.")
        return redirect("memos:memo_conflict", pk=memo.pk)

    memo.status = Memo.Status.PENDING
    memo.save(update_fields=["status"])
    messages.success(request, "Memo accepted despite conflict.")
    return redirect("memos:memo_list")


@require_http_methods(["POST"])
def memo_conflict_delegate(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)
    delegated_to_id = request.POST.get("delegated_to")
    delegated_to = None
    if delegated_to_id:
        delegated_to = get_object_or_404(User, pk=delegated_to_id)

    memo.delegated_to = delegated_to
    memo.status = Memo.Status.DELEGATED if delegated_to else Memo.Status.CONFLICT
    memo.save(update_fields=["delegated_to", "status"])
    if delegated_to:
        messages.success(request, f"Memo delegated to {delegated_to.get_username()}.")
    else:
        messages.error(request, "Select a user to delegate to.")
        return redirect("memos:memo_conflict", pk=memo.pk)
    return redirect("memos:memo_list")


@require_http_methods(["POST"])
def memo_conflict_reschedule(request, pk: int):
    memo = get_object_or_404(Memo, pk=pk)
    messages.info(request, "Reschedule this memo to resolve the conflict.")
    return redirect("memos:memo_edit", pk=memo.pk)


@login_required
def decision_panel(request):
    if not _is_admin(request.user):
        messages.error(request, "You do not have permission to access this panel.")
        return redirect("accounts:post_login")
    conflicted = Memo.objects.filter(status=Memo.Status.CONFLICT).order_by("date", "start_time")
    pending = Memo.objects.filter(status=Memo.Status.PENDING).order_by("date", "start_time")
    return render(
        request,
        "memos/decision_panel.html",
        {"conflicted": conflicted, "pending": pending},
    )


@login_required
@require_http_methods(["POST"])
def decision_approve(request, pk: int):
    if not _is_approver(request.user):
        messages.error(request, "You do not have permission to approve memos.")
        return redirect("accounts:post_login")

    memo = get_object_or_404(Memo, pk=pk)
    memo.status = Memo.Status.APPROVED
    memo.save(update_fields=["status"])
    MemoDecision.objects.create(
        memo=memo,
        decided_by=request.user,
        action=MemoDecision.Action.APPROVE,
        note=(request.POST.get("note") or "").strip(),
    )
    messages.success(request, "Memo approved.")
    _notify_decision(request, memo, approved=True)
    next_url = request.POST.get("next")
    return redirect(next_url or "memos:decision_panel")


@login_required
@require_http_methods(["POST"])
def decision_reject(request, pk: int):
    if not _is_approver(request.user):
        messages.error(request, "You do not have permission to reject memos.")
        return redirect("accounts:post_login")

    memo = get_object_or_404(Memo, pk=pk)
    memo.status = Memo.Status.REJECTED
    memo.save(update_fields=["status"])
    MemoDecision.objects.create(
        memo=memo,
        decided_by=request.user,
        action=MemoDecision.Action.REJECT,
        note=(request.POST.get("note") or "").strip(),
    )
    messages.warning(request, "Memo rejected.")
    _notify_decision(request, memo, approved=False)
    next_url = request.POST.get("next")
    return redirect(next_url or "memos:decision_panel")


def _notify_conflict(request, memo: Memo) -> None:
    Notification.objects.create(
        user=memo.assigned_user,
        title="Conflict Detected",
        message=f"Your memo '{memo.title}' overlaps with another schedule.",
        severity=Notification.Severity.WARNING,
    )


def _notify_decision(request, memo: Memo, approved: bool) -> None:
    if approved:
        title = "Memo Approved"
        severity = Notification.Severity.INFO
        message = f"Your memo '{memo.title}' has been approved."
    else:
        title = "Memo Rejected"
        severity = Notification.Severity.DANGER
        message = f"Your memo '{memo.title}' has been rejected."

    Notification.objects.create(
        user=memo.assigned_user,
        title=title,
        message=message,
        severity=severity,
    )
