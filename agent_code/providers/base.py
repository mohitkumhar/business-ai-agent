from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MessageDTO:
    """Normalized Data Transfer Object for messages from various platforms."""
    platform: str
    sender_id: str
    business_id: str
    thread_id: str
    text: Optional[str] = None
    media_id: Optional[str] = None
    mime_type: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None


class MessagingProvider(ABC):
    """Abstract base class for messaging platform providers (Strategy Pattern)."""

    @abstractmethod
    def verify_request(self, request: Any) -> bool:
        """Verify the authenticity of the incoming webhook request."""
        pass

    @abstractmethod
    def parse_messages(self, request: Any) -> list[MessageDTO]:
        """Parse platform-specific request payload into a list of normalized MessageDTOs."""
        pass

    @abstractmethod
    def download_media(self, media_id: str) -> tuple[bytes, str]:
        """Download media from the platform and return bytes and mime type."""
        pass

    @abstractmethod
    def send_text_reply(self, recipient_id: str, text: str) -> None:
        """Send a text reply back to the user on the specific platform."""
        pass
