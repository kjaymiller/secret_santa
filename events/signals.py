from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists when saving user (in case it was missed)
    if not hasattr(instance, "profile"):
        UserProfile.objects.create(user=instance)
    # No need to save profile if user is saved, unless we want to sync something
    # instance.profile.save() 
