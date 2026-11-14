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
import threading
import time
import urllib.request
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Grafik chizish uchun (headless rejimda)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except Exception as e:
    MATPLOTLIB_AVAILABLE = False

# ════════════════════════════════════════
#             SOZLAMALAR
# ════════════════════════════════════════
BOT_TOKEN = "9165416573:AAE73iZ7wdNe1-bkWi5b4se-x2Eae8uuW3E"
DATA_FILE = "finance_data.json"

DEFAULT_BOT_PASSWORD = "12345"
DEFAULT_ADMIN_LOGIN = "Muhammad"
DEFAULT_ADMIN_PASSWORD = "muhammad2002"

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
            "bot_password": DEFAULT_BOT_PASSWORD,
            "admin_login": DEFAULT_ADMIN_LOGIN,
            "admin_password": DEFAULT_ADMIN_PASSWORD,
            "authorized_users": [],
            "transactions": []
        }
        save_data(initial_data)
        return initial_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "bot_password" not in data or not data["bot_password"]:
                data["bot_password"] = data.get("password", DEFAULT_BOT_PASSWORD)
            if "admin_login" not in data or not data["admin_login"]:
                data["admin_login"] = DEFAULT_ADMIN_LOGIN
            if "admin_password" not in data or not data["admin_password"]:
                data["admin_password"] = DEFAULT_ADMIN_PASSWORD
            if "authorized_users" not in data:
                data["authorized_users"] = []
            if "transactions" not in data:
                data["transactions"] = []
            return data
    except Exception as e:
        log.error(f"Faylni o'qishda xatolik: {e}")
        return {
            "bot_password": DEFAULT_BOT_PASSWORD,
            "admin_login": DEFAULT_ADMIN_LOGIN,
            "admin_password": DEFAULT_ADMIN_PASSWORD,
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

def make_ratio_bar(income: float, expense: float, length: int = 10):
    """Kirim va chiqim nisbatiga qarab yashil va qizil chiziqcha yasaydi"""
    total = income + expense
    if total <= 0:
        return "⬜" * length, 0, 0
    inc_pct = round((income / total) * 100)
    exp_pct = 100 - inc_pct
    inc_blocks = round((inc_pct / 100) * length)
    exp_blocks = length - inc_blocks
    bar = ("🟩" * inc_blocks) + ("🟥" * exp_blocks)
    return bar, inc_pct, exp_pct

def generate_trading_chart(transactions: list):
    """Treyderlar uslubidagi (qora fon, yashil/qizil shamchalar/ustunlar va balans chizig'i) grafik yaratadi"""
    if not MATPLOTLIB_AVAILABLE:
        return None

    try:
        plt.style.use("dark_background")
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(10, 6),
            gridspec_kw={"height_ratios": [2.5, 1.2]},
            facecolor="#131722"
        )
        ax1.set_facecolor("#131722")
        ax2.set_facecolor("#131722")

        if not transactions:
            ax1.text(0.5, 0.5, "Hozircha amallar mavjud emas\n(Kirim yoki Chiqim qo'shing)",
                     color="#8b949e", fontsize=13, ha="center", va="center")
            ax1.set_xticks([])
            ax1.set_yticks([])
            ax2.set_xticks([])
            ax2.set_yticks([])
        else:
            recent_tx = transactions[-20:]
            running_bal = 0
            balances = []
            volumes = []
            colors = []
            labels = []

            for t in recent_tx:
                amt = t["amount"]
                if t["type"] == "income":
                    running_bal += amt
                    volumes.append(amt)
                    colors.append("#26a69a")  # TradingView yashil
                else:
                    running_bal -= amt
                    volumes.append(-amt)
                    colors.append("#ef5350")  # TradingView qizil
                balances.append(running_bal)
                labels.append(t["date"][5:16])

            x_indices = list(range(len(recent_tx)))

            # 1-Grafik: Balansning o'sishi / kamayishi (Equity curve)
            line_color = "#2962ff"
            ax1.plot(x_indices, balances, color=line_color, linewidth=2.5, marker="o", markersize=4, label="Balans")
            ax1.fill_between(x_indices, balances, alpha=0.2, color=line_color)

            for i, (b, col) in enumerate(zip(balances, colors)):
                marker = "^" if col == "#26a69a" else "v"
                ax1.scatter([i], [b], color=col, s=80, zorder=5, marker=marker)

            ax1.set_title("📊 TRADINGVIEW USLUBIDAGI KASSA GRAFIGI", color="#ffffff", fontsize=12, fontweight="bold", pad=12)
            ax1.grid(True, linestyle="--", alpha=0.2, color="#787b86")
            ax1.tick_params(colors="#8b949e", labelsize=8)
            ax1.set_ylabel("Kassa (so'm)", color="#8b949e", fontsize=9)
            ax1.set_xticks([])

            # 2-Grafik: Hajmlar (Volume bars - Yashil kirim, Qizil chiqim)
            bar_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in volumes]
            ax2.bar(x_indices, [abs(v) for v in volumes], color=bar_colors, width=0.55, alpha=0.85)
            ax2.set_ylabel("Hajm (so'm)", color="#8b949e", fontsize=9)
            ax2.grid(True, linestyle="--", alpha=0.2, color="#787b86")
            ax2.tick_params(colors="#8b949e", labelsize=8)

            ax2.set_xticks(x_indices)
            ax2.set_xticklabels(labels, rotation=30, ha="right", color="#8b949e", fontsize=7)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=140, facecolor=fig.get_facecolor(), edgecolor="none")
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        log.error(f"Grafik chizishda xatolik: {e}")
        return None

