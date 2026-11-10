#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║                💰  KIRDI-CHIQDI (MOLIYA / KASSA) BOTI                ║
║                      python-telegram-bot v20+                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import sys
import json
import logging
import os
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ════════════════════════════════════════
#             SOZLAMALAR
# ════════════════════════════════════════
BOT_TOKEN = "9165416573:AAE73iZ7wdNe1-bkWi5b4se-x2Eae8uuW3E"
DATA_FILE = "finance_data.json"
DEFAULT_PASSWORD = "muhammad0206"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ════════════════════════════════════════
#          MA'LUMOTLAR BAZASI (JSON)
# ════════════════════════════════════════
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "password": DEFAULT_PASSWORD,
            "authorized_users": [],
            "transactions": []
        }
        save_data(initial_data)
        return initial_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "password" not in data or not data["password"]:
                data["password"] = DEFAULT_PASSWORD
            if "authorized_users" not in data:
                data["authorized_users"] = []
            if "transactions" not in data:
                data["transactions"] = []
            return data
    except Exception as e:
        log.error(f"Faylni o'qishda xatolik: {e}")
        return {
            "password": DEFAULT_PASSWORD,
            "authorized_users": [],
            "transactions": []
        }

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_authorized(user_id: int) -> bool:
    data = load_data()
    return user_id in data.get("authorized_users", [])

def format_money(amount: float) -> str:
    """Sonni chiroyli ko'rinishga keltiradi (masalan: 1 250 000 so'm)"""
    if amount == int(amount):
        return f"{int(amount):,}".replace(",", " ") + " so'm"
    return f"{amount:,.2f}".replace(",", " ") + " so'm"

