from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    # Event URLs
    path("", views.EventListView.as_view(), name="event-list"),
    path("create/", views.EventCreateView.as_view(), name="event-create"),
    path("<uuid:pk>/", views.EventDetailView.as_view(), name="event-detail"),
    path("<uuid:pk>/edit/", views.EventUpdateView.as_view(), name="event-update"),
    path("<uuid:pk>/invite/", views.EventSendInvitesView.as_view(), name="event-send-invites"),
    path("<uuid:pk>/delete/", views.EventDeleteView.as_view(), name="event-delete"),
    # Assignment URLs
    path(
        "<uuid:event_pk>/generate-assignments/",
        views.AssignmentGenerateView.as_view(),
        name="assignment-generate",
    ),
    path(
        "<uuid:event_pk>/assignments/status/",
        views.AssignmentStatusView.as_view(),
        name="assignment-status",
    ),
    path(
        "<uuid:event_pk>/my-assignment/<uuid:participant_pk>/",
        views.MyAssignmentView.as_view(),
        name="my-assignment",
    ),
    # Participant URLs (within event context)
    path(
        "<uuid:pk>/participants/",
        views.EventDetailView.as_view(),
        name="participant-list",
    ),
    path(
        "<uuid:event_pk>/exclusions/",
        views.ParticipantExclusionManageView.as_view(),
        name="exclusion-manage",
    ),
    # Exclusion Group URLs
    path(
        "<uuid:event_pk>/exclusion-groups/",
        views.ExclusionGroupListView.as_view(),
        name="exclusion-group-list",
    ),
    path(
        "<uuid:event_pk>/exclusion-groups/create/",
        views.ExclusionGroupCreateView.as_view(),
        name="exclusion-group-create",
    ),
    path(
        "exclusion-groups/<uuid:pk>/edit/",
        views.ExclusionGroupUpdateView.as_view(),
        name="exclusion-group-update",
    ),
    path(
        "exclusion-groups/<uuid:pk>/delete/",
        views.ExclusionGroupDeleteView.as_view(),
        name="exclusion-group-delete",
    ),
    # Notification URLs
    path(
        "<uuid:event_pk>/notifications/",
        views.NotificationScheduleListView.as_view(),
        name="notification-list",
    ),
    path(
        "<uuid:event_pk>/notifications/create/",
        views.NotificationScheduleCreateView.as_view(),
        name="notification-create",
    ),
    path(
        "notifications/<uuid:pk>/edit/",
        views.NotificationScheduleUpdateView.as_view(),
        name="notification-update",
    ),
    path(
        "notifications/<uuid:pk>/delete/",
        views.NotificationScheduleDeleteView.as_view(),
        name="notification-delete",
    ),
]

# Public URLs (no auth required)
public_urlpatterns = [
    # Invite code entry landing page
    path("join/", views.InviteCodeEntryView.as_view(), name="invite-code-entry"),
    # Join event via invite code
    path("join/<str:invite_code>/", views.ParticipantJoinView.as_view(), name="join-event"),
    # Participant management
    path("participant/<uuid:pk>/", views.ParticipantDetailView.as_view(), name="participant-detail"),
    path("participant/<uuid:pk>/edit/", views.ParticipantUpdateView.as_view(), name="participant-update"),
    path("participant/<uuid:pk>/confirm/", views.ParticipantConfirmView.as_view(), name="participant-confirm"),
    path(
        "participant/confirm/<str:token>/",
        views.ParticipantConfirmEmailView.as_view(),
        name="participant-confirm-email",
    ),
    path("participant/<uuid:pk>/remove/", views.ParticipantRemoveView.as_view(), name="participant-remove"),
]

urlpatterns += public_urlpatterns
