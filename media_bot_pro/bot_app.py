import os
import uuid
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, MessageEntity
from config import BOT_TOKEN, PUBLIC_BASE_URL, MAX_TELEGRAM_MB
from database import (
    ensure_user,
    is_group_allowed,
    can_download,
    mark_download,
    force_join_enabled,
    get_force_channels,
)
from downloader import is_supported, detect_platform

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
URL_STORE = {}

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Windows/RDP startup cleanup
for file_name in os.listdir(DOWNLOAD_DIR):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Startup cleanup failed: {e}")

CHENUKA_LINK = "https://t.me/chenuxx"
ENIGMA_LINK = "https://t.me/EnigmaUnfiltered"

EMOJI_MAP = {
    "🎬": "5240241223632954241",
    "✨": "6129928945786686205",
    "🎵": "5327982530702359565",
    "👋": "5456140674028019486",
    "📱": "5334681713316479679",
    "✅": "6334482089018133987",
    "📖": "5210956306952758910",
    "📥": "5443127283898405358",
    "☘️": "6086827754970419634",
    "🇱🇰": "5911293163137406640",
    "✔️": "5933948939530145209",
    "🧨": "6086827754970419634",
    "❌": "5447644880824181073",
    "⏳": "5282843764451195532",
    "📤": "5415655814079723871",
    "🔁": "5416081784641168838",
    "1️⃣": "5305763715692377402",
    "2️⃣": "5307907239380528763",
    "3️⃣": "5305783000095537258",

    "🔥": "5323261730283863478",
    "💎": "5334681713316479679",
    "☮": "5327982530702359565",
    "🎯": "6129928945786686205",
    "🛠️": "5343984088493599366",
    "✍️": "5440539497383087970",
    "📊": "5211108619377977503",
    "🥈": "5447203607294265305",
    "😎": "5208495977886923528",
    "🥉": "5453902265922376865",
    "🔤": "5210880311801423356",
    "⚡": "6129574688294178305",
    "👑": "4956420859771225351",
    "🔖": "5222444124698853913",
    "🔗": "5271604874419647061",
    "☸": "5310278924616356636",
    "🚀": "6275939064843603913",
    "💥": "5386367538735104399",
    "📌": "5255897066621643282",
}

FOOTER_TEXT = """☘️  DᕮᐯᕮᒪOᑭᕮD ᗷY : ⏤͟͞𝕮ħęภยƙค™ 🇱🇰 ✔️
🧨 Sᕮᖇᐯᕮᖇ ᗷY : !—͟͞ΣПIGMΛ ⽰ ✔️"""

START_TEXT = f"""🔥💎☮🎯 ALL-IN-ONE Video Downloader Bot 🎯☮💎🔥

🛠️ ආයුබෝවන්📊
❌ ඔබට ඉක්මනින්ම Videos සහ Audio Download කරන්න හිතෙනවද🔤 මෙන්න ඔබට perfect solution එක 😎

━━━━━━━━━━━━━━━━━━━━
⚡️ Bot එකෙන් ඔබට පුළුවන් 📌 
✍️ TikTok Videos HD Quality 📥
🥈 YouTube Videos HD Quality 📥
🥉 Facebook Videos Easy Download 📥
👑 MP3 Audio Only Extract 📥

━━━━━━━━━━━━━━━━━━━━
🔖 භාවිතා කරන විදිහ📌
1️⃣ TikTok / YouTube / Facebook Link එකක් එවන්න 🔗
2️⃣ Video Quality එක හෝ MP3 Audio තෝරන්න ☸
3️⃣ Download වෙනතුරු රැදිසිටින්න 💥

━━━━━━━━━━━━━━━━━━━━
🚀දැන්ම Try කරන්න!
ඔබගේ Favorite Video Link එක එවන්න 📥
━━━━━━━━━━━━━━━━━━━━
{FOOTER_TEXT}
"""

JOIN_TEXT = """👋 Bot එක use කරන්න කලින් පහළ channels වලට join වෙන්න.

Join වෙලා ඉවරනම් Check Joined button එක Click කරන්න ✅ ."""


def tg_len(text):
    return len(text.encode("utf-16-le")) // 2


def make_entities(text, bold=True, links=True):
    entities = []

    if bold:
        entities.append(MessageEntity(type="bold", offset=0, length=tg_len(text)))

    if links:
        for label, url in [
            ("⏤͟͞𝕮ħęภยƙค™ ", CHENUKA_LINK),
            ("!—͟͞ΣПIGMΛ ⽰ ", ENIGMA_LINK),
        ]:
            idx = text.find(label)
            if idx != -1:
                entities.append(MessageEntity(
                    type="text_link",
                    offset=tg_len(text[:idx]),
                    length=tg_len(label),
                    url=url
                ))

    for symbol, emoji_id in EMOJI_MAP.items():
        start = 0
        while True:
            idx = text.find(symbol, start)
            if idx == -1:
                break
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=tg_len(text[:idx]),
                length=tg_len(symbol),
                custom_emoji_id=emoji_id
            ))
            start = idx + len(symbol)

    return entities


