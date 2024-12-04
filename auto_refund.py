from __future__ import annotations

import json
from FunPayAPI.updater.events import types
from FunPayAPI.types import MessageTypes
from FunPayAPI.common.utils import RegularExpressions
from os.path import exists
from tg_bot import CBT
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B
import telebot
from cardinal import Cardinal
from FunPayAPI.updater.events import NewMessageEvent, NewOrderEvent
from Utils import cardinal_tools
import logging
from collections import defaultdict

logger = logging.getLogger("FPC.REFUND")
LOGGER_PREFIX = "[AUTOREFUND]"
logger.info(f"{LOGGER_PREFIX} Плагин успешно запущен.")

NAME = "Auto Refund"
VERSION = "0.0.5"
DESCRIPTION = "Данный плагин автоматически возвращает средства, если покупатель оставил плохой отзыв."
CREDITS = "@fasxw | @vsevolodezz"
UUID = "d1fa6712-6780-4d36-b7b7-e1ac2b7a9e1a"
SETTINGS_PAGE = True

SETTINGS = {
    "star_1": False,
    "star_2": False,
    "star_3": False,
    "star_4": False,
    "star_5": False,
    "max_price": 1,
    "block_user": True,
    "refund_notification": False,
    "feedback_delete": False,
    "refund_notification_chat_id": 0,
    "blacklist_message": "Вы в черном списке магазина. ❌"
}

CBT_PRICE_CHANGE = "AutoRefund_Price_Change"
CBT_PRICE_CHANGED = "AutoRefund_Price_Changed"
CBT_SWITCH = "AutoRefund_Switch"
CBT_CHANGE_TEXT = "AutoRefund_Change_Text"

REQUIRED_COLUMNS = list(SETTINGS.keys())

def init(cardinal: Cardinal):
    tg = cardinal.telegram
    bot = tg.bot

    def load_config():
        try:
            with open("storage/plugins/auto_refund.json", "r", encoding="UTF-8") as f:
                return json.loads(f.read())
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("Error: Unable to parse JSON file.")
            return {}
    
    def update_config(config):
        for column in REQUIRED_COLUMNS:
            config.setdefault(column, SETTINGS[column])
        return config

    def save_config():
        with open("storage/plugins/auto_refund.json", "w", encoding="UTF-8") as f:
            json.dump(SETTINGS, f, indent=4, ensure_ascii=False)

    config = load_config()
    if not config:
        save_config()
        config = load_config()

    updated_config = update_config(config)

    global SETTINGS
    SETTINGS.update(updated_config)
    save_config()

    def switch(call: telebot.types.CallbackQuery):
        setting_key = call.data.split(":")[1]
        if setting_key in SETTINGS:
            SETTINGS[setting_key] = not SETTINGS[setting_key]
            save_config()
            settings(call)

    def change_max_price(call: telebot.types.CallbackQuery):
        bot.answer_callback_query(call.id)

        msg = bot.send_message(call.message.chat.id, "🔰 Введите сумму до которой будет делаться возврат")
        bot.register_next_step_handler(msg, process_new_max_price)

    def process_new_max_price(message):
        try:
            new_max_price = float(message.text)
            if new_max_price < 0:
                raise ValueError("🚨 Максимальная сумма для возврата должна быть числом.")
        except ValueError:
            raise ValueError("🚨 Максимальная сумма для возврата должна быть числом.")
        
        SETTINGS["max_price"] = new_max_price
        save_config()
        keyboard = K().row(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}"))
        bot.reply_to(message, "✅ Успешно изменено!", reply_markup=keyboard)

    def change_text(call: telebot.types.CallbackQuery):
        bot.answer_callback_query(call.id)
        
        msg = bot.send_message(call.message.chat.id, "📛 Введите текст, который будет отправлен пользователю при ЧС.")
        bot.register_next_step_handler(msg, process_new_text)

    def process_new_text(message):
        new_text = message.text
        SETTINGS["blacklist_message"] = new_text

        save_config()
        tg.clear_state(message.chat.id, message.from_user.id, True)
        keyboard = K()
        keyboard.add(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}"))
        bot.reply_to(message, f"✅ Успешно изменено!", reply_markup=keyboard)

    def toggle_refund_notifications(call: telebot.types.CallbackQuery):
        SETTINGS["refund_notification"] = not SETTINGS.get("refund_notification", False)
        SETTINGS["refund_notification_chat_id"] = call.message.chat.id
        save_config()
        settings(call)

    def settings(call: telebot.types.CallbackQuery):
        logger.info(f"{LOGGER_PREFIX} Пользователь {call.from_user.username} открыл настройки плагина")

        keyboard = K()

        options = [
            ("Возврат до:", SETTINGS.get('max_price', ''), CBT_PRICE_CHANGE, False),
            ("Текст при ЧС:", SETTINGS.get('blacklist_message', '')[:5] + "...", CBT_CHANGE_TEXT, False),
            ("Добавлять в ЧС?", SETTINGS.get('block_user', False), f"{CBT_SWITCH}:block_user", True),
            ("Уведомления?", SETTINGS.get('refund_notification', False), f"{CBT_SWITCH}:refund_notification", True),
            ("ЧС при удалении отзыва?", SETTINGS.get('feedback_delete', False), f"{CBT_SWITCH}:feedback_delete", True)
        ]

        for label, setting, callback, is_toggle in options:
            state = f"{'✅' if setting else '❌'}" if is_toggle else setting
            keyboard.add(B(f"{label}: {state}", callback_data=callback))

        for i in range(1, 6):
            star_state = "🟢" if SETTINGS.get(f"star_{i}", False) else "🔴"
            keyboard.row(B(f"{'⭐' * i}", callback_data=f"{CBT_SWITCH}:star_{i}"),
                         B(star_state, callback_data=f"{CBT_SWITCH}:star_{i}"))

        keyboard.add(B("◀️ Назад", callback_data=f"{CBT.EDIT_PLUGIN}:{UUID}:0"))

        bot.edit_message_text("В данном разделе вы можете настроить плагин", call.message.chat.id, call.message.id, reply_markup=keyboard)
        bot.answer_callback_query(call.id)

    tg.cbq_handler(toggle_refund_notifications, lambda c: f"{CBT_SWITCH}:refund_notification" in c.data)
    tg.cbq_handler(settings, lambda c: f"{CBT.PLUGIN_SETTINGS}:{UUID}" in c.data)
    tg.cbq_handler(switch, lambda c: CBT_SWITCH in c.data)
    tg.cbq_handler(change_max_price, lambda c: f"{CBT_PRICE_CHANGE}" in c.data)
    tg.cbq_handler(change_text, lambda c: CBT_CHANGE_TEXT in c.data)

