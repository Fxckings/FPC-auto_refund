from __future__ import annotations
from typing import TYPE_CHECKING, List
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from Utils import cardinal_tools

logger = logging.getLogger("FPC.AutoRefund.Blacklist")


class BlacklistManager:
    def __init__(self, cardinal: Cardinal):
        self._cardinal = cardinal

    def is_blacklisted(self, username: str) -> bool:
        return username in self._cardinal.blacklist

    def add_to_blacklist(self, username: str) -> None:
        if username in self._cardinal.blacklist:
            logger.debug(f"User {username} already in blacklist")
            return

        self._cardinal.blacklist.append(username)
        cardinal_tools.cache_blacklist(self._cardinal.blacklist)
        logger.info(f"Added {username} to blacklist")

    def remove_from_blacklist(self, username: str) -> None:
        if username not in self._cardinal.blacklist:
            return

        self._cardinal.blacklist.remove(username)
        cardinal_tools.cache_blacklist(self._cardinal.blacklist)
        logger.info(f"Removed {username} from blacklist")