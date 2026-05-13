"""
Notification system.
Desktop push notifications, Discord webhooks, Telegram bot messages.
"""

import os
import json
import threading
from typing import Dict, Optional

import requests


class Notifier:
    """
    Sends notifications on download/queue completion.
    Supports desktop, Discord webhooks, and Telegram bot.
    """

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def notify(
        self,
        title: str,
        message: str,
        notification_type: str = "complete",
        data: Dict = None,
    ):
        """
        Send notification through all configured channels.
        notification_type: complete, error, queue_complete, info
        """
        if not self.config.get("notify_on_complete", False):
            return

        threads = []

        if self.config.get("notify_desktop", False):
            t = threading.Thread(
                target=self._desktop_notify,
                args=(title, message),
                daemon=True,
            )
            threads.append(t)

        webhook_url = self.config.get("discord_webhook_url", "")
        if webhook_url:
            t = threading.Thread(
                target=self._discord_notify,
                args=(title, message, notification_type, webhook_url),
                daemon=True,
            )
            threads.append(t)

        token = self.config.get("telegram_bot_token", "")
        chat_id = self.config.get("telegram_chat_id", "")
        if token and chat_id:
            t = threading.Thread(
                target=self._telegram_notify,
                args=(title, message, token, chat_id),
                daemon=True,
            )
            threads.append(t)

        for t in threads:
            t.start()

    def _desktop_notify(self, title: str, message: str):
        """Send desktop notification."""
        try:
            import platform
            system = platform.system()

            if system == "Darwin":
                os.system(
                    f"""osascript -e 'display notification "{message}" """
                    f"""with title "{title}"'"""
                )
            elif system == "Linux":
                os.system(f'notify-send "{title}" "{message}" 2>/dev/null')
            elif system == "Windows":
                try:
                    from plyer import notification
                    notification.notify(
                        title=title,
                        message=message,
                        app_name="Mangadeck",
                        timeout=10,
                    )
                except ImportError:
                    # Fallback: use powershell toast
                    ps_cmd = (
                        f"powershell -Command \""
                        f"[Windows.UI.Notifications.ToastNotificationManager,"
                        f" Windows.UI.Notifications, ContentType = WindowsRuntime]"
                        f" | Out-Null; "
                        f"$template = [Windows.UI.Notifications.ToastTemplateType]"
                        f"::ToastText02; "
                        f"$xml = [Windows.UI.Notifications.ToastNotificationManager]"
                        f"::GetTemplateContent($template); "
                        f"$xml.GetElementsByTagName('text')[0].AppendChild("
                        f"$xml.CreateTextNode('{title}')); "
                        f"$xml.GetElementsByTagName('text')[1].AppendChild("
                        f"$xml.CreateTextNode('{message}')); "
                        f"$toast = [Windows.UI.Notifications.ToastNotification]"
                        f"::new($xml); "
                        f"[Windows.UI.Notifications.ToastNotificationManager]"
                        f"::CreateToastNotifier('Mangadeck').Show($toast)\""
                    )
                    os.system(ps_cmd)

        except Exception as e:
            self.logger.debug(f"[Notifier] Desktop notification failed: {e}")

    def _discord_notify(
        self, title: str, message: str, notification_type: str, webhook_url: str
    ):
        """Send Discord webhook notification."""
        try:
            color_map = {
                "complete": 0x4CAF50,
                "error": 0xF44336,
                "queue_complete": 0x2196F3,
                "info": 0x9E9E9E,
            }

            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": color_map.get(notification_type, 0x9E9E9E),
                    "footer": {"text": "Mangadeck"},
                }]
            }

            resp = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )

            if resp.status_code not in (200, 204):
                self.logger.debug(
                    f"[Notifier] Discord webhook returned {resp.status_code}"
                )

        except Exception as e:
            self.logger.debug(f"[Notifier] Discord notification failed: {e}")

    def _telegram_notify(
        self, title: str, message: str, token: str, chat_id: str
    ):
        """Send Telegram bot message."""
        try:
            text = f"*{title}*\n{message}"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code != 200:
                self.logger.debug(
                    f"[Notifier] Telegram returned {resp.status_code}"
                )
        except Exception as e:
            self.logger.debug(f"[Notifier] Telegram notification failed: {e}")

    def test_discord(self, webhook_url: str = None) -> bool:
        """Test Discord webhook connection."""
        url = webhook_url or self.config.get("discord_webhook_url", "")
        if not url:
            return False
        try:
            self._discord_notify(
                "Mangadeck Test",
                "Webhook connection successful.",
                "info",
                url,
            )
            return True
        except Exception:
            return False

    def test_telegram(
        self, token: str = None, chat_id: str = None
    ) -> bool:
        """Test Telegram bot connection."""
        t = token or self.config.get("telegram_bot_token", "")
        c = chat_id or self.config.get("telegram_chat_id", "")
        if not t or not c:
            return False
        try:
            self._telegram_notify("Mangadeck Test", "Connection successful.", t, c)
            return True
        except Exception:
            return False