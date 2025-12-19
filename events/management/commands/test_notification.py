"""Management command to test email and SMS notifications."""

from django.core.management.base import BaseCommand

from events.services.notifications import get_notification_service


class Command(BaseCommand):
    help = "Test email and SMS notification functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Email address to send test email to",
        )
        parser.add_argument(
            "--sms",
            type=str,
            help="Phone number to send test SMS to (E.164 format: +1234567890)",
        )

    def handle(self, *args, **options):
        test_email = options.get("email")
        test_phone = options.get("sms")

        if not test_email and not test_phone:
            self.stdout.write(
                self.style.ERROR("Please specify either --email or --sms (or both)")
            )
            return

        notification_service = get_notification_service()

        # Test email
        if test_email:
            self.stdout.write(f"\nTesting email notification to: {test_email}")
            try:
                context = {
                    "event_name": "Test Secret Santa Event",
                    "event_date": "December 25, 2025",
                    "invite_code": "TEST1234",
                    "budget_max": 50,
                    "participant_name": "Test User",
                    "organizer_name": "Test Organizer",
                    "registration_deadline": "December 15, 2025",
                }

                success = notification_service.send_email_notification(
                    to_email=test_email,
                    subject="Test Email from Secret Santa",
                    template_name="registration_reminder",
                    context=context,
                    to_name="Test User",
                )

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Test email sent successfully to {test_email}")
                    )
                    self.stdout.write(
                        "  Check your inbox (and spam folder) for the test email."
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed to send test email to {test_email}")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error sending test email: {e}")
                )

        # Test SMS
        if test_phone:
            self.stdout.write(f"\nTesting SMS notification to: {test_phone}")
            try:
                test_message = (
                    "This is a test SMS from Secret Santa. "
                    "If you received this, your SMS notifications are working!"
                )

                success = notification_service.send_sms_notification(
                    to_phone=test_phone,
                    message=test_message,
                )

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Test SMS sent successfully to {test_phone}")
                    )
                    self.stdout.write(
                        "  Check your phone for the test SMS."
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed to send test SMS to {test_phone}")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error sending test SMS: {e}")
                )

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("Test complete!")
        self.stdout.write("=" * 70)
