"""
欢迎页组件 - 在数据区域显示，类似VSCode
"""

from typing import Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QSizePolicy,
    QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor

from csv_analyzer.core.workspace import WorkspaceManager, WorkspaceInfo
from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class RecentWorkspaceItem(QWidget):
    """最近工作区项"""
    
    clicked = pyqtSignal(str)  # workspace_id
    
    def __init__(self, info: WorkspaceInfo, parent=None):
        super().__init__(parent)
        self.workspace_id = info.id
        self.workspace_name = info.name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(get_icon("folder").pixmap(20, 20))
        layout.addWidget(icon_label)
        
        # 文字区域
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # 名称
        name_label = QLabel(info.name)
        name_label.setFont(QFont("Segoe UI", 10))
        name_label.setStyleSheet(f"color: {VSCODE_COLORS['accent']};")
        text_layout.addWidget(name_label)
        
        # 详情
        try:
            dt = datetime.fromisoformat(info.last_modified)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = ""
        
        if time_str:
            detail_text = f"{info.file_count} 个文件 · {time_str}"
            detail_label = QLabel(detail_text)
            detail_label.setFont(QFont("Segoe UI", 9))
            detail_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
            text_layout.addWidget(detail_label)
        
        layout.addWidget(text_widget, 1)
        
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border-radius: 4px;
            }}
            QWidget:hover {{
                background-color: {VSCODE_COLORS['hover']};
            }}
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.workspace_id)
        super().mousePressEvent(event)


class WelcomePage(QWidget):
    """欢迎页"""
    
    # 信号
    open_file_requested = pyqtSignal()
    new_workspace_requested = pyqtSignal()
    workspace_selected = pyqtSignal(str)  # workspace_id
    
    def __init__(self, workspace_manager: WorkspaceManager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.setObjectName("welcomePage")
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 内容容器
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(60, 60, 60, 60)
        content_layout.setSpacing(40)
        
        # 标题区域
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        # 主标题
        title_label = QLabel("CSV Analyzer")
        title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Light))
        title_label.setStyleSheet(f"color: {VSCODE_COLORS['foreground']};")
        title_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("大体积CSV文件查看与分析工具")
        subtitle_label.setFont(QFont("Segoe UI", 12))
        subtitle_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        title_layout.addWidget(subtitle_label)
        
        content_layout.addWidget(title_widget)
        
        # 两列布局
        columns_widget = QWidget()
        columns_layout = QHBoxLayout(columns_widget)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(60)
        
        # 左列：开始
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        start_label = QLabel("开始")
        start_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        start_label.setStyleSheet(f"color: {VSCODE_COLORS['foreground']};")
        left_layout.addWidget(start_label)
        
        # 新建工作区按钮
        new_ws_btn = self._create_link_button("新建工作区", "add")
        new_ws_btn.clicked.connect(self.new_workspace_requested.emit)
        left_layout.addWidget(new_ws_btn)
        
        # 打开文件按钮
        open_file_btn = self._create_link_button("打开CSV文件...", "folder")
        open_file_btn.clicked.connect(self.open_file_requested.emit)
        left_layout.addWidget(open_file_btn)
        
        left_layout.addStretch()
        columns_layout.addWidget(left_column)
        
        # 右列：最近
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        recent_label = QLabel("最近")
        recent_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        recent_label.setStyleSheet(f"color: {VSCODE_COLORS['foreground']};")
        right_layout.addWidget(recent_label)
        
        # 最近工作区列表
        self.recent_list = QWidget()
        self.recent_list_layout = QVBoxLayout(self.recent_list)
        self.recent_list_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_list_layout.setSpacing(4)
        right_layout.addWidget(self.recent_list)
        
        right_layout.addStretch()
        columns_layout.addWidget(right_column)
        
        # 确保两列等宽
        columns_layout.setStretch(0, 1)
        columns_layout.setStretch(1, 1)
        
        content_layout.addWidget(columns_widget)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # 样式
        self.setStyleSheet(f"""
            QWidget#welcomePage {{
                background-color: {VSCODE_COLORS['background']};
            }}
            QScrollArea {{
                background-color: {VSCODE_COLORS['background']};
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {VSCODE_COLORS['background']};
            }}
        """)
        
        # 加载最近工作区
        self.refresh_recent_workspaces()
    
    def _create_link_button(self, text: str, icon_name: str) -> QPushButton:
        """创建链接样式按钮"""
        btn = QPushButton(text)
        btn.setIcon(get_icon(icon_name))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {VSCODE_COLORS['accent']};
                text-align: left;
                padding: 6px 0px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {VSCODE_COLORS['accent_hover']};
                text-decoration: underline;
            }}
        """)
        return btn
    
    def refresh_recent_workspaces(self):
        """刷新最近工作区列表"""
        # 清空现有列表
        while self.recent_list_layout.count():
            item = self.recent_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取最近工作区
        workspaces = self.workspace_manager.get_recent_workspaces()
        
        if not workspaces:
            empty_label = QLabel("暂无最近工作区")
            empty_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']}; padding: 8px 0;")
            self.recent_list_layout.addWidget(empty_label)
            return
        
        # 只显示前5个
        for info in workspaces[:5]:
            item = RecentWorkspaceItem(info)
            item.clicked.connect(self.workspace_selected.emit)
            self.recent_list_layout.addWidget(item)
