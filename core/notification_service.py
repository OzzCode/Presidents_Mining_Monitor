"""Notification service for sending alerts via email and webhooks."""
from __future__ import annotations
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List
import requests
from miner_config import SMTP_SERVER, SMTP_PORT, ALERT_EMAIL
from core.db import Alert, AlertRule, SessionLocal

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles sending notifications for alerts."""

    def __init__(self, smtp_server: Optional[str] = None, smtp_port: int = None,
                 smtp_user: Optional[str] = None, smtp_password: Optional[str] = None,
                 alert_email: Optional[str] = None):
        """Initialize notification service with SMTP settings."""
        self.smtp_server = smtp_server or SMTP_SERVER
        self.smtp_port = smtp_port or SMTP_PORT
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.alert_email = alert_email or ALERT_EMAIL

    def notify_alert(self, alert: Alert, rule: Optional[AlertRule] = None) -> bool:
        """
        Send notification for an alert based on rule configuration.
        Returns True if any notification was sent successfully.
        """
        success = False

        # Get rule if not provided
        if rule is None and alert.rule_id:
            session = SessionLocal()
            try:
                rule = session.query(AlertRule).filter(AlertRule.id == alert.rule_id).first()
            finally:
                session.close()

        # Send email notification
        if rule and rule.notify_email and self.alert_email:
            if self._send_email(alert, rule):
                success = True
        elif not rule and self.alert_email:
            # Manual alert without rule
            if self._send_email(alert, None):
                success = True

        # Send webhook notification
        if rule and rule.notify_webhook and rule.webhook_url:
            if self._send_webhook(alert, rule):
                success = True

        # Update alert notification status
        session = SessionLocal()
        try:
            db_alert = session.query(Alert).filter(Alert.id == alert.id).first()
            if db_alert:
                db_alert.notified_at = datetime.utcnow()
                db_alert.notification_status = 'sent' if success else 'failed'
                session.commit()
        except Exception as e:
            logger.exception("Failed to update alert notification status", exc_info=e)
        finally:
            session.close()

        return success

    def _send_email(self, alert: Alert, rule: Optional[AlertRule]) -> bool:
        """Send email notification for an alert."""
        if not self.smtp_server or not self.alert_email:
            logger.warning("Email notifications not configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self._format_email_subject(alert)
            msg['From'] = self.smtp_user or 'noreply@mining-monitor.local'
            msg['To'] = self.alert_email

            # Create HTML and plain text versions
            text_body = self._format_email_text(alert, rule)
            html_body = self._format_email_html(alert, rule)

            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                if self.smtp_port in [587, 465]:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Sent email notification for alert {alert.id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to send email for alert {alert.id}", exc_info=e)
            return False

    def _send_webhook(self, alert: Alert, rule: AlertRule) -> bool:
        """Send webhook notification for an alert."""
        try:
            payload = {
                'alert_id': alert.id,
                'miner_ip': alert.miner_ip,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'details': alert.details,
                'timestamp': alert.created_at.isoformat() if alert.created_at else None,
                'rule_name': rule.name if rule else None
            }

            response = requests.post(
                rule.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )

            response.raise_for_status()
            logger.info(f"Sent webhook notification for alert {alert.id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to send webhook for alert {alert.id}", exc_info=e)
            return False

    def _format_email_subject(self, alert: Alert) -> str:
        """Format email subject line."""
        severity_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        emoji = severity_emoji.get(alert.severity, '')
        return f"{emoji} {alert.severity.upper()}: {alert.alert_type} - {alert.miner_ip}"

    def _format_email_text(self, alert: Alert, rule: Optional[AlertRule]) -> str:
        """Format plain text email body."""
        lines = [
            "Mining Monitor Alert",
            "=" * 50,
            "",
            f"Alert ID: {alert.id}",
            f"Severity: {alert.severity.upper()}",
            f"Miner IP: {alert.miner_ip}",
            f"Alert Type: {alert.alert_type}",
            f"Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if alert.created_at else 'N/A'}",
            "",
            "Message:",
            alert.message,
            ""
        ]

        if rule:
            lines.extend([
                f"Rule: {rule.name}",
                f"Description: {rule.description or 'N/A'}",
                ""
            ])

        if alert.details:
            lines.append("Details:")
            for key, value in alert.details.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        lines.extend([
            "=" * 50,
            "This is an automated alert from Presidents Mining Monitor"
        ])

        return "\n".join(lines)

    def _format_email_html(self, alert: Alert, rule: Optional[AlertRule]) -> str:
        """Format HTML email body."""
        severity_color = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'critical': '#dc3545'
        }
        color = severity_color.get(alert.severity, '#6c757d')

        details_html = ""
        if alert.details:
            detail_rows = "".join([
                f"<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>"
                for key, value in alert.details.items()
            ])
            details_html = f"""
            <h3>Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {detail_rows}
            </table>
            """

        rule_html = ""
        if rule:
            rule_html = f"""
            <h3>Alert Rule</h3>
            <p><strong>Rule:</strong> {rule.name}</p>
            <p><strong>Description:</strong> {rule.description or 'N/A'}</p>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .alert-info {{ background-color: white; padding: 15px; border-left: 4px solid {color}; margin: 15px 0; }}
                table {{ width: 100%; margin: 10px 0; }}
                td {{ padding: 5px; }}
                .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">Mining Monitor Alert</h1>
                    <p style="margin: 5px 0 0 0;">{alert.severity.upper()} - {alert.alert_type}</p>
                </div>
                <div class="content">
                    <div class="alert-info">
                        <p><strong>Miner IP:</strong> {alert.miner_ip}</p>
                        <p><strong>Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if alert.created_at else 'N/A'}</p>
                        <p><strong>Message:</strong> {alert.message}</p>
                    </div>
                    
                    {details_html}
                    {rule_html}
                    
                    <div class="footer">
                        <p>This is an automated alert from Presidents Mining Monitor</p>
                        <p>Alert ID: {alert.id}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def send_test_email(self) -> bool:
        """Send a test email to verify configuration."""
        if not self.smtp_server or not self.alert_email:
            logger.error("SMTP not configured")
            return False

        try:
            msg = MIMEText(
                "This is a test email from Presidents Mining Monitor. Email notifications are working correctly!")
            msg['Subject'] = "Test Email - Mining Monitor"
            msg['From'] = self.smtp_user or 'noreply@mining-monitor.local'
            msg['To'] = self.alert_email

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                if self.smtp_port in [587, 465]:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info("Test email sent successfully")
            return True

        except Exception as e:
            logger.exception("Failed to send test email", exc_info=e)
            return False

    def batch_notify(self, alerts: List[Alert]) -> int:
        """
        Send notifications for multiple alerts.
        Returns count of successful notifications.
        """
        success_count = 0
        for alert in alerts:
            if self.notify_alert(alert):
                success_count += 1
        return success_count
