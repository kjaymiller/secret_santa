import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Event(models.Model):
    """Secret Santa event that participants can join."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_events",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    invite_code = models.CharField(max_length=50, unique=True, db_index=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    event_date = models.DateField()
    registration_deadline = models.DateField(blank=True, null=True)
    assignments_revealed_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Generate invite code if not set."""
        if not self.invite_code:
            # Generate a unique 8-character code
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)


class Participant(models.Model):
    """A participant in a Secret Santa event."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="participations",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    wishlist_markdown = models.TextField(blank=True, null=True, help_text="Markdown formatted wishlist")
    exclusions_old = models.TextField(
        blank=True, null=True, help_text="DEPRECATED: Use exclusions ManyToMany field instead"
    )
    exclusions = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="excluded_by",
        blank=True,
        help_text="Participants this person cannot be assigned to give gifts to",
    )
    is_confirmed = models.BooleanField(default=False)
    confirmation_token = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["event", "email"], name="unique_participant_per_event"),
        ]

    def __str__(self):
        return f"{self.name} ({self.event.name})"

    def generate_confirmation_token(self):
        """Generate a unique confirmation token for email verification."""
        if not self.confirmation_token:
            self.confirmation_token = uuid.uuid4().hex
            self.save(update_fields=["confirmation_token"])


class ExclusionGroup(models.Model):
    """A group of participants who should not be assigned to each other."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="exclusion_groups")
    name = models.CharField(
        max_length=100, help_text="Name for this exclusion group (e.g., 'Smith Family', 'Marketing Team')"
    )
    description = models.TextField(blank=True, null=True, help_text="Optional description of this group")
    members = models.ManyToManyField(
        Participant,
        related_name="exclusion_groups",
        blank=True,
        help_text="Participants in this group will not be assigned to give gifts to each other",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["event", "name"], name="unique_group_name_per_event"),
        ]

    def __str__(self):
        return f"{self.name} ({self.event.name})"

    def apply_exclusions(self):
        """Apply mutual exclusions between all members of this group."""
        members = list(self.members.all())
        for member in members:
            # Exclude all other members in the group
            other_members = [m for m in members if m != member]
            member.exclusions.add(*other_members)

    def remove_exclusions(self):
        """Remove all exclusions between members of this group."""
        members = list(self.members.all())
        for member in members:
            # Remove exclusions to other members
            other_members = [m for m in members if m != member]
            member.exclusions.remove(*other_members)


class Assignment(models.Model):
    """Assignment of a giver to a receiver in a Secret Santa event."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="assignments")
    giver = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="giving_assignments",
    )
    receiver = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="receiving_assignments",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    is_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["assigned_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "giver"], name="unique_giver_per_event"),
            models.CheckConstraint(
                condition=~models.Q(giver=models.F("receiver")),
                name="no_self_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.giver.name} → {self.receiver.name} ({self.event.name})"

    def mark_as_viewed(self):
        """Mark assignment as viewed and record timestamp."""
        if not self.is_viewed:
            self.is_viewed = True
            self.viewed_at = timezone.now()
            self.save(update_fields=["is_viewed", "viewed_at"])



class UserProfile(models.Model):
    """User profile for storing additional preferences."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    notification_preference = models.CharField(
        max_length=10,
        choices=[("email", "Email"), ("sms", "SMS")],
        default="email",
        help_text="Preferred method for receiving notifications",
    )

    def __str__(self):
        return f"Profile for {self.user}"


class NotificationSchedule(models.Model):
    """Scheduled notification for an event."""

    NOTIFICATION_TYPES = [
        ("registration_reminder", "Registration Reminder"),
        ("assignment_reveal", "Assignment Reveal"),
        ("event_reminder", "Event Reminder"),
        ("custom", "Custom"),
    ]

    DELIVERY_METHODS = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("both", "Both"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="notification_schedules")
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    scheduled_at = models.DateTimeField()
    message_template = models.TextField(blank=True, null=True)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_METHODS, default="email")
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.event.name} at {self.scheduled_at}"

    def mark_as_sent(self):
        """Mark notification as sent and record timestamp."""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
            self.save(update_fields=["is_sent", "sent_at"])
