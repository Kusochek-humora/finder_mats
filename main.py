import os
import tempfile
import shutil
import asyncio
import httpx
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI

app = FastAPI()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

MATY = [
    "блять", "блядь", "бляд", "блядина", "блядский",
    "хуй", "хуя", "хуе", "хуёв", "похуй", "нахуй", "захуй", "хуйня", "хуйло",
    "пизда", "пизды", "пизде", "пиздец", "пиздёж", "пиздить", "пиздатый",
    "ебать", "ебёт", "ебал", "ебаный", "ёбаный", "еблан", "ёб", "въебать",
    "заебал", "заебись", "наебать", "отъебись", "пиздануть",
    "сука", "суки", "сучка", "сучара",
    "мудак", "мудила", "мудачок",
    "долбоёб", "долбаёб", "долбоеб",
    "ёбнуть", "ёбнул", "разъебать",
    "пизданул", "шлюха", "шлюхи",
    "залупа", "залупин",
    "ёпта", "епта", "твою мать",
    "курва", "блядство", "блядовать",
    "уёбок", "уёбище",
    "пиздобол", "хуесос", "хуесоска",
    "ёбаная", "ёбаный",
    "пидор", "пидорас", "пидр",
    "ёбнутый", "ёбнутая",
    "сикти", "сиктир", "сиктір",
    "быздык", "зынданай", "зындан",
    "қаңыр", "қаңырсоқ",
    "қотыр", "қотырсоқ",
]

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def find_mats(text):
    return [m for m in MATY if m in text.lower()]

def process_audio(audio_path: str) -> list:
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    results = []
    for segment in response.segments:
        text = segment.text
        found = find_mats(text)
        if found:
            results.append({
                "time_start": format_time(segment.start),
                "time_end": format_time(segment.end),
                "text": text.strip(),
                "maty": found
            })
    return results

async def send_telegram(results: list, filename: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    if not results:
        text = f"✅ Файл *{filename}*\nМаты не найдены 🎉"
    else:
        lines = [f"🔴 Файл *{filename}* — найдено фрагментов: {len(results)}\n"]
        for r in results:
            lines.append(f"[{r['time_start']} — {r['time_end']}]")
            lines.append(f"_{r['text']}_")
            lines.append(f"⚠️ {', '.join(r['maty'])}\n")
        text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text[:4096],
            "parse_mode": "Markdown"
        })

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(file.file, tmp)
    tmp.close()
    try:
        results = await asyncio.to_thread(process_audio, tmp.name)
        await send_telegram(results, file.filename)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        os.remove(tmp.name)
    return JSONResponse({"results": results})
