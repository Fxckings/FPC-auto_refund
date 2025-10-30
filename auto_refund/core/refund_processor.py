from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from FunPayAPI.updater.events import NewMessageEvent, types
from FunPayAPI.types import MessageTypes
from FunPayAPI.common.utils import RegularExpressions

from .config import RefundConfig
from ..utils.blacklist_manager import BlacklistManager
from ..utils.notification_sender import NotificationSender

logger = logging.getLogger("FPC.AutoRefund.Processor")


class RefundProcessor:
    def __init__(self, cardinal: Cardinal, config: RefundConfig):
        self._cardinal = cardinal
        self._config = config
        self._blacklist_manager = BlacklistManager(cardinal)
        self._notification_sender = NotificationSender(cardinal, config)

    def _is_valid_message(self, event: NewMessageEvent) -> bool:
        if event.message.type not in (
            MessageTypes.NEW_FEEDBACK,
            MessageTypes.FEEDBACK_CHANGED,
            MessageTypes.FEEDBACK_DELETED
        ):
            return False
        
        if event.message.author_id == self._cardinal.account.id:
            return False
        
        return True

    def _extract_order_id(self, message_text: str) -> str:
        matches = RegularExpressions().ORDER_ID.findall(str(message_text))
        if not matches:
            raise ValueError("Order ID not found")
        return matches[0][1:]

    def _process_feedback_deleted(self, event: NewMessageEvent) -> None:
        if not self._config.feedback_delete:
            return

        try:
            order_id = self._extract_order_id(str(event.message))
            order = self._cardinal.account.get_order(order_id)
            
            if order.status == types.OrderStatuses.REFUNDED:
                return
            
            if order.sum > self._config.max_price:
                return

            if self._blacklist_manager.is_blacklisted(order.buyer_username):
                logger.info(f"User {order.buyer_username} already blacklisted")
                return

            self._blacklist_manager.add_to_blacklist(order.buyer_username)
            self._cardinal.account.send_message(
                event.message.chat_id,
                self._config.blacklist_message
            )
            self._notification_sender.send_blacklist_notification(order.buyer_username)
            
            logger.info(f"Blacklisted {order.buyer_username} for feedback deletion")

        except Exception as e:
            logger.error(f"Error processing deleted feedback: {e}")

    def _process_feedback(self, event: NewMessageEvent) -> None:
        try:
            order_id = self._extract_order_id(str(event.message))
            order = self._cardinal.account.get_order(order_id)
            
            if order.sum > self._config.max_price:
                logger.debug(f"Order sum {order.sum} exceeds max {self._config.max_price}")
                return

            if not order.review:
                return

            if not self._config.should_refund_stars(order.review.stars):
                return

            was_blacklisted = self._blacklist_manager.is_blacklisted(order.buyer_username)
            
            self._cardinal.account.refund(order_id)
            logger.info(f"Refunded order {order_id}")
            
            if not was_blacklisted:
                self._blacklist_manager.add_to_blacklist(order.buyer_username)
                self._cardinal.account.send_message(
                    event.message.chat_id,
                    self._config.blacklist_message
                )
                self._notification_sender.send_refund_notification(order.buyer_username)
                logger.info(f"Blacklisted and refunded for {order.buyer_username}")

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")

    def process_feedback(self, event: NewMessageEvent) -> None:
        if not self._is_valid_message(event):
            return

        if event.message.type == MessageTypes.FEEDBACK_DELETED:
            self._process_feedback_deleted(event)
        else:
            self._process_feedback(event)