"""
工作区选择对话框 - 启动时选择或创建工作区
"""

from typing import Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QWidget, QFrame,
    QMessageBox, QInputDialog, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon

from csv_analyzer.core.workspace import WorkspaceManager, WorkspaceInfo, WorkspaceConfig
from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class WorkspaceListItem(QWidget):
    """工作区列表项"""
    
    delete_clicked = pyqtSignal(str)  # workspace_id
    
    def __init__(self, info: WorkspaceInfo, parent=None):
        super().__init__(parent)
        self.workspace_id = info.id
        self.workspace_name = info.name
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(get_icon("folder").pixmap(24, 24))
        layout.addWidget(icon_label)
        
        # 文字区域
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # 名称
        name_label = QLabel(info.name)
        name_label.setFont(QFont("Segoe UI", 11))
        name_label.setStyleSheet(f"color: {VSCODE_COLORS['foreground']};")
        text_layout.addWidget(name_label)
        
        # 详情
        try:
            dt = datetime.fromisoformat(info.last_modified)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = info.last_modified
        
        detail_text = f"{info.file_count} 个文件 · 上次使用: {time_str}"
        detail_label = QLabel(detail_text)
        detail_label.setFont(QFont("Segoe UI", 9))
        detail_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        text_layout.addWidget(detail_label)
        
        layout.addWidget(text_widget, 1)
        
        # 删除按钮
        delete_btn = QPushButton()
        delete_btn.setIcon(get_icon("clear"))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setToolTip("删除工作区")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {VSCODE_COLORS['error']};
            }}
        """)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.workspace_id))
        layout.addWidget(delete_btn)


class WorkspacePickerDialog(QDialog):
    """工作区选择对话框"""
    
    workspace_selected = pyqtSignal(str)  # workspace_id
    new_workspace_requested = pyqtSignal()
    
    def __init__(self, workspace_manager: WorkspaceManager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.selected_workspace_id: Optional[str] = None
        
        self._setup_ui()
        self._load_workspaces()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("CSV Analyzer - 选择工作区")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)
        self.setModal(True)
        
        # 样式
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {VSCODE_COLORS['background']};
            }}
            QLabel {{
                color: {VSCODE_COLORS['foreground']};
            }}
            QPushButton {{
                background-color: {VSCODE_COLORS['button_bg']};
                color: {VSCODE_COLORS['foreground']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {VSCODE_COLORS['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {VSCODE_COLORS['selection']};
            }}
            QPushButton#primaryButton {{
                background-color: {VSCODE_COLORS['accent']};
            }}
            QPushButton#primaryButton:hover {{
                background-color: {VSCODE_COLORS['accent_hover']};
            }}
            QLineEdit {{
                background-color: {VSCODE_COLORS['input_bg']};
                color: {VSCODE_COLORS['foreground']};
                border: 1px solid {VSCODE_COLORS['border']};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {VSCODE_COLORS['input_focus_border']};
            }}
            QListWidget {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border: 1px solid {VSCODE_COLORS['border']};
                border-radius: 6px;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
                border-radius: 4px;
                margin: 2px 4px;
            }}
            QListWidget::item:hover {{
                background-color: {VSCODE_COLORS['hover']};
            }}
            QListWidget::item:selected {{
                background-color: {VSCODE_COLORS['selection']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("欢迎使用 CSV Analyzer")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("选择一个工作区继续，或创建新的工作区")
        subtitle_label.setFont(QFont("Segoe UI", 11))
        subtitle_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(10)
        
        # 搜索栏
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索工作区...")
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)
        
        # 工作区列表
        self.workspace_list = QListWidget()
        self.workspace_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.workspace_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.workspace_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.workspace_list, 1)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # 新建工作区
        self.new_btn = QPushButton("新建工作区")
        self.new_btn.setIcon(get_icon("add"))
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.clicked.connect(self._on_new_workspace)
        button_layout.addWidget(self.new_btn)
        
        button_layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("退出")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # 打开按钮
        self.open_btn = QPushButton("打开工作区")
        self.open_btn.setObjectName("primaryButton")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._on_open)
        button_layout.addWidget(self.open_btn)
        
        layout.addLayout(button_layout)
    
    def _load_workspaces(self, query: str = ""):
        """加载工作区列表"""
        self.workspace_list.clear()
        
        if query:
            workspaces = self.workspace_manager.search_workspaces(query)
        else:
            workspaces = self.workspace_manager.get_recent_workspaces()
            if not workspaces:
                workspaces = self.workspace_manager.list_workspaces()
        
        for info in workspaces:
            item = QListWidgetItem(self.workspace_list)
            item.setData(Qt.ItemDataRole.UserRole, info.id)
            item.setSizeHint(QSize(0, 60))
            
            widget = WorkspaceListItem(info)
            widget.delete_clicked.connect(self._on_delete_workspace)
            
            self.workspace_list.setItemWidget(item, widget)
        
        # 如果没有工作区，显示提示
        if not workspaces:
            item = QListWidgetItem("没有找到工作区，点击 \"新建工作区\" 开始")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.workspace_list.addItem(item)
    
    def _on_search(self, text: str):
        """搜索工作区"""
        self._load_workspaces(text)
    
    def _on_selection_changed(self):
        """选择改变"""
        selected = self.workspace_list.selectedItems()
        self.open_btn.setEnabled(bool(selected))
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击打开工作区"""
        workspace_id = item.data(Qt.ItemDataRole.UserRole)
        if workspace_id:
            self.selected_workspace_id = workspace_id
            self.accept()
    
    def _on_open(self):
        """打开选中的工作区"""
        selected = self.workspace_list.selectedItems()
        if selected:
            workspace_id = selected[0].data(Qt.ItemDataRole.UserRole)
            if workspace_id:
                self.selected_workspace_id = workspace_id
                self.accept()
    
    def _on_new_workspace(self):
        """创建新工作区"""
        name, ok = QInputDialog.getText(
            self, "新建工作区", "请输入工作区名称:",
            text="新工作区"
        )
        
        if ok and name.strip():
            config = self.workspace_manager.create_workspace(name.strip())
            self.selected_workspace_id = config.id
            self.accept()
    
    def _on_delete_workspace(self, workspace_id: str):
        """删除工作区"""
        reply = QMessageBox.question(
            self, "删除工作区",
            "确定要删除这个工作区吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.workspace_manager.delete_workspace(workspace_id)
            self._load_workspaces(self.search_input.text())
    
    def get_selected_workspace_id(self) -> Optional[str]:
        """获取选中的工作区ID"""
        return self.selected_workspace_id
