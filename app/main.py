from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, os, io, base64
import qrcode

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_DIR, "data")
SUBMIT_DIR = os.path.join(DATA_DIR, "submissions")
os.makedirs(SUBMIT_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "config.json"), "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

with open(os.path.join(DATA_DIR, "stories.json"), "r", encoding="utf-8") as f:
    STORIES = json.load(f)

app = FastAPI(title="Рука помощи — MVP")
app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

def gen_qr_data_url(text: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

@app.middleware("http")
async def add_config_to_request(request: Request, call_next):
    response = await call_next(request)
    return response

def urlencode(value: str | None) -> str:
    from urllib.parse import quote
    return quote(value or "")

templates.env.filters["urlencode"] = urlencode

def get_story_by_id(story_id: str):
    for s in STORIES:
        if s["id"] == story_id:
            return s
    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "stories": STORIES, "config": CONFIG})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request, "config": CONFIG})

@app.get("/stories", response_class=HTMLResponse)
async def stories(request: Request):
    return templates.TemplateResponse("stories.html", {"request": request, "stories": STORIES, "config": CONFIG})

@app.get("/stories/{story_id}", response_class=HTMLResponse)
async def story(request: Request, story_id: str):
    s = get_story_by_id(story_id)
    if not s:
        return templates.TemplateResponse("404.html", {"request": request, "config": CONFIG}, status_code=404)
    return templates.TemplateResponse("story.html", {"request": request, "story": s, "config": CONFIG})

@app.get("/donate", response_class=HTMLResponse)
async def donate(request: Request, purpose: str | None = None):
    # Сформируем строку для QR (СБП/перевод по реквизитам — как текст-подсказка)
    bank = CONFIG.get("bank", {})
    lines = [
        f"Получатель: {bank.get('beneficiary', '')}",
        f"ИНН: {bank.get('inn', '')}",
        f"Счёт: {bank.get('account', '')}",
        f"Банк: {bank.get('bank_name', '')}",
        f"БИК: {bank.get('bik', '')}",
        f"Назначение: {purpose or bank.get('purpose', '')}",
    ]
    qr_text = "\n".join(lines)
    qr_data_url = gen_qr_data_url(qr_text)
    return templates.TemplateResponse("donate.html", {"request": request, "config": CONFIG, "qr_data_url": qr_data_url, "purpose": purpose})

@app.get("/contacts", response_class=HTMLResponse)
async def contacts_get(request: Request):
    return templates.TemplateResponse("contacts.html", {"request": request, "config": CONFIG, "submitted": False})

@app.post("/contacts", response_class=HTMLResponse)
async def contacts_post(request: Request, name: str = Form(...), contact: str = Form(...), message: str = Form(...)):
    # Сохраняем локально как JSON (можно расширить отправкой на email/Google Sheets)
    import time, re
    item = {"ts": int(time.time()), "name": name, "contact": contact, "message": message}
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)[:40] or "user"
    filename = os.path.join(SUBMIT_DIR, f"{int(time.time())}_{safe_name}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)
    return templates.TemplateResponse("contacts.html", {"request": request, "config": CONFIG, "submitted": True})

@app.get("/documents", response_class=HTMLResponse)
async def documents(request: Request):
    return templates.TemplateResponse("documents.html", {"request": request, "config": CONFIG})

@app.get("/policy", response_class=HTMLResponse)
async def policy(request: Request):
    return templates.TemplateResponse("policy.html", {"request": request, "config": CONFIG})

@app.get("/offer", response_class=HTMLResponse)
async def offer(request: Request):
    return templates.TemplateResponse("offer.html", {"request": request, "config": CONFIG})
