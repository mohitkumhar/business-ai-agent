FROM node:20-alpine AS deps

WORKDIR /app

COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app

ENV TANSTACK_START_TARGET=node-server

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=5173

COPY --from=builder /app/.output ./.output
COPY --from=builder /app/public ./public

EXPOSE 5173

CMD ["node", ".output/server/index.mjs"]
