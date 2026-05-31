#!/usr/bin/env bash
# 在腾讯云 Linux 服务器上一键部署 telegrambot。
# 用法:
#   1) 把整个项目目录上传到 /opt/telegrambot (见 README 的 scp 命令)
#   2) ssh 到服务器,执行:  sudo bash /opt/telegrambot/deploy/install.sh
set -euo pipefail

INSTALL_DIR="/opt/telegrambot"
SERVICE_NAME="telegrambot"

if [[ $EUID -ne 0 ]]; then
  echo "请用 sudo 运行此脚本" >&2
  exit 1
fi

echo "==> 检查项目目录"
if [[ ! -f "${INSTALL_DIR}/bot.py" ]]; then
  echo "找不到 ${INSTALL_DIR}/bot.py,请先把项目上传到 ${INSTALL_DIR}" >&2
  exit 1
fi

echo "==> 安装系统依赖 (python3, venv)"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y python3 python3-venv python3-pip
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y python3 python3-pip
elif command -v yum >/dev/null 2>&1; then
  yum install -y python3 python3-pip
else
  echo "未识别的发行版,请手动安装 python3 和 python3-venv" >&2
  exit 1
fi

echo "==> 创建虚拟环境"
cd "${INSTALL_DIR}"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

echo "==> 安装 Python 依赖"
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> 检查 .env"
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo "已从 .env.example 创建 .env,请编辑后再启动服务:  sudo nano ${INSTALL_DIR}/.env"
  else
    echo "缺少 .env 文件" >&2
    exit 1
  fi
fi
chmod 600 .env

echo "==> 安装 systemd 服务"
cp "${INSTALL_DIR}/deploy/telegrambot.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo ""
echo "✅ 部署完成。"
echo ""
echo "下一步:"
echo "  1. 编辑配置:   sudo nano ${INSTALL_DIR}/.env"
echo "  2. 启动服务:   sudo systemctl start ${SERVICE_NAME}"
echo "  3. 查看状态:   sudo systemctl status ${SERVICE_NAME}"
echo "  4. 查看日志:   sudo journalctl -u ${SERVICE_NAME} -f"
echo "  5. 重启服务:   sudo systemctl restart ${SERVICE_NAME}"
echo ""
