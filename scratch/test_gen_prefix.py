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
    
    # Testing with models/ prefix
    model_name = "models/gemini-pro-latest"
    print(f"Testing model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content("Say 'Hello Test'")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error with {model_name}: {e}")

    model_name_2 = "models/gemini-flash-lite-latest"
    print(f"Testing model: {model_name_2}...")
    try:
        model = genai.GenerativeModel(model_name=model_name_2)
        response = model.generate_content("Say 'Hello Test'")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error with {model_name_2}: {e}")
