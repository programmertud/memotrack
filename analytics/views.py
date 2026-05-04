from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import SchedulingMetric, SchedulingRiskIndicator
from memos.models import Memo
from resources.models import Venue

def is_admin(user):
    return user.is_staff or (hasattr(user, 'profile') and user.profile.role == 'admin')

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    metrics = SchedulingMetric.objects.all().order_by('-reference_date')[:10]
    risks = SchedulingRiskIndicator.objects.all().order_by('target_date')[:5]
    
    # Generate some basic stats for the dashboard if empty
    total_memos = Memo.objects.count()
    conflict_memos = Memo.objects.filter(status=Memo.Status.CONFLICT).count()
    total_venues = Venue.objects.count()
    
    context = {
        'metrics': metrics,
        'risks': risks,
        'stats': {
            'total_memos': total_memos,
            'conflict_memos': conflict_memos,
            'total_venues': total_venues,
            'conflict_rate': round((conflict_memos / total_memos * 100) if total_memos > 0 else 0, 1)
        }
    }
    return render(request, 'analytics/dashboard.html', context)
