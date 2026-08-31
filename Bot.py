import logging
import random
import time
import json
import os
import string
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# --- AYARLAR ---
BOT_TOKEN = "8995026184:AAGXUbOLs14YWaZCVuBThhrqpWKzOnJLlEI"
CHANNEL_USERNAME = "@hapsolmusumarsiv"
CONTACT_USERNAME = "@HapsoImusum"
OWNER_ID = 8376729976  # Kurucu ID

DATA_FILE = "data.json"

PRICE_LIST = {
    "midasbuy": 6,
    "pubg": 6,
    "predunyam": 5,
    "smsonay": 8,
    "zara": 4,
    "exxen": 7,
    "blutv": 5,
    "carparking": 4,
    "twitter": 6,
    "netflix": 6,
    "hepsiburada": 5,
    "hotmail": 8,
    "facebook": 6
}

CATEGORY_NAMES = {
    "midasbuy": "MidasBuy Hesap",
    "pubg": "PUBG Mobile Hesap",
    "predunyam": "Predunyam Hesap",
    "smsonay": "SmsOnay Hesap",
    "zara": "Zara Hesap",
    "exxen": "Exxen Hesap",
    "blutv": "BluTv Hesap",
    "carparking": "Carparking Hesap",
    "twitter": "Twitter Hesap",
    "netflix": "Netflix Hesap",
    "hepsiburada": "Hepsiburada Hesap",
    "hotmail": "Hotmail Hesap",
    "facebook": "Facebook Hesap"
}

# --- KALICI VERİ DEPOLAMA (JSON) ---
def load_data():
    default_data = {
        "admins": [OWNER_ID],
        "banned_users": [],
        "users": {},
        "stocks": {kat: [] for kat in PRICE_LIST.keys()},
        "promo_codes": {}
    }
    if not os.path.exists(DATA_FILE):
        return default_data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "admins" not in data or OWNER_ID not in data["admins"]:
                data.setdefault("admins", []).append(OWNER_ID)
            if "stocks" not in data:
                data["stocks"] = {kat: [] for kat in PRICE_LIST.keys()}
            if "promo_codes" not in data:
                data["promo_codes"] = {}
            for kat in PRICE_LIST.keys():
                if kat not in data["stocks"]:
                    data["stocks"][kat] = []
            return data
    except Exception:
        return default_data

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

db = load_data()

# --- YARDIMCI FONKSİYONLAR ---
def get_greeting():
    turkey_time = datetime.now(timezone.utc) + timedelta(hours=3)
    hour = turkey_time.hour
    if 6 <= hour < 12:
        return "☀️ Günaydın!"
    elif 12 <= hour < 18:
        return "🌤️ Tünaydın / İyi Günler!"
    elif 18 <= hour < 21:
        return "🌆 İyi Akşamlar!"
    else:
        return "🌙 İyi Geceler!"

def generate_play_code():
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(4)]
    return "-".join(parts)

# --- KANAL KATILIM KONTROLÜ ---
async def is_subscribed(bot, user_id):
    if user_id == OWNER_ID or user_id in db["admins"]:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Kanal kontrol hatası (Bot kanalda admin mi?): {e}")
        return True

