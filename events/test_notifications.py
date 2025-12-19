"""Tests for notification service."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker

from events.models import Assignment, Event, NotificationSchedule, Participant
from events.services.notifications import (
    EmailNotificationError,
    NotificationService,
    SMSNotificationError,
    get_notification_service,
)

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    return baker.make(User)


@pytest.fixture
def event(user):
    """Create a test event."""
    return baker.make(
        Event,
        organizer=user,
        name="Test Secret Santa",
        invite_code="TEST1234",
        budget_max=50,
    )


@pytest.fixture
def participant(event):
    """Create a test participant."""
    return baker.make(
        Participant,
        event=event,
        name="John Doe",
        email="john@example.com",
        phone_number="+1234567890",
        is_confirmed=True,
    )


@pytest.fixture
def notification_service():
    """Get notification service instance."""
    return get_notification_service()


@pytest.mark.django_db
class TestNotificationService:
    """Test NotificationService class."""

    def test_get_notification_service(self):
        """Test getting notification service instance."""
        service = get_notification_service()
        assert isinstance(service, NotificationService)

    @patch("events.services.notifications.render_to_string")
    @patch("events.services.notifications.EmailMultiAlternatives")
    def test_send_email_notification_success(
        self, mock_email_class, mock_render, notification_service, settings
    ):
        """Test sending email notification successfully."""
        settings.DEBUG = True
        mock_render.return_value = "<p>Test email content</p>"
        mock_email = Mock()
        mock_email_class.return_value = mock_email

        result = notification_service.send_email_notification(
            to_email="test@example.com",
            subject="Test Subject",
            template_name="registration_reminder",
            context={"event_name": "Test Event"},
        )

        assert result is True
        mock_render.assert_called_once()
        mock_email.send.assert_called_once()

    @patch("events.services.notifications.render_to_string")
    @patch("events.services.notifications.EmailMultiAlternatives")
    def test_send_email_notification_failure(
        self, mock_email_class, mock_render, notification_service, settings
    ):
        """Test email notification failure handling."""
        settings.DEBUG = True
        mock_render.return_value = "<p>Test email content</p>"
        mock_email = Mock()
        mock_email.send.side_effect = Exception("SMTP error")
        mock_email_class.return_value = mock_email

        with pytest.raises(EmailNotificationError):
            notification_service.send_email_notification(
                to_email="test@example.com",
                subject="Test Subject",
                template_name="registration_reminder",
                context={"event_name": "Test Event"},
            )

    @patch("events.services.notifications.Client")
    def test_send_sms_notification_success(
        self, mock_twilio_client, notification_service, settings
    ):
        """Test sending SMS notification successfully."""
        settings.DEBUG = True

        result = notification_service.send_sms_notification(
            to_phone="+1234567890",
            message="Test SMS message",
        )

        assert result is True

    def test_send_sms_notification_no_phone(self, notification_service):
        """Test SMS notification fails without phone number."""
        with pytest.raises(SMSNotificationError, match="phone number is required"):
            notification_service.send_sms_notification(
                to_phone="",
                message="Test message",
            )

    @patch("events.services.notifications.Client")
    def test_send_sms_notification_failure(
        self, mock_twilio_client, notification_service, settings
    ):
        """Test SMS notification failure handling."""
        settings.DEBUG = False
        settings.TWILIO_ACCOUNT_SID = "test_sid"
        settings.TWILIO_AUTH_TOKEN = "test_token"

        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("Twilio error")
        mock_twilio_client.return_value = mock_client

        with pytest.raises(SMSNotificationError):
            notification_service.send_sms_notification(
                to_phone="+1234567890",
                message="Test message",
            )

    def test_get_email_subject(self, notification_service, event):
        """Test email subject generation."""
        subject = notification_service._get_email_subject("registration_reminder", event)
        assert "Test Secret Santa" in subject

        subject = notification_service._get_email_subject("assignment_reveal", event)
        assert "Assignment" in subject

        subject = notification_service._get_email_subject("custom", event)
        assert "Update" in subject

    def test_get_sms_message(self, notification_service):
        """Test SMS message generation."""
        context = {
            "event_name": "Test Event",
            "invite_code": "TEST1234",
            "event_date": "2025-12-25",
        }

        message = notification_service._get_sms_message("registration_reminder", context)
        assert len(message) <= 160
        assert "Test Event" in message
        assert "TEST1234" in message

        message = notification_service._get_sms_message("assignment_reveal", context)
        assert len(message) <= 160

    def test_sms_message_truncation(self, notification_service):
        """Test SMS message is truncated if too long."""
        context = {
            "event_name": "Very Long Event Name That Goes On And On",
            "invite_code": "LONG1234",
            "custom_message": "A" * 200,  # Very long message
        }

        message = notification_service._get_sms_message("custom", context)
        assert len(message) <= 160

    @patch.object(NotificationService, "send_email_notification")
    @patch.object(NotificationService, "send_sms_notification")
    def test_send_assignment_notification(
        self, mock_sms, mock_email, notification_service, event, participant
    ):
        """Test sending assignment notification."""
        receiver = baker.make(
            Participant,
            event=event,
            name="Jane Doe",
            wishlist_markdown="I want a book",
            is_confirmed=True,
        )
        assignment = baker.make(
            Assignment,
            event=event,
            giver=participant,
            receiver=receiver,
        )

        mock_email.return_value = True
        mock_sms.return_value = True

        result = notification_service.send_assignment_notification(assignment)

        assert result is True
        mock_email.assert_called_once()
        mock_sms.assert_called_once()

    @patch.object(NotificationService, "send_email_notification")
    @patch.object(NotificationService, "send_sms_notification")
    def test_send_invite_notification(
        self, mock_sms, mock_email, notification_service, participant, event
    ):
        """Test sending invite notification."""
        mock_email.return_value = True
        mock_sms.return_value = True

        result = notification_service.send_invite_notification(participant, event)

        assert result is True
        mock_email.assert_called_once()
        mock_sms.assert_called_once()

    @patch.object(NotificationService, "send_email_notification")
    def test_send_invite_notification_email_only(
        self, mock_email, notification_service, event
    ):
        """Test sending invite to participant without phone number."""
        participant_no_phone = baker.make(
            Participant,
            event=event,
            name="No Phone",
            email="nophone@example.com",
            phone_number=None,
            is_confirmed=True,
        )

        mock_email.return_value = True

        result = notification_service.send_invite_notification(participant_no_phone, event)

        assert result is True
        mock_email.assert_called_once()

    @patch.object(NotificationService, "send_email_notification")
    @patch.object(NotificationService, "send_sms_notification")
    def test_send_notification_schedule(
        self, mock_sms, mock_email, notification_service, event, participant
    ):
        """Test sending notification from schedule."""
        notification_schedule = baker.make(
            NotificationSchedule,
            event=event,
            notification_type="registration_reminder",
            delivery_method="both",
            is_sent=False,
        )

        mock_email.return_value = True
        mock_sms.return_value = True

        result = notification_service.send_notification(notification_schedule)

        assert result is True
        notification_schedule.refresh_from_db()
        assert notification_schedule.is_sent is True
        assert notification_schedule.sent_at is not None

    def test_send_notification_already_sent(
        self, notification_service, event
    ):
        """Test sending notification that was already sent."""
        notification_schedule = baker.make(
            NotificationSchedule,
            event=event,
            notification_type="registration_reminder",
            is_sent=True,
        )

        result = notification_service.send_notification(notification_schedule)

        assert result is False

    @patch.object(NotificationService, "send_email_notification")
    def test_send_notification_email_only(
        self, mock_email, notification_service, event, participant
    ):
        """Test sending email-only notification."""
        notification_schedule = baker.make(
            NotificationSchedule,
            event=event,
            notification_type="event_reminder",
            delivery_method="email",
            is_sent=False,
        )

        mock_email.return_value = True

        result = notification_service.send_notification(notification_schedule)

        assert result is True
        mock_email.assert_called()

    @patch.object(NotificationService, "send_sms_notification")
    def test_send_notification_sms_only(
        self, mock_sms, notification_service, event, participant
    ):
        """Test sending SMS-only notification."""
        notification_schedule = baker.make(
            NotificationSchedule,
            event=event,
            notification_type="event_reminder",
            delivery_method="sms",
            is_sent=False,
        )

        mock_sms.return_value = True

        result = notification_service.send_notification(notification_schedule)

        assert result is True
        mock_sms.assert_called()
