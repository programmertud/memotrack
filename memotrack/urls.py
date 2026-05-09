"""
URL configuration for memotrack project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as accounts_views

from django.core.management import call_command
from django.http import HttpResponse
from django.contrib.auth import get_user_model

def init_db(request):
    try:
        # Run migrations
        call_command('migrate', no_input=True)
        
        # Create a default admin if none exists
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            return HttpResponse("Database initialized and superuser 'admin' (password: admin) created successfully!")
        
        return HttpResponse("Database migrations applied successfully!")
    except Exception as e:
        return HttpResponse(f"Error initializing database: {e}")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('init-db/', init_db),
    path('', include('public.urls')),
    path('accounts/', include('accounts.urls')),
    path('memos/', include('memos.urls')),
    path('resources/', include('resources.urls')),
    path('notifications/', include('notifications.urls')),
    path('governance/', include('governance.urls')),
    path('analytics/', include('analytics.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
