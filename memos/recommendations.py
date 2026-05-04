from datetime import datetime, timedelta, time
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from .conflicts import check_conflicts
import logging

logger = logging.getLogger(__name__)

def find_candidate_slots(memo, days_ahead=7):
    """
    Find conflict-free time slots for a given memo.
    Returns a list of dictionaries with 'date', 'start_time', 'end_time', and 'score'.
    """
    candidates = []
    duration = datetime.combine(datetime.today(), memo.end_time) - datetime.combine(datetime.today(), memo.start_time)
    
    # Define working hours: 8:00 AM to 5:00 PM
    WORKING_START = time(8, 0)
    WORKING_END = time(17, 0)
    
    start_date = memo.date
    resources = [rb.resource for rb in memo.resource_bookings.all()]
    
    for i in range(days_ahead + 1):
        target_date = start_date + timedelta(days=i)
        
        # Propose slots throughout the day
        # We'll check every 30 minutes
        current_time = datetime.combine(target_date, WORKING_START)
        end_of_day = datetime.combine(target_date, WORKING_END)
        
        while current_time + duration <= end_of_day:
            slot_start = current_time.time()
            slot_end = (current_time + duration).time()
            
            # Skip the original slot if we are on the original date
            if target_date == memo.date and slot_start == memo.start_time:
                current_time += timedelta(minutes=30)
                continue
            
            conflicts = check_conflicts(
                date=target_date,
                start_time=slot_start,
                end_time=slot_end,
                user=memo.assigned_user,
                venue=memo.venue,
                resources=resources,
                exclude_memo_id=memo.pk
            )
            
            if not conflicts:
                score = calculate_slot_score(memo, target_date, slot_start, slot_end)
                candidates.append({
                    'date': target_date,
                    'start_time': slot_start,
                    'end_time': slot_end,
                    'score': score
                })
            
            current_time += timedelta(minutes=30)
            
    # Sort candidates by score (highest first)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:3]  # Return top 3 suggestions

def calculate_slot_score(memo, date, start_time, end_time):
    """
    Score a candidate slot based on various parameters.
    """
    score = 100.0
    
    # 1. Distance from original date/time (closer is better)
    days_diff = abs((date - memo.date).days)
    score -= days_diff * 10
    
    # 2. Time of day preference (Institutional Pattern)
    # Heuristic: University preferred hours are 9:00 AM to 4:00 PM
    if start_time >= time(9, 0) and end_time <= time(16, 0):
        score += 5
    
    # 3. Lunch break avoidance (12:00 PM to 1:00 PM)
    lunch_start = time(12, 0)
    lunch_end = time(13, 0)
    if not (start_time >= lunch_end or end_time <= lunch_start):
        score -= 15 # Avoid overlapping with lunch
        
    # 4. Priority impact
    # High priority items should ideally be as early as possible
    if memo.priority == 'high':
        # Reward earlier dates
        score -= days_diff * 5
        # Reward earlier times in the day
        score += (17 - start_time.hour) * 0.5
        
    return score

def get_recommendation_summary(memo):
    """
    Orchestrates finding slots and generating the AI summary.
    """
    candidates = find_candidate_slots(memo)
    
    if not candidates:
        return {
            "summary": "No conflict-free slots found in the next 7 days. Consider delegating or overriding.",
            "slots": []
        }
        
    from memotrack.ai_utils import get_gemini_model
    model = get_gemini_model(json_mode=False)
    
    slots_str = "\n".join([
        f"- {c['date'].strftime('%Y-%m-%d')} at {c['start_time'].strftime('%H:%M')} - {c['end_time'].strftime('%H:%M')} (Score: {c['score']:.1f})"
        for c in candidates
    ])
    
    prompt = f"""
    You are an AI scheduling assistant. A memo titled "{memo.title}" has conflicts.
    Priority: {memo.get_priority_display()}
    Category: {memo.get_category_display()}
    
    Available optimal slots:
    {slots_str}
    
    Analyze these options and provide a concise, professional recommendation (max 3 sentences).
    Explain why these slots are better based on priority and efficiency.
    Mention if any slot is particularly good because it's close to the original time or fits better within standard working hours.
    """
    
    summary = "Suggested alternative slots are available below."
    try:
        if model:
            response = model.generate_content(prompt)
            summary = response.text.strip()
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        
    return {
        "summary": summary,
        "slots": candidates
    }
