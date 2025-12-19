from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Event, ExclusionGroup, NotificationSchedule, Participant


class InviteCodeForm(forms.Form):
    """Form for entering an event invite code."""

    invite_code = forms.CharField(
        max_length=8,
        min_length=8,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter 8-character invite code",
                "style": "text-transform: uppercase;",
            }
        ),
        help_text="Enter the invite code you received from the event organizer",
    )

    def clean_invite_code(self):
        invite_code = self.cleaned_data.get("invite_code", "").upper()
        if not Event.objects.filter(invite_code=invite_code, is_active=True).exists():
            raise ValidationError("Invalid or inactive invite code. Please check and try again.")
        return invite_code


class EventForm(forms.ModelForm):
    """Form for creating/updating events."""

    class Meta:
        model = Event
        fields = ["name", "description", "event_date", "registration_deadline", "budget_max", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Holiday Gift Exchange 2025"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe your Secret Santa event...",
                }
            ),
            "event_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "registration_deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "budget_max": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "50.00",
                    "step": "0.01",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "registration_deadline": "Participants must join before this date",
            "budget_max": "Suggested maximum budget for gifts (optional)",
        }

    def clean(self):
        cleaned_data = super().clean()
        event_date = cleaned_data.get("event_date")
        registration_deadline = cleaned_data.get("registration_deadline")

        if event_date and registration_deadline:
            if registration_deadline >= event_date:
                raise ValidationError("Registration deadline must be before the event date.")

        if event_date and event_date < timezone.now().date():
            raise ValidationError("Event date cannot be in the past.")

        return cleaned_data


class ParticipantJoinForm(forms.ModelForm):
    """Form for joining an event."""

    class Meta:
        model = Participant
        fields = ["name", "email", "phone_number"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "your.email@example.com"}),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+1234567890 (optional)",
                }
            ),
        }
        help_texts = {
            "phone_number": "Optional - for SMS notifications",
        }


class ParticipantUpdateForm(forms.ModelForm):
    """Form for updating participant information."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Only show other participants from the same event (exclude self)
            self.fields["exclusions"].queryset = Participant.objects.filter(
                event=self.instance.event, is_confirmed=True
            ).exclude(pk=self.instance.pk)

    class Meta:
        model = Participant
        fields = ["name", "email", "phone_number", "wishlist_markdown", "exclusions"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "wishlist_markdown": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Use markdown to format your wishlist:\n\n- Item 1\n- Item 2\n- Item 3",
                }
            ),
            "exclusions": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "wishlist_markdown": "Use Markdown formatting. Your Secret Santa will see this list.",
            "exclusions": "Select people you should not be assigned to (e.g., spouse, close family)",
        }


class NotificationScheduleForm(forms.ModelForm):
    """Form for scheduling notifications."""

    class Meta:
        model = NotificationSchedule
        fields = ["notification_type", "scheduled_at", "message_template", "delivery_method"]
        widgets = {
            "notification_type": forms.Select(attrs={"class": "form-select"}),
            "scheduled_at": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "message_template": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter your custom message (optional)",
                }
            ),
            "delivery_method": forms.Select(attrs={"class": "form-select"}),
        }
        help_texts = {
            "scheduled_at": "When should this notification be sent?",
            "message_template": "Optional custom message. Leave blank for default message.",
        }

    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data.get("scheduled_at")
        if scheduled_at and scheduled_at < timezone.now():
            raise ValidationError("Scheduled time cannot be in the past.")
        return scheduled_at


class ParticipantExclusionForm(forms.ModelForm):
    """Form for managing participant exclusions (organizer only)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Only show other participants from the same event (exclude self)
            self.fields["exclusions"].queryset = Participant.objects.filter(
                event=self.instance.event, is_confirmed=True
            ).exclude(pk=self.instance.pk)
            # Use a more compact widget for organizer view
            self.fields["exclusions"].label_from_instance = lambda obj: f"{obj.name} ({obj.email})"

    class Meta:
        model = Participant
        fields = ["exclusions"]
        widgets = {
            "exclusions": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "exclusions": "Select participants this person cannot be assigned to",
        }


class ExclusionGroupForm(forms.ModelForm):
    """Form for managing exclusion groups."""

    def __init__(self, *args, **kwargs):
        event = kwargs.pop("event", None)
        super().__init__(*args, **kwargs)
        if event:
            # Only show confirmed participants from this event
            self.fields["members"].queryset = Participant.objects.filter(event=event, is_confirmed=True).order_by(
                "name"
            )

    class Meta:
        model = ExclusionGroup
        fields = ["name", "description", "members"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "members": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "name": "Give this group a descriptive name (e.g., 'Smith Family', 'Marketing Team')",
            "description": "Optional description of this group",
            "members": "Select all participants who should be excluded from each other",
        }
