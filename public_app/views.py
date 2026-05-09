from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
import os

def home(request):
    try:
        return render(request, 'public/home.html')
    except Exception as e:
        templates_dir = settings.BASE_DIR / 'templates'
        try:
            files = os.listdir(templates_dir)
            public_files = os.listdir(templates_dir / 'public')
        except Exception as dir_err:
            files = str(dir_err)
            public_files = ""
        
        debug_info = f"Error: {e}<br><br>BASE_DIR: {settings.BASE_DIR}<br><br>Templates dir contents: {files}<br><br>Public dir contents: {public_files}"
        return HttpResponse(debug_info)

def about(request):
    return render(request, 'public/about.html')
