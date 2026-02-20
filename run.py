#!/usr/bin/env python3
"""
CSV Analyzer — 统一启动入口

使用方式:
  python run.py                  # 启动 Electron 前端 + Python 后端
  python run.py --backend-only   # 仅启动后端 (stdin/stdout JSON-RPC)
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    # --backend-only: 仅启动 Python JSON-RPC 服务 (供调试)
    if "--backend-only" in sys.argv:
        from csv_analyzer.backend.server import main as server_main
        server_main()
        return

    # 启动 Electron (内部自动管理 Python 后端子进程)
    electron_dir = os.path.join(ROOT, "electron")
    node_modules = os.path.join(electron_dir, "node_modules")

    if not os.path.isdir(node_modules):
        print("📦 首次运行，安装 npm 依赖 ...")
        subprocess.check_call(["npm", "install"], cwd=electron_dir)

    npx = "npx"
    try:
        subprocess.run(
            [npx, "electron", "."],
            cwd=electron_dir,
            check=True,
        )
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("❌ 未找到 npx / Node.js，请先安装: https://nodejs.org/")
        sys.exit(1)


if __name__ == "__main__":
    main()
