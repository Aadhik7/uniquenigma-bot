#!/usr/bin/env python3
"""
UniquEnigma 1Min Prediction - Telegram Bot
Same AI prediction logic as the HTML file
"""

import asyncio
import logging
import requests
from collections import deque
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ══════════════════════════════════════════════
#  ⚙️  CONFIG — இங்கே உங்கள் Bot Token போடுங்கள்
# ══════════════════════════════════════════════
BOT_TOKEN = "8622421395:AAGvfCyyMs3l8_RTpPhu2j1ItvtHJM6GeHI"   # @BotFather-ல இருந்து எடுக்கவும்

API_URL = "https://api.tkshostify.in/api/1m/latest?count=100"
REFRESH_SECONDS = 60   # ஒவ்வொரு minute-க்கும் check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  🧠  PREDICTOR (HTML-ல இருந்த exact logic)
# ══════════════════════════════════════════════
class RealTimePredictor:
    def __init__(self):
        self.results = deque(maxlen=500)
        self.confidence = 75.0
        self.consecutive_errors = 0
        self.recent_accuracy = deque(maxlen=30)
        self.markov_table = {}

    def to_size(self, n):
        return 'B' if n >= 5 else 'S'

    def update_markov(self, results):
        self.markov_table = {}
        s = [self.to_size(r) for r in results]
        for order in range(1, 5):
            for i in range(order, len(s)):
                key = ''.join(s[i-order:i])
                if key not in self.markov_table:
                    self.markov_table[key] = {'B': 0, 'S': 0}
                self.markov_table[key][s[i]] += 1

    def markov_predict(self, results):
        s = [self.to_size(r) for r in results]
        for order in range(4, 0, -1):
            key = ''.join(s[-order:])
            t = self.markov_table.get(key)
            if t and (t['B'] + t['S']) >= 4:
                total = t['B'] + t['S']
                pred = 'B' if t['B'] > t['S'] else 'S'
                strength = abs(t['B'] - t['S']) / total
                return {'pred': pred, 'strength': strength}
        return None

    def streak_reversal(self, results):
        if len(results) < 3:
            return None
        s = [self.to_size(r) for r in results]
        last = s[-1]
        streak = 1
        for i in range(len(s)-2, -1, -1):
            if s[i] == last:
                streak += 1
            else:
                break
        if streak >= 4:
            return {'pred': 'S' if last == 'B' else 'B', 'strength': min(0.85, 0.4 + streak * 0.1)}
        if streak == 3:
            return {'pred': 'S' if last == 'B' else 'B', 'strength': 0.55}
        return None

    def alternating_predict(self, results):
        if len(results) < 6:
            return None
        s = [self.to_size(r) for r in results[-8:]]
        alt_score = sum(1 for i in range(1, len(s)) if s[i] != s[i-1])
        if alt_score >= len(s) - 2:
            return {'pred': 'S' if s[-1] == 'B' else 'B', 'strength': 0.65}
        return None

    def double_pattern(self, results):
        if len(results) < 8:
            return None
        s = [self.to_size(r) for r in results[-8:]]
        score = sum(1 if s[i] == s[i+1] else -1 for i in range(0, len(s)-1, 2))
        if score >= 3:
            last2_same = s[-1] == s[-2]
            if last2_same:
                return {'pred': 'S' if s[-1] == 'B' else 'B', 'strength': 0.6}
            else:
                return {'pred': s[-1], 'strength': 0.5}
        return None

    def mean_reversion(self, results):
        if len(results) < 15:
            return None
        recent = list(results)[-20:]
        big_ratio = sum(1 for r in recent if r >= 5) / len(recent)
        if big_ratio > 0.7:
            return {'pred': 'S', 'strength': (big_ratio - 0.5) * 1.5}
        if big_ratio < 0.3:
            return {'pred': 'B', 'strength': (0.5 - big_ratio) * 1.5}
        return None

    def momentum(self, results):
        if len(results) < 8:
            return None
        s = [1 if r >= 5 else 0 for r in list(results)[-10:]]
        w = [1, 1, 1, 2, 2, 3, 3, 4, 4, 5]
        wl = w[-len(s):]
        w_sum = sum(wl)
        w_avg = sum(v * wl[i] for i, v in enumerate(s)) / w_sum
        if w_avg > 0.60:
            return {'pred': 'B', 'strength': (w_avg - 0.5) * 2}
        if w_avg < 0.40:
            return {'pred': 'S', 'strength': (0.5 - w_avg) * 2}
        return None

    def zigzag_predict(self, results):
        if len(results) < 6:
            return None
        s = [self.to_size(r) for r in list(results)[-6:]]
        last4 = s[-4:]
        if last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
            return {'pred': last4[2], 'strength': 0.55}
        return None

    def fibonacci_window(self, results):
        if len(results) < 13:
            return None
        rlist = list(results)
        wins = []
        for w in [3, 5, 8, 13]:
            sl = rlist[-w:]
            wins.append(sum(1 for r in sl if r >= 5) / len(sl))
        avg_big = sum(wins) / len(wins)
        variance = sum(abs(x - avg_big) for x in wins) / len(wins)
        if variance < 0.15:
            if avg_big > 0.58:
                return {'pred': 'B', 'strength': 0.5}
            if avg_big < 0.42:
                return {'pred': 'S', 'strength': 0.5}
        return None

    def window_consensus(self, results):
        if len(results) < 20:
            return None
        rlist = list(results)
        votes = []
        for w in [5, 10, 15, 20]:
            s = rlist[-w:]
            b = sum(1 for r in s if r >= 5)
            votes.append('B' if b / len(s) > 0.5 else 'S')
        b_votes = votes.count('B')
        if b_votes >= 3:
            return {'pred': 'B', 'strength': 0.5 + (b_votes - 2) * 0.1}
        if b_votes <= 1:
            return {'pred': 'S', 'strength': 0.5 + (2 - b_votes) * 0.1}
        return None

    def pair_transition(self, results):
        if len(results) < 10:
            return None
        rlist = list(results)
        s = [self.to_size(r) for r in rlist]
        last_pair = ''.join(s[-2:])
        transitions = {}
        for i in range(1, len(s)-1):
            pair = ''.join(s[i-1:i+1])
            if pair not in transitions:
                transitions[pair] = {'B': 0, 'S': 0}
            transitions[pair][s[i+1]] += 1
        t = transitions.get(last_pair)
        if t and (t['B'] + t['S']) >= 3:
            total = t['B'] + t['S']
            pred = 'B' if t['B'] > t['S'] else 'S'
            return {'pred': pred, 'strength': abs(t['B'] - t['S']) / total}
        return None

    def predict_next(self, historical_data):
        data = list(self.results) if len(self.results) > 20 else historical_data
        self.update_markov(data)

        strategies = [
            {'name': 'markov',    'result': self.markov_predict(data),       'weight': 2.0},
            {'name': 'streak',    'result': self.streak_reversal(data),       'weight': 1.8},
            {'name': 'alt',       'result': self.alternating_predict(data),   'weight': 1.6},
            {'name': 'double',    'result': self.double_pattern(data),        'weight': 1.4},
            {'name': 'meanrev',   'result': self.mean_reversion(data),        'weight': 1.3},
            {'name': 'momentum',  'result': self.momentum(data),              'weight': 1.5},
            {'name': 'zigzag',    'result': self.zigzag_predict(data),        'weight': 1.4},
            {'name': 'fibonacci', 'result': self.fibonacci_window(data),      'weight': 1.2},
            {'name': 'window',    'result': self.window_consensus(data),      'weight': 1.3},
            {'name': 'pair',      'result': self.pair_transition(data),       'weight': 1.6},
        ]

        score_b, score_s, used = 0, 0, 0
        for strat in strategies:
            if not strat['result']:
                continue
            weighted = strat['result']['strength'] * strat['weight']
            if strat['result']['pred'] == 'B':
                score_b += weighted
            else:
                score_s += weighted
            used += 1

        raw_pred = 'B' if score_b >= score_s else 'S'
        total_score = max(score_b + score_s, 0.01)
        dominance = abs(score_b - score_s) / total_score

        conf = 60
        conf += dominance * 25
        conf += min(15, used * 1.5)
        if len(data) > 50:
            conf += 5
        if self.consecutive_errors == 0 and len(data) > 10:
            conf += 5
        elif self.consecutive_errors >= 3:
            conf -= 12
        if len(self.recent_accuracy) >= 10:
            r_rate = sum(self.recent_accuracy) / len(self.recent_accuracy)
            conf = conf * 0.65 + r_rate * 100 * 0.35
        conf = max(54, min(91, conf))
        self.confidence = conf

        numbers = [5, 6, 7, 8, 9] if raw_pred == 'B' else [0, 1, 2, 3, 4]
        return {
            'pred': raw_pred,
            'conf': round(conf),
            'numbers': numbers,
            'label': 'BIG 🔴' if raw_pred == 'B' else 'SMALL 🔵',
        }

    def learn(self, last_pred, actual_num):
        actual_size = 'B' if actual_num >= 5 else 'S'
        correct = last_pred == actual_size
        self.recent_accuracy.append(1 if correct else 0)
        if correct:
            self.confidence = min(91, self.confidence + 2)
            self.consecutive_errors = 0
        else:
            self.confidence = max(54, self.confidence - 5)
            self.consecutive_errors += 1
        return correct

    def update(self, new_result):
        self.results.append(new_result)


