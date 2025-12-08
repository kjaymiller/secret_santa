import random
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from .forms import EventForm, InviteCodeForm, NotificationScheduleForm, ParticipantJoinForm, ParticipantUpdateForm
from .models import Assignment, Event, NotificationSchedule, Participant


# Home Page View


class HomeView(View):
    """Landing page for the Secret Santa application."""

    def get(self, request):
        from django.shortcuts import render

        context = {
            "total_events": Event.objects.count(),
            "active_events": Event.objects.filter(is_active=True).count(),
        }
        return render(request, "home.html", context)


# Event Views


class EventListView(LoginRequiredMixin, ListView):
    """List all events organized by the current user."""

    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user).select_related("organizer")


class EventDetailView(LoginRequiredMixin, DetailView):
    """View details of a specific event."""

    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user).prefetch_related(
            "participants", "assignments", "notification_schedules"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        context["participants"] = event.participants.all()
        context["confirmed_participants"] = event.participants.filter(is_confirmed=True)
        context["assignments_count"] = event.assignments.count()
        context["can_generate_assignments"] = event.participants.filter(is_confirmed=True).count() >= 3
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    """Create a new Secret Santa event."""

    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        response = super().form_valid(form)

        # Auto-enroll organizer as a participant
        Participant.objects.create(
            event=self.object,
            user=self.request.user,
            name=self.request.user.get_full_name() or self.request.user.username,
            email=self.request.user.email,
            is_confirmed=True,
        )

        messages.success(self.request, f"Event '{form.instance.name}' created successfully!")
        return response

    def get_success_url(self):
        return reverse("events:event-detail", kwargs={"pk": self.object.pk})


class EventUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing event."""

    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f"Event '{form.instance.name}' updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("events:event-detail", kwargs={"pk": self.object.pk})


class EventDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an event."""

    model = Event
    template_name = "events/event_confirm_delete.html"
    success_url = reverse_lazy("events:event-list")

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f"Event '{self.object.name}' deleted successfully!")
        return super().form_valid(form)


# Participant Views


class InviteCodeEntryView(View):
    """Landing page for entering invite code to join an event."""

    def get(self, request):
        from django.shortcuts import render

        form = InviteCodeForm()
        return render(request, "events/invite_code_entry.html", {"form": form})

    def post(self, request):
        from django.shortcuts import render

        form = InviteCodeForm(request.POST)
        if form.is_valid():
            invite_code = form.cleaned_data["invite_code"]
            return redirect("events:join-event", invite_code=invite_code)
        return render(request, "events/invite_code_entry.html", {"form": form})


