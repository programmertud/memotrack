"""
SkedIt AI Engine — MemoBot
Self-contained, no external API required.
Uses intent detection + knowledge base + context tracking.
"""
import re
import math
from datetime import datetime


# ── KNOWLEDGE BASE ─────────────────────────────────────────────
# Each entry: (keywords_list, response_text, weight)
# Weight boosts entries that are more specific
KB = [
    # ── GREETINGS ──────────────────────────────────────────────
    (["hello","hi","hey","good morning","good afternoon","good evening","sup","greetings"],
     "Hello {name}! 👋 I'm **MemoBot**, your SkedIt AI Assistant. I can help you with:\n- 📋 Memos & scheduling\n- ⚔️ Conflict resolution\n- 👥 User management\n- 🚗 Vehicles & trips\n- 📊 Dashboard navigation\n\nWhat would you like help with today?", 1.0),

    (["how are you","how r u","how do you do","are you okay"],
     "I'm running perfectly, {name}! Always online, always here to help. What do you need?", 0.9),

    (["who are you","what are you","introduce yourself","your name","what is memobot"],
     "I'm **MemoBot** — the built-in AI assistant of SkedIt. I'm trained specifically on this system and can answer any question about memos, scheduling, users, vehicles, and more. I run locally so I'm always fast and always available!", 1.0),

    # ── MEMOS ──────────────────────────────────────────────────
    (["create memo","make memo","new memo","add memo","write memo"],
     "To **create a memo**:\n1. Click **Create Memo** in the sidebar (under Memos section)\n2. Fill in: Title, Body/Content, Priority (High/Medium/Low)\n3. Set the Date and Time range\n4. Assign users who will be involved\n5. Attach a vehicle if needed\n6. Click **Submit** to send for approval, or **Save Draft** to save without submitting", 1.2),

    (["what is memo","what is a memo","memo meaning","define memo"],
     "A **memo** (memorandum) in SkedIt is an official university document used for:\n- Assigning tasks to staff/instructors\n- Scheduling events or meetings\n- Making formal requests\n- Broadcasting announcements\n\nEach memo has a status: **Draft → Pending → Approved/Rejected**", 1.0),

    (["memo status","status of memo","memo states","draft pending approved"],
     "Memo statuses in SkedIt:\n- **Draft** — saved but not yet submitted\n- **Pending** — submitted, awaiting decision\n- **Approved** — accepted by the approver\n- **Rejected** — declined with a reason\n\nOnly admins and approvers can change status.", 1.1),

    (["edit memo","update memo","modify memo","change memo"],
     "To **edit a memo**:\n1. Go to **Memos → All Memos** in the sidebar\n2. Find the memo and click it to open\n3. Click the **Edit** button\n4. Make your changes and save\n\n⚠️ Note: Only **Draft** and **Pending** memos can be edited. Approved memos are locked.", 1.1),

    (["delete memo","remove memo","cancel memo"],
     "To **delete a memo**:\n1. Go to **Memos → All Memos**\n2. Open the memo you want to delete\n3. Click **Delete** (only available to Admins)\n\n⚠️ Deletion is permanent and cannot be undone.", 1.1),

    (["view memo","see memo","find memo","list memo","all memo"],
     "To **view memos**:\n- **All Memos**: Sidebar → Memos → All Memos (admin sees all; others see assigned)\n- **My Memos**: Your assigned memos filtered by your account\n- Use the search/filter bar to find by title, date, or status", 1.0),

    (["priority","high priority","medium priority","low priority","memo priority"],
     "Memo **priority levels**:\n- 🔴 **High** — urgent, must be resolved immediately\n- 🟡 **Medium** — important but not critical\n- 🟢 **Low** — routine, can be handled later\n\nPriority helps the Decision Panel determine which memo takes precedence in a conflict.", 1.0),

    # ── DECISION PANEL ─────────────────────────────────────────
    (["decision panel","approve memo","reject memo","pending decision","approve request"],
     "The **Decision Panel** is where pending memo requests are reviewed:\n1. Go to **Memos → Decision Panel** in the sidebar\n2. You'll see all memos awaiting a decision\n3. Click **Approve** ✅ to accept or **Reject** ❌ to decline\n4. For rejections, add a reason/note\n\nOnly **Admins** and **Approvers (Dept Heads)** can access this.", 1.2),

    # ── CONFLICTS ──────────────────────────────────────────────
    (["conflict","schedule conflict","time conflict","overlap","double booking","conflicting memo"],
     "A **scheduling conflict** happens when two memos are assigned to the same user at the same date/time.\n\n**How to resolve:**\n1. Go to the **Admin Dashboard** — conflicts appear with a 🔴 badge\n2. Open the **Decision Panel**\n3. Review both conflicting memos side by side\n4. Approve the higher-priority memo\n5. Reject or reschedule the lower-priority one\n\nThe system automatically detects overlaps when a memo is submitted.", 1.3),

    # ── NOTIFICATIONS ──────────────────────────────────────────
    (["notification","bell","unread","alert","notify"],
     "The **notification bell** 🔔 is in the top bar:\n- Shows a badge with unread count\n- Click it to see recent notifications\n- You get notified for: memo assigned, approved, rejected, conflict detected\n- Clicking a notification marks it as read\n\nNotifications update each time you navigate to a new page.", 1.0),

    # ── USERS & ROLES ──────────────────────────────────────────
    (["user role","roles","what is admin","what is hr","what is instructor","what is approver","what is staff","what is student","what is transportation"],
     "SkedIt has **7 user roles**:\n\n| Role | Access |\n|------|--------|\n| **Admin** | Full access — everything |\n| **HR** | Employee records, leave, attendance |\n| **Instructor** | Submit requests, view own memos |\n| **Approver** | Approve/reject dept requests |\n| **Transportation** | Manage vehicles & trips |\n| **Staff** | View memos, limited actions |\n| **Student** | Read-only memo access |", 1.2),

    (["manage user","add user","create user","new user","register user","user management"],
     "To **manage users** (Admin only):\n1. Sidebar → **People** section\n2. Choose: **Instructors**, **Staff**, or **Students**\n3. Click **Add New** to create a user\n4. Fill in: name, school ID, email, mobile, role\n5. The user can then log in with their school ID or email", 1.2),

    (["edit user","update user","change user","modify user"],
     "To **edit a user**:\n1. Sidebar → People → choose the role category\n2. Find the user in the list\n3. Click **Edit** next to their name\n4. Update the fields and save\n\nYou can change their name, contact info, department, and role.", 1.1),

    (["delete user","remove user","deactivate user"],
     "To **delete a user**:\n1. Sidebar → People → find the user\n2. Click **Delete** next to their name\n3. Confirm the deletion\n\n⚠️ This permanently removes the user and all their data. Consider editing their role to 'Student' to deactivate instead.", 1.1),

    # ── VEHICLES ───────────────────────────────────────────────
    (["vehicle","transport","trip","van","car","bus","booking","vehicle booking"],
     "**Vehicle management** in SkedIt:\n- Sidebar → **Resources → Vehicles**\n- View all university vehicles and their availability\n- Vehicles are linked to memos when transport is needed\n- Transportation role approves vehicle requests\n- Double-booking is automatically prevented\n\nTo request a vehicle: include it when creating a memo.", 1.2),

    (["grouped trip","trip group","group trip"],
     "**Grouped Trips** consolidate multiple vehicle requests for the same route/date:\n- Sidebar → **Resources → Grouped Trips**\n- The system groups compatible trip requests automatically\n- Reduces vehicle usage and optimizes transport scheduling", 1.0),

    # ── DASHBOARD ──────────────────────────────────────────────
    (["dashboard","admin dashboard","overview","kpi","statistics","stats"],
     "The **Admin Dashboard** shows:\n- 📅 **Today's Memos** — memos scheduled for today\n- ⏳ **Pending** — awaiting decision\n- ✅ **Approved** — approved memos count\n- 👥 **Total Users** — all registered users\n- ⚔️ **Conflicts** — active scheduling conflicts\n\nIt also has panels for Recent Memos and Pending Decisions.", 1.1),

    # ── LOGIN & AUTH ───────────────────────────────────────────
    (["login","sign in","cannot login","login error","wrong password","forgot password","school id login"],
     "**Login options** in SkedIt:\n- Username, Email, School ID, or Mobile Number — all work!\n- Make sure you're on the correct login page (Admin vs User)\n- If login fails: check CAPS LOCK, verify your school ID format\n- Admin users must use the **Admin Login** button\n\nForgot password? Contact your system administrator to reset it.", 1.1),

    (["logout","sign out","log out"],
     "To **log out**:\n- Click the **Logout** button at the **bottom of the sidebar**\n- You'll be redirected to the login page\n- Your session is cleared automatically", 0.9),

    # ── PROFILE ────────────────────────────────────────────────
    (["profile","my profile","edit profile","change name","change photo","profile picture","avatar","update profile"],
     "To **update your profile**:\n1. Click your **avatar** in the top-right corner\n2. Select **My Profile** from the dropdown\n3. Click **Edit Profile**\n4. Update: First Name, Middle Name, Last Name, Email, Mobile\n5. To change photo: click the camera icon on your avatar\n6. Crop and save your new photo\n7. Click **Save Changes**", 1.2),

    # ── SIDEBAR NAVIGATION ─────────────────────────────────────
    (["sidebar","navigation","menu","where is","how to navigate","find section"],
     "**Sidebar navigation** (Admin view):\n\n📊 **Overview**\n- Admin Dashboard\n\n👥 **People**\n- Instructors | Staff | Students\n\n📋 **Memos**\n- All Memos | Create Memo | Decision Panel\n\n🚗 **Resources**\n- Vehicles | Grouped Trips\n\nThe active page is highlighted in green.", 1.1),

    # ── SYSTEM / TECHNICAL ─────────────────────────────────────
    (["philippines time","timezone","philippine standard time","pst","asia manila"],
     "SkedIt uses **Philippine Standard Time (PST / UTC+8)** for all dates and times. The dashboard date shown at the top updates according to PH time.", 0.9),

    (["system","what system","what is memotrack","about memotrack","cns","college of natural sciences"],
     "**SkedIt** is a university memorandum and scheduling management system built for the **College of Natural Sciences (CNS)**. It manages:\n- Official memos and document workflows\n- Class and event scheduling\n- Conflict detection and resolution\n- User management across all roles\n- Vehicle and trip coordination\n\nBuilt with Django (Python) and modern web technologies.", 1.0),

    # ── GENERAL KNOWLEDGE ──────────────────────────────────────
    (["what is python","python language","django","what is django"],
     "**Python** is the programming language SkedIt is built with. **Django** is the web framework used — it handles routing, database models, authentication, and views. SkedIt is a Django project.", 0.8),

    (["what is ai","artificial intelligence","machine learning","how does ai work"],
     "**AI (Artificial Intelligence)** is the simulation of human intelligence in computers. I'm MemoBot — a rule-based AI trained specifically on SkedIt's knowledge base. I use **intent detection** and a **knowledge base** to understand your questions and give accurate answers.", 0.8),

    (["thank","thanks","thank you","ty","appreciate","great","awesome","nice","good job","well done"],
     "You're welcome, {name}! 😊 I'm always here if you need anything else.", 0.8),

    (["bye","goodbye","see you","take care","exit","quit","close"],
     "Goodbye, {name}! 👋 Come back anytime — I'm always online.", 0.8),

    (["help","what can you do","commands","features","capabilities"],
     "I can help you with anything in SkedIt:\n\n📋 **Memos** — create, edit, view, approve, reject\n⚔️ **Conflicts** — detect and resolve scheduling conflicts\n👥 **Users** — manage roles, add/edit/delete users\n🚗 **Vehicles** — bookings and trip management\n📊 **Dashboard** — understand KPI cards and panels\n🔔 **Notifications** — how they work\n🔐 **Login** — troubleshoot login issues\n\nJust ask me anything!", 1.0),
]

