import telebot
from telebot import types
import requests
import time
import threading
from collections import defaultdict, deque

# --- CONFIGURATION (Change these values) ---
API_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
ASTRA_URL = 'http://127.0.0.1:8000' # Your Astra Control Panel URL
ASTRA_AUTH = ('admin', 'PASSWORD_HERE') # Username and Password for Astra

# Add your Telegram User IDs here to grant access
WHITELIST = [123456789, 987654321] 

bot = telebot.TeleBot(API_TOKEN)
alerted_streams = set()
down_times = {} # Stores the timestamp when a stream first went offline

# --- ACCESS CONTROL ---
def is_authorized(user_id):
    return user_id in WHITELIST

# --- HELPER: GET GROUP NAME ---
def get_group_name(s):
    g = s.get("groups", "No Group")
    if isinstance(g, dict):
        return str(next(iter(g.values()))) if g else "No Group"
    if isinstance(g, list):
        return str(g[0]) if g else "No Group"
    return str(g)

# --- ASTRA API FUNCTIONS ---
def get_stream_list():
    try:
        r = requests.post(f"{ASTRA_URL}/control/", auth=ASTRA_AUTH, json={"cmd": "load"}, timeout=5)
        return r.json().get("make_stream", [])
    except: return []

def get_stream_status(stream_id):
    try:
        r = requests.get(f"{ASTRA_URL}/api/stream-status/{stream_id}?t=0", auth=ASTRA_AUTH, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def send_astra_cmd(payload):
    try:
        r = requests.post(f"{ASTRA_URL}/control/", auth=ASTRA_AUTH, json=payload, timeout=5)
        return r.json()
    except: return {"error": "connection failed"}

# --- FORMATTING ---
def format_bitrate(kbps):
    val = float(kbps)
    if val >= 1024:
        return f"{val/1024:.2f} Mbps"
    return f"{int(val)} Kbps"

# --- MONITORING THREAD (With Anti-Spam Filter) ---
def monitoring_thread():
    while True:
        try:
            streams = get_stream_list()
            for s in streams:
                sid = s.get("id")
                name = s.get("name", "Unknown")
                status_data = get_stream_status(sid)
                onair = status_data.get("onair", False)
                enabled = s.get("enable", True)

                # If stream is enabled but currently offline
                if enabled and not onair:
                    if sid not in alerted_streams:
                        # Record the time when it first went down
                        if sid not in down_times:
                            down_times[sid] = time.time()
                        
                        # Trigger alert only if it stays down for more than 30 seconds
                        if time.time() - down_times[sid] >= 30:
                            for admin_id in WHITELIST:
                                try:
                                    bot.send_message(admin_id, f"🚨 **ALERT: Stream DOWN!**\n📺 Name: {name}\n🆔 ID: `{sid}`\n🚦 Status: OFFLINE")
                                except: pass
                            alerted_streams.add(sid)
                
                # If stream comes back online
                elif onair:
                    if sid in down_times:
                        del down_times[sid]
                    
                    if sid in alerted_streams:
                        for admin_id in WHITELIST:
                            try:
                                bot.send_message(admin_id, f"✅ **Stream RECOVERED!**\n📺 Name: {name}\n🆔 ID: `{sid}`\n🚦 Status: ONLINE")
                            except: pass
                        alerted_streams.remove(sid)
        except: pass
        time.sleep(10)

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 Access Denied!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📁 View Groups", callback_data="list_groups"))
    bot.send_message(message.chat.id, "🛰 **ASTRA CONTROL BOT**\nSelect an option:", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "list_groups")
def list_groups_callback(call):
    if not is_authorized(call.from_user.id): return
    
    streams = get_stream_list()
    groups = set()
    for s in streams:
        group = get_group_name(s)
        groups.add(group)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for g_name in sorted(groups):
        markup.add(types.InlineKeyboardButton(f"📂 {g_name}", callback_data=f"group_{g_name}"))
    
    bot.edit_message_text("Select a group:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("group_"))
def list_group_streams(call):
    if not is_authorized(call.from_user.id): return
    
    group_name = call.data.replace("group_", "")
    streams = get_stream_list()
    
    if not streams:
        bot.answer_callback_query(call.id, "Error connecting to Astra!")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for s in streams:
        if get_group_name(s) == group_name:
            sid = s.get("id")
            name = s.get("name", "Unknown")
            
            data = get_stream_status(sid)
            kbps = data.get("bitrate", 0)
            onair = data.get("onair", False)
            
            icon = "🟢" if onair else "🔴"
            btn_text = f"{icon} {name} | {format_bitrate(kbps)}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"details_{sid}"))
    
    markup.add(types.InlineKeyboardButton("⬅️ Back to Groups", callback_data="list_groups"))
    bot.edit_message_text(f"Streams in: {group_name}", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("details_"))
def details_callback(call):
    if not is_authorized(call.from_user.id): return
    sid = call.data.split("_")[1]
    data = get_stream_status(sid)
    
    if not data:
        bot.answer_callback_query(call.id, "No data available.")
        return

    streams = get_stream_list()
    current_group = next((get_group_name(s) for s in streams if s.get("id") == sid), "No Group")

    text = (f"📺 **Stream:** {data.get('name')}\n"
            f"🆔 ID: `{sid}`\n"
            f"🚦 Status: {'✅ ONLINE' if data.get('onair') else '❌ OFFLINE'}\n"
            f"🚀 Bitrate: `{format_bitrate(data.get('bitrate', 0))}`\n"
            f"⚠️ CC Errors: `{data.get('cc_error', 0)}` (Container)\n"
            f"🧩 PES Errors: `{data.get('pes_error', 0)}` (AV Sync)")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Restart", callback_data=f"cmd_restart_{sid}"),
        types.InlineKeyboardButton("⏯ Toggle On/Off", callback_data=f"cmd_toggle_{sid}")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Back to List", callback_data=f"group_{current_group}"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("cmd_"))
def handle_commands(call):
    if not is_authorized(call.from_user.id): return
    parts = call.data.split("_")
    action, sid = parts[1], parts[2]
    
    if action == "restart":
        send_astra_cmd({"cmd": "restart-stream", "id": sid})
        bot.answer_callback_query(call.id, "✅ Restart command sent!")
    elif action == "toggle":
        send_astra_cmd({"cmd": "toggle-stream", "id": sid})
        bot.answer_callback_query(call.id, "✅ Stream status toggled!")
    
    time.sleep(1.5)
    details_callback(call)

if __name__ == "__main__":
    threading.Thread(target=monitoring_thread, daemon=True).start()
    print("Astra Bot is running...")
    bot.infinity_polling()