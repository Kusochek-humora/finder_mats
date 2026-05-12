import whisper
import subprocess
import os
import sys
import asyncio
import httpx
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import tempfile
import shutil

app = FastAPI()

# ===== НАСТРОЙКИ =====
TELEGRAM_TOKEN = "ВАШ_ТОКЕН_БОТА"
TELEGRAM_CHAT_ID = "ВАШ_CHAT_ID"
# =====================

MATY = [
    # Русский
    "блять", "блядь", "бляд", "блядина", "блядский",
    "хуй", "хуя", "хуе", "хуёв", "похуй", "нахуй", "захуй", "хуйня", "хуйло",
    "пизда", "пизды", "пизде", "пиздец", "пиздёж", "пиздить", "пиздатый",
    "ебать", "ебёт", "ебал", "ебаный", "ёбаный", "еблан", "ёб", "въебать",
    "заебал", "заебись", "наебать", "отъебись", "пиздануть",
    "сука", "суки", "сучка", "сучара",
    "мудак", "мудила", "мудачок",
    "долбоёб", "долбаёб", "долбоеб",
    "ёбнуть", "ёбнул", "въебать", "разъебать",
    "пиздануть", "пизданул",
    "шлюха", "шлюхи",
    "залупа", "залупин",
    "ёпта", "епта", "ёптвоюмать",
    "твоюмать", "твою мать",
    "пиздёнок", "пиздёныш",
    "ёбтвоюмать", "ёб твою мать",
    "курва",
    "блядство", "блядовать",
    "уёбок", "уёбище",
    "пиздобол", "пиздоболить",
    "хуесос", "хуесоска",
    "ёбаная", "ёбаный",
    "пидор", "пидорас", "пидр",
    "залупоголовый",
    "ёбнутый", "ёбнутая",
    # Казахский
    "сикти", "сиктир", "сиктір",
    "быздык", "бізды",
    "зынданай", "зындан",
    "шеше", "шешең",
    "атаң", "атасын",
    "қаңыр", "қаңырсоқ",
    "пысык", "пысыксоқ",
    "қотыр", "қотырсоқ",
]

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def find_mats_in_text(text):
    text_lower = text.lower()
    return [mat for mat in MATY if mat in text_lower]

async def send_to_telegram(file_path: str, filename: str, count: int):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    caption = f"✅ Готово! Найдено фрагментов с матами: {count}"
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            await client.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
            }, files={"document": (filename, f, "text/plain")})

def process_audio(audio_path: str, output_path: str):
    print("Загружаем модель Whisper small...")
    model = whisper.load_model("small")

    print("Транскрибируем...")
    result = model.transcribe(
        audio_path,
        language="ru",
        word_timestamps=True,
        fp16=False  # CPU-совместимо
    )

    results = []
    for segment in result["segments"]:
        text = segment["text"]
        found = find_mats_in_text(text)
        if found:
            entry = {
                "time_start": format_time(segment["start"]),
                "time_end": format_time(segment["end"]),
                "text": text.strip(),
                "maty": found
            }
            results.append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Найдено фрагментов с матами: {len(results)}\n")
        f.write("=" * 60 + "\n\n")
        for r in results:
            f.write(f"[{r['time_start']} - {r['time_end']}]\n")
            f.write(f"Маты: {', '.join(r['maty'])}\n")
            f.write(f"Текст: {r['text']}\n")
            f.write("-" * 40 + "\n")

    return len(results)

async def handle_job(audio_path: str, original_name: str):
    output_path = audio_path + "_maty.txt"
    try:
        count = await asyncio.to_thread(process_audio, audio_path, output_path)
        await send_to_telegram(output_path, "maty.txt", count)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(output_path):
            os.remove(output_path)

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()

@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(file.file, tmp)
    tmp.close()
    background_tasks.add_task(handle_job, tmp.name, file.filename)
    return JSONResponse({"status": "ok", "message": "Файл принят! Результат придёт в Telegram."})