# ── MATH SUPPORT ───────────────────────────────────────────────
MATH_PATTERN = re.compile(
    r'^[\s\d\+\-\*\/\(\)\.\%\^]+$'
)

def try_math(text: str):
    """Try to evaluate a simple math expression."""
    clean = text.strip().replace('^', '**').replace('x', '*').replace('×', '*').replace('÷', '/')
    if MATH_PATTERN.match(clean):
        try:
            result = eval(clean, {"__builtins__": {}})
            return f"**{text.strip()} = {result}**"
        except Exception:
            pass
    return None


# ── TOKENIZER ──────────────────────────────────────────────────
def tokenize(text: str):
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    # Remove very short noise words
    stopwords = {'a','an','the','is','are','was','were','be','been','being',
                 'have','has','had','do','does','did','will','would','could',
                 'should','may','might','must','can','i','me','my','you','your',
                 'we','our','they','their','it','its','this','that','these',
                 'those','and','or','but','in','on','at','to','for','of','with',
                 'about','how','what','where','when','why','which','who','whom'}
    return [t for t in tokens if len(t) > 1 and t not in stopwords]


# ── SCORER ─────────────────────────────────────────────────────
def score_entry(tokens: list, keywords: list, weight: float) -> float:
    """Calculate relevance score for a KB entry."""
    if not tokens:
        return 0.0
    user_set = set(tokens)
    kw_set   = set(keywords)

    # Exact keyword matches
    exact = len(user_set & kw_set)

    # Partial matches (keyword substring in token or vice versa)
    partial = 0
    for t in tokens:
        for k in keywords:
            if k != t and (k in t or t in k) and len(t) > 3:
                partial += 0.4

    raw   = exact + partial
    ratio = raw / max(len(kw_set), 1)
    coverage = raw / max(len(tokens), 1)

    score = (ratio * 0.6 + coverage * 0.4) * weight
    return score


