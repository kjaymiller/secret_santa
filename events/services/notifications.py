"""Notification service for sending email and SMS notifications using Twilio SendGrid and Twilio SMS."""

import logging
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Base exception for notification errors."""


class EmailNotificationError(NotificationError):
    """Exception for email notification errors."""


class SMSNotificationError(NotificationError):
    """Exception for SMS notification errors."""


class NotificationService:
    """Service for sending email and SMS notifications."""

    def __init__(self):
        """Initialize notification service with Twilio credentials."""
        self.sendgrid_api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME
        self.twilio_account_sid = settings.TWILIO_ACCOUNT_SID
        self.twilio_auth_token = settings.TWILIO_AUTH_TOKEN
        self.twilio_phone_number = settings.TWILIO_PHONE_NUMBER

    def send_email_notification(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict[str, Any],
        to_name: str | None = None,
    ) -> bool:
        """
        Send email notification using SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_name: Name of the email template (without .html extension)
            context: Context data for template rendering
            to_name: Optional recipient name

        Returns:
            True if email was sent successfully, False otherwise

        Raises:
            EmailNotificationError: If email sending fails
        """
        try:
            # Render HTML and plain text versions
            html_content = render_to_string(f"emails/{template_name}.html", context)
            text_content = strip_tags(html_content)

            if self.sendgrid_api_key and not settings.DEBUG:
                # Use SendGrid API for production
                message = Mail(
                    from_email=(self.from_email, self.from_name),
                    to_emails=to_email,
                    subject=subject,
                    plain_text_content=text_content,
                    html_content=html_content,
                )

                sg = SendGridAPIClient(self.sendgrid_api_key)
                response = sg.send(message)

                if response.status_code not in [200, 201, 202]:
                    raise EmailNotificationError(f"SendGrid returned status code {response.status_code}")

                logger.info(f"Email sent to {to_email} via SendGrid: {subject}")
            else:
                # Use Django's email backend for development (console backend if DEBUG=True)
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=f"{self.from_name} <{self.from_email}>",
                    to=[to_email],
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

                logger.info(f"Email sent to {to_email} via Django backend: {subject}")

            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise EmailNotificationError(f"Failed to send email: {e}")

    def send_sms_notification(
        self,
        to_phone: str,
        message: str,
    ) -> bool:
        """
        Send SMS notification using Twilio.

        Args:
            to_phone: Recipient phone number (E.164 format recommended)
            message: SMS message content (max 160 characters recommended)

        Returns:
            True if SMS was sent successfully, False otherwise

        Raises:
            SMSNotificationError: If SMS sending fails
        """
        if not to_phone:
            raise SMSNotificationError("Recipient phone number is required")

        if len(message) > 160:
            logger.warning(
                f"SMS message exceeds 160 characters ({len(message)} chars), may be split into multiple parts"
            )

        try:
            if self.twilio_account_sid and self.twilio_auth_token and not settings.DEBUG:
                # Use Twilio API for production
                client = Client(self.twilio_account_sid, self.twilio_auth_token)

                twilio_message = client.messages.create(body=message, from_=self.twilio_phone_number, to=to_phone)

                logger.info(f"SMS sent to {to_phone} via Twilio. SID: {twilio_message.sid}")
            else:
                # Log to console for development
                logger.info(f"[DEV] SMS to {to_phone}: {message}")

            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            raise SMSNotificationError(f"Failed to send SMS: {e}")

    def send_notification(
        self,
        notification_schedule,
    ) -> bool:
        """
        Send notification based on NotificationSchedule configuration.

        Args:
            notification_schedule: NotificationSchedule model instance

        Returns:
            True if notification was sent successfully

        Raises:
            NotificationError: If notification sending fails
        """

        if notification_schedule.is_sent:
            logger.warning(f"Notification {notification_schedule.id} has already been sent")
            return False

        event = notification_schedule.event
        delivery_method = notification_schedule.delivery_method
        notification_type = notification_schedule.notification_type

        # Prepare context for templates
        context = {
            "event": event,
            "event_name": event.name,
            "event_date": event.event_date,
            "invite_code": event.invite_code,
            "budget_max": event.budget_max,
            "organizer_name": event.organizer.get_full_name()
            if hasattr(event.organizer, "get_full_name")
            else str(event.organizer),
        }

        # Add custom message if provided
        if notification_schedule.message_template:
            context["custom_message"] = notification_schedule.message_template

        success = False

        try:
            # Get participants for this event
            participants = event.participants.filter(is_confirmed=True)

            for participant in participants:
                context["participant_name"] = participant.name

                # Send email if required
                if delivery_method in ["email", "both"] and participant.email:
                    try:
                        self.send_email_notification(
                            to_email=participant.email,
                            subject=self._get_email_subject(notification_type, event),
                            template_name=notification_type,
                            context=context,
                            to_name=participant.name,
                        )
                    except EmailNotificationError as e:
                        logger.error(f"Failed to send email to {participant.email}: {e}")
                        # Continue with other participants even if one fails

                # Send SMS if required
                if delivery_method in ["sms", "both"] and participant.phone_number:
                    try:
                        sms_message = self._get_sms_message(notification_type, context)
                        self.send_sms_notification(
                            to_phone=participant.phone_number,
                            message=sms_message,
                        )
                    except SMSNotificationError as e:
                        logger.error(f"Failed to send SMS to {participant.phone_number}: {e}")
                        # Continue with other participants even if one fails

            # Mark notification as sent
            notification_schedule.mark_as_sent()
            success = True

        except Exception as e:
            logger.error(f"Failed to send notification {notification_schedule.id}: {e}")
            raise NotificationError(f"Failed to send notification: {e}")

        return success

    def _get_email_subject(self, notification_type: str, event) -> str:
        """Get email subject based on notification type."""
        subjects = {
            "registration_reminder": f"Reminder: Join {event.name} Secret Santa",
            "assignment_reveal": f"Your Secret Santa Assignment - {event.name}",
            "event_reminder": f"Reminder: {event.name} is coming up!",
            "custom": f"Update from {event.name}",
        }
        return subjects.get(notification_type, f"Notification from {event.name}")

    def _get_sms_message(self, notification_type: str, context: dict[str, Any]) -> str:
        """
        Get SMS message based on notification type.

        SMS messages are kept under 160 characters to avoid multi-part messages.
        """
        event_name = context["event_name"]
        invite_code = context["invite_code"]

        messages = {
            "registration_reminder": f"Don't forget to join {event_name}! Use code: {invite_code}",
            "assignment_reveal": f"Your Secret Santa assignment for {event_name} is ready! Check your email for details.",
            "event_reminder": f"Reminder: {event_name} is on {context['event_date']}. Happy gifting!",
            "custom": context.get("custom_message", f"Update from {event_name}. Check your email for details."),
        }

        message = messages.get(notification_type, f"Notification from {event_name}")

        # Truncate if necessary (shouldn't happen with our predefined messages)
        if len(message) > 160:
            message = message[:157] + "..."

        return message

    def send_assignment_notification(self, assignment) -> bool:
        """
        Send assignment notification to a participant.

        Args:
            assignment: Assignment model instance

        Returns:
            True if notification was sent successfully
        """
        giver = assignment.giver
        receiver = assignment.receiver
        event = assignment.event

        context = {
            "event": event,
            "event_name": event.name,
            "event_date": event.event_date,
            "budget_max": event.budget_max,
            "participant_name": giver.name,
            "assignment_name": receiver.name,
            "wishlist": receiver.wishlist_markdown or "No wishlist provided yet.",
        }

        success = True

        # Send email
        if giver.email:
            try:
                self.send_email_notification(
                    to_email=giver.email,
                    subject=f"Your Secret Santa Assignment - {event.name}",
                    template_name="assignment_reveal",
                    context=context,
                    to_name=giver.name,
                )
            except EmailNotificationError as e:
                logger.error(f"Failed to send assignment email to {giver.email}: {e}")
                success = False

        # Send SMS if phone number is provided
        if giver.phone_number:
            try:
                sms_message = f"Your Secret Santa assignment for {event.name} is ready! You're giving a gift to {receiver.name}. Check your email for their wishlist."
                self.send_sms_notification(
                    to_phone=giver.phone_number,
                    message=sms_message,
                )
            except SMSNotificationError as e:
                logger.error(f"Failed to send assignment SMS to {giver.phone_number}: {e}")
                # Don't fail if SMS fails but email succeeded

        return success

    def send_invite_notification(self, participant, event) -> bool:
        """
        Send invite notification to a participant.

        Args:
            participant: Participant model instance
            event: Event model instance

        Returns:
            True if notification was sent successfully
        """
        context = {
            "event": event,
            "event_name": event.name,
            "event_date": event.event_date,
            "invite_code": event.invite_code,
            "budget_max": event.budget_max,
            "participant_name": participant.name,
            "registration_deadline": event.registration_deadline,
            "organizer_name": event.organizer.get_full_name()
            if hasattr(event.organizer, "get_full_name")
            else str(event.organizer),
        }

        success = True

        # Send email
        if participant.email:
            try:
                self.send_email_notification(
                    to_email=participant.email,
                    subject=f"You're invited to {event.name}!",
                    template_name="registration_reminder",
                    context=context,
                    to_name=participant.name,
                )
            except EmailNotificationError as e:
                logger.error(f"Failed to send invite email to {participant.email}: {e}")
                success = False

        # Send SMS if phone number is provided
        if participant.phone_number:
            try:
                sms_message = f"You're invited to {event.name}! Join using code: {event.invite_code}"
                self.send_sms_notification(
                    to_phone=participant.phone_number,
                    message=sms_message,
                )
            except SMSNotificationError as e:
                logger.error(f"Failed to send invite SMS to {participant.phone_number}: {e}")
                # Don't fail if SMS fails but email succeeded

        return success

    def send_confirmation_email(self, participant, confirmation_url: str) -> bool:
        """
        Send confirmation email to a participant.

        Args:
            participant: Participant model instance
            confirmation_url: Full URL for confirming participation

        Returns:
            True if email was sent successfully
        """
        event = participant.event

        context = {
            "event": event,
            "event_name": event.name,
            "event_date": event.event_date,
            "budget_max": event.budget_max,
            "participant_name": participant.name,
            "registration_deadline": event.registration_deadline,
            "organizer_name": event.organizer.get_full_name()
            if hasattr(event.organizer, "get_full_name")
            else str(event.organizer),
            "confirmation_url": confirmation_url,
        }

        try:
            self.send_email_notification(
                to_email=participant.email,
                subject=f"Confirm your participation in {event.name}",
                template_name="participant_confirmation",
                context=context,
                to_name=participant.name,
            )
            logger.info(f"Confirmation email sent to {participant.email}")
            return True
        except EmailNotificationError as e:
            logger.error(f"Failed to send confirmation email to {participant.email}: {e}")
            return False

    def send_exclusion_group_notification(self, exclusion_group) -> bool:
        """
        Send notification emails to all members of an exclusion group.

        Args:
            exclusion_group: ExclusionGroup model instance

        Returns:
            True if all emails were sent successfully
        """
        event = exclusion_group.event
        members = list(exclusion_group.members.all())

        if not members:
            logger.warning(f"No members in exclusion group {exclusion_group.id}, skipping notification")
            return True

        success_count = 0
        failed_count = 0

        for member in members:
            # Get other members (excluding current member)
            other_members = [m for m in members if m != member]

            context = {
                "event": event,
                "event_name": event.name,
                "event_date": event.event_date,
                "participant_name": member.name,
                "group_name": exclusion_group.name,
                "group_description": exclusion_group.description,
                "member_count": len(members),
                "other_members": other_members,
                "organizer_name": event.organizer.get_full_name()
                if hasattr(event.organizer, "get_full_name")
                else str(event.organizer),
            }

            try:
                self.send_email_notification(
                    to_email=member.email,
                    subject=f"You've been added to {exclusion_group.name} - {event.name}",
                    template_name="exclusion_group_notification",
                    context=context,
                    to_name=member.name,
                )
                logger.info(f"Exclusion group notification sent to {member.email}")
                success_count += 1
            except EmailNotificationError as e:
                logger.error(f"Failed to send exclusion group notification to {member.email}: {e}")
                failed_count += 1

        logger.info(f"Exclusion group notification complete: {success_count} sent, {failed_count} failed")
        return failed_count == 0

    def send_event_creation_notification(self, event, request) -> bool:
        """
        Send confirmation email to organizer when event is created.

        Args:
            event: Event model instance
            request: HTTP request object for building absolute URLs

        Returns:
            True if email was sent successfully
        """
        organizer = event.organizer

        # Build URLs for the email
        join_url = request.build_absolute_uri(f"/events/join/{event.invite_code}/")
        event_url = request.build_absolute_uri(f"/events/{event.pk}/")

        context = {
            "event": event,
            "event_name": event.name,
            "event_date": event.event_date,
            "registration_deadline": event.registration_deadline,
            "budget_max": event.budget_max,
            "organizer_name": organizer.get_full_name() if hasattr(organizer, "get_full_name") else str(organizer),
            "invite_code": event.invite_code,
            "join_url": join_url,
            "event_url": event_url,
        }

        try:
            self.send_email_notification(
                to_email=organizer.email,
                subject=f'Your Secret Santa event "{event.name}" has been created!',
                template_name="event_created",
                context=context,
                to_name=organizer.get_full_name() if hasattr(organizer, "get_full_name") else str(organizer),
            )
            logger.info(f"Event creation notification sent to {organizer.email}")
            return True
        except EmailNotificationError as e:
            logger.error(f"Failed to send event creation notification to {organizer.email}: {e}")
            return False

    def send_event_deletion_notification(self, event, cancellation_message: str = "") -> bool:
        """
        Send notification emails to all participants when an event is deleted.

        Args:
            event: Event model instance
            cancellation_message: Optional message from organizer explaining the cancellation

        Returns:
            True if all emails were sent successfully
        """
        participants = list(event.participants.all())

        if not participants:
            logger.info(f"No participants in event {event.id}, skipping deletion notification")
            return True

        success_count = 0
        failed_count = 0

        organizer_email = event.organizer.email if hasattr(event.organizer, "email") else None

        for participant in participants:
            context = {
                "event": event,
                "event_name": event.name,
                "event_date": event.event_date,
                "budget_max": event.budget_max,
                "participant_name": participant.name,
                "organizer_name": event.organizer.get_full_name()
                if hasattr(event.organizer, "get_full_name")
                else str(event.organizer),
                "organizer_email": organizer_email,
                "cancellation_message": cancellation_message if cancellation_message else None,
            }

            try:
                self.send_email_notification(
                    to_email=participant.email,
                    subject=f"{event.name} has been cancelled",
                    template_name="event_deletion",
                    context=context,
                    to_name=participant.name,
                )
                logger.info(f"Event deletion notification sent to {participant.email}")
                success_count += 1
            except EmailNotificationError as e:
                logger.error(f"Failed to send event deletion notification to {participant.email}: {e}")
                failed_count += 1

        logger.info(f"Event deletion notification complete: {success_count} sent, {failed_count} failed")
        return failed_count == 0


# Convenience function for easy import
def get_notification_service() -> NotificationService:
    """Get an instance of the notification service."""
    return NotificationService()
