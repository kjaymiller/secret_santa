from unittest.mock import Mock, patch
import pytest
from django.contrib.auth import get_user_model
from events.services.notifications import get_notification_service

User = get_user_model()

@pytest.mark.django_db
class TestAccountNotification:
    
    @patch("events.services.notifications.NotificationService.send_email_notification")
    def test_user_creation_triggers_email(self, mock_send_email):
        """Test that creating a user triggers the welcome email via signal."""
        # This tests the whole flow: User creation -> Signal -> Service -> Email
        user = User.objects.create_user(username="newuser", email="new@example.com", password="password")
        
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        assert call_args["to_email"] == "new@example.com"
        assert call_args["subject"] == "Welcome to Secret Santa!"
        assert call_args["template_name"] == "account_created"
        assert "login_url" in call_args["context"]
        # Since we didn't provide first/last name, it falls back to username
        assert call_args["context"]["user_name"] == "newuser" 

    @patch("events.services.notifications.NotificationService.send_email_notification")
    def test_service_method_direct(self, mock_send_email):
        """Test the service method directly."""
        # Use an unsaved user to avoid triggering the signal
        user = User(username="manual", email="manual@example.com")
        
        service = get_notification_service()
        result = service.send_account_creation_email(user)
        
        assert result is True
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        assert call_args["to_email"] == "manual@example.com"