def get_main_keyboard(user_id):
    puan_str = "Sınırsız ∞" if user_id == OWNER_ID else f"{db['users'].get(str(user_id), {}).get('points', 0)} Puan"
    keyboard = [
        [InlineKeyboardButton("👤 Profilim", callback_data="profil"), InlineKeyboardButton("📜 Geçmişim", callback_data="gecmis")],
        [InlineKeyboardButton("🎰 Günlük Bonus", callback_data="cark"), InlineKeyboardButton("🎟️ Promo Kod Kullan", callback_data="promo_input_prompt")],
        [InlineKeyboardButton("🛍️ Hesap Menüsü", callback_data="hesap_menu"), InlineKeyboardButton("🤝 Davet Et Kazan", callback_data="ref")],
        [InlineKeyboardButton("📢 VIP Kanal", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"), InlineKeyboardButton("💬 İletişim", url=f"https://t.me/{CONTACT_USERNAME[1:]}")],
        [InlineKeyboardButton(f"💰 Bakiye: {puan_str}", callback_data="bakiye_bilgi")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_text():
    stok_bilgisi = "\n".join([f"• {CATEGORY_NAMES.get(kat, kat.upper())}: {len(db['stocks'].get(kat, []))} adet" for kat in PRICE_LIST.keys()])
    ekle_komutlari = "\n".join([f"• /{kat}ekle — {CATEGORY_NAMES[kat]}" for kat in PRICE_LIST.keys()])

    return (
        f"👑 KURUCU VE YÖNETİCİ PANELİ\n💬 İletişim: {CONTACT_USERNAME}\n\n"
        "📌 Yönetim Komutları:\n"
        "• /admin_ekle <ID> — Yönetici ekler.\n"
        "• /admin_sil <ID> — Yönetici siler.\n"
        "• /ban <ID> — Engeller.\n"
        "• /unban <ID> — Banı kaldırır.\n"
        "• /aktifler — Kullanıcı listesi ve istatistik.\n"
        "• /duyuru <mesaj> — Tüm kullanıcılara mesaj atar.\n\n"
        "💰 Bakiye & Promo:\n"
        "• /bakiye_ekle <ID|tumu> <miktar>\n"
        "• /bakiye_sil <ID|tumu> <miktar>\n"
        "• /promo_olustur <kod> <puan> <limit>\n\n"
        "🗑️ Stok Sıfırlama:\n"
        "• /stok_sil <kategori> — (Örn: /stok_sil midasbuy)\n\n"
        "📦 Tıklanabilir Stok Ekleme Komutları:\n"
        f"{ekle_komutlari}\n\n"
        f"📊 Anlık Stok Durumu:\n{stok_bilgisi}\n"
        "--------------------------------------"
    )

# --- BAŞLANGIÇ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    str_user_id = str(user_id)

    if user_id in db["banned_users"]:
        await update.message.reply_text("⛔ Banlandığınız için botu kullanamazsınız.")
        return

    context.user_data["waiting_promo_code"] = False
    context.user_data["waiting_stock_cat"] = None

    args = context.args
    name = user.first_name or "İsimsiz"
    username = f"@{user.username}" if user.username else "Kullanıcı adı yok"

    if str_user_id not in db["users"]:
        ref_id = str(args[0]) if args and args[0].isdigit() and args[0] != str_user_id else None
        db["users"][str_user_id] = {
            "name": name,
            "username": username,
            "points": 0, 
            "ref_by": ref_id, 
            "last_cark": 0, 
            "history": []
        }
        
        if ref_id and ref_id in db["users"]:
            db["users"][ref_id]["points"] += 1
            try:
                await context.bot.send_message(int(ref_id), "🎉 Tebrikler! Davet linkinizle yeni bir üye katıldı, +1 Puan!")
            except Exception:
                pass
        save_data()
    else:
        db["users"][str_user_id]["name"] = name
        db["users"][str_user_id]["username"] = username
        if "history" not in db["users"][str_user_id]:
            db["users"][str_user_id]["history"] = []
        save_data()

    subscribed = await is_subscribed(context.bot, user_id)
    if not subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ Katıldım / Kontrol Et", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            f"⚠️ Botu kullanabilmek için lütfen önce kanalımıza katılın:\n{CHANNEL_USERNAME}\n\nİletişim: {CONTACT_USERNAME}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    greeting = get_greeting()
    await update.message.reply_text(
        f"{greeting}\n\n⚡ Dijital Alışveriş Merkezine Hoşgeldiniz!\n💬 İletişim: {CONTACT_USERNAME}\n\nLütfen yapmak istediğiniz işlemi seçiniz:",
        reply_markup=get_main_keyboard(user_id)
    )

# --- BUTON İŞLEMLERİ ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    str_user_id = str(user_id)

    if user_id in db["banned_users"]:
        await query.answer("⛔ Banlandınız!", show_alert=True)
        return

    if str_user_id not in db["users"]:
        db["users"][str_user_id] = {
            "name": query.from_user.first_name or "İsimsiz",
            "username": f"@{query.from_user.username}" if query.from_user.username else "Yok",
            "points": 0, "ref_by": None, "last_cark": 0, "history": []
        }
        save_data()

    if query.data == "check_sub":
        await query.answer()
        if await is_subscribed(context.bot, user_id):
            await query.message.edit_text(
                f"{get_greeting()}\n\n✅ Kanal katılımınız doğrulandı!\n💬 İletişim: {CONTACT_USERNAME}",
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            await query.answer("❌ Halen kanala katılmamış görünüyorsunuz!", show_alert=True)
        return

    if query.data.startswith("stok_secim_"):
        parts = query.data.split("_")
        tip = parts[2]
        cat = parts[3]
        
        context.user_data["waiting_stock_cat"] = cat
        context.user_data["waiting_stock_type"] = tip
        
        await query.answer()
        if tip == "text":
            await query.message.edit_text(
                f"📝 {CATEGORY_NAMES.get(cat, cat.upper())} için eklenecek stokları metin olarak (her satıra 1 stok) yazıp gönderin:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="cancel_stock_input")]])
            )
        else:
            await query.message.edit_text(
                f"📁 {CATEGORY_NAMES.get(cat, cat.upper())} için stokların bulunduğu .txt dosyasını belge olarak gönderin:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="cancel_stock_input")]])
            )
        return

    elif query.data.startswith("stok_sifirla_"):
        cat = query.data.split("_")[2]
        if user_id in db["admins"]:
            eski_sayi = len(db["stocks"].get(cat, []))
            db["stocks"][cat] = []
            save_data()
            await query.answer(f"✅ {CATEGORY_NAMES.get(cat, cat.upper())} stoğu sıfırlandı!", show_alert=True)
            await query.message.edit_text(f"🗑️ **{CATEGORY_NAMES.get(cat, cat.upper())}** kategorisindeki **{eski_sayi}** adet stok başarıyla silindi.")
        return

    elif query.data == "cancel_stock_input":
        await query.answer("Stok ekleme iptal edildi.")
        context.user_data["waiting_stock_cat"] = None
        context.user_data["waiting_stock_type"] = None
        await query.message.edit_text("❌ Stok ekleme işlemi iptal edildi.")
        return

    elif query.data == "profil":
        await query.answer()
        puan = "Sınırsız ∞" if user_id == OWNER_ID else f"{db['users'][str_user_id].get('points', 0)} Puan"
        await query.message.edit_text(
            f"👤 Profil Bilgileri\n\n🆔 Kullanıcı ID: {user_id}\n👤 İsim: {db['users'][str_user_id].get('name', 'Bilinmiyor')}\n💰 Bakiyeniz: {puan}\n💬 İletişim: {CONTACT_USERNAME}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data == "gecmis":
        await query.answer()
        history = db["users"][str_user_id].get("history", [])
        if not history:
            gecmis_str = "Henüz bir satın alım geçmişiniz yok."
        else:
            gecmis_str = "\n".join([f"• {h}" for h in history[-10:]])
        await query.message.edit_text(
            f"📜 Satın Alma Geçmişiniz (Son 10):\n\n{gecmis_str}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data == "bakiye_bilgi":
        puan = "Sınırsız ∞" if user_id == OWNER_ID else f"{db['users'][str_user_id].get('points', 0)} Puan"
        await query.answer(f"💰 Güncel Bakiyeniz: {puan}", show_alert=True)

    elif query.data == "promo_input_prompt":
        await query.answer()
        context.user_data["waiting_promo_code"] = True
        
        text = (
            "╭───『 🎟️ Promo Kod 』\n"
            "│\n"
            "├─ 💼 Kullanmak istediğiniz promo kodu girin:\n"
            "│\n"
            f"╰───. {CHANNEL_USERNAME}\n"
            f"İletişim {CONTACT_USERNAME}"
        )
        keyboard = [[InlineKeyboardButton("❌ İptal", callback_data="cancel_promo_input")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "cancel_promo_input":
        await query.answer("İşlem iptal edildi.")
        context.user_data["waiting_promo_code"] = False
        greeting = get_greeting()
        await query.message.edit_text(
            f"{greeting}\n\n⚡ Dijital Alışveriş Merkezine Hoşgeldiniz!\n💬 İletişim: {CONTACT_USERNAME}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data == "ref":
        await query.answer()
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user_id}"
        await query.message.edit_text(
            f"🤝 Davet Et Kazan\n\nHer davet ettiğin kullanıcı için +1 Puan kazanırsın!\n\n🔗 Davet Linkin:\n{link}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data == "cark":
        now = time.time()
        last_time = db["users"][str_user_id].get("last_cark", 0)
        cooldown = 24 * 3600

        if now - last_time < cooldown:
            remaining = cooldown - (now - last_time)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await query.answer(f"⌛ Sistemin soğuması gerekiyor! Kalan süre: {hours} Saat {minutes} Dakika", show_alert=True)
            return

        await query.answer()
        db["users"][str_user_id]["last_cark"] = now
        if user_id != OWNER_ID:
            db["users"][str_user_id]["points"] += 1
        save_data()

        await query.message.reply_dice(emoji="🎰")
        puan_str = "Sınırsız ∞" if user_id == OWNER_ID else f"{db['users'][str_user_id]['points']} Puan"
        await query.message.reply_text(
            f"🥂 Günlük ödülünüz verildi.\n💎 Cüzdana Eklenen: +1 Puan\nHarika!\n\nGüncel Bakiyeniz: {puan_str}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data == "hesap_menu":
        await query.answer()
        keyboard = []
        keyboard.append([InlineKeyboardButton("🎮 Google Play Kod Üretici - 2 Puan", callback_data="buy_playcode")])
        
        for kat_key, kat_title in CATEGORY_NAMES.items():
            fiyat = PRICE_LIST[kat_key]
            stok_adedi = len(db["stocks"].get(kat_key, []))
            stok_durum = f"✅ Stokta ({stok_adedi})" if stok_adedi > 0 else "❌ Stok Yok"
            keyboard.append([InlineKeyboardButton(f"{kat_title} - {fiyat} Puan | {stok_durum}", callback_data=f"buy_{kat_key}")])
        keyboard.append([InlineKeyboardButton("🗣️ Üst Menü", callback_data="main_menu")])
        
        await query.message.edit_text(
            "🛍️ Hesap Menü\n\nAlt kategori veya ürün seçiniz:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "buy_playcode":
        puan = db["users"][str_user_id].get("points", 0)
        if user_id != OWNER_ID and puan < 2:
            await query.answer("⚠️ Yetersiz Bakiye! Play Kod üretmek için 2 Puan gerekiyor.", show_alert=True)
            return

        await query.answer()

        if user_id != OWNER_ID:
            db["users"][str_user_id]["points"] -= 2

        play_code = generate_play_code()
        db["users"][str_user_id]["history"].append(f"🎮 Play Kod: {play_code}")
        save_data()

        puan_str = "Sınırsız ∞" if user_id == OWNER_ID else f"{db['users'][str_user_id]['points']} Puan"
        await query.message.edit_text(
            f"🎮 Google Play Kodu Üretildi!\n\n🎟️ Kodunuz:\n{play_code}\n\n💰 Kalan Bakiyeniz: {puan_str}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data.startswith("buy_"):
        kat = query.data.split("_")[1]
        fiyat = PRICE_LIST[kat]
        puan = db["users"][str_user_id].get("points", 0)

        if len(db["stocks"].get(kat, [])) == 0:
            await query.answer("❌ Bu kategoride stok tükenmiştir!", show_alert=True)
            return

        if user_id != OWNER_ID and puan < fiyat:
            await query.answer(f"⚠️ Yetersiz Bakiye! Bu hesap için {fiyat} Puan gerekiyor.", show_alert=True)
            return

        await query.answer()

        if user_id != OWNER_ID:
            db["users"][str_user_id]["points"] -= fiyat

        hesap = db["stocks"][kat].pop(0)
        db["users"][str_user_id]["history"].append(f"{CATEGORY_NAMES[kat]}: {hesap}")
        save_data()

        puan_str = "Sınırsız ∞" if user_id == OWNER_ID else f"{db['users'][str_user_id]['points']} Puan"
        await query.message.edit_text(
            f"🎉 Satın Alım Başarılı!\n\n📦 Teslim Edilen Hesap:\n{hesap}\n\n💰 Kalan Bakiyeniz: {puan_str}",
            reply_markup=get_main_keyboard(user_id)
        )

    elif query.data == "main_menu":
        await query.answer()
        context.user_data["waiting_promo_code"] = False
        greeting = get_greeting()
        await query.message.edit_text(f"{greeting}\n\n🌟 Dijital Alışveriş Merkezine Hoşgeldiniz!\n💬 İletişim: {CONTACT_USERNAME}", reply_markup=get_main_keyboard(user_id))

# --- METİN VE PROMO İŞLEMLERİ ---
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    str_user_id = str(user_id)

    if user_id in db["admins"] and context.user_data.get("waiting_stock_cat"):
        cat = context.user_data.get("waiting_stock_cat")
        context.user_data["waiting_stock_cat"] = None
        context.user_data["waiting_stock_type"] = None

        text = update.message.text.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        if lines:
            db["stocks"][cat].extend(lines)
            save_data()
            await update.message.reply_text(
                f"✅ {CATEGORY_NAMES.get(cat, cat.upper())} kategorisine {len(lines)} adet stok eklendi.\n📊 Anlık Toplam Stok: {len(db['stocks'][cat])}"
            )
        return

    if context.user_data.get("waiting_promo_code"):
        context.user_data["waiting_promo_code"] = False
        code = update.message.text.strip().upper()

        keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]]

        if code not in db["promo_codes"]:
            text = (
                "╭───『 ❌ Geçersiz Kod 』\n"
                "│\n"
                "├─ Bu promo kod bulunamadı.\n"
                "│\n"
                f"╰───. {CHANNEL_USERNAME}\n"
                f"İletişim {CONTACT_USERNAME}"
            )
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        promo = db["promo_codes"][code]
        if str_user_id in promo["used_by"]:
            text = (
                "╭───『 ⚠️ Kod Kullanılmış 』\n"
                "│\n"
                "├─ Bu promo kodu daha önce kullandınız.\n"
                "│\n"
                f"╰───. {CHANNEL_USERNAME}\n"
                f"İletişim {CONTACT_USERNAME}"
            )
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if len(promo["used_by"]) >= promo["limit"]:
            text = (
                "╭───『 ❌ Limit Doldu 』\n"
                "│\n"
                "├─ Bu promo kodun kullanım limiti dolmuştur.\n"
                "│\n"
                f"╰───. {CHANNEL_USERNAME}\n"
                f"İletişim {CONTACT_USERNAME}"
            )
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        promo["used_by"].append(str_user_id)
        db["users"][str_user_id]["points"] += promo["points"]
        save_data()

        text = (
            "╭───『 🎉 Kod Başarılı 』\n"
            "│\n"
            f"├─ Tebrikler! +{promo['points']} Puan cüzdanınıza eklendi.\n"
            "│\n"
            f"╰───. {CHANNEL_USERNAME}\n"
            f"İletişim {CONTACT_USERNAME}"
        )
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_document_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in db["admins"] and context.user_data.get("waiting_stock_cat"):
        cat = context.user_data.get("waiting_stock_cat")
        context.user_data["waiting_stock_cat"] = None
        context.user_data["waiting_stock_type"] = None

        file = await context.bot.get_file(update.message.document.file_id)
        content = (await file.download_as_bytearray()).decode('utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        if lines:
            db["stocks"][cat].extend(lines)
            save_data()
            await update.message.reply_text(
                f"✅ {CATEGORY_NAMES.get(cat, cat.upper())} kategorisine {len(lines)} adet stok eklendi.\n📊 Anlık Toplam Stok: {len(db['stocks'][cat])}"
            )

# --- YÖNETİCİ KOMUTLARI ---
async def komutlar_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in db["admins"]:
        await update.message.reply_text("⛔ Bu komutu sadece yetkili yöneticiler görebilir!")
        return

    await update.message.reply_text(get_admin_panel_text())

async def stok_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in db["admins"]:
        return

    if context.args:
        cat = context.args[0].lower().replace("_", "")
        if cat in db["stocks"]:
            eski_sayi = len(db["stocks"][cat])
            db["stocks"][cat] = []
            save_data()
            await update.message.reply_text(f"🗑️ **{CATEGORY_NAMES.get(cat, cat.upper())}** kategorisindeki **{eski_sayi}** adet stok başarıyla silindi.")
        else:
            await update.message.reply_text("❌ Geçersiz kategori ismi!")
    else:
        keyboard = []
        for kat_key, kat_title in CATEGORY_NAMES.items():
            stok_adedi = len(db["stocks"].get(kat_key, []))
            keyboard.append([InlineKeyboardButton(f"🗑️ {kat_title} Stok Sıfırla ({stok_adedi})", callback_data=f"stok_sifirla_{kat_key}")])
        
        await update.message.reply_text(
            "🗑️ **Sıfırlamak / Silmek istediğiniz stoğu seçiniz:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def promo_olustur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return
    if len(context.args) < 3:
        await update.message.reply_text("⚠️ Kullanım: /promo_olustur <kod> <puan> <limit>")
        return

    code = context.args[0].upper()
    try:
        points = int(context.args[1])
        limit = int(context.args[2])
    except ValueError:
        await update.message.reply_text("⚠️ Puan ve limit değerleri sayı olmalıdır!")
        return

    db["promo_codes"][code] = {"points": points, "limit": limit, "used_by": []}
    save_data()
    await update.message.reply_text(f"✅ Promo Kod Oluşturuldu:\n🏷️ Kod: {code}\n💎 Ödül: {points} Puan\n👥 Kullanım Limiti: {limit}")

async def bakiye_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Kullanım: /bakiye_ekle <ID|tumu> <miktar>")
        return

    target = context.args[0].lower()
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Geçerli bir miktar giriniz!")
        return

    if target == "tumu":
        for u_id in db["users"]:
            db["users"][u_id]["points"] += amount
        save_data()
        await update.message.reply_text(f"✅ Tüm kullanıcıların bakiyesine +{amount} Puan eklendi.")
    else:
        if target in db["users"]:
            db["users"][target]["points"] += amount
            save_data()
            await update.message.reply_text(f"✅ ID: {target} kullanıcısına +{amount} Puan eklendi.")
        else:
            await update.message.reply_text("❌ Kullanıcı veritabanında bulunamadı!")

async def bakiye_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Kullanım: /bakiye_sil <ID|tumu> <miktar>")
        return

    target = context.args[0].lower()
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Geçerli bir miktar giriniz!")
        return

    if target == "tumu":
        for u_id in db["users"]:
            db["users"][u_id]["points"] = max(0, db["users"][u_id]["points"] - amount)
        save_data()
        await update.message.reply_text(f"🗑️ Tüm kullanıcıların bakiyesinden -{amount} Puan düşüldü.")
    else:
        if target in db["users"]:
            db["users"][target]["points"] = max(0, db["users"][target]["points"] - amount)
            save_data()
            await update.message.reply_text(f"🗑️ ID: {target} kullanıcısının bakiyesinden -{amount} Puan düşüldü.")
        else:
            await update.message.reply_text("❌ Kullanıcı veritabanında bulunamadı!")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if context.args:
        try:
            target_id = int(context.args[0])
            if target_id not in db["admins"]:
                db["admins"].append(target_id)
                save_data()
            await update.message.reply_text(f"✅ ID: {target_id} yönetici yapıldı.")
        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir kullanıcı ID'si giriniz!")

async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if context.args:
        try:
            target_id = int(context.args[0])
            if target_id in db["admins"]:
                db["admins"].remove(target_id)
                save_data()
            await update.message.reply_text(f"🗑️ ID: {target_id} yöneticilikten silindi.")
        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir kullanıcı ID'si giriniz!")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return
    if context.args:
        try:
            target_id = int(context.args[0])
            if target_id not in db["banned_users"]:
                db["banned_users"].append(target_id)
                save_data()
            await update.message.reply_text(f"🚫 ID: {target_id} banlandı.")
        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir kullanıcı ID'si giriniz!")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return
    if context.args:
        try:
            target_id = int(context.args[0])
            if target_id in db["banned_users"]:
                db["banned_users"].remove(target_id)
                save_data()
                await update.message.reply_text(f"✅ ID: {target_id} kullanıcısının banı kaldırıldı.")
            else:
                await update.message.reply_text("❌ Bu kullanıcı zaten banlı değil!")
        except ValueError:
            await update.message.reply_text("⚠️ Lütfen geçerli bir kullanıcı ID'si giriniz!")
    else:
        await update.message.reply_text("⚠️ Kullanım: /unban <Kullanıcı_ID>")

# --- DETAYLI AKTİFLER LİSTESİ ---
async def active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return
    
    user_count = len(db["users"])
    admin_count = len(db["admins"])
    ban_count = len(db["banned_users"])

    user_list_str = ""
    sorted_users = list(db["users"].items())[-20:]
    for u_id, u_info in sorted_users:
        name = u_info.get("name", "İsimsiz")
        uname = u_info.get("username", "Yok")
        points = u_info.get("points", 0)
        user_list_str += f"• {name} ({uname}) | ID: `{u_id}` | 💰 {points} P\n"

    if not user_list_str:
        user_list_str = "Henüz kayıtlı kullanıcı yok."

    text = (
        f"📊 **Bot İstatistikleri ve Kullanıcılar**\n\n"
        f"👥 Toplam Kullanıcı: {user_count}\n"
        f"👑 Yöneticiler: {admin_count}\n"
        f"🚫 Banlılar: {ban_count}\n\n"
        f"👤 **Son Kayıt Olan Kullanıcılar (Son 20):**\n"
        f"{user_list_str}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# --- /DUYURU SİSTEMİ ---
async def duyuru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in db["admins"]:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: /duyuru <Göndermek istediğiniz mesaj>")
        return

    broadcast_message = " ".join(context.args)
    success_count = 0
    fail_count = 0

    status_msg = await update.message.reply_text("📢 Duyuru gönderiliyor, lütfen bekleyin...")

    for u_id in list(db["users"].keys()):
        try:
            await context.bot.send_message(
                chat_id=int(u_id), 
                text=f"📢 **DUYURU**\n\n{broadcast_message}", 
                parse_mode="Markdown"
            )
            success_count += 1
            time.sleep(0.05)
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"✅ Duyuru Gönderimi Tamamlandı!\n\n"
        f"📤 Başarılı: {success_count}\n"
        f"❌ Ulaşılamayan (Botu engelleyen): {fail_count}"
    )

# --- İKİ AŞAMALI STOK EKLEME ---
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in db["admins"]:
        return

    text_to_check = update.message.text or update.message.caption or ""
    if not text_to_check:
        return

    cmd_raw = text_to_check.split()[0][1:].lower()
    cmd = cmd_raw.replace("_ekle", "").replace("ekle", "")

    if cmd in db["stocks"]:
        lines = []
        if update.message.document:
            file = await context.bot.get_file(update.message.document.file_id)
            content = (await file.download_as_bytearray()).decode('utf-8')
            lines = [line.strip() for line in content.splitlines() if line.strip()]
        else:
            text = text_to_check.split(maxsplit=1)
            if len(text) > 1:
                lines = [line.strip() for line in text[1].splitlines() if line.strip()]

        if lines:
            db["stocks"][cmd].extend(lines)
            save_data()
            await update.message.reply_text(
                f"✅ {CATEGORY_NAMES.get(cmd, cmd.upper())} kategorisine {len(lines)} adet stok eklendi.\n📊 Anlık Toplam Stok: {len(db['stocks'][cmd])}"
            )
        else:
            keyboard = [
                [
                    InlineKeyboardButton("📝 Metin Olarak Yolla", callback_data=f"stok_secim_text_{cmd}"),
                    InlineKeyboardButton("📁 TXT Dosyası Yolla", callback_data=f"stok_secim_txt_{cmd}")
                ]
            ]
            await update.message.reply_text(
                f"📦 {CATEGORY_NAMES.get(cmd, cmd.upper())} için stoğu nasıl eklemek istersiniz?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

# --- BOTU ÇALIŞTIR ---
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("komutlar", komutlar_panel))
    app.add_handler(CommandHandler("admin_ekle", add_admin))
    app.add_handler(CommandHandler("admin_sil", del_admin))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("aktifler", active_users))
    app.add_handler(CommandHandler("duyuru", duyuru))
    
    app.add_handler(CommandHandler("bakiye_ekle", bakiye_ekle))
    app.add_handler(CommandHandler("bakiye_sil", bakiye_sil))
    app.add_handler(CommandHandler("promo_olustur", promo_olustur))

    app.add_handler(CommandHandler("stok_sil", stok_sil))
    app.add_handler(CommandHandler("stoksil", stok_sil))

    for kat in PRICE_LIST.keys():
        app.add_handler(CommandHandler(f"{kat}_ekle", add_stock))
        app.add_handler(CommandHandler(f"{kat}ekle", add_stock))
        app.add_handler(MessageHandler(filters.Document.ALL & filters.CaptionRegex(f"^/{kat}"), add_stock))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_messages))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    print(f"Bot sorunsuz çalışıyor! İletişim: {CONTACT_USERNAME}")
    app.run_polling()

if __name__ == "__main__":
    main()
