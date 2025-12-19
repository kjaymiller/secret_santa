import random
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View

from .forms import (
    EventForm,
    EventInviteForm,
    ExclusionGroupForm,
    InviteCodeForm,
    NotificationScheduleForm,
    ParticipantExclusionForm,
    ParticipantJoinForm,
    ParticipantUpdateForm,
    UserProfileForm,
)
from .models import Assignment, Event, ExclusionGroup, NotificationSchedule, Participant, UserProfile


# Home Page View


class HomeView(View):
    """Landing page for the Secret Santa application."""

    def get(self, request):
        from django.shortcuts import render

        context = {
            "total_events": Event.objects.count(),
            "active_events": Event.objects.filter(is_active=True).count(),
        }
        if request.user.is_authenticated:
            context["user_event_count"] = Event.objects.filter(organizer=request.user).count()
        
        return render(request, "home.html", context)


# Account Views


class AccountView(LoginRequiredMixin, UpdateView):
    """User account management page."""

    template_name = "events/account.html"
    form_class = UserProfileForm
    success_url = reverse_lazy("account")

    def get_object(self):
        # Ensure user has a profile
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Notification preferences updated!")
        return super().form_valid(form)


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    """Delete the current user's account."""

    template_name = "events/account_confirm_delete.html"
    success_url = reverse_lazy("home")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        user = self.get_object()
        messages.success(self.request, f"Your account ({user.email}) has been deleted. We're sorry to see you go!")
        return super().form_valid(form)


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
        if self.request.user == event.organizer:
            context["invite_form"] = EventInviteForm()
        return context


class EventSendInvitesView(LoginRequiredMixin, View):
    """Send invites to email addresses for a specific event."""

    def post(self, request, pk):
        from events.services.notifications import get_notification_service

        event = get_object_or_404(Event, pk=pk, organizer=request.user)
        form = EventInviteForm(request.POST)

        if form.is_valid():
            emails = form.cleaned_data["emails"]
            invited_count = 0
            existing_count = 0
            notification_service = get_notification_service()

            for email in emails:
                # Check if participant already exists
                participant, created = Participant.objects.get_or_create(
                    event=event,
                    email=email,
                    defaults={
                        "name": email.split("@")[0],  # Default name from email
                        "is_confirmed": False,
                    },
                )

                if created:
                    invited_count += 1
                    # Send invite notification
                    try:
                        notification_service.send_invite_notification(participant, event)
                    except Exception:
                        # Log error but continue sending to others
                        pass
                else:
                    existing_count += 1
                    # Optional: Resend invite if not confirmed?
                    # For now, we'll just skip if they already exist
                    if not participant.is_confirmed:
                        try:
                            notification_service.send_invite_notification(participant, event)
                            invited_count += 1 # Count as invited if we resent the invite
                            existing_count -= 1 # Move from existing to invited bucket for feedback
                        except Exception:
                            pass

            message_parts = []
            if invited_count > 0:
                message_parts.append(f"Sent invites to {invited_count} people.")
            if existing_count > 0:
                message_parts.append(f"{existing_count} people were already in the list.")

            if message_parts:
                messages.success(request, " ".join(message_parts))
            else:
                messages.info(request, "No new invites were sent.")

        else:
            for error in form.errors.values():
                messages.error(request, error)

        return redirect("events:event-detail", pk=pk)


class EventCreateView(LoginRequiredMixin, CreateView):
    """Create a new Secret Santa event."""

    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        from events.services.notifications import get_notification_service

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

        # Send event creation confirmation email to organizer
        notification_service = get_notification_service()
        try:
            notification_service.send_event_creation_notification(self.object, self.request)
            messages.success(
                self.request,
                f"Event '{form.instance.name}' created successfully! Confirmation email sent with invite code.",
            )
        except Exception:
            messages.warning(
                self.request,
                f"Event '{form.instance.name}' created successfully! (Email notification failed to send)",
            )

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
        from events.services.notifications import get_notification_service

        event_name = self.object.name
        participant_count = self.object.participants.count()

        # Send deletion notification emails to all participants before deleting
        if participant_count > 0:
            notification_service = get_notification_service()
            try:
                notification_service.send_event_deletion_notification(self.object)
                messages.success(
                    self.request,
                    f"Event '{event_name}' deleted successfully! Cancellation emails sent to {participant_count} participant(s).",
                )
            except Exception:
                messages.warning(
                    self.request,
                    f"Event '{event_name}' deleted, but some cancellation emails failed to send.",
                )
        else:
            messages.success(self.request, f"Event '{event_name}' deleted successfully!")

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
        from events.services.notifications import get_notification_service

        invite_code = self.kwargs.get("invite_code")
        event = get_object_or_404(Event, invite_code=invite_code, is_active=True)

        # Check if email already registered for this event
        if Participant.objects.filter(event=event, email=form.instance.email).exists():
            messages.error(self.request, "This email is already registered for this event.")
            return self.form_invalid(form)

        form.instance.event = event
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user

        response = super().form_valid(form)

        # Generate confirmation token
        self.object.generate_confirmation_token()

        # Send confirmation email
        confirmation_url = self.request.build_absolute_uri(
            reverse("events:participant-confirm-email", kwargs={"token": self.object.confirmation_token})
        )

        notification_service = get_notification_service()
        try:
            notification_service.send_confirmation_email(self.object, confirmation_url)
            messages.success(
                self.request,
                f"Successfully joined '{event.name}'! Please check your email to confirm your participation.",
            )
        except Exception:
            messages.warning(
                self.request,
                f"You've been registered for '{event.name}', but we couldn't send the confirmation email. Please contact the organizer.",
            )

        return response

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
    """Confirm participation in an event (legacy button-based confirmation)."""

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