class ParticipantJoinView(CreateView):
    """Join an event via invite code (public view)."""

    model = Participant
    form_class = ParticipantJoinForm
    template_name = "events/participant_join.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite_code = self.kwargs.get("invite_code")
        context["event"] = get_object_or_404(Event, invite_code=invite_code, is_active=True)
        return context

    def form_valid(self, form):
        invite_code = self.kwargs.get("invite_code")
        event = get_object_or_404(Event, invite_code=invite_code, is_active=True)

        # Check if email already registered for this event
        if Participant.objects.filter(event=event, email=form.instance.email).exists():
            messages.error(self.request, "This email is already registered for this event.")
            return self.form_invalid(form)

        form.instance.event = event
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user

        messages.success(
            self.request,
            f"Successfully joined '{event.name}'! Please check your email to confirm your participation.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("events:participant-detail", kwargs={"pk": self.object.pk})


class ParticipantDetailView(DetailView):
    """View participant details and wishlist."""

    model = Participant
    template_name = "events/participant_detail.html"
    context_object_name = "participant"

    def get_queryset(self):
        return Participant.objects.select_related("event", "user")


class ParticipantUpdateView(UpdateView):
    """Update participant information."""

    model = Participant
    form_class = ParticipantUpdateForm
    template_name = "events/participant_form.html"

    def get_queryset(self):
        qs = Participant.objects.select_related("event")
        # Allow updates if user owns the participant or is the event organizer
        if self.request.user.is_authenticated:
            return qs.filter(user=self.request.user) | qs.filter(event__organizer=self.request.user)
        return qs.none()

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("events:participant-detail", kwargs={"pk": self.object.pk})


class ParticipantConfirmView(View):
    """Confirm participation in an event."""

    def post(self, request, pk):
        participant = get_object_or_404(Participant, pk=pk)

        # Check authorization
        if request.user.is_authenticated and (
            participant.user == request.user or participant.event.organizer == request.user
        ):
            participant.is_confirmed = True
            participant.save(update_fields=["is_confirmed", "updated_at"])
            messages.success(request, f"Confirmed participation for {participant.name}!")
        else:
            messages.error(request, "You don't have permission to confirm this participant.")

        return redirect("events:participant-detail", pk=pk)


class ParticipantRemoveView(LoginRequiredMixin, DeleteView):
    """Remove a participant from an event (organizer only)."""

    model = Participant
    template_name = "events/participant_confirm_delete.html"

    def get_queryset(self):
        return Participant.objects.filter(event__organizer=self.request.user)

    def get_success_url(self):
        return reverse("events:event-detail", kwargs={"pk": self.object.event.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Participant '{self.object.name}' removed from event!")
        return super().form_valid(form)


class ParticipantExclusionManageView(LoginRequiredMixin, View):
    """Manage exclusions for all participants in an event (organizer only)."""

    def get(self, request, event_pk):
        from django.shortcuts import render
        from django.forms import modelformset_factory

        event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
        participants = event.participants.filter(is_confirmed=True).order_by('name')

        ParticipantExclusionFormSet = modelformset_factory(
            Participant,
            form=ParticipantExclusionForm,
            extra=0,
        )

        formset = ParticipantExclusionFormSet(queryset=participants)

        # Zip participants with forms for template
        participant_forms = zip(participants, formset)

        return render(
            request,
            "events/participant_exclusion_manage.html",
            {
                "event": event,
                "formset": formset,
                "participant_forms": participant_forms,
            },
        )

    def post(self, request, event_pk):
        from django.shortcuts import render
        from django.forms import modelformset_factory

        event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
        participants = event.participants.filter(is_confirmed=True).order_by('name')

        ParticipantExclusionFormSet = modelformset_factory(
            Participant,
            form=ParticipantExclusionForm,
            extra=0,
        )

        formset = ParticipantExclusionFormSet(request.POST, queryset=participants)

        if formset.is_valid():
            formset.save()
            messages.success(request, "Exclusions updated successfully!")
            return redirect("events:event-detail", pk=event_pk)

        # Zip participants with forms for template
        participant_forms = zip(participants, formset)

        return render(
            request,
            "events/participant_exclusion_manage.html",
            {
                "event": event,
                "formset": formset,
                "participant_forms": participant_forms,
            },
        )


# Assignment Views


class AssignmentGenerateView(LoginRequiredMixin, View):
    """Generate Secret Santa assignments for an event."""

    def post(self, request, event_pk):
        event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

        # Check if assignments already exist
        if event.assignments.exists():
            messages.error(request, "Assignments have already been generated for this event.")
            return redirect("events:event-detail", pk=event_pk)

        # Get confirmed participants
        participants = list(event.participants.filter(is_confirmed=True))

        if len(participants) < 3:
            messages.error(request, "At least 3 confirmed participants are required to generate assignments.")
            return redirect("events:event-detail", pk=event_pk)

        # Generate assignments
        success = self._generate_assignments(event, participants)

        if success:
            event.assignments_revealed_at = timezone.now()
            event.save(update_fields=["assignments_revealed_at"])
            messages.success(request, f"Successfully generated {len(participants)} assignments!")
        else:
            messages.error(
                request,
                "Failed to generate valid assignments. The exclusion rules may be too restrictive. Please review and try again.",
            )

        return redirect("events:event-detail", pk=event_pk)

    def _generate_assignments(self, event, participants, max_retries=1000):
        """
        Generate circular assignments with exclusion rules.
        Returns True if successful, False otherwise.
        """
        # Build exclusion map: participant_id -> set of excluded participant emails (lowercase)
        exclusion_map = {}
        for participant in participants:
            if participant.exclusions:
                # Parse exclusions as comma or newline separated emails
                excluded_emails = set()
                for email in participant.exclusions.replace('\n', ',').split(','):
                    email = email.strip().lower()
                    if email:
                        excluded_emails.add(email)
                exclusion_map[participant.id] = excluded_emails
            else:
                exclusion_map[participant.id] = set()

        for attempt in range(max_retries):
            # Shuffle participants
            shuffled = participants.copy()
            random.shuffle(shuffled)

            # Create circular chain: i gives to i+1, last gives to first
            valid = True
            assignments = []

            for i, giver in enumerate(shuffled):
                receiver = shuffled[(i + 1) % len(shuffled)]

                # Check for self-assignment (already enforced by database constraint)
                if giver == receiver:
                    valid = False
                    break

                # Check exclusion rules
                giver_exclusions = exclusion_map.get(giver.id, set())
                if receiver.email.lower() in giver_exclusions:
                    valid = False
                    break

                assignments.append(Assignment(event=event, giver=giver, receiver=receiver))

            if valid:
                # Save all assignments in a transaction
                try:
                    with transaction.atomic():
                        Assignment.objects.bulk_create(assignments)
                    return True
                except Exception:
                    # If database constraint fails, try again
                    continue

        return False


class MyAssignmentView(DetailView):
    """View my Secret Santa assignment."""

    model = Assignment
    template_name = "events/my_assignment.html"
    context_object_name = "assignment"

    def get_object(self):
        event_pk = self.kwargs.get("event_pk")
        participant_pk = self.kwargs.get("participant_pk")

        assignment = get_object_or_404(
            Assignment.objects.select_related("event", "giver", "receiver"),
            event__pk=event_pk,
            giver__pk=participant_pk,
        )

        # Mark as viewed
        assignment.mark_as_viewed()

        return assignment


class AssignmentStatusView(LoginRequiredMixin, DetailView):
    """View assignment status for an event (organizer only)."""

    model = Event
    template_name = "events/assignment_status.html"
    context_object_name = "event"

    def get_queryset(self):
        return Event.objects.filter(organizer=self.request.user).prefetch_related(
            "assignments__giver", "assignments__receiver"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignments = self.object.assignments.all()
        context["assignments"] = assignments
        context["viewed_count"] = assignments.filter(is_viewed=True).count()
        context["total_count"] = assignments.count()
        return context


# Notification Views


class NotificationScheduleListView(LoginRequiredMixin, ListView):
    """List notification schedules for an event."""

    model = NotificationSchedule
    template_name = "events/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        event_pk = self.kwargs.get("event_pk")
        return NotificationSchedule.objects.filter(
            event__pk=event_pk, event__organizer=self.request.user
        ).select_related("event")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_pk = self.kwargs.get("event_pk")
        context["event"] = get_object_or_404(Event, pk=event_pk, organizer=self.request.user)
        return context


class NotificationScheduleCreateView(LoginRequiredMixin, CreateView):
    """Create a notification schedule."""

    model = NotificationSchedule
    form_class = NotificationScheduleForm
    template_name = "events/notification_form.html"

    def dispatch(self, request, *args, **kwargs):
        event_pk = self.kwargs.get("event_pk")
        self.event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.event = self.event
        messages.success(self.request, "Notification scheduled successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("events:notification-list", kwargs={"event_pk": self.event.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.event
        return context


class NotificationScheduleUpdateView(LoginRequiredMixin, UpdateView):
    """Update a notification schedule."""

    model = NotificationSchedule
    form_class = NotificationScheduleForm
    template_name = "events/notification_form.html"

    def get_queryset(self):
        return NotificationSchedule.objects.filter(event__organizer=self.request.user, is_sent=False)

    def form_valid(self, form):
        messages.success(self.request, "Notification updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("events:notification-list", kwargs={"event_pk": self.object.event.pk})


class NotificationScheduleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a notification schedule."""

    model = NotificationSchedule
    template_name = "events/notification_confirm_delete.html"

    def get_queryset(self):
        return NotificationSchedule.objects.filter(event__organizer=self.request.user, is_sent=False)

    def get_success_url(self):
        return reverse("events:notification-list", kwargs={"event_pk": self.object.event.pk})

    def form_valid(self, form):
        messages.success(self.request, "Notification schedule deleted!")
        return super().form_valid(form)
