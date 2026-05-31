"""一个好玩的多功能 Telegram 机器人。"""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from typing import Dict

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from data import (
    ENCOURAGEMENTS,
    FORTUNES,
    JOKES,
    KEYWORD_REPLIES,
    RPS_EMOJI,
    RPS_NAME,
    SLOGANS,
    TAROT,
)
from mimo import MimoClient, from_env as build_mimo

# ---------- 基础配置 ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Telegram 出网代理 (国内服务器需要),例:http://127.0.0.1:7890 或 socks5://user:pwd@host:port
TG_PROXY = os.getenv("TG_PROXY", "").strip() or None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# 屏蔽一下 httpx 的噪音
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# 猜数字游戏的进行中状态(按 chat_id 存)
guess_games: Dict[int, Dict] = {}

# MiMo 客户端,在 main() 里初始化
mimo: MimoClient | None = None


# ---------- 通用命令 ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = (
        f"嘿,{user.mention_html()}!欢迎来到 <b>好玩 Bot</b> 🎉\n\n"
        "我会陪你打发无聊时间,也会给你算命占卜讲段子。\n"
        "输入 /help 查看所有功能,或者直接跟我聊天试试 ✨"
    )
    await update.message.reply_html(text, reply_markup=main_menu_keyboard())


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """主菜单内联键盘。"""
    buttons = [
        [
            InlineKeyboardButton("🎲 骰子", callback_data="dice"),
            InlineKeyboardButton("🪙 抛硬币", callback_data="coin"),
            InlineKeyboardButton("🎯 飞镖", callback_data="dart"),
        ],
        [
            InlineKeyboardButton("😂 讲笑话", callback_data="joke"),
            InlineKeyboardButton("🔮 今日运势", callback_data="fortune"),
            InlineKeyboardButton("🃏 抽塔罗", callback_data="tarot"),
        ],
        [
            InlineKeyboardButton("🐱 猫猫", callback_data="cat"),
            InlineKeyboardButton("🐶 狗狗", callback_data="dog"),
            InlineKeyboardButton("🦊 狐狸", callback_data="fox"),
        ],
        [
            InlineKeyboardButton("✊ 石头剪刀布", callback_data="rps"),
            InlineKeyboardButton("🎯 猜数字", callback_data="guess_start"),
        ],
        [
            InlineKeyboardButton("💬 一言", callback_data="hito"),
            InlineKeyboardButton("💛 鼓励一下", callback_data="cheer"),
            InlineKeyboardButton("🐟 摸鱼语录", callback_data="slogan"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>📖 功能列表</b>\n\n"
        "<b>🤖 AI 闲聊 (小米 MiMo)</b>\n"
        "/ai 你的问题 - 显式调用 AI\n"
        "/reset - 清空会话上下文\n"
        "<i>(直接发文本消息也会自动调用 AI)</i>\n\n"
        "<b>娱乐互动</b>\n"
        "/dice - 掷骰子 🎲\n"
        "/coin - 抛硬币 🪙\n"
        "/dart - 投飞镖 🎯\n"
        "/rps - 石头剪刀布 ✊✋✌️\n"
        "/guess - 猜数字游戏 (1-100)\n\n"
        "<b>占卜玄学</b>\n"
        "/fortune - 今日运势 🔮\n"
        "/tarot - 抽一张塔罗牌 🃏\n\n"
        "<b>放松一下</b>\n"
        "/joke - 来个段子 😂\n"
        "/hito - 一言 / 名言警句 💬\n"
        "/cheer - 鼓励一下我 💛\n"
        "/slogan - 打工人语录 🐟\n\n"
        "<b>萌宠图片</b>\n"
        "/cat - 随机猫猫 🐱\n"
        "/dog - 随机狗狗 🐶\n"
        "/fox - 随机狐狸 🦊\n\n"
        "<b>实用工具</b>\n"
        "/reverse 文字 - 反转文字\n"
        "/morse 文字 - 摩斯密码\n"
        "/choose A|B|C - 帮你选一个\n"
        "/menu - 调出主菜单"
    )
    await update.message.reply_html(text)


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("点点看想玩什么 👇", reply_markup=main_menu_keyboard())


# ---------- 娱乐:骰子/硬币/飞镖 ----------
async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.effective_chat.send_dice(emoji="🎲")
    await update.effective_chat.send_message(f"你掷出了 <b>{msg.dice.value}</b> 点!", parse_mode=ParseMode.HTML)


async def coin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = random.choice(["正面 👑", "反面 🪙"])
    await update.effective_chat.send_message(f"硬币飞起来啦...\n\n结果是: <b>{result}</b>", parse_mode=ParseMode.HTML)


async def dart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.effective_chat.send_dice(emoji="🎯")
    score = msg.dice.value
    if score == 6:
        comment = "正中红心!神枪手!🎯✨"
    elif score >= 4:
        comment = "靠近中心,不错!"
    else:
        comment = "再练练吧 😅"
    await update.effective_chat.send_message(f"得分: <b>{score}</b> — {comment}", parse_mode=ParseMode.HTML)


# ---------- 段子/运势/塔罗 ----------
async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message("😂 " + random.choice(JOKES))


async def fortune_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 用日期+用户ID做种子,这样同一个人当天结果一致
    user_id = update.effective_user.id
    seed = int(datetime.now().strftime("%Y%m%d")) + user_id
    rnd = random.Random(seed)
    title, desc, good, bad = rnd.choice(FORTUNES)
    text = (
        f"<b>🔮 今日运势 · {title}</b>\n\n"
        f"{desc}\n\n"
        f"✅ {good}\n"
        f"❌ {bad}\n\n"
        f"<i>(每日 0 点刷新)</i>"
    )
    await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML)


async def tarot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name, meaning = random.choice(TAROT)
    reversed_card = random.random() < 0.3  # 30% 概率逆位
    pos = "逆位 🔄" if reversed_card else "正位 ⬆️"
    text = (
        f"<b>🃏 你抽到了:{name}</b>\n"
        f"位置:<b>{pos}</b>\n\n"
        f"{meaning}\n"
        f"{'(逆位往往提示需要反思相反的一面)' if reversed_card else ''}"
    )
    await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML)


