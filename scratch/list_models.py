import google.generativeai as genai
from django.conf import settings
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'memotrack.settings')
django.setup()

api_key = getattr(settings, "GEMINI_API_KEY", None)
if not api_key:
    print("No API Key found")
else:
    genai.configure(api_key=api_key)
    print("Listing models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error: {e}")
