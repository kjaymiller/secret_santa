"""Management command to send assignment notifications to participants."""

from django.core.management.base import BaseCommand, CommandError

from events.models import Event
from events.services.notifications import get_notification_service


class Command(BaseCommand):
    help = "Send assignment notifications to all participants in a Secret Santa event"

    def add_arguments(self, parser):
        parser.add_argument("event_id", type=str, help="UUID of the event")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually sending",
        )

    def handle(self, *args, **options):
        event_id = options["event_id"]
        dry_run = options.get("dry_run", False)

        # Get the event
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            raise CommandError(f"Event with ID {event_id} does not exist")

        # Check if assignments exist
        assignments = event.assignments.all()
        if not assignments.exists():
            raise CommandError(
                f"No assignments found for event '{event.name}'. "
                "Please generate assignments first using the admin interface or views."
            )

        assignment_count = assignments.count()
        participant_count = event.participants.filter(is_confirmed=True).count()

        if assignment_count != participant_count:
            self.stdout.write(
                self.style.WARNING(
                    f"Warning: Found {assignment_count} assignments but {participant_count} confirmed participants. "
                    "Some participants may not have assignments."
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No emails/SMS will be sent\n"))

        self.stdout.write(f"Sending assignment notifications for event: {event.name}")
        self.stdout.write(f"Total assignments: {assignment_count}\n")

        notification_service = get_notification_service()
        sent_count = 0
        failed_count = 0

        for assignment in assignments:
            giver = assignment.giver
            receiver = assignment.receiver

            if dry_run:
                self.stdout.write(
                    f"Would send notification to {giver.name} ({giver.email}) - Assignment: {receiver.name}"
                )
                sent_count += 1
            else:
                try:
                    success = notification_service.send_assignment_notification(assignment)
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Sent assignment to {giver.name} ({giver.email}) - Assigned to: {receiver.name}"
                            )
                        )
                        # Mark assignment as viewed for tracking
                        if not assignment.is_viewed:
                            assignment.mark_as_viewed()
                        sent_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"✗ Failed to send assignment to {giver.name} ({giver.email})")
                        )
                        failed_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Error sending assignment to {giver.name} ({giver.email}): {e}")
                    )
                    failed_count += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nDRY RUN Summary: Would send {sent_count} notifications"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSummary: {sent_count} sent, {failed_count} failed"))

            if sent_count == assignment_count:
                self.stdout.write(self.style.SUCCESS("All assignment notifications sent successfully!"))
