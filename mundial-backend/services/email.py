import logging
import os

import resend


logger = logging.getLogger(__name__)


# default sender uses resend's sandbox domain — works out of the box but only
# delivers to your own account email until a real domain is verified.
# set EMAIL_FROM in .env to a verified-domain address for production.
_DEFAULT_FROM = "Mundial Typer <onboarding@resend.dev>"


def _send(to: str, subject: str, html: str) -> None:
    # core sender. no-op when RESEND_API_KEY is missing so tests and local
    # dev run without hitting the network (same pattern as the poll job)
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.info("RESEND_API_KEY not set — skipping email to %s", to)
        return

    resend.api_key = api_key
    sender = os.getenv("EMAIL_FROM", _DEFAULT_FROM)
    resend.Emails.send({
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html,
    })
    logger.info("sent email '%s' to %s", subject, to)


def _frontend_url() -> str:
    # base URL used to build links in emails
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def send_verification_email(to: str, token: str) -> None:
    # link the user clicks to confirm their account after registering
    link = f"{_frontend_url()}/verify-email?token={token}"
    html = (
        "<h2>Witaj w Mundial Typer!</h2>"
        "<p>Potwierdź swój adres email klikając w link poniżej:</p>"
        f'<p><a href="{link}">Potwierdź konto</a></p>'
        "<p>Jeśli to nie Ty zakładałeś konto, zignoruj tę wiadomość.</p>"
    )
    _send(to, "Potwierdź konto w Mundial Typer", html)


def send_password_reset_email(to: str, token: str) -> None:
    # link to the reset form. token is valid for 1 hour (enforced server-side)
    link = f"{_frontend_url()}/reset-password?token={token}"
    html = (
        "<h2>Reset hasła</h2>"
        "<p>Kliknij w link poniżej aby ustawić nowe hasło:</p>"
        f'<p><a href="{link}">Zresetuj hasło</a></p>'
        "<p>Link jest ważny przez 1 godzinę. Jeśli to nie Ty prosiłeś o reset, "
        "zignoruj tę wiadomość.</p>"
    )
    _send(to, "Reset hasła — Mundial Typer", html)
