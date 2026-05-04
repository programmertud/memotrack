from django.contrib import admin
from .models import SchedulingMetric, SchedulingRiskIndicator

@admin.register(SchedulingMetric)
class SchedulingMetricAdmin(admin.ModelAdmin):
    list_display = ('metric_type', 'value', 'reference_date', 'created_at')
    list_filter = ('metric_type', 'reference_date')

@admin.register(SchedulingRiskIndicator)
class SchedulingRiskIndicatorAdmin(admin.ModelAdmin):
    list_display = ('target_date', 'risk_level', 'prediction_confidence', 'created_at')
    list_filter = ('risk_level', 'target_date')
