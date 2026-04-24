from .models import Notification


def unread_notifications(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {
            "unread_notifications_count": 0,
            "recent_notifications": [],
        }

    return {
        "unread_notifications_count": Notification.objects.filter(user=user, is_read=False).count(),
        "recent_notifications": (
            Notification.objects.filter(user=user)
            .order_by("-created_at")[:8]
        ),
    }