# ---------- 一言 / 鼓励 / 摸鱼 ----------
async def hitokoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """从 hitokoto.cn 拉一句话。"""
    await update.effective_chat.send_chat_action(ChatAction.TYPING)
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get("https://v1.hitokoto.cn/?c=a&c=b&c=c&c=d&c=i&c=j&c=k")
            r.raise_for_status()
            data = r.json()
        text = f"💬 <i>{data['hitokoto']}</i>\n\n—— {data.get('from', '佚名')}"
        await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.warning("hitokoto failed: %s", e)
        await update.effective_chat.send_message("💬 " + random.choice(ENCOURAGEMENTS))


async def cheer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(random.choice(ENCOURAGEMENTS))


async def slogan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message("🐟 " + random.choice(SLOGANS))


# ---------- 萌宠图片 ----------
async def _send_photo_safe(update: Update, url: str, caption: str, fallback: str) -> None:
    try:
        await update.effective_chat.send_photo(photo=url, caption=caption)
    except Exception as e:
        logger.warning("send_photo failed: %s", e)
        await update.effective_chat.send_message(fallback)


async def cat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_chat_action(ChatAction.UPLOAD_PHOTO)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.thecatapi.com/v1/images/search")
            r.raise_for_status()
            url = r.json()[0]["url"]
        await _send_photo_safe(update, url, "🐱 喵~", "找不到猫猫了 😢")
    except Exception as e:
        logger.warning("cat api failed: %s", e)
        await update.effective_chat.send_message("猫猫去散步了,稍后再试 🐱")


async def dog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_chat_action(ChatAction.UPLOAD_PHOTO)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://dog.ceo/api/breeds/image/random")
            r.raise_for_status()
            url = r.json()["message"]
        await _send_photo_safe(update, url, "🐶 汪!", "狗狗去骨头店了 😢")
    except Exception as e:
        logger.warning("dog api failed: %s", e)
        await update.effective_chat.send_message("狗狗在啃骨头,稍后再来 🐶")


async def fox_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_chat_action(ChatAction.UPLOAD_PHOTO)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://randomfox.ca/floof/")
            r.raise_for_status()
            url = r.json()["image"]
        await _send_photo_safe(update, url, "🦊 嗷呜~", "狐狸躲进森林了 😢")
    except Exception as e:
        logger.warning("fox api failed: %s", e)
        await update.effective_chat.send_message("狐狸跑啦,稍后再试 🦊")


# ---------- 石头剪刀布 ----------
async def rps_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✊ 石头", callback_data="rps:rock"),
                InlineKeyboardButton("✋ 布", callback_data="rps:paper"),
                InlineKeyboardButton("✌️ 剪刀", callback_data="rps:scissors"),
            ]
        ]
    )
    await update.effective_chat.send_message("出招吧!选一个 👇", reply_markup=kb)


def _rps_judge(user: str, bot: str) -> str:
    if user == bot:
        return "平局!再来一局?"
    wins = {("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")}
    return "你赢了!🎉" if (user, bot) in wins else "我赢啦 😎"


