# WhatsApp Integration Guide

This document explains how to use and configure the WhatsApp integration for the Intelligent Business Agent (ProfitPilot).

## Overview

The WhatsApp integration allows business owners to:
1.  **Ingest Bills and Invoices**: By sending a photo of a receipt or bill to the WhatsApp number, the agent automatically extracts the data, records the transaction, and provides a financial analysis.
2.  **Query Business Data**: Ask questions like "What was my total revenue last month?" directly via WhatsApp.
3.  **Chat with AI Agent**: Interact with the same intelligent agent available on the web dashboard to get business insights.

---

## 1. Setup & Configuration

To enable WhatsApp, you need a **Meta Developer Account** and a **WhatsApp Business API** setup. 

### Environment Variables
Add the following variables to your `agent_code/.env` file:

```env
# WhatsApp Cloud API Credentials
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id

# Optional: Default business ID if the phone number isn't registered
DEFAULT_BUSINESS_ID=your-uuid-here
```

### Webhook Configuration
1.  **URL**: `https://<your-domain>/api/v1/whatsapp/webhook`
2.  **Verification**: Meta will send a GET request to verify the token. Ensure `WHATSAPP_VERIFY_TOKEN` matches what you enter in the Meta Dashboard.
3.  **Subscribed Events**: Subscribe to `messages` in the Webhooks section of your WhatsApp settings in the Meta App.

---

## 2. Features

### A. Bill Ingestion (Image Upload)
When you send an **image** of a bill/receipt:
- The system downloads the image from Meta's servers.
- It uses LLM Vision to extract: `vendor_name`, `amount`, `transaction_date`, `type` (Revenue/Expense), and `category`.
- It inserts a new record into `daily_transactions`.
- It performs a financial analysis comparing this bill to your monthly totals.
- It sends a summary and 3 actionable recommendations back to you.

### B. Natural Language Queries (Text)
When you send a **text message**:
- **"Analyze all"**: If your message starts with "analyze all", the agent will perform a comprehensive analysis of all your business data and send a report.
- **General Queries**: The agent treats text as a query. It maintains context using a thread ID based on your phone number (`wa-<phone_number>`).
- **Data Access**: The agent has access to your recent transactions and financial summaries to answer your questions accurately.

---

## 3. Database Schema

The system automatically manages two tables for WhatsApp:

1.  **`public.whatsapp_contacts`**: Links a phone number to a specific `business_id`.
2.  **`public.billing_ingestions`**: Tracks every bill processed via WhatsApp, linking the media ID to the created transaction.

---

## 4. Technical Implementation Details

- **Webhook Endpoints**: Located in `agent_code/app.py`.
    - `GET /api/v1/whatsapp/webhook`: Handles verification.
    - `POST /api/v1/whatsapp/webhook`: Handles incoming messages (text and images).
- **Core Functions**:
    - `_download_whatsapp_media(media_id)`: Fetches the image blob from Meta.
    - `_extract_bill_data_from_image(image_bytes, mime_type)`: LLM processing for images.
    - `_send_whatsapp_text(to_number, text)`: Sends replies back to the user.
    - `_resolve_business_id(phone)`: Determines which business the sender belongs to.

---

## 5. Troubleshooting

- **Check Logs**: All WhatsApp events are logged. Check the `agent_code` logs for `WhatsApp webhook failed` or `WhatsApp send skipped`.
- **Media Download Failures**: Ensure your `WHATSAPP_ACCESS_TOKEN` has the necessary permissions (`whatsapp_business_messaging`, `whatsapp_business_management`).
- **Database Connection**: Ensure the agent can connect to the PostgreSQL database to retrieve and store transaction data.
