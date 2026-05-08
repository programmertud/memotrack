from django.shortcuts import render

from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from .models import Memo, MemoDecision
from .forms import MemoForm
from .conflicts import check_conflicts

from notifications.models import Notification
from memotrack.ai_utils import parse_memo_text, get_scheduling_recommendation, get_predictive_analytics, parse_memo_image, extract_text_from_file
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json



from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from accounts.models import Campus, Department


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
    
    # Predictive Analytics
    upcoming = Memo.objects.filter(date__gte=timezone.now().date()).order_by("date")[:20]
    ai_forecast = get_predictive_analytics(upcoming)

    return render(
        request,
        "memos/dashboard.html",
        {
            "recent_memos": recent_memos,
            "conflicts_count": conflicts_count,
            "pending_decisions_count": pending_decisions_count,
            "ai_forecast": ai_forecast,
        },
    )


def memo_list(request):
    if request.user.is_authenticated and not request.user.is_staff:
        memos = Memo.objects.filter(employees=request.user).select_related("created_by")
    else:
        memos = Memo.objects.all().select_related("created_by")
    return render(request, "memos/memo_list.html", {"memos": memos})


@login_required
def memo_admin_list(request):
    if not _is_admin(request.user):
        messages.error(request, "You do not have permission to view this page.")
        return redirect("accounts:post_login")
    memos = Memo.objects.all().prefetch_related("employees", "created_by").order_by("-date", "start_time")
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
        memo.status = Memo.Status.PENDING
        memo.save()
        form.save_m2m()
        
        if memo.has_conflicts():
            memo.status = Memo.Status.CONFLICT
            memo.save()
            messages.warning(request, "Conflict detected. Review options before finalizing.")
            try:
                _notify_conflict(request, memo)
            except NameError:
                pass # in case _notify_conflict is not imported/defined
            return redirect("memos:memo_conflict", pk=memo.pk)

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
    if not memo.employees.filter(id=request.user.id).exists() or request.user.is_staff:
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
    if not memo.employees.filter(id=request.user.id).exists() or request.user.is_staff:
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
    
    # AI Recommendation
    ai_recommendation = get_scheduling_recommendation({
        'title': memo.title,
        'date': str(memo.date),
        'start_time': str(memo.start_time),
        'end_time': str(memo.end_time),
        'venue': memo.venue,
        'priority': memo.priority,
    }, conflicts)

    users = User.objects.all().order_by("username")
    return render(
        request,
        "memos/memo_conflict.html",
        {
            "memo": memo, 
            "conflicts": conflicts, 
            "suggestion": suggestion, 
            "ai_recommendation": ai_recommendation,
            "users": users
        },
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


@login_required
@require_http_methods(["POST"])
def memo_parse_ai(request):
    """AJAX endpoint to parse memo text using AI."""
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        data = json.loads(request.body)
        text = data.get("text", "")
        if not text:
            return JsonResponse({"error": "No text provided"}, status=400)
        
        parsed_data = parse_memo_text(text)
        if parsed_data:
            return JsonResponse(parsed_data)
        else:
            return JsonResponse({"error": "AI failed to parse text"}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def memo_parse_ai_file(request):
    """AJAX endpoint to parse an uploaded file (image, PDF, DOCX, TXT) using AI."""
    if not _is_admin(request.user):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"error": "No file provided"}, status=400)

    file_name = uploaded.name.lower()
    IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff")

    try:
        if any(file_name.endswith(ext) for ext in IMAGE_TYPES):
            # Route images to Gemini Vision
            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp",
                ".gif": "image/gif", ".bmp": "image/bmp",
                ".tiff": "image/tiff",
            }
            ext = next(ext for ext in IMAGE_TYPES if file_name.endswith(ext))
            mime_type = mime_map.get(ext, "image/jpeg")
            image_bytes = uploaded.read()
            parsed_data = parse_memo_image(image_bytes, mime_type)
        else:
            # Extract text from PDF/DOCX/TXT then parse
            text = extract_text_from_file(uploaded, uploaded.name)
            if not text:
                return JsonResponse({"error": "Could not extract any text from the file."}, status=400)
            parsed_data = parse_memo_text(text)

        if parsed_data:
            return JsonResponse(parsed_data)
        else:
            return JsonResponse({"error": "AI failed to parse the file."}, status=500)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {e}"}, status=500)



def _notify_conflict(request, memo: Memo) -> None:
    for employee in memo.employees.all():
        Notification.objects.create(
            user=employee,
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

    for employee in memo.employees.all():
        Notification.objects.create(
            user=employee,
            title=title,
            message=message,
            severity=severity,
        )


@login_required
@require_http_methods(["POST"])
def memo_check_conflicts(request):
    """AJAX endpoint to perform real-time conflict detection."""
    try:
        data = json.loads(request.body)
        date = data.get("date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        user_ids = data.get("employees") or []
        if not user_ids and data.get("assigned_user"):
            user_ids = [data.get("assigned_user")]

        venue = data.get("venue")
        resource_ids = data.get("resources", [])
        exclude_memo_id = data.get("exclude_memo_id")

        if not all([date, start_time, end_time]):
            return JsonResponse({"conflicts": []})

        users = User.objects.filter(pk__in=user_ids)

        conflicts = check_conflicts(
            date=date,
            start_time=start_time,
            end_time=end_time,
            users=users,
            venue=venue,
            resources=resource_ids,
            exclude_memo_id=exclude_memo_id
        )

        return JsonResponse({"conflicts": conflicts})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def memo_recommendations(request, pk=None):
    """
    AJAX endpoint to get AI-based scheduling recommendations.
    Accepts GET (for existing) or POST (for new/preview).
    """
    from .models import Memo
    from .recommendations import get_recommendation_summary
    from django.shortcuts import get_object_or_404
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Create a transient Memo instance for the recommendation engine
            memo = Memo(
                title=data.get('title', 'Untitled'),
                date=data.get('date'),
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                venue=data.get('venue', ''),
                priority=data.get('priority', 'medium'),
                category=data.get('category', 'department')
            )
            # Try to attach assigned user
            user_ids = data.get('employees') or []
            if not user_ids and data.get('assigned_user'):
                user_ids = [data.get('assigned_user')]
            
            if user_ids:
                memo.employees.set(User.objects.filter(pk__in=user_ids))
            
            # Since it's a mock, it has no PK. We'll handle resource_bookings mock in find_candidate_slots if needed.
        except Exception as e:
            return JsonResponse({"error": f"Invalid data: {str(e)}"}, status=400)
    else:
        memo = get_object_or_404(Memo, pk=pk)
    
    # Permission check (simplified for now)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    result = get_recommendation_summary(memo)
    
    formatted_slots = []
    for slot in result['slots']:
        formatted_slots.append({
            'date': slot['date'].strftime('%Y-%m-%d'),
            'start_time': slot['start_time'].strftime('%H:%M'),
            'end_time': slot['end_time'].strftime('%H:%M'),
            'score': round(slot['score'], 1)
        })
    
    return JsonResponse({
        "summary": result['summary'],
        "slots": formatted_slots
    })
