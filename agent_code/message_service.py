from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from db_config import execute_read_query_params, get_db_connection
from llm.base_llm import base_llm
from logger.logger import logger
from query_execution import stream_agent_sse_lines
from providers.base import MessageDTO, MessagingProvider


class MessageService:
    """Platform-agnostic service for processing messages and media."""

    def __init__(self, agent_intent_count_metric: Any = None):
        self.agent_intent_count_metric = agent_intent_count_metric

    def process_message(self, provider: MessagingProvider, dto: MessageDTO) -> None:
        """Unified pipeline for processing a message from any provider."""
        try:
            if dto.media_id:
                reply = self._handle_media_message(provider, dto)
            elif dto.text:
                reply = self._handle_text_message(dto)
            else:
                return

            provider.send_text_reply(dto.sender_id, reply)
        except Exception as exc:
            logger.error(
                "Failed to process message from %s: %s",
                dto.platform,
                exc,
                exc_info=True
            )
            provider.send_text_reply(
                dto.sender_id,
                "I encountered an error while processing your request. Please try again later."
            )

    def _handle_media_message(self, provider: MessagingProvider, dto: MessageDTO) -> str:
        """Handle messages containing media (bills/invoices)."""
        if not dto.media_id:
            return "No media ID provided."

        image_bytes, mime_type = provider.download_media(dto.media_id)
        extracted = self.extract_bill_data(image_bytes, mime_type or dto.mime_type or "image/jpeg")
        normalized = self.normalize_bill_fields(extracted)
        
        tx_id = self.insert_bill_transaction(
            business_id=dto.business_id,
            platform=dto.platform,
            sender_id=dto.sender_id,
            media_id=dto.media_id,
            normalized=normalized,
            extracted=extracted,
        )
        
        analysis = self.analyze_transaction(tx_id, dto.business_id)
        
        return (
            f"Bill recorded successfully.\n"
            f"Transaction ID: {tx_id}\n"
            f"Amount: {normalized['amount']}\n"
            f"Type: {normalized['type']}\n"
            f"Category: {normalized['category']}\n\n"
            f"Analysis:\n{analysis}"
        )

    def _handle_text_message(self, dto: MessageDTO) -> str:
        """Handle plain text messages."""
        if not dto.text:
            return "No text provided."

        text = dto.text.strip()
        if text.lower().startswith("analyze all"):
            return self.analyze_business_data(dto.business_id, text)
        
        return self.run_agent_to_text(text, dto.thread_id, dto.business_id)

    def extract_bill_data(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        """Extract bill/invoice data using LLM vision."""
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"
        msgs = [
            SystemMessage(
                content=(
                    "You extract bill/invoice data. Return ONLY JSON with keys: "
                    "vendor_name, amount, transaction_date(YYYY-MM-DD), type(Revenue|Expense), "
                    "category, description, confidence(0..1)."
                )
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Extract billing details from this image."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            ),
        ]
        res = base_llm.invoke(msgs)
        text = res.content if isinstance(res.content, str) else json.dumps(res.content)
        return self._json_from_llm_text(text)

    def normalize_bill_fields(self, extracted: dict[str, Any]) -> dict[str, Any]:
        """Normalize extracted bill fields."""
        amount = extracted.get("amount")
        try:
            amount = float(amount) if amount is not None else 0.0
        except (ValueError, TypeError):
            amount = 0.0
        
        tx_date = str(extracted.get("transaction_date") or datetime.utcnow().date().isoformat())
        ttype = str(extracted.get("type") or "Expense").strip().lower()
        if ttype not in ("revenue", "expense"):
            ttype = "expense"
            
        category = str(extracted.get("category") or extracted.get("vendor_name") or "Uncategorized")
        description = str(extracted.get("description") or extracted.get("vendor_name") or "Bill ingestion")
        
        return {
            "amount": max(amount, 0.0),
            "transaction_date": tx_date,
            "type": "Revenue" if ttype == "revenue" else "Expense",
            "category": category[:100],
            "description": description,
            "vendor_name": str(extracted.get("vendor_name") or "").strip(),
            "confidence": extracted.get("confidence", None),
        }

    def insert_bill_transaction(
        self,
        business_id: str,
        platform: str,
        sender_id: str | None,
        media_id: str,
        normalized: dict[str, Any],
        extracted: dict[str, Any],
    ) -> int:
        """Insert transaction and ingestion record into database."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.daily_transactions (business_id, transaction_date, type, category, amount, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING transaction_id
                    """,
                    (
                        business_id,
                        normalized["transaction_date"],
                        normalized["type"],
                        normalized["category"],
                        normalized["amount"],
                        normalized["description"],
                    ),
                )
                tx_id = int(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO public.billing_ingestions (business_id, source, sender_phone, media_id, transaction_id, extracted_json)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (business_id, platform, sender_id, media_id, tx_id, json.dumps(extracted)),
                )
            conn.commit()
            return tx_id
        finally:
            conn.close()

    def analyze_transaction(self, transaction_id: int, business_id: str) -> str:
        """Perform financial analysis on a single transaction."""
        rows = execute_read_query_params(
            """
            SELECT transaction_id, transaction_date, type, category, amount, description
            FROM public.daily_transactions
            WHERE transaction_id = %s AND business_id = %s
            """,
            (transaction_id, business_id),
        )
        if not rows:
            return "Bill captured but transaction not found for analysis."
            
        tx = rows[0]
        month_rows = execute_read_query_params(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS month_revenue,
                COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS month_expense
            FROM public.daily_transactions
            WHERE business_id = %s
              AND date_trunc('month', transaction_date) = date_trunc('month', %s::date)
            """,
            (business_id, tx["transaction_date"]),
        )
        prompt = (
            "You are a business finance analyst. Give concise analysis for this bill and impact.\n"
            f"Transaction: {json.dumps(tx, default=str)}\n"
            f"Monthly totals: {json.dumps(month_rows[0] if month_rows else {}, default=str)}\n"
            "Return a short paragraph plus 3 bullet recommendations."
        )
        res = base_llm.invoke(prompt)
        return res.content if isinstance(res.content, str) else json.dumps(res.content)

    def analyze_business_data(self, business_id: str, user_question: str) -> str:
        """Perform broad business data analysis."""
        summary = execute_read_query_params(
            """
            SELECT
                COALESCE(SUM(CASE WHEN type='Revenue' THEN amount END), 0) AS total_revenue,
                COALESCE(SUM(CASE WHEN type='Expense' THEN amount END), 0) AS total_expense,
                COUNT(*) AS transaction_count
            FROM public.daily_transactions
            WHERE business_id = %s
            """,
            (business_id,),
        )
        recent = execute_read_query_params(
            """
            SELECT transaction_date, type, category, amount, description
            FROM public.daily_transactions
            WHERE business_id = %s
            ORDER BY transaction_date DESC, transaction_id DESC
            LIMIT 25
            """,
            (business_id,),
        )
        prompt = (
            "You are a business analyst. Answer user question based on business transaction data.\n"
            f"Question: {user_question}\n"
            f"Summary: {json.dumps(summary[0] if summary else {}, default=str)}\n"
            f"Recent transactions: {json.dumps(recent, default=str)}\n"
            "Answer clearly with actionable suggestions."
        )
        res = base_llm.invoke(prompt)
        return res.content if isinstance(res.content, str) else json.dumps(res.content)

    def run_agent_to_text(self, query: str, thread_id: str, business_id: str) -> str:
        """Execute the AI agent and collect streaming output into a final string."""
        full = []
        fallback_error = None
        
        on_intent = None
        if self.agent_intent_count_metric:
            on_intent = lambda n: self.agent_intent_count_metric.labels(n).inc()

        for line in stream_agent_sse_lines(
            query,
            thread_id,
            business_id,
            on_chain_intent=on_intent,
        ):
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload:
                continue
            try:
                evt = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if evt.get("type") == "token":
                full.append(evt.get("content", ""))
            elif evt.get("type") == "error":
                fallback_error = evt.get("error")
                
        text = "".join(full).strip()
        if text:
            return text
            
        if fallback_error:
            logger.error("Agent execution failed: %s", fallback_error)
            return f"I encountered an error while processing your request: {fallback_error}"
            
        return "I couldn't generate a response. Please try rephrasing your question."

    def _json_from_llm_text(self, text: str) -> dict[str, Any]:
        """Helper to extract JSON from LLM response text."""
        text = (text or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    return {}
        return {}
