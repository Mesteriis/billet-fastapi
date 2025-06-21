"""
Notification system for critical errors.

This module provides various notification channels for alerting developers
about critical application errors and system failures.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    Base class for notification providers.

    All notification providers should inherit from this class and implement
    the send_notification method.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @abstractmethod
    async def send_notification(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: str = "error",
    ) -> bool:
        """
        Send notification to the provider.

        Args:
            title: Notification title
            message: Notification message
            context: Optional context data
            severity: Severity level (error, warning, info)

        Returns:
            True if notification was sent successfully, False otherwise
        """
        pass

    def is_enabled(self) -> bool:
        """Check if the notifier is enabled."""
        return self.enabled


class TelegramNotifier(BaseNotifier):
    """
    Telegram notification provider.

    Sends notifications to a Telegram chat using bot API.
    """

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None, enabled: bool = True):
        super().__init__(enabled)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage" if bot_token else None

    async def send_notification(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: str = "error",
    ) -> bool:
        """Send notification to Telegram chat."""
        if not self.enabled or not self.api_url or not self.chat_id:
            logger.debug("Telegram notifier is disabled or not configured")
            return False

        try:
            # Format message for Telegram
            formatted_message = self._format_telegram_message(title, message, context, severity)

            payload = {
                "chat_id": self.chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()

            logger.info("Telegram notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def _format_telegram_message(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: str = "error",
    ) -> str:
        """Format message for Telegram with Markdown."""
        emoji = {
            "error": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
            "critical": "💥",
        }.get(severity, "🔔")

        formatted = f"{emoji} *{title}*\n\n{message}"

        if context:
            formatted += "\n\n*Context:*"
            for key, value in context.items():
                if key in ["trace_id", "method", "url", "client_ip"]:
                    formatted += f"\n• *{key.replace('_', ' ').title()}:* `{value}`"

        # Limit message length for Telegram
        if len(formatted) > 4000:
            formatted = formatted[:3900] + "\n\n... *Message truncated*"

        return formatted


class EmailNotifier(BaseNotifier):
    """
    Email notification provider.

    Sends notifications via email using SMTP.
    """

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
        from_email: str | None = None,
        to_emails: list[str] | None = None,
        enabled: bool = True,
    ):
        super().__init__(enabled)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_emails = to_emails or []

    async def send_notification(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: str = "error",
    ) -> bool:
        """Send notification via email."""
        if not self.enabled or not self.smtp_host or not self.to_emails:
            logger.debug("Email notifier is disabled or not configured")
            return False

        try:
            # This is a placeholder - in production you'd use aiosmtplib or similar
            logger.info("Email notification would be sent (not implemented in example)")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class SlackNotifier(BaseNotifier):
    """
    Slack notification provider.

    Sends notifications to Slack channel using webhook.
    """

    def __init__(self, webhook_url: str | None = None, channel: str | None = None, enabled: bool = True):
        super().__init__(enabled)
        self.webhook_url = webhook_url
        self.channel = channel

    async def send_notification(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: str = "error",
    ) -> bool:
        """Send notification to Slack channel."""
        if not self.enabled or not self.webhook_url:
            logger.debug("Slack notifier is disabled or not configured")
            return False

        try:
            # Format message for Slack
            payload = self._format_slack_payload(title, message, context, severity)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()

            logger.info("Slack notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _format_slack_payload(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        severity: str = "error",
    ) -> dict[str, Any]:
        """Format payload for Slack webhook."""
        color = {
            "error": "danger",
            "warning": "warning",
            "info": "good",
            "critical": "danger",
        }.get(severity, "warning")

        payload = {
            "text": f"🚨 Application Error: {title}",
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "Application Error Monitor",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ],
        }

        if self.channel:
            payload["channel"] = self.channel

        if context:
            fields = []
            for key, value in context.items():
                if key in ["trace_id", "method", "url", "client_ip"]:
                    fields.append(
                        {
                            "title": key.replace("_", " ").title(),
                            "value": str(value),
                            "short": True,
                        }
                    )

            if fields:
                payload["attachments"][0]["fields"] = fields

        return payload


class NotificationManager:
    """
    Notification manager that handles multiple notification providers.

    Manages sending notifications through various channels and handles
    rate limiting to prevent notification spam.
    """

    def __init__(self):
        from core.config import get_settings

        self.settings = get_settings()
        self.notifiers: list[BaseNotifier] = []
        self._setup_notifiers()
        self._notification_cache: dict[str, datetime] = {}
        self._rate_limit_window = 300  # 5 minutes

    def _setup_notifiers(self):
        """Setup notification providers based on configuration."""
        # Telegram notifier
        if hasattr(self.settings, "TELEGRAM_BOT_TOKEN") and hasattr(self.settings, "TELEGRAM_CHAT_ID"):
            telegram_notifier = TelegramNotifier(
                bot_token=getattr(self.settings, "TELEGRAM_BOT_TOKEN", None),
                chat_id=getattr(self.settings, "TELEGRAM_CHAT_ID", None),
                enabled=getattr(self.settings, "TELEGRAM_NOTIFICATIONS_ENABLED", False),
            )
            self.notifiers.append(telegram_notifier)

        # Email notifier
        if hasattr(self.settings, "SMTP_HOST") and hasattr(self.settings, "NOTIFICATION_EMAILS"):
            email_notifier = EmailNotifier(
                smtp_host=getattr(self.settings, "SMTP_HOST", None),
                smtp_port=getattr(self.settings, "SMTP_PORT", 587),
                smtp_username=getattr(self.settings, "SMTP_USERNAME", None),
                smtp_password=getattr(self.settings, "SMTP_PASSWORD", None),
                from_email=getattr(self.settings, "FROM_EMAIL", None),
                to_emails=getattr(self.settings, "NOTIFICATION_EMAILS", []),
                enabled=getattr(self.settings, "EMAIL_NOTIFICATIONS_ENABLED", False),
            )
            self.notifiers.append(email_notifier)

        # Slack notifier
        if hasattr(self.settings, "SLACK_WEBHOOK_URL"):
            slack_notifier = SlackNotifier(
                webhook_url=getattr(self.settings, "SLACK_WEBHOOK_URL", None),
                channel=getattr(self.settings, "SLACK_CHANNEL", None),
                enabled=getattr(self.settings, "SLACK_NOTIFICATIONS_ENABLED", False),
            )
            self.notifiers.append(slack_notifier)

    async def notify_critical_error(
        self,
        title: str,
        message: str,
        context: dict[str, Any] | None = None,
        exception_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Send critical error notification through all configured channels.

        Args:
            title: Error title
            message: Error message
            context: Request context
            exception_data: Exception details
        """
        # Create notification key for rate limiting
        notification_key = f"{title}:{message[:50]}"

        # Check rate limiting
        if self._is_rate_limited(notification_key):
            logger.debug(f"Notification rate limited: {notification_key}")
            return

        # Mark notification as sent
        self._notification_cache[notification_key] = datetime.utcnow()

        # Combine context and exception data
        full_context = {**(context or {}), **(exception_data or {})}

        # Send notifications through all enabled channels
        tasks = []
        for notifier in self.notifiers:
            if notifier.is_enabled():
                task = notifier.send_notification(
                    title=title,
                    message=message,
                    context=full_context,
                    severity="critical",
                )
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for result in results if result is True)
            logger.info(f"Sent critical error notification through {successful}/{len(tasks)} channels")
        else:
            logger.warning("No notification channels configured or enabled")

    def _is_rate_limited(self, notification_key: str) -> bool:
        """Check if notification is rate limited."""
        if notification_key not in self._notification_cache:
            return False

        last_sent = self._notification_cache[notification_key]
        time_since_last = (datetime.utcnow() - last_sent).total_seconds()

        return time_since_last < self._rate_limit_window

    def clear_rate_limit_cache(self) -> None:
        """Clear the rate limit cache."""
        self._notification_cache.clear()
        logger.info("Notification rate limit cache cleared")
