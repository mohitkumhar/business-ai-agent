from __future__ import annotations

import hmac
from typing import Any, Callable

import requests
from flask import Request

from logger.logger import logger
from .base import MessageDTO, MessagingProvider


class TelegramProvider(MessagingProvider):
    """Implementation of Telegram messaging provider."""

    def __init__(
        self,
        bot_token: str,
        webhook_secret: str,
        resolve_business_id_fn: Callable[[str | None], str],
    ):
        self.bot_token = bot_token
        self.webhook_secret = webhook_secret
        self.resolve_business_id_fn = resolve_business_id_fn

    def verify_request(self, request: Request) -> bool:
        """Verify Telegram webhook secret token."""
        if not self.webhook_secret:
            return True # Not configured, skip check (as per existing logic)

        supplied_secret = (
            request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
        ).strip()
        
        return hmac.compare_digest(supplied_secret, self.webhook_secret)

    def parse_messages(self, request: Request) -> list[MessageDTO]:
        """Parse Telegram specific payload into MessageDTOs."""
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return []

        msg = data.get("message") or data.get("edited_message") or {}
        if not msg:
            return []

        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return []

        sender_id = str(chat_id)
        business_id = self.resolve_business_id_fn(None) # Telegram usually doesn't have phone-to-business map in current logic
        
        dtos = []
        photos = msg.get("photo") or []
        caption = (msg.get("caption") or "").strip()
        text = (msg.get("text") or "").strip()

        dto_params: dict[str, Any] = {
            "platform": "telegram",
            "sender_id": sender_id,
            "business_id": business_id,
            "thread_id": f"tg-{sender_id}",
            "raw_payload": msg,
        }

        if photos:
            largest = max(photos, key=lambda p: p.get("file_size", 0))
            file_id = largest.get("file_id")
            if file_id:
                dto_params["media_id"] = file_id
                dto_params["mime_type"] = "image/jpeg"
                if caption:
                    dto_params["text"] = caption
        elif text:
            dto_params["text"] = text

        if "text" in dto_params or "media_id" in dto_params:
            dtos.append(MessageDTO(**dto_params))
            
        return dtos

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        """Download Telegram file."""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
            
        meta = requests.get(
            f"https://api.telegram.org/bot{self.bot_token}/getFile",
            params={"file_id": media_id},
            timeout=30,
        )
        meta.raise_for_status()
        info = meta.json().get("result") or {}
        file_path = info.get("file_path")
        
        if not file_path:
            raise ValueError("Telegram getFile missing file_path.")
            
        url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        blob = requests.get(url, timeout=60)
        blob.raise_for_status()
        return blob.content, "image/jpeg"

    def send_text_reply(self, recipient_id: str, text: str) -> None:
        """Send Telegram message."""
        if not self.bot_token:
            logger.warning("Telegram send skipped; TELEGRAM_BOT_TOKEN not configured.")
            return
            
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": int(recipient_id), "text": text[:4096]},
                timeout=30,
            ).raise_for_status()
        except Exception as exc:
            logger.error("Failed to send Telegram message: %s", exc, exc_info=True)
