# 部署到腾讯云服务器

bot 用 **Telegram 长轮询**(不是 webhook),所以服务器:
- ✅ 不需要域名
- ✅ 不需要 SSL 证书
- ✅ 不需要开放任何入站端口
- ✅ 只要能出网就行

需要的资源:**1 核 1G(或 2G) Linux 服务器** 即可。

---

## 一、选服务器:重点看地域

| 地域 | 直连 Telegram | 直连小米 MiMo | 推荐 |
|------|---------------|---------------|------|
| 香港 / 新加坡 / 硅谷 (轻量) | ✅ | ✅ | **强烈推荐** |
| 北京 / 上海 / 广州 (国内) | ❌ 必须代理 | ✅ | 看你有没有现成代理 |

### 推荐方案 A:腾讯云轻量应用服务器 - 境外地域

- 控制台 → 轻量应用服务器 → 新建实例
- **地域选**:香港 / 新加坡 / 硅谷(任意一个,香港延迟最低)
- **镜像**:Ubuntu 22.04 LTS 或 Debian 12
- **套餐**:最低档(1核1G,24元/月左右)就够
- 创建好后,在控制台「防火墙」里**不需要**额外开端口(默认 22 SSH 够了)

### 方案 B:国内地域 + 代理

如果你已经有 CVM 在国内,需要在那台机或者另一台机上跑 HTTP/SOCKS5 代理(比如 [Xray](https://github.com/XTLS/Xray-core)、Clash 等),然后把代理地址填进 `.env` 的 `TG_PROXY`。具体搭代理的方法不在本文档范围内。

---

## 二、上传代码到服务器

在你**本地 PowerShell**(项目目录下)执行,把项目同步到服务器:

```powershell
# 把 1.2.3.4 换成你的服务器公网 IP,Ubuntu/Debian 默认 root,有些镜像是 ubuntu
# 如果不是 root 用户,后面命令前都加 sudo
scp -r . root@1.2.3.4:/opt/telegrambot
```

> **注意:** `.env` 文件包含真实 token,会一起被 scp 上去。如果不希望上传,先 `del .env` 再 scp,然后到服务器上重新建 `.env`。

或者你也可以上传到自己的 GitHub 然后服务器上 `git clone`(注意 `.env` 别提交)。

---

## 三、在服务器上一键部署

SSH 登录服务器:

```bash
ssh root@1.2.3.4
```

跑部署脚本:

```bash
sudo bash /opt/telegrambot/deploy/install.sh
```

脚本会自动:
1. 安装 `python3`、`python3-venv`、`pip`(支持 apt / dnf / yum)
2. 创建 `.venv` 虚拟环境
3. 安装 `requirements.txt`
4. 复制 `.env.example` → `.env`(如果还没有)
5. 安装 `systemd` 服务并设为开机自启

---

## 四、配置 `.env`

```bash
sudo nano /opt/telegrambot/.env
```

按你之前确认过的内容填:

```ini
BOT_TOKEN=8651040585:AAH...           # ⚠️ 记得已经泄露的去 BotFather revoke
TG_PROXY=                              # 境外服务器留空,国内填 socks5://x.x.x.x:port

MIMO_AUTH_STYLE=xiaomi
MIMO_API_KEY=小米给你的 key
MIMO_BASE_URL=小米给你的 BASE_URL  (到 /v1 为止,不带 /chat/completions)
MIMO_MODEL=mimo-v2.5-pro
```

保存退出(nano: Ctrl+O 回车,Ctrl+X)。

---

## 五、启动 & 查看

```bash
sudo systemctl start telegrambot          # 启动
sudo systemctl status telegrambot         # 看状态(active=运行中)
sudo journalctl -u telegrambot -f         # 实时看日志(Ctrl+C 退出查看)
```

启动成功你应该能看到:
```
INFO - MiMo enabled: model=mimo-v2.5-pro base=...
INFO - Bot starting... 按 Ctrl+C 退出
INFO - Application started
```

打开 Telegram 找你的 bot,发 `/start` 测试。

---

## 六、常用运维命令

```bash
# 重启(改完 .env 必须重启才生效)
sudo systemctl restart telegrambot

# 停止
sudo systemctl stop telegrambot

# 关闭开机自启
sudo systemctl disable telegrambot

# 查最近 200 行日志
sudo journalctl -u telegrambot -n 200 --no-pager

# 更新代码(本地改完,在本地跑)
scp -r . root@1.2.3.4:/opt/telegrambot
# 然后在服务器上重启
ssh root@1.2.3.4 "sudo systemctl restart telegrambot"
```

---

## 七、踩坑速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `httpx.ConnectTimeout` 连 telegram | 国内服务器没配代理 | 填 `TG_PROXY` 或换境外地域 |
| `401 Invalid token` | API key 错或 BOT_TOKEN 泄露被吊销 | 重新生成 |
| `404 model not found` | `MIMO_MODEL` 写错 | 检查官方文档 |
| 服务起不来 | 9 成是 `.env` 配置问题 | 看 `journalctl -u telegrambot -n 50` |
| `Conflict: terminated by other getUpdates` | 同一个 token 被多个进程用 | 关掉本地的 `python bot.py`,只保留服务器一份 |

---

## 八、安全建议

- `.env` 已经设了 `chmod 600`,只有 root 能读
- 防火墙除了 22(SSH)别的端口都不需要开
- 强烈建议改 SSH 端口、禁用密码登录改用密钥
- 定期 `sudo apt update && sudo apt upgrade -y` 打补丁
