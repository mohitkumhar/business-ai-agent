from __future__ import annotations

import hashlib
import hmac
from typing import Any, Callable

import requests
from flask import Request

from logger.logger import logger
from .base import MessageDTO, MessagingProvider


class WhatsAppProvider(MessagingProvider):
    """Implementation of WhatsApp messaging provider."""

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        app_secret: str,
        resolve_business_id_fn: Callable[[str | None], str],
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.app_secret = app_secret
        self.resolve_business_id_fn = resolve_business_id_fn

    def verify_request(self, request: Request) -> bool:
        """Verify WhatsApp signature."""
        if not self.app_secret:
            return False

        signature_header = request.headers.get("X-Hub-Signature-256")
        if not signature_header:
            return False

        raw_body = request.get_data(cache=True)
        scheme, separator, received_signature = signature_header.partition("=")
        if separator != "=" or scheme != "sha256" or not received_signature:
            return False

        expected_signature = hmac.new(
            self.app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(received_signature, expected_signature)

    def parse_messages(self, request: Request) -> list[MessageDTO]:
        """Parse WhatsApp specific payload into MessageDTOs."""
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return []

        dtos = []
        entries = data.get("entry") or []
        for entry in entries:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for msg in value.get("messages") or []:
                    from_phone = str(msg.get("from") or "").strip()
                    business_id = self.resolve_business_id_fn(from_phone)
                    msg_type = msg.get("type")
                    
                    dto_params: dict[str, Any] = {
                        "platform": "whatsapp",
                        "sender_id": from_phone,
                        "business_id": business_id,
                        "thread_id": f"wa-{from_phone}",
                        "raw_payload": msg,
                    }

                    if msg_type == "image":
                        media_id = (msg.get("image") or {}).get("id")
                        if media_id:
                            dto_params["media_id"] = media_id
                            dto_params["mime_type"] = (msg.get("image") or {}).get("mime_type") or "image/jpeg"
                    elif msg_type == "text":
                        body = ((msg.get("text") or {}).get("body") or "").strip()
                        if body:
                            dto_params["text"] = body

                    if "text" in dto_params or "media_id" in dto_params:
                        dtos.append(MessageDTO(**dto_params))
        
        return dtos

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        """Download WhatsApp media."""
        if not self.access_token:
            raise ValueError("WHATSAPP_ACCESS_TOKEN is not configured.")
        
        meta = requests.get(
            f"https://graph.facebook.com/v21.0/{media_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        meta.raise_for_status()
        meta_json = meta.json()
        media_url = meta_json.get("url")
        mime_type = meta_json.get("mime_type") or "image/jpeg"
        
        if not media_url:
            raise ValueError("Media URL missing in WhatsApp response.")
            
        blob = requests.get(
            media_url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=60,
        )
        blob.raise_for_status()
        return blob.content, mime_type

    def send_text_reply(self, recipient_id: str, text: str) -> None:
        """Send WhatsApp message."""
        if not (self.access_token and self.phone_number_id):
            logger.warning("WhatsApp send skipped; credentials not configured.")
            return

        body = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"preview_url": False, "body": text[:4096]},
        }
        
        requests.post(
            f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        ).raise_for_status()
