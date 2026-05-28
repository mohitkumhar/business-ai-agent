# Use a Debian-slim Node image that ships with a real Chromium (needed by puppeteer/whatsapp-web.js)
FROM node:20-slim

# Install Chromium and its OS dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    wget \
    --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# Tell puppeteer to use the system Chromium (avoids downloading its own)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

# Auth data persisted in a named volume
VOLUME ["/app/.wwebjs_auth"]

CMD ["node", "index.js"]