class ParticipantConfirmEmailView(View):
    """Confirm participation via email token."""

    def get(self, request, token):
        participant = get_object_or_404(Participant, confirmation_token=token)

        if participant.is_confirmed:
            messages.info(request, "Your participation has already been confirmed!")
        else:
            participant.is_confirmed = True
            participant.save(update_fields=["is_confirmed", "updated_at"])
            messages.success(
                request,
                f"Thank you for confirming your participation in {participant.event.name}!",
            )

        return redirect("events:participant-detail", pk=participant.pk)


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
        participants = event.participants.filter(is_confirmed=True).order_by("name")

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
        participants = event.participants.filter(is_confirmed=True).order_by("name")

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


# Exclusion Group Views


class ExclusionGroupListView(LoginRequiredMixin, ListView):
    """List all exclusion groups for an event."""

    model = ExclusionGroup
    template_name = "events/exclusion_group_list.html"
    context_object_name = "groups"

    def get_queryset(self):
        event_pk = self.kwargs.get("event_pk")
        return ExclusionGroup.objects.filter(event__pk=event_pk, event__organizer=self.request.user).prefetch_related(
            "members"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_pk = self.kwargs.get("event_pk")
        context["event"] = get_object_or_404(Event, pk=event_pk, organizer=self.request.user)
        return context


class ExclusionGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new exclusion group."""

    model = ExclusionGroup
    form_class = ExclusionGroupForm
    template_name = "events/exclusion_group_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        event_pk = self.kwargs.get("event_pk")
        kwargs["event"] = get_object_or_404(Event, pk=event_pk, organizer=self.request.user)
        return kwargs

    def form_valid(self, form):
        from events.services.notifications import get_notification_service

        event_pk = self.kwargs.get("event_pk")
        form.instance.event = get_object_or_404(Event, pk=event_pk, organizer=self.request.user)
        response = super().form_valid(form)

        # Apply exclusions between all members
        self.object.apply_exclusions()

        # Send notification emails to all group members
        notification_service = get_notification_service()
        try:
            notification_service.send_exclusion_group_notification(self.object)
            messages.success(
                self.request,
                f"Exclusion group '{self.object.name}' created and exclusions applied! Notification emails sent to all members.",
            )
        except Exception:
            messages.warning(
                self.request,
                f"Exclusion group '{self.object.name}' created, but some notification emails failed to send.",
            )

        return response

    def get_success_url(self):
        return reverse("events:exclusion-group-list", kwargs={"event_pk": self.object.event.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_pk = self.kwargs.get("event_pk")
        context["event"] = get_object_or_404(Event, pk=event_pk, organizer=self.request.user)
        return context


class ExclusionGroupUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing exclusion group."""

    model = ExclusionGroup
    form_class = ExclusionGroupForm
    template_name = "events/exclusion_group_form.html"

    def get_queryset(self):
        return ExclusionGroup.objects.filter(event__organizer=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["event"] = self.object.event
        return kwargs

    def form_valid(self, form):
        from events.services.notifications import get_notification_service

        # Remove old exclusions first
        self.object.remove_exclusions()

        response = super().form_valid(form)

        # Apply new exclusions
        self.object.apply_exclusions()

        # Send notification emails to all group members
        notification_service = get_notification_service()
        try:
            notification_service.send_exclusion_group_notification(self.object)
            messages.success(
                self.request,
                f"Exclusion group '{self.object.name}' updated and exclusions reapplied! Notification emails sent to all members.",
            )
        except Exception:
            messages.warning(
                self.request,
                f"Exclusion group '{self.object.name}' updated, but some notification emails failed to send.",
            )

        return response

    def get_success_url(self):
        return reverse("events:exclusion-group-list", kwargs={"event_pk": self.object.event.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.object.event
        return context


class ExclusionGroupDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an exclusion group."""

    model = ExclusionGroup
    template_name = "events/exclusion_group_confirm_delete.html"

    def get_queryset(self):
        return ExclusionGroup.objects.filter(event__organizer=self.request.user)

    def get_success_url(self):
        return reverse("events:exclusion-group-list", kwargs={"event_pk": self.object.event.pk})

    def form_valid(self, form):
        # Remove exclusions before deleting the group
        self.object.remove_exclusions()
        messages.success(self.request, f"Exclusion group '{self.object.name}' deleted and exclusions removed!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event"] = self.object.event
        return context


# Assignment Views


class AssignmentGenerateView(LoginRequiredMixin, View):
    """Generate Secret Santa assignments for an event."""

    def post(self, request, event_pk):
        event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

        # Check if assignments already exist
        if event.assignments.exists():
            messages.error(request, "Assignments have already been generated for this event.")
            return redirect("events:event-detail", pk=event_pk)

        # Get confirmed participants with prefetched exclusions for efficiency
        participants = list(event.participants.filter(is_confirmed=True).prefetch_related("exclusions"))

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
        # Build exclusion map: participant_id -> set of excluded participant IDs
        exclusion_map = {}
        for participant in participants:
            # Use prefetch_related for efficiency
            excluded_ids = set(participant.exclusions.values_list("id", flat=True))
            exclusion_map[participant.id] = excluded_ids

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

                # Check exclusion rules using M2M relationship
                giver_exclusions = exclusion_map.get(giver.id, set())
                if receiver.id in giver_exclusions:
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