# ════════════════════════════════════════
#                KLAVIATURA
# ════════════════════════════════════════
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("➕ Kirim qo'shish"), KeyboardButton("➖ Chiqim qo'shish")],
        [KeyboardButton("💰 Kassa holati (Balans)"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("📜 Oxirgi amallar"), KeyboardButton("👑 Admin panel"), KeyboardButton("🔒 Chiqish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("🔑 Botga kirish parolini o'zgartirish")],
        [KeyboardButton("📊 Umumiy kassa hisoboti"), KeyboardButton("👥 Foydalanuvchilar")],
        [KeyboardButton("⬅️ Asosiy menyuga qaytish")]
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
            "Botdan foydalanish uchun parolni kiriting:",
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

    # 1. AGAR FOYDALANUVCHI HALI BOTGA KIRMAGAN BO'LSA (Botga kirish paroli: 12345)
    if not is_authorized(user_id):
        current_bot_password = data.get("bot_password", DEFAULT_BOT_PASSWORD).strip()

        if user_text == current_bot_password or user_text.lower() == current_bot_password.lower():
            if user_id not in data["authorized_users"]:
                data["authorized_users"].append(user_id)
                save_data(data)

            context.user_data.clear()
            await update.message.reply_text(
                "✅ *Parol to'g'ri! Botga xush kelibsiz.*\n\n"
                "Quyidagi menyu orqali ishlashingiz mumkin:",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ *Noto'g'ri parol!*\n\n"
                "Iltimos, botga kirish parolini to'g'ri kiriting:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        return

    # 2. AGAR BEKOR QILISH BOSILSA
    if user_text == "❌ Bekor qilish":
        is_in_admin = context.user_data.get("is_admin", False)
        context.user_data.clear()
        if is_in_admin:
            context.user_data["is_admin"] = True
            await update.message.reply_text("Amal bekor qilindi.", reply_markup=get_admin_keyboard())
        else:
            await update.message.reply_text("Amal bekor qilindi.", reply_markup=get_main_keyboard())
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

    # 4. ADMIN PANELGA KIRISH TUGMASI (1-Muhammad, 2-muhammad2002)
    elif user_text == "👑 Admin panel":
        if context.user_data.get("is_admin", False):
            await update.message.reply_text("👑 Admin boshqaruv paneli:", reply_markup=get_admin_keyboard())
            return

        context.user_data["step"] = "ADMIN_AUTH_LOGIN"
        await update.message.reply_text(
            "👑 *Admin paneliga kirish*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ *1-parolni (Login)* kiriting:\n\n"
            "Bekor qilish uchun: '❌ Bekor qilish'",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif user_text == "⬅️ Asosiy menyuga qaytish":
        context.user_data["step"] = None
        await update.message.reply_text("Asosiy menyuga qaytdingiz.", reply_markup=get_main_keyboard())
        return

    elif user_text in ["🔒 Chiqish", "🔒 Chiqish (Qulflash)"]:
        if user_id in data["authorized_users"]:
            data["authorized_users"].remove(user_id)
            save_data(data)
        context.user_data.clear()
        await update.message.reply_text(
            "🔒 Siz botdan chiqdingiz. Qayta kirish uchun parolni kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # 5. ADMIN MENYUSIDAGI BUYRUQLAR (Faqat adminga kirgandan so'ng)
    if user_text in ["🔑 Botga kirish parolini o'zgartirish", "🔑 Bot parolini o'zgartirish"]:
        if not context.user_data.get("is_admin", False):
            await update.message.reply_text("⚠️ Faqat admin parolni o'zgartira oladi!", reply_markup=get_main_keyboard())
            return

        context.user_data["step"] = "SET_NEW_BOT_PASSWORD"
        current_p = data.get("bot_password", DEFAULT_BOT_PASSWORD)
        await update.message.reply_text(
            f"🔑 *Botga kirish parolini o'zgartirish*\n"
            f"Joriy parol: `{current_p}`\n\n"
            f"Endi botga kirish uchun *yangi parolni* kiriting:\n"
            f"(Bu parol botga kirishdagi `{current_p}` o'rniga o'rnatiladi)\n\n"
            f"Bekor qilish uchun: '❌ Bekor qilish'",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return

    elif user_text == "📊 Umumiy kassa hisoboti":
        if not context.user_data.get("is_admin", False):
            await update.message.reply_text("⚠️ Ruxsat yo'q!", reply_markup=get_main_keyboard())
            return
        await show_global_balance(update)
        return

    elif user_text == "👥 Foydalanuvchilar":
        if not context.user_data.get("is_admin", False):
            await update.message.reply_text("⚠️ Ruxsat yo'q!", reply_markup=get_main_keyboard())
            return
        users_count = len(data.get("authorized_users", []))
        tx_count = len(data.get("transactions", []))
        await update.message.reply_text(
            f"👥 *Bot foydalanuvchilari statistikasi:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔹 Tizimga kirgan foydalanuvchilar: *{users_count} ta*\n"
            f"🔹 Jami bajarilgan amallar: *{tx_count} ta*\n",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
        return

    # 6. BOSQICHMA-BOSQICH JARAYONLAR (STEPS)
    current_step = context.user_data.get("step")

    # A) Admin 1-parol (Login: Muhammad)
    if current_step == "ADMIN_AUTH_LOGIN":
        admin_login = data.get("admin_login", DEFAULT_ADMIN_LOGIN).strip()
        if user_text.lower() == admin_login.lower():
            context.user_data["step"] = "ADMIN_AUTH_PASS"
            await update.message.reply_text(
                "✅ 1-parol (Login) to'g'ri!\n\n"
                "2️⃣ Endi *2-parolni* kiriting:\n\n"
                "Bekor qilish uchun: '❌ Bekor qilish'",
                parse_mode="Markdown",
                reply_markup=get_cancel_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ *1-parol (Login) noto'g'ri!*\n"
                "Iltimos, qaytadan to'g'ri kiriting:\n(Bekor qilish: '❌ Bekor qilish')",
                parse_mode="Markdown"
            )
        return

    # B) Admin 2-parol (muhammad2002)
    elif current_step == "ADMIN_AUTH_PASS":
        admin_pass = data.get("admin_password", DEFAULT_ADMIN_PASSWORD).strip()
        if user_text == admin_pass or user_text.lower() == admin_pass.lower():
            context.user_data["is_admin"] = True
            context.user_data["step"] = None
            await update.message.reply_text(
                "👑 *Admin paneliga xush kelibsiz, Muhammad!*\n\n"
                "Bu yerdan botga kirish parolini o'zgartirishingiz va umumiy hisobotlarni ko'rishingiz mumkin:",
                parse_mode="Markdown",
                reply_markup=get_admin_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ *2-parol noto'g'ri!*\n"
                "Iltimos, parolni qaytadan kiriting:\n(Bekor qilish: '❌ Bekor qilish')",
                parse_mode="Markdown"
            )
        return

    # C) Bot parolini o'zgartirish (faqat admin tomonidan)
    elif current_step == "SET_NEW_BOT_PASSWORD":
        if len(user_text) < 3:
            await update.message.reply_text("⚠️ Parol kamida 3 ta belgidan iborat bo'lsin:")
            return

        data["bot_password"] = user_text
        save_data(data)
        context.user_data["step"] = None

        await update.message.reply_text(
            f"✅ *Botga kirish paroli muvaffaqiyatli o'zgartirildi!*\n\n"
            f"Endi yangi foydalanuvchilar `/start` bosganda ushbu yangi parolni kiritishadi:\n"
            f"👉 `{user_text}`",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
        return

    # D) Kirim summasini qabul qilish
    elif current_step == "INCOME_AMOUNT":
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

    # E) Kirim izohini qabul qilish va saqlash
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

    # F) Chiqim summasini qabul qilish
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

    # G) Chiqim izohini qabul qilish va saqlash
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

    # Agar hech qanday shartga tushmasa
    await update.message.reply_text(
        "Iltimos, quyidagi menyu tugmalaridan birini tanlang:",
        reply_markup=get_main_keyboard()
    )

# ════════════════════════════════════════
#          HISOBOT FUNKSIYALARI
# ════════════════════════════════════════
async def show_balance(update: Update):
    user_id = update.effective_user.id
    data = load_data()
    transactions = [t for t in data.get("transactions", []) if t.get("user_id") == user_id]

    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = total_income - total_expense

    bar, inc_pct, exp_pct = make_ratio_bar(total_income, total_expense, length=10)

    if balance > 0:
        trend = "📈 *Sof foyda:* `+" + format_money(balance) + "` ⬆️"
        status_icon = "🟢"
    elif balance < 0:
        trend = "📉 *Zarar (Kassada kamomad):* `-" + format_money(abs(balance)) + "` ⬇️"
        status_icon = "🔴"
    else:
        trend = "⚖️ *Qoldiq:* `0 so'm` ➖"
        status_icon = "⚪"

    msg = (
        "💼 *SHAXSIY KASSA HOLATI (BALANS)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 *Kirim:* `+{format_money(total_income)}` ({inc_pct}%) ⬆️\n"
        f"🔴 *Chiqim:* `-{format_money(total_expense)}` ({exp_pct}%) ⬇️\n\n"
        f"📊 *Nisbat chizig'i:*\n"
        f"[{bar}]\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_icon} *Kassadagi qoldiq:*\n"
        f"👉 *{format_money(balance)}*\n"
        f"{trend}\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def show_statistics(update: Update):
    user_id = update.effective_user.id
    data = load_data()
    transactions = [t for t in data.get("transactions", []) if t.get("user_id") == user_id]

    today_str = datetime.now().strftime("%Y-%m-%d")
    month_str = datetime.now().strftime("%Y-%m")

    # Bugungi kun
    today_income = sum(t["amount"] for t in transactions if t["type"] == "income" and t["date"].startswith(today_str))
    today_expense = sum(t["amount"] for t in transactions if t["type"] == "expense" and t["date"].startswith(today_str))
    today_net = today_income - today_expense
    today_bar, today_inc_p, today_exp_p = make_ratio_bar(today_income, today_expense, length=8)

    today_trend = "📈 ⬆️" if today_net > 0 else ("📉 ⬇️" if today_net < 0 else "⚖️ ➖")
    today_sign = "+" if today_net >= 0 else "-"

    # Shu oy
    month_income = sum(t["amount"] for t in transactions if t["type"] == "income" and t["date"].startswith(month_str))
    month_expense = sum(t["amount"] for t in transactions if t["type"] == "expense" and t["date"].startswith(month_str))
    month_net = month_income - month_expense
    month_bar, month_inc_p, month_exp_p = make_ratio_bar(month_income, month_expense, length=8)

    month_trend = "📈 ⬆️" if month_net > 0 else ("📉 ⬇️" if month_net < 0 else "⚖️ ➖")
    month_sign = "+" if month_net >= 0 else "-"

    msg = (
        "📊 *SHAXSIY MOLIYAVIY STATISTIKA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Bugungi kun:* `({today_str})`\n"
        f"  🟢 Kirim:  `+{format_money(today_income)}` ({today_inc_p}%) ⬆️\n"
        f"  🔴 Chiqim: `-{format_money(today_expense)}` ({today_exp_p}%) ⬇️\n"
        f"  📊 Chiziq: `[{today_bar}]`\n"
        f"  🔹 Natija: *{today_sign}{format_money(abs(today_net))}* {today_trend}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗓 *Shu oyda:* `({month_str})`\n"
        f"  🟢 Kirim:  `+{format_money(month_income)}` ({month_inc_p}%) ⬆️\n"
        f"  🔴 Chiqim: `-{format_money(month_expense)}` ({month_exp_p}%) ⬇️\n"
        f"  📊 Chiziq: `[{month_bar}]`\n"
        f"  🔹 Natija: *{month_sign}{format_money(abs(month_net))}* {month_trend}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    chart_buf = generate_trading_chart(transactions)
    if chart_buf:
        await update.message.reply_photo(
            photo=chart_buf,
            caption=msg,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def show_recent_transactions(update: Update):
    user_id = update.effective_user.id
    data = load_data()
    transactions = [t for t in data.get("transactions", []) if t.get("user_id") == user_id]

    if not transactions:
        await update.message.reply_text("📭 Hozircha sizda hech qanday amallar mavjud emas.", reply_markup=get_main_keyboard())
        return

    recent = transactions[-10:]
    recent.reverse()

    lines = ["📜 *SIZNING OXIRGI 10 TA AMALINGIZ:*\n━━━━━━━━━━━━━━━━━━━━━━"]
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

async def show_global_balance(update: Update):
    """Admin uchun barcha foydalanuvchilarning umumiy kassasi"""
    data = load_data()
    transactions = data.get("transactions", [])

    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = total_income - total_expense

    msg = (
        "👑 *BUTUN BOT BO'YICHA UMUMIY KASSA:*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"➕ Barcha Kirimlar: *{format_money(total_income)}*\n"
        f"➖ Barcha Chiqimlar: *{format_money(total_expense)}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 *Jami qoldiq: {format_money(balance)}*\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_admin_keyboard())

# ════════════════════════════════════════
#       RENDER 24/7 SERVER VA KEEP-ALIVE
# ════════════════════════════════════════
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot 24/7 faol ishlamoqda!")

    def log_message(self, format, *args):
        pass

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

def keep_alive_ping(url: str):
    time.sleep(30)
    while True:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Render-KeepAlive-Ping/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                log.info(f"Keep-Alive ping yuborildi: {resp.status}")
        except Exception as e:
            log.warning(f"Keep-Alive pingda xatolik: {e}")
        time.sleep(600)

def run_render_web_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = ReusableHTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"✅ Render Web Service {port}-portda muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        print(f"⚠️ Port ochishda ogohlantirish (e'tiborsiz qoldirish mumkin): {e}")

    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        ping_thread = threading.Thread(target=keep_alive_ping, args=(render_url,), daemon=True)
        ping_thread.start()
        print(f"🔄 Render Keep-Alive (uxlamaslik) rejimi yoqildi: {render_url}")

# ════════════════════════════════════════
#               ASOSIY QISM
# ════════════════════════════════════════
def main():
    run_render_web_server()
    if not BOT_TOKEN:
        print("XATO: BOT_TOKEN o'rnatilmagan!")
        return

    load_data()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("=" * 50)
    print("🤖 Kirdi-Chiqdi (Moliya) boti ishga tushirildi!")
    print(f"🔑 Botga kirish paroli: {DEFAULT_BOT_PASSWORD}")
    print(f"👤 Admin Login: {DEFAULT_ADMIN_LOGIN}")
    print(f"🔐 Admin Parol: {DEFAULT_ADMIN_PASSWORD}")
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