# ---------- 猜数字 ----------
async def guess_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    target = random.randint(1, 100)
    guess_games[chat_id] = {"target": target, "tries": 0}
    await update.effective_chat.send_message(
        "🎯 我心里想了个 <b>1-100</b> 的数,直接发数字给我猜!\n发 /stopguess 可以放弃。",
        parse_mode=ParseMode.HTML,
    )


async def stop_guess_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    game = guess_games.pop(chat_id, None)
    if game:
        await update.effective_chat.send_message(f"游戏结束,正确答案是 <b>{game['target']}</b> 😏", parse_mode=ParseMode.HTML)
    else:
        await update.effective_chat.send_message("现在没有进行中的游戏哦,/guess 开一局?")


# ---------- 实用工具 ----------
async def reverse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("用法:/reverse 你想反转的文字")
        return
    text = " ".join(context.args)
    await update.message.reply_text(text[::-1])


# 摩斯密码表
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "!": "-.-.--", " ": "/",
}


async def morse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("用法:/morse HELLO WORLD (仅支持英文/数字/标点)")
        return
    text = " ".join(context.args).upper()
    encoded = " ".join(MORSE.get(ch, "?") for ch in text)
    await update.message.reply_text(f"📡 {encoded}")


async def choose_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = " ".join(context.args) if context.args else ""
    if not raw:
        await update.message.reply_text("用法:/choose 火锅|烧烤|麻辣烫")
        return
    options = [o.strip() for o in raw.replace(",", "|").replace(",", "|").split("|") if o.strip()]
    if len(options) < 2:
        await update.message.reply_text("至少给我两个选项嘛(用 | 分隔)")
        return
    await update.message.reply_text(f"🎯 我帮你选了:<b>{random.choice(options)}</b>", parse_mode=ParseMode.HTML)


# ---------- AI 闲聊 (MiMo) ----------
async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """显式让 MiMo 回答。/ai 你想问的问题"""
    if not context.args:
        await update.message.reply_text("用法:/ai 你想问的问题\n或者直接给我发文本消息也行 ✨")
        return
    text = " ".join(context.args)
    await _ai_reply(update, text)


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """清空当前会话的 MiMo 上下文。"""
    if mimo is None:
        await update.message.reply_text("AI 没启用,清空个寂寞 😅")
        return
    chat_id = update.effective_chat.id
    n = mimo.history_size(chat_id)
    mimo.reset(chat_id)
    await update.message.reply_text(f"🧹 已清空对话上下文(原本 {n} 条历史)。")


async def _ai_reply(update: Update, user_text: str) -> None:
    """统一调用 MiMo 并把回复发出去。"""
    if mimo is None:
        await update.message.reply_text(
            "AI 还没配置好哦,管理员需要在 .env 里填上 MIMO_API_KEY / MIMO_BASE_URL / MIMO_MODEL"
        )
        return
    chat_id = update.effective_chat.id
    await update.effective_chat.send_chat_action(ChatAction.TYPING)
    try:
        reply = await mimo.chat(chat_id, user_text)
    except RuntimeError as e:
        await update.message.reply_text(f"⚠️ {e}")
        return
    except Exception as e:  # noqa: BLE001
        logger.exception("mimo chat failed: %s", e)
        await update.message.reply_text("⚠️ 我刚刚走神了,再说一遍?")
        return

    if not reply:
        await update.message.reply_text("（沉默）")
        return

    # Telegram 单条消息上限 4096,超长就拆
    for chunk in _split_for_telegram(reply, 3500):
        await update.message.reply_text(chunk)


