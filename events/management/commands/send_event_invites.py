"""Management command to send event invitations to participants."""

from django.core.management.base import BaseCommand, CommandError

from events.models import Event, Participant
from events.services.notifications import get_notification_service


class Command(BaseCommand):
    help = "Send invitation emails/SMS to participants for a Secret Santa event"

    def add_arguments(self, parser):
        parser.add_argument("event_id", type=str, help="UUID of the event")
        parser.add_argument(
            "--emails",
            type=str,
            help="Comma-separated list of email addresses to invite",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Send invites to all unconfirmed participants in the event",
        )
        parser.add_argument(
            "--confirmed",
            action="store_true",
            help="Include confirmed participants (use with --all)",
        )

    def handle(self, *args, **options):
        event_id = options["event_id"]
        emails_str = options.get("emails")
        send_to_all = options.get("all")
        include_confirmed = options.get("confirmed")

        # Get the event
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            raise CommandError(f"Event with ID {event_id} does not exist")

        notification_service = get_notification_service()

        if send_to_all:
            # Send to all participants in the event
            if include_confirmed:
                participants = event.participants.all()
                self.stdout.write(f"Sending invites to all participants in {event.name}...")
            else:
                participants = event.participants.filter(is_confirmed=False)
                self.stdout.write(f"Sending invites to unconfirmed participants in {event.name}...")

            sent_count = 0
            failed_count = 0

            for participant in participants:
                try:
                    success = notification_service.send_invite_notification(participant, event)
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"✓ Sent invite to {participant.email}"))
                        sent_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"✗ Failed to send invite to {participant.email}"))
                        failed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Error sending to {participant.email}: {e}"))
                    failed_count += 1

            self.stdout.write(
                self.style.SUCCESS(f"\nSummary: {sent_count} sent, {failed_count} failed")
            )

        elif emails_str:
            # Send to specific email addresses
            emails = [email.strip() for email in emails_str.split(",")]
            self.stdout.write(f"Sending invites to {len(emails)} email(s) for {event.name}...")

            sent_count = 0
            failed_count = 0

            for email in emails:
                try:
                    # Check if participant exists
                    participant = event.participants.filter(email=email).first()

                    if participant:
                        # Send to existing participant
                        success = notification_service.send_invite_notification(participant, event)
                        if success:
                            self.stdout.write(self.style.SUCCESS(f"✓ Sent invite to {email}"))
                            sent_count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f"✗ Failed to send invite to {email}"))
                            failed_count += 1
                    else:
                        # Create new participant and send invite
                        participant = Participant.objects.create(
                            event=event,
                            email=email,
                            name=email.split("@")[0],  # Use email prefix as temporary name
                        )
                        success = notification_service.send_invite_notification(participant, event)
                        if success:
                            self.stdout.write(
                                self.style.SUCCESS(f"✓ Created participant and sent invite to {email}")
                            )
                            sent_count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f"✗ Failed to send invite to {email}"))
                            failed_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Error sending to {email}: {e}"))
                    failed_count += 1

            self.stdout.write(
                self.style.SUCCESS(f"\nSummary: {sent_count} sent, {failed_count} failed")
            )

        else:
            raise CommandError("Please specify either --emails or --all")
