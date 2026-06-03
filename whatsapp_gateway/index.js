'use strict';

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const axios = require('axios');
const qrcode = require('qrcode-terminal');

// ── Config ────────────────────────────────────────────────────────────────────
const BACKEND_URL = (process.env.BACKEND_URL || 'http://backend:5000').replace(/\/$/, '');
const MY_NUMBER   = process.env.MY_WHATSAPP_NUMBER || ''; // E.164 without '+'
const PROCESS_URL = `${BACKEND_URL}/api/v1/whatsapp-personal/process`;

console.log(`[gateway] Backend  : ${BACKEND_URL}`);
console.log(`[gateway] My number: ${MY_NUMBER || 'not configured'}`);

// ── WhatsApp client ───────────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: '/app/.wwebjs_auth' }),
  puppeteer: {
    headless: true,
    args: [
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--no-first-run',
      '--no-zygote',
      '--single-process',
      '--disable-gpu',
    ],
  },
});

// ── Events ────────────────────────────────────────────────────────────────────
client.on('qr', (qr) => {
  console.log('\n[gateway] ── Scan this QR code with your WhatsApp ──\n');
  qrcode.generate(qr, { small: true });
  console.log('\n[gateway] QR code printed above. Open WhatsApp → Linked Devices → Link a Device.\n');
});

client.on('authenticated', () => console.log('[gateway] Authenticated ✓'));
client.on('auth_failure', (msg) => console.error('[gateway] Auth failure:', msg));
client.on('ready', () => console.log('[gateway] WhatsApp Personal Gateway is READY 🚀'));
client.on('disconnected', (reason) => console.warn('[gateway] Disconnected:', reason));

client.on('message', async (msg) => {
  // ── Guard: only respond to messages received by our number ──────────────
  if (msg.fromMe) return;            // ignore echoes of our own sends
  if (msg.isStatus) return;          // ignore status updates
  if (msg.isGroupMsg) return;        // optional: skip group messages

  const from = msg.from;                         // e.g. "919876543210@c.us"
  const fromNumber = from.replace('@c.us', '');  // strip suffix

  console.log(`[gateway] ← Message from ${fromNumber}: ${msg.body?.slice(0, 80)}`);

  try {
    let payload;

    if (msg.hasMedia) {
      // ── Image / document bill ──────────────────────────────────────────
      const media = await msg.downloadMedia();
      payload = {
        from_number : fromNumber,
        type        : 'image',
        media_base64: media.data,        // already base64
        mime_type   : media.mimetype,
        body        : msg.body || '',
      };
    } else {
      // ── Plain text ─────────────────────────────────────────────────────
      payload = {
        from_number: fromNumber,
        type       : 'text',
        body       : msg.body || '',
      };
    }

    const res = await axios.post(PROCESS_URL, payload, {
      timeout: 180_000,   // 3 min – agent can be slow
      headers: { 'Content-Type': 'application/json' },
    });

    const reply = (res.data?.reply || '').trim();
    if (reply) {
      // WhatsApp message limit is ~65 k chars; keep well within it
      await msg.reply(reply.slice(0, 4096));
      console.log(`[gateway] → Replied to ${fromNumber}`);
    }
  } catch (err) {
    const detail = err.response?.data || err.message;
    console.error(`[gateway] Error processing message from ${fromNumber}:`, detail);
    await msg.reply('⚠️ Sorry, I hit an error processing your request. Please try again.');
  }
});

// ── Boot ──────────────────────────────────────────────────────────────────────
console.log('[gateway] Initialising WhatsApp client …');
client.initialize().catch((err) => {
  console.error('[gateway] Fatal init error:', err);
  process.exit(1);
});
