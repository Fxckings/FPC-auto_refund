from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from ..core.config import RefundConfig

logger = logging.getLogger("FPC.AutoRefund.Notifications")


class NotificationSender:
    def __init__(self, cardinal: Cardinal, config: RefundConfig):
        self._cardinal = cardinal
        self._config = config

    def _send_telegram_notification(self, message: str) -> None:
        if not self._config.refund_notification:
            return

        chat_id = self._config.refund_notification_chat_id
        if chat_id == 0:
            logger.warning("Notification chat_id not configured")
            return

        try:
            self._cardinal.telegram.bot.send_message(chat_id, message)
            logger.debug(f"Notification sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def send_blacklist_notification(self, username: str) -> None:
        message = f"[AutoRefund] Пользователь {username} добавлен в ЧС"
        self._send_telegram_notification(message)

    def send_refund_notification(self, username: str) -> None:
        message = f"[AutoRefund]\n<b>Возврат выполнен.</b>\n<i>Пользователь {username} добавлен в ЧС</i>"
        self._send_telegram_notification(message)

    def send_order_refund_notification(self, username: str) -> None:
        message = (
            f"[AutoRefund] Пользователь {username} из ЧС попытался оформить заказ. "
            "Выполнен автоматический возврат"
        )
        self._send_telegram_notification(message)