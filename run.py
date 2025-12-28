#!/usr/bin/env python
"""
快速启动脚本
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_analyzer.main import main

if __name__ == "__main__":
    main()
