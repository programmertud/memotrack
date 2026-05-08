from google import genai
from google.genai import types
from django.conf import settings
import json
import logging
import base64
from datetime import datetime

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


def get_genai_client():
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def parse_memo_image(image_bytes: bytes, mime_type: str):
    """
    Uses Gemini Vision to extract structured scheduling data from an image.
    Accepts raw image bytes and its MIME type (e.g. 'image/jpeg', 'image/png').
    Returns a dict with the same keys as parse_memo_text, or None on failure.
    """
    client = get_genai_client()
    if not client:
        return None

    from django.utils import timezone
    now = timezone.now()

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
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
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


def local_parse_memo_text(text):
    """
    Fallback parser using regex and keyword matching when AI API is unavailable.
    """
    import re
    from django.utils import timezone
    now = timezone.now()
    
    # Defaults
    data = {
        "title": "New Event",
        "date": now.strftime("%Y-%m-%d"),
        "start_time": "08:00",
        "end_time": "17:00",
        "venue": "",
        "destination": "",
        "priority": "medium",
        "category": "department",
        "participants": "",
        "activity_type": "Meeting",
        "description": text[:200] + "..." if len(text) > 200 else text
    }

    # 1. Extract Title (usually Subject line or First line)
    subj_match = re.search(r'(?:Subject|Re|Title):\s*(.*)', text, re.I)
    if subj_match:
        data["title"] = subj_match.group(1).strip()
    else:
        # Take first non-empty line
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines: data["title"] = lines[0][:100]

    # 2. Extract Date (supports YYYY-MM-DD, MM/DD/YYYY, and Month DD, YYYY)
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})(?:st|nd|rd|th)?,\s+(\d{4})'
    ]
    for p in date_patterns:
        m = re.search(p, text, re.I)
        if m:
            if len(m.groups()) == 1:
                data["date"] = m.group(1)
            else:
                # Convert Month DD, YYYY to YYYY-MM-DD
                month, day, year = m.group(1), m.group(2), m.group(3)
                for fmt in ("%b", "%B"):
                    try:
                        dt = datetime.strptime(f"{month} {day} {year}", f"{fmt} %d %Y")
                        data["date"] = dt.strftime("%Y-%m-%d")
                        break
                    except: continue
            break

    # 3. Extract Times (supports HH:MM AM/PM and 24h)
    time_matches = re.findall(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)', text)
    if time_matches:
        # Convert first match to 24h
        t1 = time_matches[0].upper()
        try:
            if 'AM' in t1 or 'PM' in t1:
                dt = datetime.strptime(t1.replace(" ", ""), "%I:%M%p")
            else:
                dt = datetime.strptime(t1, "%H:%M")
            data["start_time"] = dt.strftime("%H:%M")
            
            # If second match exists, set end_time
            if len(time_matches) > 1:
                t2 = time_matches[1].upper()
                if 'AM' in t2 or 'PM' in t2:
                    dt2 = datetime.strptime(t2.replace(" ", ""), "%I:%M%p")
                else:
                    dt2 = datetime.strptime(t2, "%H:%M")
                data["end_time"] = dt2.strftime("%H:%M")
        except: pass

    # 4. Extract Venue and Destination
    # Captures consecutive capitalized words before a known location keyword
    # Example: "University Gymnasium"
    v_pattern = r'([A-Z][\w]*(?:\s+[A-Z][\w]*)*\s+(?:Building|Room|Hall|Gym|Gymnasium|AVR|Campus|Center|Office|Lab|Library|Auditorium|Clinic))'
    v_match = re.search(v_pattern, text)
    if v_match:
        data["venue"] = v_match.group(1).strip()
        # Remove common introductory words if they were caught
        for word in ["The", "A", "This", "Our", "In", "At"]:
            if data["venue"].startswith(word + " "):
                data["venue"] = data["venue"][len(word)+1:].strip()
    
    # If no match, try the "at/in" fallback
    if not data["venue"]:
        v_fallback = re.search(r'(?:at|in|Venue:)\s*([A-Z][\w\s,]+)', text, re.I)
        if v_fallback: data["venue"] = v_fallback.group(1).strip()
    
    # Look for "Destination:", "to:" (if travel related)
    # Filter out common false positives like "TO:" (recipient)
    if any(w in text.lower() for w in ["travel", "itinerary", "destination", "trip"]):
        # Find all lines with "to:" or "Destination:"
        for line in text.split('\n'):
            l_strip = line.strip()
            if l_strip.upper().startswith("TO:") and "DESTINATION" not in l_strip.upper():
                continue
            dest_match = re.search(r'(?:Destination|to):\s*([A-Z][\w\s,]+)', l_strip, re.I)
            if dest_match:
                data["destination"] = dest_match.group(1).strip()
                break

    # 5. Extract Description (First meaningful block of text after headers)
    # Filter out lines that look like headers (To:, From:, Date:, Subject:)
    body_lines = []
    found_start = False
    for line in text.split('\n'):
        l = line.strip()
        if not l: continue
        if any(l.startswith(h) for h in ["TO:", "FROM:", "DATE:", "SUBJECT:", "MEMORANDUM"]):
            continue
        body_lines.append(l)
    
    if body_lines:
        # Join first two non-empty blocks if they are short, or just the first one
        data["description"] = " ".join(body_lines[:2])

    # 6. Priority inference
    if any(w in text.lower() for w in ["urgent", "mandatory", "required", "immediate", "critical"]):
        data["priority"] = "high"

    return data


