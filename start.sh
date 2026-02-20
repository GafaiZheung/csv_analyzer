#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  CSV Analyzer — 统一启动脚本
#  同时管理 Python 后端依赖 + Electron 前端依赖并启动应用
# ─────────────────────────────────────────────────────────
set -euo pipefail

# 项目根目录（脚本所在目录）
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── 颜色输出 ──
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }

# ── 1. Python 虚拟环境 ──
if [ ! -d ".venv" ]; then
  yellow "📦 创建 Python 虚拟环境 (.venv) ..."
  python3 -m venv .venv
fi

PYTHON="$ROOT/.venv/bin/python"
PIP="$ROOT/.venv/bin/pip"

if [ ! -f "$PYTHON" ]; then
  red "❌ Python 虚拟环境异常，找不到 $PYTHON"
  exit 1
fi

green "✅ Python: $($PYTHON --version)"

# ── 2. 安装 Python 依赖 ──
yellow "📦 检查 Python 依赖 ..."
$PIP install -q -e ".[all]" 2>/dev/null || $PIP install -q -e .
green "✅ Python 依赖已就绪"

# ── 3. Node.js / npm 检查 ──
if ! command -v node &>/dev/null; then
  red "❌ 未找到 Node.js，请先安装: https://nodejs.org/"
  exit 1
fi
if ! command -v npm &>/dev/null; then
  red "❌ 未找到 npm，请先安装 Node.js"
  exit 1
fi
green "✅ Node: $(node --version)  npm: $(npm --version)"

# ── 4. 安装 Electron / npm 依赖 ──
ELECTRON_DIR="$ROOT/electron"
if [ ! -d "$ELECTRON_DIR/node_modules" ]; then
  yellow "📦 安装 npm 依赖 ..."
  (cd "$ELECTRON_DIR" && npm install)
else
  # 快速检查 electron 二进制是否存在
  if [ ! -f "$ELECTRON_DIR/node_modules/.package-lock.json" ]; then
    yellow "📦 npm 依赖可能不完整，重新安装 ..."
    (cd "$ELECTRON_DIR" && npm install)
  fi
fi
green "✅ npm 依赖已就绪"

# ── 5. 启动 Electron（内部自动启动 Python 后端） ──
echo ""
green "🚀 启动 CSV Analyzer ..."
echo "   前端: Electron"
echo "   后端: Python JSON-RPC (由 Electron 自动管理)"
echo "   按 Ctrl+C 退出"
echo ""

cd "$ELECTRON_DIR"
exec npx electron .
