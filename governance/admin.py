from django.contrib import admin
from .models import Policy, SchedulingAuditLog

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'policy_type', 'is_active', 'priority_weight', 'created_at')
    list_filter = ('policy_type', 'is_active')
    search_fields = ('name', 'description')

@admin.register(SchedulingAuditLog)
class SchedulingAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'memo', 'actor', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('memo__title', 'actor__username')
    readonly_fields = ('timestamp',)
