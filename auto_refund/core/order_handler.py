from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from FunPayAPI.updater.events import NewOrderEvent

from .config import RefundConfig
from ..utils.blacklist_manager import BlacklistManager
from ..utils.notification_sender import NotificationSender

logger = logging.getLogger("FPC.AutoRefund.OrderHandler")


class OrderHandler:
    def __init__(self, cardinal: Cardinal, config: RefundConfig):
        self._cardinal = cardinal
        self._config = config
        self._blacklist_manager = BlacklistManager(cardinal)
        self._notification_sender = NotificationSender(cardinal, config)

    def process_order(self, event: NewOrderEvent) -> None:
        if not self._blacklist_manager.is_blacklisted(event.order.buyer_username):
            return

        if event.order.sum > self._config.max_price:
            return

        try:
            chat = self._cardinal.account.get_chat_by_name(event.order.buyer_username)
            if not chat:
                logger.warning(f"Chat not found for {event.order.buyer_username}")
                return

            self._cardinal.account.refund(event.order.id)
            self._cardinal.account.send_message(chat.id, self._config.blacklist_message)
            
            self._notification_sender.send_order_refund_notification(event.order.buyer_username)
            
            logger.info(f"Refunded order from blacklisted user {event.order.buyer_username}")

        except Exception as e:
            logger.error(f"Error processing order: {e}")