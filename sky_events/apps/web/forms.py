from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class LoginForm(AuthenticationForm):
    """Custom login form — changes username widget to email type."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username_field = self.fields["username"]
        username_field.widget.attrs.update(
            {
                "type": "email",
                "autocomplete": "email",
                "placeholder": _("you@example.com"),
                "class": "form-input",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "placeholder": "••••••••••••",
                "autocomplete": "current-password",
                "class": "form-input",
                "id": "id_password",
            }
        )