def reply_premium(msg, text, reply_markup=None, bold=True, links=False):
    return bot.reply_to(
        msg,
        text,
        entities=make_entities(text, bold=bold, links=links),
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


def send_text_premium(chat_id, text, reply_markup=None, bold=True, links=False):
    return bot.send_message(
        chat_id,
        text,
        entities=make_entities(text, bold=bold, links=links),
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


def edit_premium(chat_id, message_id, text, reply_markup=None, bold=True, links=False):
    return bot.edit_message_text(
        text,
        chat_id,
        message_id,
        entities=make_entities(text, bold=bold, links=links),
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


def format_size(size_mb):
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    return f"{size_mb:.2f} MB"


def build_caption(media_type, platform, quality, size_mb, duration=None):
    title = "✅ MP3 Downloaded Successfully" if media_type == "audio" else "✅ MP4 Downloaded Successfully"
    quality_text = "MP3 Audio" if media_type == "audio" else quality

    return f"""{title}
━━━━━━━━━━━━━━━━━━━━
🔁 Platform - {platform}
🔁 Durations - {duration or "N/A"}
🔁 Quality - {quality_text}
🔁 File Size - {format_size(size_mb)}
━━━━━━━━━━━━━━━━━━━━

{FOOTER_TEXT}"""


def force_join_markup():
    markup = InlineKeyboardMarkup()
    for ch in get_force_channels(active_only=True):
        markup.add(InlineKeyboardButton(ch["button_name"], url=ch["channel_link"]))
    markup.add(InlineKeyboardButton("✅ Check Joined", callback_data="check_join"))
    return markup


def _clean_channel_ref(ref):
    ref = (ref or "").strip()
    if ref.startswith("https://t.me/"):
        name = ref.replace("https://t.me/", "").strip("/")
        if name.startswith("+"):
            return ref
        return "@" + name.lstrip("@")
    return ref


def user_joined_all(user_id):
    if not force_join_enabled():
        return True, []

    missing = []
    for ch in get_force_channels(active_only=True):
        ref = _clean_channel_ref(ch["channel_ref"])
        try:
            member = bot.get_chat_member(ref, int(user_id))
            if member.status in ("left", "kicked"):
                missing.append(ch)
        except Exception:
            missing.append(ch)

    return len(missing) == 0, missing


def require_join_message(chat_id):
    return send_text_premium(
        chat_id,
        JOIN_TEXT,
        reply_markup=force_join_markup(),
        links=False
    )


def quality_keyboard(url):
    uid = str(uuid.uuid4())
    URL_STORE[uid] = url

    m = InlineKeyboardMarkup()
    m.row(
        InlineKeyboardButton("360p", callback_data=f"video|360|{uid}"),
        InlineKeyboardButton("480p", callback_data=f"video|480|{uid}"),
    )
    m.row(
        InlineKeyboardButton("720p", callback_data=f"video|720|{uid}"),
        InlineKeyboardButton("Best", callback_data=f"video|best|{uid}"),
    )
    m.row(InlineKeyboardButton("🎵 MP3 Audio", callback_data=f"audio|mp3|{uid}"))
    return m


@bot.message_handler(commands=["start"])
def start(msg):
    ensure_user(msg.from_user)

    ok, _ = user_joined_all(msg.from_user.id)
    if not ok:
        require_join_message(msg.chat.id)
        return

    reply_premium(msg, START_TEXT, links=True)


@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(call):
    ensure_user(call.from_user)

    ok, _ = user_joined_all(call.from_user.id)
    if ok:
        bot.answer_callback_query(call.id, "Joined verified ✅")
        edit_premium(call.message.chat.id, call.message.message_id, START_TEXT, links=True)
    else:
        bot.answer_callback_query(
            call.id,
            "තවම හැම channel එකකටම join වෙලා නැහැ ❌",
            show_alert=True
        )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def get_link(msg):
    ensure_user(msg.from_user)
    url = (msg.text or "").strip()

    # Group වල normal messages වලට bot reply නොකරන්න
    if msg.chat.type != "private" and not is_supported(url):
        return

    # Force join private chat වලට විතරයි
    if msg.chat.type == "private":
        ok, _ = user_joined_all(msg.from_user.id)
        if not ok:
            require_join_message(msg.chat.id)
            return

    # Group access check link එකක් දැම්මොත් විතරයි
    if msg.chat.type != "private" and not is_group_allowed(msg.chat.id):
        reply_premium(
            msg,
            f"⚠️ මෙම Group එකට access නැහැ.\n\nGroup ID: {msg.chat.id}"
        )
        return

    if not is_supported(url):
        reply_premium(msg, "❌ TikTok හෝ YouTube link එකක් එවන්න.")
        return

    ok, reason = can_download(msg.from_user.id)
    if not ok:
        reply_premium(msg, f"❌ Download limit ඉවරයි.\n{reason}")
        return

    reply_premium(
        msg,
        f"📥 {detect_platform(url)} Quality එක හෝ MP3 තෝරන්න:",
        reply_markup=quality_keyboard(url)
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("video|") or c.data.startswith("audio|"))
def selected(call):
    path = None
    keep_file = False
    media_type = "video"
    quality = "best"
    uid = ""

    try:
        # Force join private chat වලට විතරයි
        if call.message.chat.type == "private":
            ok, _ = user_joined_all(call.from_user.id)
            if not ok:
                bot.answer_callback_query(call.id, "Join required", show_alert=True)
                edit_premium(
                    call.message.chat.id,
                    call.message.message_id,
                    JOIN_TEXT,
                    reply_markup=force_join_markup()
                )
                return

        media_type, quality, uid = call.data.split("|", 2)
        url = URL_STORE.get(uid)

        if not url:
            bot.answer_callback_query(call.id, "Link expired")
            edit_premium(
                call.message.chat.id,
                call.message.message_id,
                "❌ Link expired. ආයෙත් link එක එවන්න."
            )
            return

        ok, reason = can_download(call.from_user.id)
        if not ok:
            edit_premium(
                call.message.chat.id,
                call.message.message_id,
                f"❌ Download limit ඉවරයි.\n{reason}"
            )
            return

        bot.answer_callback_query(call.id)

        label = "MP3 Audio" if media_type == "audio" else f"Quality: {quality}"
        edit_premium(
            call.message.chat.id,
            call.message.message_id,
            f"⏳ Download වෙමින්... {label}"
        )

        r = requests.post(
            f"{PUBLIC_BASE_URL}/api/download",
            json={
                "url": url,
                "quality": quality,
                "media_type": media_type
            },
            timeout=7200,
        )

        data = r.json()

        if not data.get("ok"):
            raise Exception(data.get("error", "Download failed"))

        path = data["path"]
        duration = data.get("duration_string") or data.get("duration") or "N/A"
        title = data.get("title") or "Downloaded File"
        size_mb = os.path.getsize(path) / (1024 * 1024)

        edit_premium(
            call.message.chat.id,
            call.message.message_id,
            f"📤 Upload වෙමින්... Size: {format_size(size_mb)}"
        )

        platform = detect_platform(url)
        caption = build_caption(media_type, platform, quality, size_mb, duration)

        if size_mb > MAX_TELEGRAM_MB:
            keep_file = True
            public_link = f"{PUBLIC_BASE_URL}/files/{os.path.basename(path)}"
            send_text_premium(
                call.message.chat.id,
                f"""✅ File ready, නමුත් Telegram upload limit එකට වඩා ලොකුයි.

🔁 Title - {title}
🔁 File Size - {format_size(size_mb)}
🔁 Download Link - {public_link}

{FOOTER_TEXT}""",
                links=True,
            )
        else:
            with open(path, "rb") as f:
                if media_type == "audio":
                    bot.send_audio(
                        call.message.chat.id,
                        f,
                        caption=caption,
                        caption_entities=make_entities(caption, bold=True, links=True),
                        timeout=7200,
                    )
                else:
                    bot.send_video(
                        call.message.chat.id,
                        f,
                        caption=caption,
                        caption_entities=make_entities(caption, bold=True, links=True),
                        supports_streaming=True,
                        timeout=7200,
                    )

        mark_download(
            call.from_user.id,
            call.message.chat.id,
            url,
            platform,
            quality if media_type == "video" else "mp3",
            "success",
        )

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        URL_STORE.pop(uid, None)

    except Exception as e:
        try:
            edit_premium(
                call.message.chat.id,
                call.message.message_id,
                f"❌ Error:\n{e}"
            )
        except Exception:
            pass

        try:
            mark_download(
                call.from_user.id,
                call.message.chat.id,
                URL_STORE.get(uid, ""),
                "Unknown",
                quality,
                "failed"
            )
        except Exception:
            pass

    finally:
        # Windows compatible auto-delete
        if path and os.path.exists(path) and not keep_file:
            try:
                os.remove(path)
                print(f"Deleted file: {path}")
            except PermissionError:
                try:
                    import time
                    time.sleep(2)
                    os.remove(path)
                    print(f"Deleted after retry: {path}")
                except Exception as e:
                    print(f"Delete retry failed: {e}")
            except Exception as e:
                print(f"Delete failed: {e}")


def run_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing")
        return

    print("Telegram bot running...")
    bot.infinity_polling(
        skip_pending=True,
        timeout=60,
        long_polling_timeout=60
    )