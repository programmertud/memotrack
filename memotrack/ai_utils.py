import google.generativeai as genai
from django.conf import settings
import json
import logging
import base64

logger = logging.getLogger(__name__)


def extract_text_from_file(file_obj, file_name: str) -> str:
    """
    Extracts plain text from a PDF or DOCX file object.
    Returns the extracted text string, or raises ValueError for unsupported types.
    """
    name = file_name.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_obj)
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")
    elif name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(file_obj)
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            raise ValueError(f"Could not extract text from DOCX: {e}")
    elif name.endswith(".doc"):
        raise ValueError("Legacy .doc format is not supported. Please save as .docx.")
    elif name.endswith(".txt"):
        return file_obj.read().decode("utf-8", errors="ignore").strip()
    else:
        raise ValueError(f"Unsupported file type: {file_name}")


def parse_memo_image(image_bytes: bytes, mime_type: str):
    """
    Uses Gemini Vision to extract structured scheduling data from an image.
    Accepts raw image bytes and its MIME type (e.g. 'image/jpeg', 'image/png').
    Returns a dict with the same keys as parse_memo_text, or None on failure.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    genai.configure(api_key=api_key)

    from django.utils import timezone
    now = timezone.now()

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-image",
        generation_config={"response_mime_type": "application/json"},
    )

    prompt = f"""
    Today's Date: {now.strftime('%A, %B %d, %Y')}

    You are an intelligent scheduling assistant for a university memo tracking system.
    The attached image is a scanned memo, letter, travel order, or similar document.
    Read all visible text from the image (perform OCR if needed) and extract ALL scheduling details.

    Return ONLY a valid JSON object with these exact keys:
    - title: String — concise event/activity title
    - date: String — in YYYY-MM-DD format
    - start_time: String — in HH:MM 24-hour format
    - end_time: String — in HH:MM 24-hour format (estimate if not stated)
    - venue: String — location or room
    - destination: String — travel destination if travel order, else empty string
    - priority: String — one of: low, medium, high
    - category: String — one of: university, department, personal
    - participants: String — comma-separated names/roles/groups; empty string if none
    - activity_type: String — e.g. Meeting, Seminar, Training, Travel, Conference, Workshop
    - description: String — brief summary of purpose
    """

    try:
        image_part = {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}
        response = model.generate_content([prompt, image_part])
        content = response.text.strip()
        if "```" in content:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
        return json.loads(content)
    except Exception as e:
        if "403" in str(e):
            logger.error(f"Gemini Image Parsing Error: 403 Your project has been denied access. Please check Google AI Studio project status.")
        else:
            logger.error(f"Gemini Image Parsing Error: {e}")
        return None

def get_gemini_model(json_mode=False):
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    
    config = {}
    if json_mode:
        config["response_mime_type"] = "application/json"
        
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
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

    You are an intelligent scheduling assistant for a university memo tracking system.
    Extract ALL scheduling details from the following document (memo, email, or travel order).

    Return ONLY a valid JSON object with these exact keys:
    - title: String — concise event/activity title
    - date: String — in YYYY-MM-DD format (infer from document; use today if unclear)
    - start_time: String — in HH:MM 24-hour format
    - end_time: String — in HH:MM 24-hour format (estimate duration if not stated)
    - venue: String — location or room where the activity takes place
    - destination: String — travel destination if this is a travel order, otherwise empty string
    - priority: String — one of: low, medium, high (infer from language: "required", "urgent" = high; "all heads" = medium; otherwise low)
    - category: String — one of: university, department, personal
      * university: university-wide events, all-hands, institution-level directives
      * department: departmental meetings, office-level, specific college/unit
      * personal: individual travel orders, personal requests, single-person tasks
    - participants: String — comma-separated list of mentioned names, roles, or groups (e.g. "Dr. Santos, Prof. Reyes, All Department Heads"); empty string if none
    - activity_type: String — type of activity (e.g. Meeting, Seminar, Training, Travel, Conference, Workshop, Inspection); infer from context
    - description: String — brief summary of the memo purpose

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
        if "403" in str(e):
            logger.error(f"Gemini Parsing Error: 403 Your project has been denied access. Please check Google AI Studio project status.")
        else:
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
