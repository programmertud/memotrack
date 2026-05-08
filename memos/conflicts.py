from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import LeaveRequest
from resources.models import VehicleBooking, ResourceBooking

User = get_user_model()

def check_conflicts(date, start_time, end_time, users=None, venue=None, resources=None, exclude_memo_id=None):
    """
    Check for scheduling conflicts across multiple constraints.
    Returns a list of conflict dictionaries.
    """
    conflicts = []
    
    if users is None:
        users = []
    if not isinstance(users, (list, tuple, set)):
        users = [users]

    # 1. Temporal Overlaps for Personnel (Assigned Users)
    from memos.models import Memo
    for user in users:
        if not user:
            continue
            
        user_memos = Memo.objects.filter(employees=user, date=date)
        if exclude_memo_id:
            user_memos = user_memos.exclude(pk=exclude_memo_id)
        
        overlapping_memos = user_memos.filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )
        
        for m in overlapping_memos:
            full_name = f"{user.profile.first_name} {user.profile.last_name}" if hasattr(user, 'profile') and user.profile.first_name else user.username
            conflicts.append({
                "type": "personnel",
                "message": f"Employee {full_name} has an overlapping memo: {m.title} ({m.start_time} - {m.end_time})",
                "severity": "warning"
            })

        # 2. Personnel on Leave
        leave_overlaps = LeaveRequest.objects.filter(
            user=user,
            start_date__lte=date,
            end_date__gte=date,
            status="approved"
        )
        
        for l in leave_overlaps:
            full_name = f"{user.profile.first_name} {user.profile.last_name}" if hasattr(user, 'profile') and user.profile.first_name else user.username
            conflicts.append({
                "type": "leave",
                "message": f"Employee {full_name} is on approved leave ({l.start_date} to {l.end_date})",
                "severity": "danger"
            })

    # 3. Venue Conflicts (String-based lookup)
    if venue:
        from memos.models import Memo
        venue_memos = Memo.objects.filter(venue__iexact=venue, date=date)
        if exclude_memo_id:
            venue_memos = venue_memos.exclude(pk=exclude_memo_id)
            
        overlapping_venue = venue_memos.filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )
        
        for m in overlapping_venue:
            conflicts.append({
                "type": "venue",
                "message": f"Venue '{venue}' is already in use for: {m.title} ({m.start_time} - {m.end_time})",
                "severity": "warning"
            })

    # 4. Resource Conflicts (Structured ResourceBooking)
    if resources:
        # resources is expected to be a list of Resource IDs or objects
        for res in resources:
            res_id = res.id if hasattr(res, 'id') else res
            existing_bookings = ResourceBooking.objects.filter(
                resource_id=res_id,
                memo__date=date
            )
            if exclude_memo_id:
                existing_bookings = existing_bookings.exclude(memo_id=exclude_memo_id)
                
            overlaps = existing_bookings.filter(
                Q(memo__start_time__lt=end_time) & Q(memo__end_time__gt=start_time)
            )
            
            for b in overlaps:
                conflicts.append({
                    "type": "resource",
                    "message": f"Resource '{b.resource.name}' is already booked for: {b.memo.title}",
                    "severity": "danger"
                })

    return conflicts
