import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_password_change_flow(client, django_user_model):
    """
    Test that the password change page loads with our custom template
    and the password change flow works correctly.
    """
    # Create user
    password = "oldpassword123"
    new_password = "newpassword456"
    user = django_user_model.objects.create_user(username="testuser", email="test@example.com", password=password)
    client.force_login(user)

    # 1. Access the change password page
    url = reverse("account_change_password")
    response = client.get(url)

    assert response.status_code == 200
    # Verify our custom template is used
    templates = [t.name for t in response.templates]
    assert "account/password_change.html" in templates
    # Verify content from our template
    content = response.content.decode()
    assert "Secure your account with a new password" in content
    assert "Back to Account" in content

    # 2. Submit password change
    data = {
        "oldpassword": password,
        "password1": new_password,
        "password2": new_password,
    }
    response = client.post(url, data, follow=True)

    assert response.status_code == 200

    # 3. Verify success state
    # We verify that either we are on a success page OR we see a success message
    content = response.content.decode()
    templates = [t.name for t in response.templates]

    success = False
    if "account/password_change_done.html" in templates:
        success = "Password Changed!" in content
    elif "events/account.html" in templates:  # Account page
        success = "Password changed" in content or "successfully" in content
    elif "account/password_change.html" in templates:  # Re-rendered form
        success = "Password changed" in content or "successfully" in content

    assert success, f"Password change did not show success message. Templates: {templates}"

    # Verify the password was actually changed in DB
    user.refresh_from_db()
    assert user.check_password(new_password)
