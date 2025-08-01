import os
import smtplib
import time
import logging
from email.mime.text import MIMEText
from config import SMTP_SERVER, SMTP_PORT, ALERT_EMAIL

# Retry configuration
RETRY_COUNT = int(os.getenv('ALERT_RETRY_COUNT', 3))
RETRY_DELAY = float(os.getenv('ALERT_RETRY_DELAY', 5))  # seconds


def send_email_alert(subject: str, message: str, recipient: str = ALERT_EMAIL):
    """
    Send an email alert with retries on failure.
    """
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = ALERT_EMAIL
    msg['To'] = recipient

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                # Uncomment and configure if your SMTP requires authentication:
                # server.login(SMTP_USER, SMTP_PASSWORD)
                server.starttls()
                server.send_message(msg)
            logging.info(f"Alert sent to {recipient} (attempt {attempt})")
            break
        except Exception as e:
            logging.error(f"Attempt {attempt} failed to send email alert: {e}")
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"All {RETRY_COUNT} attempts to send email alert failed.")
