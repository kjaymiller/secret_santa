import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from events.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
def test_user_profile_creation_signal():
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    assert UserProfile.objects.filter(user=user).exists()
    assert user.profile.notification_preference == "email"


@pytest.mark.django_db
def test_account_view_context(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    client.force_login(user)

    url = reverse("account")
    response = client.get(url)

    assert response.status_code == 200
    assert "form" in response.context
    # Check if form field is rendered
    assert b"notification_preference" in response.content
    assert b"Email" in response.content
    assert b"SMS" in response.content


@pytest.mark.django_db
def test_account_view_post(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    client.force_login(user)

    url = reverse("account")
    data = {"notification_preference": "sms"}
    response = client.post(url, data)

    # Should redirect on success
    assert response.status_code == 302

    user.profile.refresh_from_db()
    assert user.profile.notification_preference == "sms"