def parse_memo_text(text):
    """
    Uses Gemini to extract structured data. Falls back to Local Regex Parser on failure.
    """
    client = get_genai_client()
    if not client:
        logger.warning("Gemini API not configured. Using local fallback parser.")
        return local_parse_memo_text(text)

    from django.utils import timezone
    now = timezone.now()
    
    prompt = f"""
    Today's Date: {now.strftime('%A, %B %d, %Y')}

    Extract ALL scheduling details from the following document.
    Return ONLY a valid JSON object with keys: title, date, start_time, end_time, venue, destination, priority, category, participants, activity_type, description.

    Memo Text:
    \"\"\"
    {text}
    \"\"\"
    """

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        # Check if response was blocked or empty
        if not response.text:
            logger.error("Gemini Parsing returned empty text. Falling back to local parser.")
            return local_parse_memo_text(text)
            
        content = response.text.strip()
        
        if "```" in content:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match: content = json_match.group(0)
        
        if not content:
            return local_parse_memo_text(text)
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"Gemini API Error: {e}. Using local fallback parser.")
        return local_parse_memo_text(text)


def get_scheduling_recommendation(memo_data, conflicts):
    """
    Asks Gemini for a recommendation. Falls back to a rule-based suggestion.
    """
    try:
        client = get_genai_client()
        if not client:
            raise ValueError("No client")
        
        conflicts_str = "\n".join([f"- {c.title} on {c.date} at {c.venue}" for c in conflicts])
        prompt = f"New event {memo_data.get('title')} conflicts with:\n{conflicts_str}\nRecommend action (reschedule/delegate/anyway)."
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        # Rule-based fallback
        if not conflicts: return "No conflicts detected. Proceed with scheduling."
        highest_prio = any(c.priority == "high" for c in conflicts)
        if memo_data.get("priority") == "high" and not highest_prio:
            return "Recommendation: This is a high-priority event. Approve anyway or reschedule existing lower-priority events."
        return "Recommendation: Overlap detected. Consider rescheduling this memo or delegating it to another user."


def get_predictive_analytics(upcoming_memos):
    """
    Analyzes schedule density. Falls back to a local calculation.
    """
    try:
        client = get_genai_client()
        if not client:
            raise ValueError("No client")
        
        memos_data = "\n".join([f"- {m.date}: {m.start_time}" for m in upcoming_memos])
        prompt = f"Analyze schedule density and predict busy periods:\n{memos_data}"
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        # Simple local calculation
        if not upcoming_memos: return "Not enough data for forecasting."
        dates = [m.date for m in upcoming_memos]
        most_common = max(set(dates), key=dates.count)
        count = dates.count(most_common)
        if count > 1:
            return f"Predictive Insight: {most_common} is identified as a high-demand day with {count} scheduled activities. Monitor for potential resource bottlenecks."
        return "Predictive Insight: Schedule density is currently optimal. No high-demand peaks predicted for the next 7 days."