# ══════════════════════════════════════════════
#  📡  STATE
# ══════════════════════════════════════════════
predictor = RealTimePredictor()
state = {
    'last_issue': None,
    'current_prediction': None,
    'current_result': 0,
    'stats': {'wins': 0, 'losses': 0},
    'streak': 0,
    'history': [],
    'subscribers': set(),   # chat_id list — auto-send prediction
}


# ══════════════════════════════════════════════
#  🌐  API FETCH
# ══════════════════════════════════════════════
def fetch_latest():
    try:
        r = requests.get(API_URL, timeout=6)
        data = r.json()
        if data.get('success') and data.get('data', {}).get('results'):
            return data['data']['results']
    except Exception as e:
        logger.error(f"API error: {e}")
    return None


# ══════════════════════════════════════════════
#  📨  FORMAT MESSAGE
# ══════════════════════════════════════════════
def format_prediction_msg(prediction, period, stats):
    total = stats['wins'] + stats['losses']
    win_rate = f"{round(stats['wins']/total*100)}%" if total > 0 else "N/A"
    nums = ' '.join(str(n) for n in prediction['numbers'])
    bar_filled = int(prediction['conf'] / 10)
    bar = '█' * bar_filled + '░' * (10 - bar_filled)

    return (
        f"🔮 *UniquEnigma 1Min Prediction*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Period: `{period}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Prediction: *{prediction['label']}*\n"
        f"🔢 Numbers: `{nums}`\n"
        f"📊 Confidence: `{prediction['conf']}%`\n"
        f"     `{bar}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Wins: {stats['wins']}  ❌ Losses: {stats['losses']}\n"
        f"📈 Win Rate: {win_rate}\n"
        f"🔥 Streak: {state['streak']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ _AI-V4 • UniquEnigma_"
    )

