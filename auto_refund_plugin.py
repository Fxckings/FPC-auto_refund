from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from FunPayAPI.updater.events import NewMessageEvent, NewOrderEvent

from plugins.auto_refund.core.config import RefundConfig
from plugins.auto_refund.core.refund_processor import RefundProcessor
from plugins.auto_refund.core.order_handler import OrderHandler
from plugins.auto_refund.ui.telegram_handler import TelegramUIHandler
from plugins.auto_refund.utils.constants import PluginMetadata

logger = logging.getLogger("FPC.AutoRefund")

NAME = PluginMetadata.NAME
VERSION = PluginMetadata.VERSION
DESCRIPTION = PluginMetadata.DESCRIPTION
CREDITS = PluginMetadata.CREDITS
UUID = PluginMetadata.UUID
SETTINGS_PAGE = True


class AutoRefundPlugin:
    def __init__(self, cardinal: Cardinal):
        self._cardinal = cardinal
        self._config = RefundConfig.load()
        self._refund_processor = RefundProcessor(cardinal, self._config)
        self._order_handler = OrderHandler(cardinal, self._config)
        self._telegram_handler: Optional[TelegramUIHandler] = None
        
        logger.info("AutoRefund plugin initialized")

    def initialize_telegram(self) -> None:
        if self._cardinal.telegram:
            self._telegram_handler = TelegramUIHandler(
                bot=self._cardinal.telegram.bot,
                tg=self._cardinal.telegram,
                config=self._config,
                uuid=UUID
            )
            self._telegram_handler.register_handlers()
            logger.info("Telegram handlers registered")

    def handle_message(self, event: NewMessageEvent) -> None:
        try:
            self._refund_processor.process_feedback(event)
        except Exception as e:
            logger.error(f"Error processing feedback: {e}", exc_info=True)

    def handle_order(self, event: NewOrderEvent) -> None:
        try:
            self._order_handler.process_order(event)
        except Exception as e:
            logger.error(f"Error processing order: {e}", exc_info=True)


_plugin_instance: Optional[AutoRefundPlugin] = None


def init(cardinal: Cardinal) -> None:
    global _plugin_instance
    _plugin_instance = AutoRefundPlugin(cardinal)
    _plugin_instance.initialize_telegram()


def message_hook(cardinal: Cardinal, event: NewMessageEvent) -> None:
    if _plugin_instance:
        _plugin_instance.handle_message(event)


def order_hook(cardinal: Cardinal, event: NewOrderEvent) -> None:
    if _plugin_instance:
        _plugin_instance.handle_order(event)


BIND_TO_PRE_INIT = [init]
BIND_TO_NEW_MESSAGE = [message_hook]
BIND_TO_NEW_ORDER = [order_hook]
BIND_TO_DELETE = None