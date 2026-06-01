import logging
import smtplib
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)


def notify_rate_limit_breach(ip, endpoint, method):
    """Log the breach and send an email alert in a background thread."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    logger.warning(
        "RATE_LIMIT_BREACH | ip=%s | endpoint=%s %s | time=%s",
        ip, method, endpoint, timestamp
    )

    threading.Thread(
        target=_send_alert_email,
        args=(ip, endpoint, method, timestamp),
        daemon=True
    ).start()


def _send_alert_email(ip, endpoint, method, timestamp):
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    admin_email = os.environ.get('ADMIN_EMAIL')

    if not all([smtp_host, smtp_user, smtp_password, admin_email]):
        logger.warning("SMTP not configured — security alert email not sent")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = admin_email
        msg['Subject'] = "[SolutionManager] Security Alert: Rate Limit Exceeded"

        body = (
            f"Security Alert — Rate Limit Exceeded\n\n"
            f"IP Address : {ip}\n"
            f"Endpoint   : {method} {endpoint}\n"
            f"Time (UTC) : {timestamp}\n\n"
            f"This IP exceeded the allowed request rate for the above endpoint.\n"
            f"Review Railway logs for the full request history."
        )
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, admin_email, msg.as_string())

        logger.info("Security alert email sent to %s", admin_email)
    except Exception as e:
        logger.error("Failed to send security alert email: %s", e)
