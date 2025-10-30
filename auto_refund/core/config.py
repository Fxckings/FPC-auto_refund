from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger("FPC.AutoRefund.Config")


@dataclass
class RefundConfig:
    star_1: bool = False
    star_2: bool = False
    star_3: bool = False
    star_4: bool = False
    star_5: bool = False
    max_price: float = 1.0
    block_user: bool = True
    refund_notification: bool = False
    feedback_delete: bool = False
    refund_notification_chat_id: int = 0
    blacklist_message: str = "Вы в черном списке магазина. ❌"
    
    _config_path: Path = field(default=Path("storage/plugins/auto_refund.json"), init=False)

    @classmethod
    def load(cls) -> RefundConfig:
        config_path = Path("storage/plugins/auto_refund.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    instance = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
                    instance._config_path = config_path
                    logger.info("Configuration loaded")
                    return instance
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        instance = cls()
        instance._config_path = config_path
        instance.save()
        return instance

    def save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def should_refund_stars(self, stars: int) -> bool:
        if not 1 <= stars <= 5:
            return False
        return getattr(self, f"star_{stars}", False)