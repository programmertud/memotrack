import google.generativeai as genai
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

def get_gemini_model(json_mode=False):
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    
    config = {}
    if json_mode:
        config["response_mime_type"] = "application/json"
        
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=config if config else None
    )

def parse_memo_text(text):
    """
    Uses Gemini to extract structured data from unstructured memo text.
    Returns a dictionary with: title, date, start_time, end_time, venue, priority, description.
    """
    model = get_gemini_model(json_mode=True)
    if not model:
        return None

    from django.utils import timezone
    now = timezone.now()
    
    prompt = f"""
    Today's Date: {now.strftime('%A, %B %d, %Y')}
    
    Extract scheduling details from the following university memo text. 
    Return a JSON object with the following keys:
    - title: String
    - date: String (YYYY-MM-DD format)
    - start_time: String (HH:MM format, 24h)
    - end_time: String (HH:MM format, 24h)
    - venue: String
    - priority: String (one of: low, medium, high)
    - description: String

    Memo Text:
    \"\"\"
    {text}
    \"\"\"
    """

    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Robust JSON extraction
        if "```" in content:
            # Try to find the first block that looks like JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
        
        return json.loads(content)
    except Exception as e:
        logger.error(f"Gemini Parsing Error: {e}")
        # Fallback: if JSON fails but we have text, return it as description? No, just return None
        return None

def get_scheduling_recommendation(memo_data, conflicts):
    """
    Asks Gemini for a recommendation when a conflict occurs.
    """
    model = get_gemini_model(json_mode=False)
    if not model:
        return "No AI model configured for recommendations."

    conflicts_str = "\n".join([f"- {c.title} on {c.date} from {c.start_time} to {c.end_time} at {c.venue}" for c in conflicts])
    
    prompt = f"""
    A new event is being scheduled but conflicts with existing ones.
    
    New Event:
    - Title: {memo_data.get('title')}
    - Date: {memo_data.get('date')}
    - Time: {memo_data.get('start_time')} - {memo_data.get('end_time')}
    - Venue: {memo_data.get('venue')}
    - Priority: {memo_data.get('priority')}
    
    Existing Conflicts:
    {conflicts_str}
    
    As an AI scheduling assistant, provide a concise recommendation (max 3 sentences). 
    Suggest whether to reschedule, delegate, or approve anyway based on priority. 
    If rescheduling, suggest a possible alternative time slot (e.g., 1 hour later).
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Recommendation Error: {e}")
        return "Error generating AI recommendation."

def get_predictive_analytics(upcoming_memos):
    """
    Analyzes upcoming schedule density and predicts high-demand periods.
    """
    if not upcoming_memos:
        return "Not enough upcoming schedules to forecast demand. Add more memos to see predictive insights."
        
    model = get_gemini_model(json_mode=False)
    if not model:
        return None

    memos_data = "\n".join([f"- {m.date}: {m.start_time}-{m.end_time} ({m.venue})" for m in upcoming_memos])

    prompt = f"""
    Analyze the following upcoming university schedules and predict high-demand periods or potential bottleneck days.
    Provide a brief summary for a dashboard (2-3 sentences).
    
    Upcoming Schedules:
    {memos_data}
    
    Analysis:
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Analytics Error: {e}")
        return "Unable to forecast demand at this time."