def _split_for_telegram(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    out, buf = [], []
    cur = 0
    for line in text.splitlines(keepends=True):
        if cur + len(line) > size and buf:
            out.append("".join(buf))
            buf, cur = [line], len(line)
        else:
            buf.append(line)
            cur += len(line)
    if buf:
        out.append("".join(buf))
    return out


# ---------- 闲聊 / 数字猜测处理 ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # 1) 如果有进行中的猜数字游戏,优先处理
    if chat_id in guess_games and text.lstrip("-").isdigit():
        await _handle_guess(update, int(text))
        return

    # 2) 关键词回复(短词、问候、emo 等,本地秒回,省 token)
    lower = text.lower()
    for keys, replies in KEYWORD_REPLIES.items():
        if any(k in lower for k in keys):
            await update.message.reply_text(random.choice(replies))
            return

    # 3) 兜底:交给 MiMo 大模型;没配置时给静态提示
    if mimo is not None:
        await _ai_reply(update, text)
        return

    fallback = random.choice(
        [
            "嗯嗯,我在听 👂 (输入 /help 看看我会啥)",
            "这个我还学不会哎,要不来玩点别的?/menu",
            "懂了懂了(其实没懂)。试试 /joke 听个段子?",
            "你说得好对,但我建议 /fortune 看看今日运势 🔮",
        ]
    )
    await update.message.reply_text(fallback)


async def _handle_guess(update: Update, num: int) -> None:
    chat_id = update.effective_chat.id
    game = guess_games[chat_id]
    game["tries"] += 1
    target = game["target"]

    if num < 1 or num > 100:
        await update.message.reply_text("范围是 1-100 哦~")
        return

    if num == target:
        tries = game["tries"]
        guess_games.pop(chat_id, None)
        if tries <= 5:
            comment = "神准!🎯"
        elif tries <= 8:
            comment = "不错不错 👍"
        else:
            comment = "终于猜到了 😅"
        await update.message.reply_html(
            f"🎉 答对啦!就是 <b>{target}</b>,你用了 <b>{tries}</b> 次。{comment}\n\n再来一局发 /guess 吧!"
        )
    elif num < target:
        await update.message.reply_text("太小啦,大点 ⬆️")
    else:
        await update.message.reply_text("太大啦,小点 ⬇️")


# ---------- 回调按钮分发 ----------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    # 石头剪刀布
    if data.startswith("rps:"):
        user_choice = data.split(":", 1)[1]
        bot_choice = random.choice(["rock", "paper", "scissors"])
        result = _rps_judge(user_choice, bot_choice)
        await query.edit_message_text(
            f"你出: {RPS_EMOJI[user_choice]} {RPS_NAME[user_choice]}\n"
            f"我出: {RPS_EMOJI[bot_choice]} {RPS_NAME[bot_choice]}\n\n"
            f"<b>{result}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    # 主菜单按钮 -> 复用对应命令逻辑
    handlers = {
        "dice": dice_cmd,
        "coin": coin_cmd,
        "dart": dart_cmd,
        "joke": joke_cmd,
        "fortune": fortune_cmd,
        "tarot": tarot_cmd,
        "cat": cat_cmd,
        "dog": dog_cmd,
        "fox": fox_cmd,
        "rps": rps_cmd,
        "guess_start": guess_cmd,
        "hito": hitokoto_cmd,
        "cheer": cheer_cmd,
        "slogan": slogan_cmd,
    }
    handler = handlers.get(data)
    if handler:
        await handler(update, context)


# ---------- 启动 ----------
def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("没找到 BOT_TOKEN,请把它写在 .env 里(参考 .env.example)")

    # 代理:国内服务器跑 telegram 必须走代理
    builder = Application.builder().token(BOT_TOKEN)
    if TG_PROXY:
        logger.info("Telegram 走代理: %s", TG_PROXY)
        builder = builder.proxy(TG_PROXY).get_updates_proxy(TG_PROXY)

    app = builder.build()

    # 命令
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("dice", dice_cmd))
    app.add_handler(CommandHandler("coin", coin_cmd))
    app.add_handler(CommandHandler("dart", dart_cmd))
    app.add_handler(CommandHandler("joke", joke_cmd))
    app.add_handler(CommandHandler("fortune", fortune_cmd))
    app.add_handler(CommandHandler("tarot", tarot_cmd))
    app.add_handler(CommandHandler("cat", cat_cmd))
    app.add_handler(CommandHandler("dog", dog_cmd))
    app.add_handler(CommandHandler("fox", fox_cmd))
    app.add_handler(CommandHandler("rps", rps_cmd))
    app.add_handler(CommandHandler("guess", guess_cmd))
    app.add_handler(CommandHandler("stopguess", stop_guess_cmd))
    app.add_handler(CommandHandler("hito", hitokoto_cmd))
    app.add_handler(CommandHandler("cheer", cheer_cmd))
    app.add_handler(CommandHandler("slogan", slogan_cmd))
    app.add_handler(CommandHandler("reverse", reverse_cmd))
    app.add_handler(CommandHandler("morse", morse_cmd))
    app.add_handler(CommandHandler("choose", choose_cmd))
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))

    # 回调按钮
    app.add_handler(CallbackQueryHandler(callback_handler))

    # 文本兜底
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    return app


def main() -> None:
    global mimo
    mimo = build_mimo()
    if mimo:
        logger.info("MiMo enabled: model=%s base=%s", mimo.model, mimo.base_url)
    else:
        logger.info("MiMo not configured (set MIMO_BASE_URL & MIMO_MODEL in .env to enable)")

    app = build_app()
    logger.info("Bot starting... 按 Ctrl+C 退出")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