def format_result_msg(issue, result, pred, won):
    actual_label = "BIG 🔴" if result >= 5 else "SMALL 🔵"
    pred_label = "BIG 🔴" if pred == 'B' else "SMALL 🔵"
    status = "✅ WIN 🎉" if won else "❌ LOSS"
    return (
        f"{'🎉' if won else '💔'} *Result Update*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Period: `{str(issue)[-6:]}`\n"
        f"🎱 Result: *{result}* ({actual_label})\n"
        f"🎯 Predicted: {pred_label}\n"
        f"🏆 Status: {status}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ {state['stats']['wins']}W  ❌ {state['stats']['losses']}L  🔥 Streak: {state['streak']}"
    )


# ══════════════════════════════════════════════
#  ⏱  BACKGROUND AUTO-SEND LOOP
# ══════════════════════════════════════════════
async def prediction_loop(app: Application):
    """Runs every 60 seconds, sends prediction to all subscribers"""
    while True:
        await asyncio.sleep(REFRESH_SECONDS)
        raw = fetch_latest()
        if not raw:
            continue

        latest = raw[0]
        latest_issue = latest.get('issue_number', 'unknown')
        latest_num = int(latest.get('result_number', 0))
        historical = list(reversed([int(i['result_number']) for i in raw]))

        # First time init
        if not state['last_issue']:
            predictor.analyze_history(historical)
            state['last_issue'] = latest_issue
            state['current_result'] = latest_num
            state['current_prediction'] = predictor.predict_next(historical)

        # New period detected
        if latest_issue != state['last_issue']:
            # Evaluate previous prediction
            if state['current_prediction']:
                won = predictor.learn(state['current_prediction']['pred'], latest_num)
                if won:
                    state['stats']['wins'] += 1
                    state['streak'] += 1
                else:
                    state['stats']['losses'] += 1
                    state['streak'] = 0

                result_msg = format_result_msg(
                    latest_issue, latest_num,
                    state['current_prediction']['pred'], won
                )
                for chat_id in list(state['subscribers']):
                    try:
                        await app.bot.send_message(
                            chat_id=chat_id,
                            text=result_msg,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.warning(f"Send error to {chat_id}: {e}")

            # New prediction
            predictor.update(latest_num)
            state['last_issue'] = latest_issue
            state['current_result'] = latest_num
            state['current_prediction'] = predictor.predict_next(historical)

            try:
                period_display = str(int(latest_issue) + 1)[-6:]
            except Exception:
                period_display = str(latest_issue)[-6:]

            pred_msg = format_prediction_msg(
                state['current_prediction'], period_display, state['stats']
            )
            for chat_id in list(state['subscribers']):
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=pred_msg,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Send error to {chat_id}: {e}")


# ══════════════════════════════════════════════
#  📲  COMMANDS
# ══════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 *UniquEnigma 1Min Bot* வரவேற்கிறோம்!\n\n"
        "📋 *Commands:*\n"
        "• /predict — இப்போது prediction பாருங்கள்\n"
        "• /subscribe — Auto predictions ON\n"
        "• /unsubscribe — Auto predictions OFF\n"
        "• /stats — Win/Loss stats\n"
        "• /history — Last 10 results\n"
        "• /help — Help\n\n"
        "⚡ _AI-V4 Ensemble Predictor_",
        parse_mode='Markdown'
    )

