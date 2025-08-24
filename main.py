import os, subprocess, requests, tempfile, pathlib
from flask import Flask, request, jsonify

# ==== ENV ====
TELEGRAM_TOKEN = os.environ["BOT_TOKEN"]   # set di Replit Secrets
API_KEY       = os.environ["API_KEY"]      # kunci antara Worker <-> Replit

app = Flask(__name__)

DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# --- helpers ---
def tg_api(method, payload=None, files=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    if files:
        return requests.post(url, data=payload, files=files, timeout=None).json()
    return requests.post(url, json=payload, timeout=None).json()

def get_file_url(file_id):
    info = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
        params={"file_id": file_id}, timeout=30
    ).json()
    path = info["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{path}"

def ratio_target(ratio: str):
    # target canvas (boleh diubah)
    return {
        "9:16": (1080, 1920),
        "1:1":  (1080, 1080),
        "16:9": (1920, 1080),
    }.get(ratio, (1080, 1920))

@app.get("/")
def health():
    return "OK"

@app.post("/job")
def job():
    # auth sederhana
    if request.headers.get("x-api-key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True)
    chat_id = data["chat_id"]
    file_id = data["file_id"]
    title   = data.get("title", "")
    code    = data.get("code", "")
    ratio   = data.get("ratio", "9:16")
    wm_text = data.get("wm_text", "@your_watermark")

    # info start
    tg_api("sendMessage", {"chat_id": chat_id, "text": "⏳ Sedang proses watermark..."})

    # unduh file dari Telegram
    src = get_file_url(file_id)

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        inp = td / "input.mp4"
        out = td / "output.mp4"

        with requests.get(src, stream=True, timeout=None) as r:
            r.raise_for_status()
            with open(inp, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)

        # filter video
        W, H = ratio_target(ratio)
        vf_parts = [
            # fit + pad ke canvas target
            f"scale='if(gt(a,{W}/{H}),{W},-2)':'if(gt(a,{W}/{H}),-2,{H})'",
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
        ]

        # watermark teks di dekat bawah tengah
        draw = (
            f"drawtext=text='{wm_text}':"
            f"fontcolor=white@0.85:borderw=2:bordercolor=black@0.6:"
            f"fontsize=48:x=(w-text_w)/2:y=(h-text_h)-60"
        )
        if os.path.exists(DEFAULT_FONT):
            draw += f":fontfile='{DEFAULT_FONT}'"
        vf_parts.append(draw)

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg","-y","-i", str(inp),
            "-vf", vf,
            "-c:v","libx264","-preset","veryfast","-crf","23",
            "-c:a","aac","-b:a","128k",
            str(out)
        ]
        subprocess.run(cmd, check=True)

        caption = f"Selesai ✅ ({ratio})\nKode: {code}\nJudul: {title}"
        with open(out, "rb") as vid:
            tg_api("sendVideo",
                   payload={"chat_id": chat_id, "caption": caption},
                   files={"video": vid})

    return jsonify({"ok": True})

if __name__ == "__main__":
    # untuk run lokal (tidak dipakai di Replit)
    app.run(host="0.0.0.0", port=8000)
