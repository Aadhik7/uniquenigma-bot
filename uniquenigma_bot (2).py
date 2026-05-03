#!/usr/bin/env python3
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8622421395:AAGvfCyyMs3l8_RTpPhu2j1ItvtHJM6GeHI"
API_URL = "https://api.tkshostify.in/api/1m/latest?count=100"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def fetch_data():
    try:
        r = requests.get(API_URL, timeout=10)
        data = r.json()
        if data.get('success'):
            return data['data']['results']
    except Exception as e:
        logging.error(f"API error: {e}")
    return None

def get_prediction():
    results = fetch_data()
    if not results:
        return None

    numbers = [int(i['result_number']) for i in results]
    latest_issue = results[0].get('issue_number', '000000')

    last10 = numbers[:10]
    big_count = sum(1 for n in last10 if n >= 5)
    small_count = 10 - big_count
    last3 = ['B' if n >= 5 else 'S' for n in numbers[:3]]

    if all(s == 'B' for s in last3):
        pred = 'S'
    elif all(s == 'S' for s in last3):
        pred = 'B'
    elif big_count >= 7:
        pred = 'S'
    elif small_count >= 7:
        pred = 'B'
    else:
        pred = 'S' if numbers[0] >= 5 else 'B'

    diff = abs(big_count - small_count)
    conf = min(85, max(60, 60 + diff * 3))
    next_period = str(int(latest_issue) + 1)[-6:]

    return {
        'pred': pred,
        'label': "BIG 🔴" if pred == 'B' else "SMALL 🔵",
        'nums': "5  6  7  8  9" if pred == 'B' else "0  1  2  3  4",
        'conf': conf,
        'period': next_period,
        'last': numbers[0],
        'last_period': str(latest_issue)[-6:]
    }

stats = {'wins': 0, 'losses': 0, 'last_pred': None, 'last_period': None}

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 *UniquEnigma 1Min Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 வணக்கம்! Bot ready!\n\n"
        "📋 *Commands:*\n"
        "🎯 /predict — Prediction பாருங்கள்\n"
        "📊 /stats — Win/Loss stats\n"
        "❓ /help — Help\n\n"
        "⚡ _AI Prediction Bot_",
        parse_mode='Markdown'
    )

async def cmd_predict(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Prediction கணக்கிடுகிறோம்...")
    result = get_prediction()

    if not result:
        await update.message.reply_text("❌ Data வரவில்லை. சிறிது நேரம் கழித்து try செய்யுங்கள்.")
        return

    if stats['last_pred'] and stats['last_period'] != result['last_period']:
        actual = 'B' if result['last'] >= 5 else 'S'
        if stats['last_pred'] == actual:
            stats['wins'] += 1
        else:
            stats['losses'] += 1

    stats['last_pred'] = result['pred']
    stats['last_period'] = result['period']

    total = stats['wins'] + stats['losses']
    win_rate = f"{round(stats['wins']/total*100)}%" if total > 0 else "–"
    bar = '█' * int(result['conf'] / 10) + '░' * (10 - int(result['conf'] / 10))

    await update.message.reply_text(
        f"🔮 *UniquEnigma 1Min Prediction*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Period: `{result['period']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Prediction: *{result['label']}*\n"
        f"🔢 Numbers: `{result['nums']}`\n"
        f"📊 Confidence: `{result['conf']}%`\n"
        f"`{bar}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Wins: {stats['wins']}  ❌ Losses: {stats['losses']}\n"
        f"📈 Win Rate: {win_rate}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ _UniquEnigma AI Bot_",
        parse_mode='Markdown'
    )

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    total = stats['wins'] + stats['losses']
    win_rate = f"{round(stats['wins']/total*100)}%" if total > 0 else "–"
    await update.message.reply_text(
        f"📊 *Statistics*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Wins: {stats['wins']}\n"
        f"❌ Losses: {stats['losses']}\n"
        f"📈 Win Rate: {win_rate}\n"
        f"📋 Total: {total}",
        parse_mode='Markdown'
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ *Help*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 /predict — இப்போதைய prediction\n"
        "📊 /stats — Win/Loss stats\n"
        "🔄 /start — Bot restart\n\n"
        "💡 ஒவ்வொரு period-க்கும் /predict செய்யுங்கள்!",
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("predict", cmd_predict))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("help", cmd_help))
    print("🤖 Bot Starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
