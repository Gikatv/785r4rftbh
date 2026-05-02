import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH

# ---------- TIMEZONE (UTC +5:30) ----------
def now_sl():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def today():
    return now_sl().date().isoformat()

# ---------- DB CONNECT ----------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

# ---------- INIT ----------
def init_db():
    con = db()
    cur = con.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        limit_value TEXT DEFAULT '50',
        downloads_today INTEGER DEFAULT 0,
        total_downloads INTEGER DEFAULT 0,
        last_reset TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS allowed_groups (
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS force_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        button_name TEXT NOT NULL,
        channel_link TEXT NOT NULL,
        channel_ref TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        url TEXT,
        platform TEXT,
        quality TEXT,
        status TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        sent_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    INSERT OR IGNORE INTO settings(key,value) VALUES('guest_limit','3');
    INSERT OR IGNORE INTO settings(key,value) VALUES('force_join_enabled','false');
    ''')
    con.commit()
    con.close()

# ---------- USER ----------
def ensure_user(user):
    con = db(); cur = con.cursor()
    uid = int(user.id)

    cur.execute('SELECT * FROM users WHERE user_id=?', (uid,))
    row = cur.fetchone()

    if not row:
        cur.execute('''INSERT INTO users(user_id, username, first_name, last_reset)
                       VALUES(?,?,?,?)''',
                    (uid, user.username or '', user.first_name or '', today()))
    else:
        cur.execute('UPDATE users SET username=?, first_name=? WHERE user_id=?',
                    (user.username or '', user.first_name or '', uid))

    con.commit(); con.close()

# ---------- SETTINGS ----------
def get_setting(key, default=''):
    con = db(); cur = con.cursor()
    cur.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = cur.fetchone()
    con.close()
    return row['value'] if row else default

def set_setting(key, value):
    con = db(); cur = con.cursor()
    cur.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                (key, str(value)))
    con.commit(); con.close()

def force_join_enabled():
    return get_setting('force_join_enabled', 'false').strip().lower() in ('true', '1', 'yes', 'on')

# ---------- CHANNELS ----------
def get_force_channels(active_only=True):
    con = db(); cur = con.cursor()
    if active_only:
        rows = cur.execute('SELECT * FROM force_channels WHERE is_active=1 ORDER BY id DESC').fetchall()
    else:
        rows = cur.execute('SELECT * FROM force_channels ORDER BY id DESC').fetchall()
    con.close()
    return rows

def is_group_allowed(chat_id):
    if chat_id > 0:
        return True
    con = db(); cur = con.cursor()
    cur.execute('SELECT chat_id FROM allowed_groups WHERE chat_id=?', (int(chat_id),))
    ok = cur.fetchone() is not None
    con.close()
    return ok

# ---------- DOWNLOAD LIMIT ----------
def can_download(user_id):
    con = db(); cur = con.cursor()

    cur.execute('SELECT * FROM users WHERE user_id=?', (int(user_id),))
    row = cur.fetchone()

    if not row:
        con.close()
        return False, 'User not registered.'

    # 🔥 DAILY RESET FIXED WITH TIMEZONE
    if row['last_reset'] != today():
        cur.execute('UPDATE users SET downloads_today=0,last_reset=? WHERE user_id=?',
                    (today(), int(user_id)))
        con.commit()

        cur.execute('SELECT * FROM users WHERE user_id=?', (int(user_id),))
        row = cur.fetchone()

    limit_value = (row['limit_value'] or '').strip().lower()

    if limit_value == 'unlimited':
        con.close()
        return True, 'unlimited'

    try:
        limit_num = int(limit_value)
    except:
        limit_num = int(get_setting('guest_limit', '3'))

    if row['downloads_today'] >= limit_num:
        con.close()
        return False, f'Daily limit finished ({limit_num})'

    con.close()
    return True, f'{row["downloads_today"]}/{limit_num}'

# ---------- SAVE DOWNLOAD ----------
def mark_download(user_id, chat_id, url, platform, quality, status='success'):
    con = db(); cur = con.cursor()

    cur.execute('''INSERT INTO downloads(user_id,chat_id,url,platform,quality,status)
                   VALUES(?,?,?,?,?,?)''',
                (int(user_id), int(chat_id), url, platform, quality, status))

    if status == 'success':
        cur.execute('''UPDATE users 
                       SET downloads_today=downloads_today+1,
                           total_downloads=total_downloads+1 
                       WHERE user_id=?''', (int(user_id),))

    con.commit(); con.close()

# ---------- STATS ----------
def stats():
    con = db(); cur = con.cursor()

    out = {}
    out['total_users'] = cur.execute('SELECT COUNT(*) c FROM users').fetchone()['c']
    out['total_downloads'] = cur.execute("SELECT COUNT(*) c FROM downloads WHERE status='success'").fetchone()['c']
    out['daily_downloads'] = cur.execute("SELECT COUNT(*) c FROM downloads WHERE status='success' AND date(created_at)=date('now')").fetchone()['c']
    out['total_broadcasts'] = cur.execute('SELECT COUNT(*) c FROM broadcasts').fetchone()['c']
    out['groups'] = cur.execute('SELECT COUNT(*) c FROM allowed_groups').fetchone()['c']
    out['channels'] = cur.execute('SELECT COUNT(*) c FROM force_channels WHERE is_active=1').fetchone()['c']

    con.close()
    return out

