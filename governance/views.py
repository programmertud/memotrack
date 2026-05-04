from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Policy, SchedulingAuditLog
from django import forms

def is_admin(user):
    return user.is_staff or (hasattr(user, 'profile') and user.profile.role == 'admin')

class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ['name', 'policy_type', 'description', 'is_active', 'rule_definition', 'priority_weight']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'policy_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rule_definition': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': '{"requires_approval": true}'}),
            'priority_weight': forms.NumberInput(attrs={'class': 'form-control'}),
        }

@login_required
@user_passes_test(is_admin)
def policy_list(request):
    policies = Policy.objects.all().order_by('-priority_weight', '-created_at')
    return render(request, 'governance/policy_list.html', {'policies': policies})

@login_required
@user_passes_test(is_admin)
def policy_create(request):
    if request.method == 'POST':
        form = PolicyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Policy created successfully.')
            return redirect('governance:policy_list')
    else:
        form = PolicyForm(initial={'rule_definition': {}})
    return render(request, 'governance/policy_form.html', {'form': form, 'title': 'Create Policy'})

@login_required
@user_passes_test(is_admin)
def policy_edit(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    if request.method == 'POST':
        form = PolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Policy updated successfully.')
            return redirect('governance:policy_list')
    else:
        form = PolicyForm(instance=policy)
    return render(request, 'governance/policy_form.html', {'form': form, 'title': 'Edit Policy'})

@login_required
@user_passes_test(is_admin)
def audit_logs(request):
    logs = SchedulingAuditLog.objects.select_related('memo', 'actor').all()
    return render(request, 'governance/audit_logs.html', {'logs': logs})
