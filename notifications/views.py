from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from .models import Notification


def notification_list(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user)[:50]
    else:
        notifications = Notification.objects.all()[:50]
    return render(
        request,
        "notifications/notification_list.html",
        {"notifications": notifications},
    )


@require_http_methods(["POST"])
def notification_mark_read(request, pk: int):
    notification = get_object_or_404(Notification, pk=pk)
    if request.user.is_authenticated and notification.user_id != request.user.id:
        messages.error(request, "You cannot modify this notification.")
        return redirect("notifications:notification_list")

    notification.is_read = True
    notification.save(update_fields=["is_read"])
    messages.success(request, "Notification marked as read.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "notifications:notification_list"
    return redirect(next_url)


@login_required
@require_http_methods(["POST"])
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "notifications:notification_list"
    return redirect(next_url)
