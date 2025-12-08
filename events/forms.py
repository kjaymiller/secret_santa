from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Event, NotificationSchedule, Participant


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
            "exclusions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter email addresses of people you cannot give gifts to (e.g., spouse@example.com, family@example.com)",
                }
            ),
        }
        help_texts = {
            "wishlist_markdown": "Use Markdown formatting. Your Secret Santa will see this list.",
            "exclusions": "Email addresses of people you should not be assigned to (e.g., spouse, close family)",
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

    class Meta:
        model = Participant
        fields = ["exclusions"]
        widgets = {
            "exclusions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Comma-separated emails (e.g., john@example.com, jane@example.com)",
                }
            ),
        }
        help_texts = {
            "exclusions": "Enter email addresses of other participants this person cannot be assigned to",
        }
