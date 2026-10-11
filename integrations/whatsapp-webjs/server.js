#!/usr/bin/env node
'use strict';

// Optional local bridge for the unofficial whatsapp-web.js transport.
// Default bind is loopback only. Do not expose this service to a LAN or public host.
const http = require('node:http');
const crypto = require('node:crypto');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const HOST = process.env.G_EMO_WEBJS_HOST || '127.0.0.1';
const PORT = Number(process.env.G_EMO_WEBJS_PORT || '8787');
const TOKEN = process.env.G_EMO_WHATSAPP_WEBJS_TOKEN;
const MAX_BODY = 16 * 1024;

if (!TOKEN || TOKEN.length < 24) {
  console.error('BLOCKED: set G_EMO_WHATSAPP_WEBJS_TOKEN to a random secret of at least 24 characters.');
  process.exit(2);
}
if (HOST !== '127.0.0.1' && HOST !== '::1' && process.env.G_EMO_ALLOW_REMOTE_BIND !== '1') {
  console.error('BLOCKED: non-loopback binding requires explicit G_EMO_ALLOW_REMOTE_BIND=1.');
  process.exit(2);
}

let ready = false;
const client = new Client({
  authStrategy: new LocalAuth({ clientId: 'g-emo' }),
  puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] },
});
client.on('qr', (qr) => {
  console.log('\nScan this QR using WhatsApp > Linked devices. Treat it like account access.\n');
  qrcode.generate(qr, { small: true });
});
client.on('authenticated', () => console.log('WhatsApp Web session authenticated.'));
client.on('ready', () => { ready = true; console.log('WhatsApp bridge ready.'); });
client.on('auth_failure', () => { ready = false; console.error('WhatsApp authentication failed; re-pair may be required.'); });
client.on('disconnected', () => { ready = false; console.warn('WhatsApp disconnected.'); });

function authorized(req) {
  const value = req.headers.authorization || '';
  const supplied = value.startsWith('Bearer ') ? value.slice(7) : '';
  const a = Buffer.from(supplied);
  const b = Buffer.from(TOKEN);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
function json(res, status, data) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(data));
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => {
      raw += chunk;
      if (Buffer.byteLength(raw, 'utf8') > MAX_BODY) {
        reject(new Error('BODY_TOO_LARGE'));
        req.destroy();
      }
    });
    req.on('end', () => {
      try { resolve(JSON.parse(raw || '{}')); }
      catch { reject(new Error('INVALID_JSON')); }
    });
    req.on('error', reject);
  });
}
const server = http.createServer(async (req, res) => {
  if (!authorized(req)) return json(res, 401, { status: 'UNAUTHORIZED' });
  if (req.method === 'GET' && req.url === '/health') {
    return json(res, 200, { status: ready ? 'CONNECTED' : 'PAIRING_OR_DISCONNECTED' });
  }
  if (req.method === 'POST' && req.url === '/send') {
    if (!ready) return json(res, 503, { status: 'NOT_READY' });
    let body;
    try { body = await readBody(req); }
    catch (err) { return json(res, err.message === 'BODY_TOO_LARGE' ? 413 : 400, { status: 'INVALID_REQUEST' }); }
    const phone = String(body.to || '').replace(/[^0-9]/g, '');
    const text = body.text;
    if (!phone || !/^\d{8,15}$/.test(phone) || typeof text !== 'string' || !text.trim() || text.length > 4096) {
      return json(res, 400, { status: 'INVALID_REQUEST', detail: 'to must be an international phone number without +; text must be 1..4096 characters' });
    }
    try {
      const number = await client.getNumberId(phone);
      if (!number) return json(res, 422, { status: 'RECIPIENT_NOT_FOUND' });
      const sent = await client.sendMessage(number._serialized, text);
      return json(res, 200, { status: 'SENT', message_id: sent.id && sent.id._serialized });
    } catch (err) {
      console.error('Send failed:', err && err.message ? err.message : 'unknown error');
      return json(res, 502, { status: 'SEND_FAILED' });
    }
  }
  return json(res, 404, { status: 'NOT_FOUND' });
});
server.listen(PORT, HOST, () => console.log(`G-EMO WhatsApp bridge listening on http://${HOST}:${PORT}`));
client.initialize().catch((err) => console.error('WhatsApp initialization failed:', err.message));
function shutdown() {
  server.close(() => {});
  client.destroy().catch(() => {});
  setTimeout(() => process.exit(0), 1500).unref();
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
