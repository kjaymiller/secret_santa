from django.contrib import admin
from .models import Assignment, Event, NotificationSchedule, Participant, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_preference"]
    search_fields = ["user__username", "user__email"]


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    fields = ["name", "email", "phone_number", "is_confirmed"]
    readonly_fields = ["created_at"]


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 0
    fields = ["giver", "receiver", "assigned_at", "is_viewed", "viewed_at"]
    readonly_fields = ["assigned_at", "viewed_at"]


class NotificationScheduleInline(admin.TabularInline):
    model = NotificationSchedule
    extra = 0
    fields = ["notification_type", "scheduled_at", "delivery_method", "is_sent", "sent_at"]
    readonly_fields = ["sent_at"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "organizer", "event_date", "invite_code", "is_active", "created_at"]
    list_filter = ["is_active", "event_date", "created_at"]
    search_fields = ["name", "invite_code", "organizer__email"]
    readonly_fields = ["invite_code", "created_at", "updated_at"]
    inlines = [ParticipantInline, AssignmentInline, NotificationScheduleInline]
    fieldsets = [
        (
            "Basic Information",
            {
                "fields": ["organizer", "name", "description", "invite_code"],
            },
        ),
        (
            "Event Details",
            {
                "fields": ["event_date", "registration_deadline", "budget_max"],
            },
        ),
        (
            "Status",
            {
                "fields": ["is_active", "assignments_revealed_at"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
            },
        ),
    ]


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "event", "is_confirmed", "created_at"]
    list_filter = ["is_confirmed", "event", "created_at"]
    search_fields = ["name", "email", "event__name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            "Basic Information",
            {
                "fields": ["event", "user", "name", "email", "phone_number"],
            },
        ),
        (
            "Preferences",
            {
                "fields": ["wishlist_markdown", "exclusions"],
            },
        ),
        (
            "Status",
            {
                "fields": ["is_confirmed"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
            },
        ),
    ]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["event", "giver", "receiver", "assigned_at", "is_viewed", "viewed_at"]
    list_filter = ["is_viewed", "event", "assigned_at"]
    search_fields = ["event__name", "giver__name", "receiver__name"]
    readonly_fields = ["assigned_at", "viewed_at"]
    fieldsets = [
        (
            "Assignment Details",
            {
                "fields": ["event", "giver", "receiver"],
            },
        ),
        (
            "Status",
            {
                "fields": ["is_viewed", "assigned_at", "viewed_at"],
            },
        ),
    ]


@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
    list_display = ["event", "notification_type", "scheduled_at", "delivery_method", "is_sent", "sent_at"]
    list_filter = ["is_sent", "notification_type", "delivery_method", "scheduled_at"]
    search_fields = ["event__name", "message_template"]
    readonly_fields = ["sent_at", "created_at"]
    fieldsets = [
        (
            "Notification Details",
            {
                "fields": ["event", "notification_type", "message_template"],
            },
        ),
        (
            "Delivery",
            {
                "fields": ["scheduled_at", "delivery_method"],
            },
        ),
        (
            "Status",
            {
                "fields": ["is_sent", "sent_at", "created_at"],
            },
        ),
    ]