async def cmd_predict(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = fetch_latest()
    if not raw:
        await update.message.reply_text("❌ API-ல இருந்து data வரவில்லை. மீண்டும் try செய்யுங்கள்.")
        return

    latest = raw[0]
    latest_issue = latest.get('issue_number', 'unknown')
    latest_num = int(latest.get('result_number', 0))
    historical = list(reversed([int(i['result_number']) for i in raw]))

    if not state['last_issue']:
        predictor.analyze_history(historical)
        state['last_issue'] = latest_issue
        state['current_result'] = latest_num
        state['current_prediction'] = predictor.predict_next(historical)

    if not state['current_prediction']:
        state['current_prediction'] = predictor.predict_next(historical)

    try:
        period_display = str(int(latest_issue) + 1)[-6:]
    except Exception:
        period_display = str(latest_issue)[-6:]

    msg = format_prediction_msg(state['current_prediction'], period_display, state['stats'])
    await update.message.reply_text(msg, parse_mode='Markdown')

async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state['subscribers'].add(chat_id)
    await update.message.reply_text(
        "✅ *Subscribe ஆனீர்கள்!*\n\n"
        "ஒவ்வொரு new period-லயும் prediction & result automatic-ஆ வரும்! 🔔",
        parse_mode='Markdown'
    )

async def cmd_unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state['subscribers'].discard(chat_id)
    await update.message.reply_text("🔕 Unsubscribed. `/subscribe` போட்டால் மீண்டும் start ஆகும்.", parse_mode='Markdown')

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    s = state['stats']
    total = s['wins'] + s['losses']
    win_rate = f"{round(s['wins']/total*100)}%" if total > 0 else "N/A"
    await update.message.reply_text(
        f"📊 *Statistics*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Wins: {s['wins']}\n"
        f"❌ Losses: {s['losses']}\n"
        f"📈 Win Rate: {win_rate}\n"
        f"🔥 Current Streak: {state['streak']}\n"
        f"📋 Total Rounds: {total}",
        parse_mode='Markdown'
    )

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not state['history']:
        await update.message.reply_text("📭 History இல்லை. சிறிது நேரம் காத்திருங்கள்.")
        return
    lines = []
    for item in list(reversed(state['history']))[:10]:
        icon = "✅" if item['status'] == 'WIN' else "❌"
        pred_label = "BIG" if item['pred'] == 'B' else "SMALL"
        actual_label = "BIG" if item['result'] >= 5 else "SMALL"
        lines.append(f"{icon} `{str(item['issue'])[-6:]}` | Pred: {pred_label} | Result: {item['result']} ({actual_label})")
    await update.message.reply_text(
        "📋 *Last 10 Results*\n━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lines),
        parse_mode='Markdown'
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Help*\n\n"
        "🔮 இந்த bot UniquEnigma 1Min prediction-ஐ Telegram-ல் தருகிறது.\n\n"
        "📋 *Commands:*\n"
        "`/predict` — இப்போதைய prediction பாருங்கள்\n"
        "`/subscribe` — Auto send ON (every period)\n"
        "`/unsubscribe` — Auto send OFF\n"
        "`/stats` — Win/Loss statistics\n"
        "`/history` — Last 10 results\n\n"
        "⚙️ _AI-V4 Ensemble: Markov + Streak + Momentum + 7 more strategies_",
        parse_mode='Markdown'
    )


# ══════════════════════════════════════════════
#  🚀  MAIN
# ══════════════════════════════════════════════
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ BOT_TOKEN மாற்றவில்லை! uniquenigma_bot.py-ல் உங்கள் token போடுங்கள்.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("predict", cmd_predict))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("help", cmd_help))

    # Start background prediction loop
    async def post_init(app):
        asyncio.create_task(prediction_loop(app))

    app.post_init = post_init

    print("🤖 UniquEnigma Bot தொடங்குகிறது...")
    app.run_polling(drop_pending_updates=True)

# Monkey-patch helper used in loop
def _analyze_history(self, results):
    self.results = deque(results, maxlen=500)
    self.update_markov(list(results))

RealTimePredictor.analyze_history = _analyze_history

if __name__ == "__main__":
    main()
