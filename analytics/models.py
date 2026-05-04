from django.db import models
from django.utils import timezone


class SchedulingMetric(models.Model):
    class MetricType(models.TextChoices):
        CONGESTION = "congestion", "Congestion Level"
        UTILIZATION = "utilization", "Venue Utilization"
        CONFLICT_RATE = "conflict_rate", "Conflict Rate"
        DEMAND = "demand", "Demand Index"

    metric_type = models.CharField(max_length=20, choices=MetricType.choices)
    value = models.FloatField()
    reference_date = models.DateField(default=timezone.now)
    context_data = models.JSONField(null=True, blank=True, help_text="Extra data like department ID or venue ID.")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reference_date", "metric_type"]

    def __str__(self) -> str:
        return f"{self.get_metric_type_display()} on {self.reference_date}: {self.value}"


class SchedulingRiskIndicator(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "Low Risk"
        MEDIUM = "medium", "Medium Risk"
        HIGH = "high", "High Risk"
        CRITICAL = "critical", "Critical Risk"

    target_date = models.DateField()
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices)
    prediction_confidence = models.FloatField(default=0.0)
    contributing_factors = models.TextField(help_text="Reasoning for the risk level.")
    recommendations = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["target_date"]

    def __str__(self) -> str:
        return f"Risk for {self.target_date}: {self.get_risk_level_display()}"
