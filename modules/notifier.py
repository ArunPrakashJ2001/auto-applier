"""
modules/notifier.py — WhatsApp notification dispatch via Twilio.

Sends a real-time alert to your WhatsApp number when a resume PDF is ready.
"""

import os
import logging
from datetime import datetime

from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

# Twilio's WhatsApp sandbox sender number
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"


def send_whatsapp_alert(
    filename: str,
    job_data: dict,
    dry_run: bool = False,
) -> bool:
    """
    Sends a WhatsApp message via Twilio confirming a resume was generated.

    Args:
        filename:  Path to the generated PDF
        job_data:  Dict with keys: title, company
        dry_run:   If True, logs the message without sending

    Returns:
        True if sent successfully (or dry_run), False on error
    """
    timestamp = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    short_name = os.path.basename(filename)

    body = (
        f"🚀 *Resume Ready!*\n\n"
        f"📋 *Role:* {job_data['title']}\n"
        f"🏢 *Company:* {job_data['company']}\n"
        f"📄 *File:* `{short_name}`\n"
        f"🕐 *Generated:* {timestamp}\n\n"
        f"Your tailored resume has been saved locally. Good luck! 🍀"
    )

    if dry_run:
        logger.info(f"[DRY RUN] WhatsApp message (not sent):\n{body}")
        return True

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
    to_number   = os.environ.get("MY_PHONE_NUMBER")

    if not all([account_sid, auth_token, to_number]):
        logger.error(
            "Twilio credentials missing. Check TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and MY_PHONE_NUMBER in your .env file."
        )
        return False

    to_whatsapp = f"whatsapp:{to_number}"

    try:
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=body,
            to=to_whatsapp,
        )
        logger.info(
            f"WhatsApp alert sent (SID: {message.sid}) → {to_whatsapp}"
        )
        return True

    except TwilioRestException as exc:
        logger.error(f"Twilio API error: {exc}")
        return False
    except Exception as exc:
        logger.error(f"Unexpected notifier error: {exc}")
        return False
