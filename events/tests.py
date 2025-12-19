from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Event, Participant

User = get_user_model()


class EventCreateViewTestCase(TestCase):
    """Test cases for EventCreateView including auto-enrollment."""

    def setUp(self):
        """Set up test user and login."""
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_create_event_auto_enrolls_organizer(self):
        """Test that creating an event automatically enrolls the organizer as a participant."""
        event_date = date.today() + timedelta(days=30)
        registration_deadline = date.today() + timedelta(days=20)

        self.client.post(
            reverse("events:event-create"),
            {
                "name": "Test Secret Santa",
                "description": "A test event",
                "event_date": event_date,
                "registration_deadline": registration_deadline,
                "budget_max": "50.00",
                "is_active": True,
            },
        )

        # Check that event was created
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertEqual(event.name, "Test Secret Santa")
        self.assertEqual(event.organizer, self.user)

        # Check that organizer was auto-enrolled as participant
        self.assertEqual(Participant.objects.count(), 1)
        participant = Participant.objects.first()
        self.assertEqual(participant.event, event)
        self.assertEqual(participant.user, self.user)
        self.assertEqual(participant.email, self.user.email)
        self.assertEqual(participant.name, "Test User")
        self.assertTrue(participant.is_confirmed)

    def test_auto_enrolled_participant_uses_full_name(self):
        """Test that auto-enrolled participant uses user's full name."""
        event_date = date.today() + timedelta(days=30)

        self.client.post(
            reverse("events:event-create"),
            {
                "name": "Test Event",
                "event_date": event_date,
                "is_active": True,
            },
        )

        participant = Participant.objects.first()
        self.assertEqual(participant.name, "Test User")

    def test_auto_enrolled_participant_uses_username_if_no_full_name(self):
        """Test that auto-enrolled participant uses username if no full name is available."""
        # Create user without full name
        User.objects.create_user(
            username="noname",
            email="noname@example.com",
            password="testpass123",
        )
        self.client.login(username="noname", password="testpass123")

        event_date = date.today() + timedelta(days=30)

        self.client.post(
            reverse("events:event-create"),
            {
                "name": "Test Event",
                "event_date": event_date,
                "is_active": True,
            },
        )

        participant = Participant.objects.first()
        self.assertEqual(participant.name, "noname")

    def test_auto_enrolled_participant_is_confirmed(self):
        """Test that auto-enrolled participant is automatically confirmed."""
        event_date = date.today() + timedelta(days=30)

        self.client.post(
            reverse("events:event-create"),
            {
                "name": "Test Event",
                "event_date": event_date,
                "is_active": True,
            },
        )

        participant = Participant.objects.first()
        self.assertTrue(participant.is_confirmed)

    def test_auto_enrolled_participant_linked_to_user(self):
        """Test that auto-enrolled participant is linked to the organizer's user account."""
        event_date = date.today() + timedelta(days=30)

        self.client.post(
            reverse("events:event-create"),
            {
                "name": "Test Event",
                "event_date": event_date,
                "is_active": True,
            },
        )

        participant = Participant.objects.first()
        self.assertEqual(participant.user, self.user)
        self.assertIsNotNone(participant.user)

    def test_multiple_events_create_separate_participants(self):
        """Test that creating multiple events creates separate participant records."""
        event_date = date.today() + timedelta(days=30)

        # Create first event
        self.client.post(
            reverse("events:event-create"),
            {
                "name": "First Event",
                "event_date": event_date,
                "is_active": True,
            },
        )

        # Create second event
        self.client.post(
            reverse("events:event-create"),
            {
                "name": "Second Event",
                "event_date": event_date,
                "is_active": True,
            },
        )

        # Should have 2 events and 2 participants (one for each event)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Participant.objects.count(), 2)

        # Each event should have exactly one participant
        first_event = Event.objects.get(name="First Event")
        second_event = Event.objects.get(name="Second Event")
        self.assertEqual(first_event.participants.count(), 1)
        self.assertEqual(second_event.participants.count(), 1)

        # Each participant should be the organizer
        first_participant = first_event.participants.first()
        second_participant = second_event.participants.first()
        self.assertEqual(first_participant.user, self.user)
        self.assertEqual(second_participant.user, self.user)


class AccountDeleteViewTestCase(TestCase):
    """Test cases for AccountDeleteView."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="testuser@example.com")
        self.client.login(username="testuser", password="testpass123")

    def test_account_delete_view_access(self):
        """Test that the account delete view is accessible for logged-in users."""
        url = reverse("account-delete")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/account_confirm_delete.html")

    def test_account_delete_view_post(self):
        """Test that posting to the account delete view deletes the user."""
        user_pk = self.user.pk
        url = reverse("account-delete")
        response = self.client.post(url)

        # Should redirect to home
        self.assertRedirects(response, reverse("home"))

        # User should be deleted
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    def test_account_delete_view_requires_login(self):
        """Test that the account delete view requires login."""
        self.client.logout()
        url = reverse("account-delete")
        response = self.client.get(url)

        # Should redirect to login
        self.assertRedirects(response, f"/accounts/login/?next={url}")
