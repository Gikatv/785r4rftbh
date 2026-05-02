from dotenv import load_dotenv
load_dotenv()
import os
import threading
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import uvicorn

from config import ADMIN_USERNAME, ADMIN_PASSWORD, HOST, PORT, DOWNLOAD_DIR
from database import init_db, db, stats, set_setting, get_setting
from downloader import download_media
from bot_app import run_bot, bot

init_db()
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = FastAPI(title="Media Bot Pro Admin")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-this-secret-key-chenuka")
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/files", StaticFiles(directory=DOWNLOAD_DIR), name="files")

templates = Jinja2Templates(directory="templates")


def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    ctx = context or {}
    ctx["request"] = request
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=ctx,
        status_code=status_code
    )


class DLReq(BaseModel):
    url: str
    quality: str = "best"
    media_type: str = "video"


@app.post("/api/download")
def api_download(req: DLReq):
    try:
        result = download_media(req.url, req.quality, req.media_type)
        result["path"] = os.path.abspath(result["path"])
        result["ok"] = True
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def admin_required(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return True


@app.get("/", response_class=HTMLResponse)
def home(request: Request, _: bool = Depends(admin_required)):
    con = db()
    cur = con.cursor()
    users = cur.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 8").fetchall()
    groups = cur.execute("SELECT * FROM allowed_groups ORDER BY created_at DESC LIMIT 8").fetchall()
    downloads = cur.execute("SELECT * FROM downloads ORDER BY created_at DESC LIMIT 10").fetchall()
    con.close()

    return render(request, "dashboard.html", {
        "stats": stats(),
        "users": users,
        "groups": groups,
        "downloads": downloads,
        "guest_limit": get_setting("guest_limit", "3"),
        "force_join_enabled": get_setting("force_join_enabled", "false")
    })


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "login.html", {"error": ""})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse("/", status_code=303)

    return render(
        request,
        "login.html",
        {"error": "Invalid username or password"},
        status_code=401
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.post("/settings")
def save_settings(
    guest_limit: str = Form(...),
    force_join_enabled: str = Form("false"),
    _: bool = Depends(admin_required)
):
    set_setting("guest_limit", guest_limit.strip())
    set_setting("force_join_enabled", "true" if force_join_enabled == "true" else "false")
    return RedirectResponse("/", status_code=303)


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, _: bool = Depends(admin_required)):
    con = db()
    users = con.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    con.close()
    return render(request, "users.html", {"users": users})


@app.post("/users/update")
def update_user(
    user_id: int = Form(...),
    limit_value: str = Form(...),
    _: bool = Depends(admin_required)
):
    con = db()
    con.execute("UPDATE users SET limit_value=? WHERE user_id=?", (limit_value.strip(), user_id))
    con.commit()
    con.close()
    return RedirectResponse("/users", status_code=303)


@app.post("/users/delete")
def delete_user(user_id: int = Form(...), _: bool = Depends(admin_required)):
    con = db()
    con.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    con.commit()
    con.close()
    return RedirectResponse("/users", status_code=303)


@app.get("/groups", response_class=HTMLResponse)
def groups_page(request: Request, _: bool = Depends(admin_required)):
    con = db()
    groups = con.execute("SELECT * FROM allowed_groups ORDER BY created_at DESC").fetchall()
    con.close()
    return render(request, "groups.html", {"groups": groups})


@app.post("/groups/add")
def add_group(chat_id: int = Form(...), title: str = Form(""), _: bool = Depends(admin_required)):
    con = db()
    con.execute(
        "INSERT OR REPLACE INTO allowed_groups(chat_id,title) VALUES(?,?)",
        (chat_id, title)
    )
    con.commit()
    con.close()
    return RedirectResponse("/groups", status_code=303)


@app.post("/groups/delete")
def del_group(chat_id: int = Form(...), _: bool = Depends(admin_required)):
    con = db()
    con.execute("DELETE FROM allowed_groups WHERE chat_id=?", (chat_id,))
    con.commit()
    con.close()
    return RedirectResponse("/groups", status_code=303)


@app.get("/channels", response_class=HTMLResponse)
def channels_page(request: Request, _: bool = Depends(admin_required)):
    con = db()
    channels = con.execute("SELECT * FROM force_channels ORDER BY id DESC").fetchall()
    con.close()
    return render(request, "channels.html", {
        "channels": channels,
        "force_join_enabled": get_setting("force_join_enabled", "false")
    })


@app.post("/channels/settings")
def save_channel_settings(
    force_join_enabled: str = Form("false"),
    _: bool = Depends(admin_required)
):
    set_setting("force_join_enabled", "true" if force_join_enabled == "true" else "false")
    return RedirectResponse("/channels", status_code=303)


@app.post("/channels/add")
def add_channel(
    button_name: str = Form(...),
    channel_link: str = Form(...),
    channel_ref: str = Form(...),
    _: bool = Depends(admin_required)
):
    con = db()
    con.execute(
        "INSERT INTO force_channels(button_name,channel_link,channel_ref,is_active) VALUES(?,?,?,1)",
        (button_name.strip(), channel_link.strip(), channel_ref.strip())
    )
    con.commit()
    con.close()
    return RedirectResponse("/channels", status_code=303)


@app.post("/channels/toggle")
def toggle_channel(
    channel_id: int = Form(...),
    is_active: int = Form(...),
    _: bool = Depends(admin_required)
):
    con = db()
    con.execute(
        "UPDATE force_channels SET is_active=? WHERE id=?",
        (1 if is_active else 0, channel_id)
    )
    con.commit()
    con.close()
    return RedirectResponse("/channels", status_code=303)


@app.post("/channels/delete")
def delete_channel(channel_id: int = Form(...), _: bool = Depends(admin_required)):
    con = db()
    con.execute("DELETE FROM force_channels WHERE id=?", (channel_id,))
    con.commit()
    con.close()
    return RedirectResponse("/channels", status_code=303)


@app.get("/broadcast", response_class=HTMLResponse)
def bc_page(request: Request, _: bool = Depends(admin_required)):
    con = db()
    rows = con.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT 30").fetchall()
    con.close()
    return render(request, "broadcast.html", {"rows": rows, "result": ""})


@app.post("/broadcast")
def send_bc(
    request: Request,
    message: str = Form(...),
    target: str = Form("users"),
    _: bool = Depends(admin_required)
):
    con = db()
    cur = con.cursor()

    ids = []
    if target in ["users", "all"]:
        ids += [r["user_id"] for r in cur.execute("SELECT user_id FROM users").fetchall()]
    if target in ["groups", "all"]:
        ids += [r["chat_id"] for r in cur.execute("SELECT chat_id FROM allowed_groups").fetchall()]

    sent = 0
    failed = 0

    for cid in set(ids):
        try:
            bot.send_message(cid, message, disable_web_page_preview=True)
            sent += 1
        except Exception:
            failed += 1

    cur.execute(
        "INSERT INTO broadcasts(message,sent_count,failed_count) VALUES(?,?,?)",
        (message, sent, failed)
    )
    con.commit()

    rows = cur.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT 30").fetchall()
    con.close()

    return render(
        request,
        "broadcast.html",
        {"rows": rows, "result": f"Sent: {sent} | Failed: {failed}"}
    )


if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT)
