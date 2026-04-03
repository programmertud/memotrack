from django.shortcuts import render

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods

from .models import Vehicle
from .models import VehicleBooking
from .forms import VehicleBookingForm, VehicleForm

from memos.models import Memo


def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by("name")
    return render(request, "resources/vehicle_list.html", {"vehicles": vehicles})


@staff_member_required
def vehicle_admin_list(request):
    vehicles = Vehicle.objects.all().order_by("name")
    return render(request, "resources/vehicle_admin_list.html", {"vehicles": vehicles})


@staff_member_required
@require_http_methods(["GET", "POST"])
def vehicle_admin_create(request):
    form = VehicleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save()
        messages.success(request, f"Vehicle '{vehicle.name}' created.")
        return redirect("resources:vehicle_admin_list")
    return render(request, "resources/vehicle_admin_form.html", {"form": form, "mode": "create"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def vehicle_admin_edit(request, pk: int):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleForm(request.POST or None, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vehicle updated.")
        return redirect("resources:vehicle_admin_list")
    return render(
        request,
        "resources/vehicle_admin_form.html",
        {"form": form, "mode": "edit", "vehicle": vehicle},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def vehicle_admin_delete(request, pk: int):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        name = vehicle.name
        vehicle.delete()
        messages.success(request, f"Vehicle '{name}' deleted.")
        return redirect("resources:vehicle_admin_list")
    return render(request, "resources/vehicle_admin_confirm_delete.html", {"vehicle": vehicle})


@require_http_methods(["GET", "POST"])
def vehicle_book(request, memo_id: int):
    memo = get_object_or_404(Memo, pk=memo_id)
    booking = VehicleBooking.objects.filter(memo=memo).first()

    form = VehicleBookingForm(request.POST or None, instance=booking)
    if request.method == "POST" and form.is_valid():
        booking = form.save(commit=False)
        booking.memo = memo

        if booking.has_conflicts():
            messages.error(request, "Vehicle unavailable due to another booking in the same time slot.")
            return redirect("resources:vehicle_book", memo_id=memo.pk)

        booking.save()
        messages.success(request, "Vehicle booking saved.")
        return redirect("memos:memo_list")

    suggestions = []
    if booking:
        suggestions = list(booking.shared_trip_suggestions()[:10])
    else:
        if (memo.destination or "").strip():
            suggestions = list(
                Memo.objects.filter(date=memo.date, destination__iexact=memo.destination)
                .exclude(pk=memo.pk)
                .order_by("start_time")[:10]
            )

    return render(
        request,
        "resources/vehicle_book.html",
        {"memo": memo, "form": form, "booking": booking, "suggestions": suggestions},
    )


def grouped_trips(request):
    memos = Memo.objects.exclude(destination="").order_by("date", "destination", "start_time")
    grouped = {}
    for m in memos:
        key = (m.date, (m.destination or "").strip().lower())
        grouped.setdefault(key, []).append(m)

    groups = [
        {"date": k[0], "destination": (v[0].destination or "").strip(), "memos": v}
        for k, v in grouped.items()
    ]
    return render(request, "resources/grouped_trips.html", {"groups": groups})
