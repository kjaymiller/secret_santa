from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse
from allauth.account.models import EmailAddress

class VerifiedEmailRequiredMixin(AccessMixin):
    """
    Mixin to ensure the user has a verified email address.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not EmailAddress.objects.filter(user=request.user, verified=True).exists():
            messages.warning(
                request,
                "You must verify your email address before performing this action."
            )
            return redirect(reverse("account"))
            
        return super().dispatch(request, *args, **kwargs)
