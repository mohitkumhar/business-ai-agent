# Telegram Integration Guide

This document explains how to use and configure the Telegram integration for the Intelligent Business Agent (ProfitPilot).

## Overview

Just like the WhatsApp integration, the Telegram integration allows you to:
1.  **Extract Bill Data from Photos**: Send a photo of a receipt or invoice to your Telegram bot, and it will be processed automatically.
2.  **Query Business Stats**: Chat with the AI agent to get insights into your revenue, expenses, and overall business health.

---

## 1. Setup & Configuration

### Step 1: Create a Telegram Bot
1.  Open Telegram and search for [@BotFather](https://t.me/botfather).
2.  Send `/newbot` and follow the instructions to get your **Bot API Token**.

### Step 2: Configure Environment Variables
Add your token to the `agent_code/.env` file:

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_bot_api_token_here
```

### Step 3: Set Up the Webhook
You need to tell Telegram where to send messages. Run the following command in your terminal (replace `<your-domain>` and `<your-token>`):

```bash
curl -X POST "https://api.telegram.org/bot<your-token>/setWebhook?url=https://<your-domain>/api/v1/telegram/webhook"
```

---

## 2. Main Features

### A. Automatic Bill Processing
Send an **image** of any bill or receipt to the bot:
- The agent downloads the image using the Telegram File API.
- It extracts financial data (Vendor, Amount, Date, Category).
- It records the transaction in your database and replies with a summary and AI-driven financial analysis.

### B. Business Agent Chat
Send a **text message** to the bot:
- **"Analyze all"**: Triggers a full business data analysis report.
- **Natural Language Queries**: Ask anything like *"Show me my top expenses this month"* or *"How is my profit trending?"*.
- The bot maintains conversation history using a thread ID based on your Telegram `chat_id` (`tg-<id>`).

---

## 3. Technical Implementation Details

- **Webhook Endpoint**: `POST /api/v1/telegram/webhook` in `agent_code/app.py`.
- **Core Functions**:
    - `_download_telegram_file(file_id)`: Uses `getFile` and the file path to fetch image blobs from Telegram servers.
    - `_send_telegram_text(chat_id, text)`: Sends asynchronous replies back to your Telegram chat.
    - `_resolve_business_id(None)`: Links the Telegram interaction to your default business profile.

---

## 4. Troubleshooting

- **Check logs**: Look for `Telegram webhook failed` or `Telegram send skipped` in the `agent_code` logs.
- **Bot not responding?**: Ensure your server is accessible from the internet and the webhook URL is correctly registered with Telegram.
- **Token Issues**: Double-check that `TELEGRAM_BOT_TOKEN` in your `.env` file is correct and the server has been restarted.
