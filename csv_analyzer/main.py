"""
CSV Analyzer 入口文件
"""

import sys
import platform
import multiprocessing

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QCoreApplication


def main():
    """应用程序入口"""
    # macOS 多进程支持
    multiprocessing.set_start_method('spawn', force=True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DisableSessionManager)
    
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
    # 确保字体大小有效
    if font.pointSize() <= 0:
        font.setPointSize(10)
    app.setFont(font)
    
    # 高DPI支持（PyQt6默认启用）
    
    # 导入工作区管理器
    from csv_analyzer.core.workspace import WorkspaceManager
    
    workspace_manager = WorkspaceManager()
    
    # 尝试迁移旧版本工作区
    migrated_id = workspace_manager.migrate_legacy_workspace()
    
    # 检查是否有最后使用的工作区
    last_workspace_id = workspace_manager.get_last_workspace_id()
    
    selected_workspace_id = None
    # 始终展示欢迎页，但仍自动加载上一次的工作区（如果存在）
    show_welcome = True
    
    if migrated_id:
        # 刚迁移完成，使用迁移的工作区
        selected_workspace_id = migrated_id
    elif last_workspace_id:
        # 有上次使用的工作区，直接加载
        selected_workspace_id = last_workspace_id
    
    # 导入并创建主窗口
    from csv_analyzer.frontend.main_window import MainWindow
    
    window = MainWindow(workspace_id=selected_workspace_id, show_welcome=show_welcome)
    window.show()
    
    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
