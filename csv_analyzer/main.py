"""
CSV Analyzer 入口文件
"""

import sys
import platform
import multiprocessing

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def main():
    """应用程序入口"""
    # macOS 多进程支持
    multiprocessing.set_start_method('spawn', force=True)
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("CSV Analyzer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("CSV Analyzer")
    
    # 设置默认字体 - 根据平台选择合适的字体
    if platform.system() == 'Darwin':
        font = QFont(".AppleSystemUIFont", 13)  # macOS 系统字体
    elif platform.system() == 'Windows':
        font = QFont("Segoe UI", 10)
    else:
        font = QFont("Ubuntu", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # 高DPI支持（PyQt6默认启用）
    
    # 导入并创建主窗口
    from csv_analyzer.frontend.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
