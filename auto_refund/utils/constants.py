from dataclasses import dataclass


@dataclass(frozen=True)
class PluginMetadata:
    NAME: str = "Auto Refund"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Автоматический возврат средств при негативных отзывах.\n\n"
        "Возможности:\n"
        "- Автовозврат по оценкам (1-5 звезд)\n"
        "- Добавление в черный список\n"
        "- Возврат при удалении отзыва\n"
        "- Telegram уведомления\n"
        "- Настройка максимальной суммы возврата\n\n"
        "v1.0.0 - Полный рефакторинг спустя 10 месяцев"
    )
    CREDITS: str = "@useanasha | @prince4scale | @vsevolodezz"
    UUID: str = "d1fa6712-6780-4d36-b7b7-e1ac2b7a9e1a"


@dataclass(frozen=True)
class UIConstants:
    CHECK_MARK: str = "✅"
    CROSS_MARK: str = "❌"


@dataclass(frozen=True)
class CallbackData:
    PRICE_CHANGE: str = "AR_PRICE_CHANGE"
    TEXT_CHANGE: str = "AR_TEXT_CHANGE"
    SWITCH: str = "AR_SWITCH"