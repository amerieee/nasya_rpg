import os
import time
import requests
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# -----------------------------
# Flask сервер для "keep_alive"
# -----------------------------
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Бот онлайн!"

def run_web():
    app_web.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_web, daemon=True)
    t.start()
    print("🌐 keep_alive запущен (Flask на :8080)")

def start_autopinger():
    url = os.environ.get("REPL_URL")  # или задаём вручную в Secrets
    if not url:
        print("⚠️ Не найден REPL_URL. Автопингер не запущен.")
        return

    def _ping_loop():
        print(f"🛰️ автопингер целится в: {url}")
        while True:
            try:
                requests.get(url, timeout=10)
            except Exception as e:
                print("Автопингер: ошибка запроса:", e)
            time.sleep(240)  # ~4 минуты

    Thread(target=_ping_loop, daemon=True).start()

# -----------------------------
# Логика бота
# -----------------------------
hp = 0
current_buttons = [["Доброе утро"]]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        await update.message.reply_text(
            "Привет! Я твой RPG-бот 🌞",
            reply_markup=ReplyKeyboardMarkup(current_buttons, one_time_keyboard=False)
        )

async def morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hp, current_buttons
    hp = 0
    if update.message and update.message.text:
        await update.message.reply_text(
            "Настюшка идёт покорять мир! 🌞\nСколько у тебя энергии (HP) сегодня? Введи число от 0 до 100.",
            reply_markup=ReplyKeyboardRemove()
        )

async def set_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hp, current_buttons
    if update.message and update.message.text:
        try:
            value = int(update.message.text)
            if 0 <= value <= 100:
                hp = value
                current_buttons = [["Подхилилась", "Враг на пути"], ["Спокойной ночи"]]
                await update.message.reply_text(
                    f"Энергия установлена: {hp} HP.\nТеперь доступны действия дня!",
                    reply_markup=ReplyKeyboardMarkup(current_buttons, one_time_keyboard=False)
                )
            else:
                await update.message.reply_text("Введи число от 0 до 100.")
        except ValueError:
            await update.message.reply_text("Введи число!")

async def action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hp, current_buttons
    if not update.message or not update.message.text:
        return

    text = update.message.text
    if text in ["Подхилилась", "Враг на пути"]:
        await update.message.reply_text("Сколько HP прибавить или убавить? Введи число:")
        if context.user_data is not None:
            context.user_data["last_action"] = text
    elif text == "Спокойной ночи":
        hp = 0
        current_buttons = [["Доброе утро"]]
        await update.message.reply_text(
            "Спокойной ночи 🌙 Энергия обнулена.",
            reply_markup=ReplyKeyboardMarkup(current_buttons, one_time_keyboard=False)
        )
    elif text == "Доброе утро":
        await morning(update, context)

async def update_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global hp
    if not update.message or not update.message.text:
        return

    user_data = context.user_data or {}
    if "last_action" in user_data:
        try:
            value = int(update.message.text)
            action_type = user_data["last_action"]

            if action_type == "Подхилилась":
                hp += value
            else:
                hp -= value

            if hp <= 0:
                message = f"{hp} HP — Ты истощена! Пора срочно хилиться! 😵"
            elif hp < 20:
                message = f"{hp} HP — Осторожно, силы тают… 🩹"
            elif hp < 50:
                message = f"{hp} HP — Ты держишься, не сдавайся!"
            elif hp < 80:
                message = f"{hp} HP — Почти полная энергия ⚔️"
            else:
                message = f"{hp} HP — Полна сил, Настюшка! 💪"

            await update.message.reply_text(message)
            user_data.pop("last_action", None)
        except ValueError:
            await update.message.reply_text("Введи число!")

# -----------------------------
# Запуск бота
# -----------------------------
def main():
    token = os.environ.get("TOKEN")
    if not token:
        raise ValueError("❌ Не найден TOKEN в Secrets!")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^Доброе утро$"), morning))
    app.add_handler(MessageHandler(filters.Regex("^[0-9]{1,3}$"), set_hp))
    app.add_handler(MessageHandler(filters.Regex("^(Подхилилась|Враг на пути|Спокойной ночи)$"), action))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), update_hp))

    print("✅ Бот запущен! (long polling)")
    app.run_polling()  # запускаем polling без старых устаревших параметров

# -----------------------------
# Точка входа
# -----------------------------
if __name__ == "__main__":
    keep_alive()        # Flask сервер для ping
    start_autopinger()  # автопинг
    Thread(target=main).start()  # бот в отдельном потоке