# ════════════════════════════════════════
#                KLAVIATURA
# ════════════════════════════════════════
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("➕ Kirim qo'shish"), KeyboardButton("➖ Chiqim qo'shish")],
        [KeyboardButton("💰 Kassa holati (Balans)"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("📜 Oxirgi amallar"), KeyboardButton("⚙️ Parolni o'zgartirish")],
        [KeyboardButton("🔒 Chiqish (Qulflash)")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    keyboard = [[KeyboardButton("❌ Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ════════════════════════════════════════
#              HANDLERLAR
# ════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start buyrug'i"""
    user_id = update.effective_user.id
    context.user_data.clear()

    if is_authorized(user_id):
        await update.message.reply_text(
            "👋 Xush kelibsiz! Kirdi-Chiqdi (Moliya) botingiz xizmatingizda.\n\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "🔒 *Assalomu alaykum!*\n\n"
            "Ushbu botdan foydalanish uchun parolni kiriting:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha matnli xabarlarni boshqarish markazi"""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    data = load_data()

    # 1. AGAR FOYDALANUVCHI HALI PAROL BILAN KIRMAGAN BO'LSA
    if not is_authorized(user_id):
        current_password = data.get("password", DEFAULT_PASSWORD).strip()

        # Parolni tekshiramiz (katta-kichik harflar va bo'shliqlarga e'tibor qaratib)
        if user_text == current_password or user_text.lower() == current_password.lower():
            if user_id not in data["authorized_users"]:
                data["authorized_users"].append(user_id)
                save_data(data)
            
            context.user_data.clear()
            await update.message.reply_text(
                "✅ *Parol to'g'ri! Botga xush kelibsiz.*\n\n"
                "Quyidagi menyu orqali kerakli bo'limni tanlang:",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ *Noto'g'ri parol!*\n\n"
                "Iltimos, parolni qaytadan to'g'ri kiriting:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        return

    # 2. AGAR BEKOR QILISH BOSILSA
    if user_text == "❌ Bekor qilish":
        context.user_data.clear()
        await update.message.reply_text(
            "Amal bekor qilindi.",
            reply_markup=get_main_keyboard()
        )
        return

    # 3. ASOSIY MENYU BUYRUQLARI
    if user_text == "➕ Kirim qo'shish":
        context.user_data["step"] = "INCOME_AMOUNT"
        await update.message.reply_text(
            "➕ *Kirim summasini kiriting:*\n"
            "Misol uchun: `150000` yoki `50000`\n\n"
            "Bekor qilish uchun pastdagi '❌ Bekor qilish' tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif user_text == "➖ Chiqim qo'shish":
        context.user_data["step"] = "EXPENSE_AMOUNT"
        await update.message.reply_text(
            "➖ *Chiqim (xarajat) summasini kiriting:*\n"
            "Misol uchun: `35000` yoki `120000`\n\n"
            "Bekor qilish uchun pastdagi '❌ Bekor qilish' tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif user_text == "💰 Kassa holati (Balans)":
        await show_balance(update)
        return

    elif user_text == "📊 Statistika":
        await show_statistics(update)
        return

    elif user_text == "📜 Oxirgi amallar":
        await show_recent_transactions(update)
        return

    elif user_text == "⚙️ Parolni o'zgartirish":
        context.user_data["step"] = "NEW_PASSWORD"
        await update.message.reply_text(
            "⚙️ *Yangi parolni kiriting:*\n"
            "(Kamida 4 ta belgidan iborat bo'lsin)\n\n"
            "Bekor qilish uchun: '❌ Bekor qilish'",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif user_text == "🔒 Chiqish (Qulflash)":
        if user_id in data["authorized_users"]:
            data["authorized_users"].remove(user_id)
            save_data(data)
        context.user_data.clear()
        await update.message.reply_text(
            "🔒 Siz botdan chiqdingiz. Qayta kirish uchun parolni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # 4. BOSQICHMA-BOSQICH JARAYONLAR (STEPS)
    current_step = context.user_data.get("step")

    # A) Kirim summasini qabul qilish
    if current_step == "INCOME_AMOUNT":
        clean_sum = user_text.replace(" ", "").replace(",", "").replace("so'm", "").replace("som", "")
        try:
            amount = float(clean_sum)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ Noto'g'ri summa kiritildi. Iltimos faqat musbat raqam kiriting:\nMasalan: `50000`",
                parse_mode="Markdown"
            )
            return

        context.user_data["temp_amount"] = amount
        context.user_data["step"] = "INCOME_COMMENT"
        await update.message.reply_text(
            f"💵 Kirim summasi: *{format_money(amount)}*\n\n"
            "Endi ushbu kirim uchun *izoh yoki manba* yozing:\n"
            "(Masalan: `Oylik maosh`, `Savdo tushumi`, `Qarz qaytdi` yoki shunchaki `-` deb yuboring)",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    # B) Kirim izohini qabul qilish va saqlash
    elif current_step == "INCOME_COMMENT":
        comment = user_text if user_text != "-" else "Kirim"
        amount = context.user_data.get("temp_amount", 0)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx = {
            "id": len(data["transactions"]) + 1,
            "type": "income",
            "amount": amount,
            "comment": comment,
            "date": now,
            "user_id": user_id,
            "user_name": update.effective_user.full_name or "Foydalanuvchi"
        }
        data["transactions"].append(tx)
        save_data(data)

        context.user_data.clear()
        await update.message.reply_text(
            f"✅ *Kirim muvaffaqiyatli saqlandi!*\n\n"
            f"➕ Summa: *+{format_money(amount)}*\n"
            f"📝 Izoh: *{comment}*\n"
            f"🕒 Sana: _{now}_",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    # C) Chiqim summasini qabul qilish
    elif current_step == "EXPENSE_AMOUNT":
        clean_sum = user_text.replace(" ", "").replace(",", "").replace("so'm", "").replace("som", "")
        try:
            amount = float(clean_sum)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ Noto'g'ri summa kiritildi. Iltimos faqat musbat raqam kiriting:\nMasalan: `25000`",
                parse_mode="Markdown"
            )
            return

        context.user_data["temp_amount"] = amount
        context.user_data["step"] = "EXPENSE_COMMENT"
        await update.message.reply_text(
            f"💸 Chiqim summasi: *{format_money(amount)}*\n\n"
            "Endi ushbu chiqim uchun *izoh yoki xarajat turini* yozing:\n"
            "(Masalan: `Bozorlik`, `Tushlik`, `Benzin`, `Kvartira` yoki shunchaki `-` deb yuboring)",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    # D) Chiqim izohini qabul qilish va saqlash
    elif current_step == "EXPENSE_COMMENT":
        comment = user_text if user_text != "-" else "Xarajat"
        amount = context.user_data.get("temp_amount", 0)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx = {
            "id": len(data["transactions"]) + 1,
            "type": "expense",
            "amount": amount,
            "comment": comment,
            "date": now,
            "user_id": user_id,
            "user_name": update.effective_user.full_name or "Foydalanuvchi"
        }
        data["transactions"].append(tx)
        save_data(data)

        context.user_data.clear()
        await update.message.reply_text(
            f"✅ *Chiqim muvaffaqiyatli saqlandi!*\n\n"
            f"➖ Summa: *-{format_money(amount)}*\n"
            f"📝 Izoh: *{comment}*\n"
            f"🕒 Sana: _{now}_",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    # E) Yangi parolni qabul qilish
    elif current_step == "NEW_PASSWORD":
        if len(user_text) < 4:
            await update.message.reply_text("⚠️ Parol juda qisqa! Kamida 4 ta belgi kiriting:")
            return

        context.user_data["temp_new_pass"] = user_text
        context.user_data["step"] = "CONFIRM_NEW_PASSWORD"
        await update.message.reply_text(
            "🔑 Yangi parolni tasdiqlash uchun uni *qaytadan kiriting*:\n\n"
            "Bekor qilish uchun: '❌ Bekor qilish'",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    # F) Yangi parolni tasdiqlash
    elif current_step == "CONFIRM_NEW_PASSWORD":
        candidate = context.user_data.get("temp_new_pass", "")
        if user_text != candidate:
            context.user_data.clear()
            await update.message.reply_text(
                "❌ Parollar bir-biriga mos kelmadi!\nParol o'zgartirish bekor qilindi.",
                reply_markup=get_main_keyboard()
            )
            return

        data["password"] = candidate
        save_data(data)
        context.user_data.clear()

        await update.message.reply_text(
            f"✅ *Parol muvaffaqiyatli o'zgartirildi!*\n\n"
            f"Yangi parolingiz: `{candidate}`\n"
            f"Uni eslab qoling!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    # Agar hech qanday shartga tushmasa, menyuni ko'rsatamiz
    await update.message.reply_text(
        "Iltimos, menyudagi tugmalardan birini tanlang:",
        reply_markup=get_main_keyboard()
    )

# ════════════════════════════════════════
#          HISOBOT FUNKSIYALARI
# ════════════════════════════════════════
async def show_balance(update: Update):
    data = load_data()
    transactions = data.get("transactions", [])

    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = total_income - total_expense

    balance_icon = "🟢" if balance >= 0 else "🔴"

    msg = (
        "💼 *UMUMIY KASSA HOLATI (BALANS):*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"➕ Jami Kirim: *{format_money(total_income)}*\n"
        f"➖ Jami Chiqim: *{format_money(total_expense)}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{balance_icon} *Qoldiq (Kassada): {format_money(balance)}*\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def show_statistics(update: Update):
    data = load_data()
    transactions = data.get("transactions", [])

    today_str = datetime.now().strftime("%Y-%m-%d")
    month_str = datetime.now().strftime("%Y-%m")

    today_income = sum(t["amount"] for t in transactions if t["type"] == "income" and t["date"].startswith(today_str))
    today_expense = sum(t["amount"] for t in transactions if t["type"] == "expense" and t["date"].startswith(today_str))
    today_net = today_income - today_expense

    month_income = sum(t["amount"] for t in transactions if t["type"] == "income" and t["date"].startswith(month_str))
    month_expense = sum(t["amount"] for t in transactions if t["type"] == "expense" and t["date"].startswith(month_str))
    month_net = month_income - month_expense

    msg = (
        "📊 *MOLIYAVIY STATISTIKA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Bugungi kun ({today_str}):*\n"
        f"  ➕ Kirim: {format_money(today_income)}\n"
        f"  ➖ Chiqim: {format_money(today_expense)}\n"
        f"  🔹 Foyda/Farq: {format_money(today_net)}\n\n"
        f"🗓 *Shu oyda ({month_str}):*\n"
        f"  ➕ Kirim: {format_money(month_income)}\n"
        f"  ➖ Chiqim: {format_money(month_expense)}\n"
        f"  🔹 Foyda/Farq: {format_money(month_net)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def show_recent_transactions(update: Update):
    data = load_data()
    transactions = data.get("transactions", [])

    if not transactions:
        await update.message.reply_text("📭 Hozircha hech qanday amallar mavjud emas.", reply_markup=get_main_keyboard())
        return

    recent = transactions[-10:]
    recent.reverse()

    lines = ["📜 *OXIRGI 10 TA AMAL:*\n━━━━━━━━━━━━━━━━━━━━━━"]
    for t in recent:
        icon = "🟢 Kirim" if t["type"] == "income" else "🔴 Chiqim"
        sign = "+" if t["type"] == "income" else "-"
        date_short = t["date"][5:16]
        comment = t.get("comment", "")
        lines.append(
            f"{icon}: *{sign}{format_money(t['amount'])}*\n"
            f"   📝 {comment} | 🕒 {date_short}"
        )
        lines.append("──────────────────────")

    msg = "\n".join(lines)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ════════════════════════════════════════
#               ASOSIY QISM
# ════════════════════════════════════════
def main():
    if not BOT_TOKEN:
        print("XATO: BOT_TOKEN o'rnatilmagan!")
        return

    load_data()

    app = Application.builder().token(BOT_TOKEN).build()

    # Buyruqlar va xabarlar
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("=" * 50)
    print("🤖 Kirdi-Chiqdi (Moliya) boti ishga tushirildi!")
    print(f"🔑 Boshlang'ich parol: {DEFAULT_PASSWORD}")
    print("=" * 50)

    app.run_polling()

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    main()
