# Video Watermark Bot Backend (Replit)

Flask + ffmpeg untuk memproses video Telegram dengan watermark.
Dipanggil dari Cloudflare Worker melalui endpoint `/job`.

## ENV (Secrets)
- BOT_TOKEN: token bot Telegram
- API_KEY: kunci acak untuk header `x-api-key`

## Jalankan di Replit
- Klik Run, tunggu URL publik muncul.
- Endpoint job: `POST <PUBLIC_URL>/job` (JSON body sesuai Worker).
