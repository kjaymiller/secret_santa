from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from allauth.account.models import EmailAddress

User = get_user_model()

class VerifiedEmailRequiredTestCase(TestCase):
    def setUp(self):
        self.verified_user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="password"
        )
        EmailAddress.objects.create(
            user=self.verified_user,
            email="verified@example.com",
            verified=True,
            primary=True
        )

        self.unverified_user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="password"
        )
        EmailAddress.objects.create(
            user=self.unverified_user,
            email="unverified@example.com",
            verified=False,
            primary=True
        )

        self.event_data = {
            "name": "Test Event",
            "event_date": date.today() + timedelta(days=30),
            "registration_deadline": date.today() + timedelta(days=20),
            "budget_max": "50.00",
            "is_active": True,
        }

    def test_verified_user_can_create_event(self):
        self.client.force_login(self.verified_user)
        response = self.client.post(reverse("events:event-create"), self.event_data)
        self.assertEqual(response.status_code, 302)  # Success redirect

    def test_verified_user_can_join_event(self):
        # Create event
        from events.models import Event
        event = Event.objects.create(
            organizer=self.verified_user,
            name="Joinable Event",
            event_date=date.today() + timedelta(days=30),
            invite_code="ABCDEF12"
        )
        
        # User 2 verified
        user2 = User.objects.create_user(username="v2", email="v2@example.com", password="pw")
        EmailAddress.objects.create(user=user2, email="v2@example.com", verified=True, primary=True)
        
        self.client.force_login(user2)
        response = self.client.post(
            reverse("events:join-event", kwargs={"invite_code": "ABCDEF12"}),
            {"email": "v2@example.com", "name": "V2"}
        )
        self.assertEqual(response.status_code, 302)

    def test_unverified_user_cannot_create_event(self):
        self.client.force_login(self.unverified_user)
        response = self.client.post(reverse("events:event-create"), self.event_data)
        
        # Should redirect to account page
        self.assertRedirects(response, reverse("account"))
        
        # Verify event was not created
        from events.models import Event
        self.assertFalse(Event.objects.filter(organizer=self.unverified_user, name="Test Event").exists())

    def test_unverified_user_cannot_join_event(self):
        # Create event
        from events.models import Event
        event = Event.objects.create(
            organizer=self.verified_user,
            name="Joinable Event",
            event_date=date.today() + timedelta(days=30),
            invite_code="ABCDEF12"
        )
        
        self.client.force_login(self.unverified_user)
        response = self.client.post(
            reverse("events:join-event", kwargs={"invite_code": "ABCDEF12"}),
            {"email": "unverified@example.com", "name": "Unverified"}
        )
        
        # Should redirect to account page
        self.assertRedirects(response, reverse("account"))
        
        # Verify participant was not created/linked
        from events.models import Participant
        self.assertFalse(Participant.objects.filter(event=event, user=self.unverified_user).exists())
