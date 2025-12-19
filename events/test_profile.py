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


@pytest.mark.django_db
def test_resend_confirmation_view(client):
    from allauth.account.models import EmailAddress

    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    client.force_login(user)

    # Create unverified primary email
    email_address = EmailAddress.objects.create(user=user, email="test@example.com", primary=True, verified=False)

    url = reverse("account-resend-confirmation")
    
    # Mock send_confirmation to verify it's called
    # We can't easily mock instance methods on created objects without patching the class
    # or refreshing.
    # So we'll check the message instead.
    response = client.post(url, follow=True)

    assert response.status_code == 200
    assert "account" in response.request["PATH_INFO"]
    messages = list(response.context["messages"])
    assert len(messages) == 1
    assert "Confirmation email sent" in str(messages[0])


@pytest.mark.django_db
def test_resend_confirmation_view_no_email(client):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
    client.force_login(user)

    # No EmailAddress object created

    url = reverse("account-resend-confirmation")
    response = client.post(url, follow=True)

    assert response.status_code == 200
    messages = list(response.context["messages"])
    assert len(messages) == 1
    assert "No unverified primary email found" in str(messages[0])
