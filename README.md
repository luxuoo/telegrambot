# 好玩 Bot 🤖

一个用 Python 写的多功能 Telegram 机器人,**直接对话接入小米 MiMo 大模型**,自带各种小游戏、占卜、笑话、萌宠图片。

## ✨ 功能一览

- 🤖 **AI 闲聊**:接入小米 MiMo(OpenAI 兼容协议),多轮上下文,可一键 `/reset`
- 🎲 掷骰子 / 抛硬币 / 投飞镖(Telegram 原生动画)
- ✊ 石头剪刀布对战(内联键盘按钮)
- 🎯 1-100 猜数字游戏(带次数评分)
- 🔮 今日运势(同一个人当天结果一致)
- 🃏 塔罗牌占卜(22 张大阿卡那 + 30% 概率逆位)
- 😂 中文冷笑话 / 段子
- 💬 一言名句(调用 hitokoto.cn)
- 💛 鼓励语 / 🐟 摸鱼语录
- 🐱🐶🦊 随机猫猫狗狗狐狸图片
- 📡 摩斯密码编码 / 文字反转 / 帮我做选择
- 📋 主菜单内联键盘,点点就能玩

## 🚀 快速开始

### 1. 拿到 Bot Token

在 Telegram 找 [@BotFather](https://t.me/BotFather),发 `/newbot` 跟着提示创建一个机器人,把 token 拿好。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> 建议先建虚拟环境:`python -m venv .venv && .venv\Scripts\activate`(Windows)

### 3. 配置 .env

把 `.env.example` 复制为 `.env`,填好两组配置:

```ini
# Telegram
BOT_TOKEN=你的token

# 小米 MiMo
MIMO_API_KEY=sk-xxx
MIMO_BASE_URL=https://api.siliconflow.cn/v1
MIMO_MODEL=XiaomiMiMo/MiMo-7B-RL
```

**MiMo 接入支持任何 OpenAI 兼容服务**,常见三种:

| 服务 | base_url | model |
|------|----------|-------|
| 硅基流动(推荐) | `https://api.siliconflow.cn/v1` | `XiaomiMiMo/MiMo-7B-RL` |
| 自建 vLLM | `http://localhost:8000/v1` | 你的模型路径 |
| 自建 Ollama | `http://localhost:11434/v1` | `mimo` |

> MiMo 不配置也能跑,只是直接发文本时会回退到静态提示,游戏占卜功能完全不受影响。

### 4. 跑起来

```bash
python bot.py
```

在 Telegram 找你的 bot,发 `/start` 就能玩;直接发任何文本就会调用 MiMo。

## 📂 项目结构

```
telegrambot/
├── bot.py              # 主程序、所有命令和回调
├── mimo.py             # MiMo 大模型客户端 (OpenAI 兼容协议)
├── data.py             # 静态数据(笑话、运势、塔罗等)
├── requirements.txt    # 依赖
├── .env.example        # 环境变量模板
├── deploy/
│   ├── install.sh      # 服务器一键部署脚本
│   └── telegrambot.service  # systemd 服务文件
├── DEPLOY.md           # 部署到腾讯云的完整文档
└── README.md
```

## 🛠️ 想加点别的功能?

- 想加新命令:在 `bot.py` 里新写一个 `async def xxx_cmd(...)`,然后在 `build_app()` 里 `app.add_handler(CommandHandler("xxx", xxx_cmd))`
- 想换/加段子运势:直接改 `data.py` 就行
- 想加新关键词回复:往 `data.py` 的 `KEYWORD_REPLIES` 里塞

## 📝 命令速查

| 命令 | 功能 |
|------|------|
| `/start` | 欢迎页 + 主菜单 |
| `/help` | 完整功能列表 |
| `/menu` | 调出主菜单 |
| `/ai 问题` | 显式调用 MiMo 大模型 |
| `/reset` | 清空 AI 对话上下文 |
| `/dice` `/coin` `/dart` | 骰子 / 硬币 / 飞镖 |
| `/rps` | 石头剪刀布 |
| `/guess` `/stopguess` | 猜数字游戏 |
| `/fortune` `/tarot` | 运势 / 塔罗 |
| `/joke` `/hito` `/cheer` `/slogan` | 段子 / 一言 / 鼓励 / 摸鱼 |
| `/cat` `/dog` `/fox` | 萌宠图片 |
| `/reverse 文字` | 反转文字 |
| `/morse HELLO` | 摩斯密码 |
| `/choose A\|B\|C` | 帮你选一个 |

> 💡 直接给 bot 发任何文本消息就会调用 MiMo 闲聊;问候 / emo 等关键词会走本地秒回。

享受调戏 bot 的快乐吧 🎉