# ── MAIN RESPONSE FUNCTION ─────────────────────────────────────
def get_response(message: str, user_name: str = "there", history: list = None) -> str:
    """
    Generate a response to the user's message.
    history: list of {"role": "user"|"assistant", "content": str}
    """
    msg    = message.strip()
    tokens = tokenize(msg)

    # 1. Math check
    math_result = try_math(msg)
    if math_result:
        return f"🧮 {math_result}"

    # 2. Score all KB entries
    scored = []
    for (keywords, response, weight) in KB:
        s = score_entry(tokens, keywords, weight)
        if s > 0:
            scored.append((s, response))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 3. Return best match if confident enough
    if scored and scored[0][0] >= 0.12:
        best_response = scored[0][1]
        # Substitute {name} placeholder
        fn = user_name.split()[0] if user_name and user_name != "there" else "there"
        best_response = best_response.replace("{name}", fn)
        return best_response

    # 4. Context-aware follow-up
    if history:
        last_ai = next(
            (h["content"] for h in reversed(history) if h.get("role") == "assistant"), ""
        )
        # If previous topic was memo-related and question seems like follow-up
        if any(w in last_ai.lower() for w in ["memo","decision","conflict","vehicle"]):
            if any(w in tokens for w in ["yes","no","how","when","why","more","explain","detail"]):
                return ("Could you be more specific? For example:\n"
                        "- *'How do I create a memo?'*\n"
                        "- *'What happens after I approve?'*\n"
                        "- *'How do I resolve a conflict?'*")

    # 5. Friendly fallback
    fn = user_name.split()[0] if user_name and user_name != "there" else "there"
    return (f"I'm not sure I understood that, {fn}. Here are things I can help with:\n\n"
            "- 📋 **Memos** — create, edit, approve, reject\n"
            "- ⚔️ **Conflicts** — detect and resolve\n"
            "- 👥 **Users** — manage roles and accounts\n"
            "- 🚗 **Vehicles** — bookings and trips\n"
            "- 📊 **Dashboard** — KPI cards and panels\n\n"
            "Try asking: *'How do I create a memo?'* or *'What is the Decision Panel?'*")