def message_hook(cardinal: Cardinal, event: NewMessageEvent) -> None:
    global SETTINGS

    if event.message.type not in (MessageTypes.NEW_FEEDBACK, MessageTypes.FEEDBACK_CHANGED, MessageTypes.FEEDBACK_DELETED):
        return
    if event.message.author_id == cardinal.account.id:
        return

    if event.message.type == MessageTypes.FEEDBACK_DELETED and SETTINGS["feedback_delete"]:
        order_id = RegularExpressions().ORDER_ID.findall(str(event.message))[0][1:]
        order = cardinal.account.get_order(order_id)
        if order.status == types.OrderStatuses.REFUNDED or order.sum > SETTINGS["max_price"]:
            return

        if order.buyer_username in cardinal.blacklist:
            logger.info(f"{LOGGER_PREFIX} {order.buyer_username} уже в черном списке")
        else:
            cardinal.blacklist.append(order.buyer_username)
            cardinal_tools.cache_blacklist(cardinal.blacklist)
            cardinal.account.send_message(event.message.chat_id, SETTINGS['blacklist_message'])
            if SETTINGS["refund_notification"]:
                chat_id = SETTINGS["refund_notification_chat_id"]
                cardinal.telegram.bot.send_message(chat_id, f"{LOGGER_PREFIX} {order.buyer_username} добавлен в чс")
                logger.info(f"{LOGGER_PREFIX} добавил в ЧС {order.buyer_username} и отправил уведомление")

    elif event.message.type in (MessageTypes.NEW_FEEDBACK, MessageTypes.FEEDBACK_CHANGED):
        order_id = RegularExpressions().ORDER_ID.findall(str(event.message))[0][1:]
        order = cardinal.account.get_order(order_id)
        if order.sum > SETTINGS["max_price"]:
            return

        if order.review and SETTINGS[f"star_{order.review.stars}"]:
            if order.buyer_username in cardinal.blacklist:
                cardinal.account.refund(order_id)
            else:
                cardinal.account.refund(order_id)
                cardinal.blacklist.append(order.buyer_username)
                cardinal_tools.cache_blacklist(cardinal.blacklist)
                cardinal.account.send_message(event.message.chat_id, SETTINGS['blacklist_message'])
                if SETTINGS["refund_notification"]:
                    chat_id = SETTINGS["refund_notification_chat_id"]
                    cardinal.telegram.bot.send_message(chat_id, f"{LOGGER_PREFIX} {order.buyer_username} добавлен в чс. Выполнен возврат.")
                    logger.info(f"{LOGGER_PREFIX} сделал возврат и добавил в ЧС {order.buyer_username} и отправил уведомление")

def order_hook(cardinal: Cardinal, event: NewOrderEvent) -> None:
    global SETTINGS

    if event.order.buyer_username not in cardinal.blacklist or event.order.sum > SETTINGS["max_price"]:
        return

    tg = cardinal.telegram
    chat_id = cardinal.account.get_chat_by_name(event.order.buyer_username).id
    cardinal.account.refund(event.order.id)
    cardinal.account.send_message(chat_id, SETTINGS['blacklist_message'])

    if SETTINGS.get("refund_notification", False):
        notification_chat_id = SETTINGS.get("refund_notification_chat_id")
        tg.bot.send_message(notification_chat_id, f"{LOGGER_PREFIX} Пользователь {event.order.buyer_username} попытался купить товар, он в черном списке магазина. Выполнен возврат.")
        logger.info(f"{LOGGER_PREFIX} сделал возврат так как {event.order.buyer_username} в ЧС и отправил уведомление")

BIND_TO_PRE_INIT = [init]
BIND_TO_NEW_MESSAGE = [message_hook]
BIND_TO_NEW_ORDER = [order_hook]
BIND_TO_DELETE = None