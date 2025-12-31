"""
主窗口 - 应用程序的主界面
采用VSCode风格的布局
"""

import os
import platform
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QFileDialog,
    QTabWidget, QMessageBox, QInputDialog, QLabel, QProgressBar,
    QApplication, QToolButton, QFrame, QLineEdit, QCompleter,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QEvent, QRect, QStringListModel
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPainter, QColor, QPen, QShortcut

from csv_analyzer.core.ipc import IPCClient, MessageType
from csv_analyzer.core.workspace import WorkspaceManager, WorkspaceConfig, WorkspaceInfo
from csv_analyzer.frontend.styles.theme import get_main_stylesheet, VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon
from csv_analyzer.frontend.components.sidebar import SidebarWidget
from csv_analyzer.frontend.components.data_table import DataTableWidget
from csv_analyzer.frontend.components.sql_editor import SQLEditorWidget
from csv_analyzer.frontend.components.cell_inspector import CellInspectorWidget


class MacTrafficButton(QToolButton):
    """macOS风格的红绿灯按钮，悬停时显示功能图标"""
    
    def __init__(self, button_type: str, parent=None):
        super().__init__(parent)
        self._button_type = button_type  # 'close', 'minimize', 'zoom'
        self._hovered = False
        self._group_hovered = False  # 整组按钮是否被悬停
        
        # 颜色配置
        self._colors = {
            'close': '#ff5f57',
            'minimize': '#febc2e', 
            'zoom': '#28c840'
        }
        self._inactive_color = '#4a4a4a'
        
        self.setFixedSize(12, 12)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def set_group_hovered(self, hovered: bool):
        """设置整组按钮的悬停状态"""
        self._group_hovered = hovered
        self.update()
    
    def enterEvent(self, event):
        self._hovered = True
        # 通知其他按钮整组被悬停
        parent = self.parent()
        if parent:
            for child in parent.findChildren(MacTrafficButton):
                child.set_group_hovered(True)
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hovered = False
        parent = self.parent()
        if parent:
            for child in parent.findChildren(MacTrafficButton):
                child.set_group_hovered(False)
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制圆形背景
        color = QColor(self._colors.get(self._button_type, '#666666'))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 12, 12)
        
        # 悬停时绘制功能图标
        if self._group_hovered:
            pen = QPen(QColor('#4a0000' if self._button_type == 'close' else '#5a3d00' if self._button_type == 'minimize' else '#0a4a0a'))
            pen.setWidth(2)
            painter.setPen(pen)
            
            if self._button_type == 'close':
                # X 图标
                painter.drawLine(3, 3, 9, 9)
                painter.drawLine(9, 3, 3, 9)
            elif self._button_type == 'minimize':
                # - 图标
                painter.drawLine(3, 6, 9, 6)
            elif self._button_type == 'zoom':
                # + 图标 (或对角箭头)
                painter.drawLine(3, 6, 9, 6)
                painter.drawLine(6, 3, 6, 9)
        
        painter.end()


class AsyncWorker(QThread):
    """异步工作线程"""
    
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _WindowDragArea(QWidget):
    """工具栏中的可拖拽区域（无边框窗口移动/双击最大化）"""

    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self._dragging = False
        self._drag_offset = QPoint()
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            try:
                self._drag_offset = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            except Exception:
                self._drag_offset = QPoint()
            event.accept()
            return
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            if self._window.isMaximized():
                # 从最大化状态拖拽时，先还原再移动（保持鼠标相对位置）
                try:
                    global_pos = event.globalPosition().toPoint()
                    ratio_x = max(0.0, min(1.0, event.position().x() / max(1.0, float(self.width()))))
                    self._window.showNormal()
                    if hasattr(self._window, "_sync_max_restore_icon"):
                        self._window._sync_max_restore_icon()
                    new_offset_x = int(self._window.width() * ratio_x)
                    self._drag_offset = QPoint(new_offset_x, int(event.position().y()))
                    self._window.move(global_pos - self._drag_offset)
                except Exception:
                    pass
                event.accept()
                return

            try:
                global_pos = event.globalPosition().toPoint()
                self._window.move(global_pos - self._drag_offset)
            except Exception:
                pass
            event.accept()
            return
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
            return
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self._window, "_toggle_max_restore"):
            self._window._toggle_max_restore()
            event.accept()
            return
        return super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, workspace_id: Optional[str] = None, show_welcome: bool = False):
        super().__init__()
        
        # IPC客户端
        self.ipc_client = IPCClient()
        
        # 工作区管理器
        self.workspace_manager = WorkspaceManager()
        
        # 当前工作区
        self._current_workspace_id: Optional[str] = workspace_id
        self._current_workspace_name: str = "未命名工作区"
        
        # 是否显示欢迎页
        self._show_welcome = show_welcome
        
        # 工作区修改标记
        self._workspace_dirty: bool = False
        self._last_saved_state: Optional[str] = None  # 用于比较状态
        
        # 工作区名称到ID的映射
        self._workspace_name_to_id: Dict[str, str] = {}
        
        # 当前状态
        self._current_table: Optional[str] = None
        self._workers: list = []
        self._loaded_files: List[str] = []
        self._shutting_down: bool = False
        
        # 表名到文件路径的映射
        self._table_to_file: Dict[str, str] = {}

        # 无边框窗口 + 自定义窗口控制
        self._frameless_enabled = True
        self._resize_margin = 6
        self._resizing = False
        self._resize_edges: set[str] = set()
        self._resize_start_global = QPoint()
        self._resize_start_geo = QRect()
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

        # 捕获全局鼠标事件：用于无边框边缘缩放（鼠标事件大多会落在子控件上）
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        
        # 设置快捷键
        self._setup_shortcuts()
        
        # 延迟启动后端和加载工作区，确保界面先显示
        QTimer.singleShot(100, self._delayed_init)
    
    def _delayed_init(self):
        """延迟初始化 - 在界面显示后启动后端和加载工作区"""
        # 启动后端（异步）
        def start_backend_async():
            try:
                self.ipc_client.start()
                return True
            except Exception as e:
                return str(e)
        
        def on_backend_started(result):
            if result is True:
                self.backend_status.setText("后端：运行中")
                self._show_status("后端服务已启动")
                # 后端启动成功后，延迟加载工作区
                QTimer.singleShot(200, self._load_workspace_async)
            else:
                self.backend_status.setText("后端：启动失败")
                QMessageBox.critical(self, "错误", f"后端启动失败: {result}")
        
        self._run_async(start_backend_async, on_backend_started)
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Cmd+F / Ctrl+F 打开列搜索
        find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        find_shortcut.activated.connect(self._show_column_search)
        
        # Esc 关闭列搜索
        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.activated.connect(self._hide_column_search)
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("CSV Analyzer")
        self.setMinimumSize(1200, 600)
        self.resize(1400, 800)

        if self._frameless_enabled:
            # 开启无边框窗口（自定义标题栏/按钮/拖拽/缩放）
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.setWindowFlag(Qt.WindowType.WindowSystemMenuHint, True)
            self.setMouseTracking(True)
            # 设置窗口透明背景以支持圆角
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # macOS特有设置：让工具栏和标题栏融合
        if (not self._frameless_enabled) and platform.system() == 'Darwin':
            # 允许工具栏在标题栏区域显示
            self.setUnifiedTitleAndToolBarOnMac(True)
        
        # 应用主题（包含macOS Tahoe风格圆角）
        self.setStyleSheet(get_main_stylesheet())
        
        # 中心部件 - 使用圆角容器
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        # 添加边距以便圆角可见
        if self._frameless_enabled:
            main_layout.setContentsMargins(0, 0, 0, 0)
        else:
            main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 内容区域（横向布局）
        content_widget = QWidget()
        layout = QHBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 主分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)  # 防止子控件被完全折叠
        
        # 侧边栏
        self.sidebar = SidebarWidget()
        self.sidebar.setMinimumWidth(120)  # 降低最小宽度以便调整
        # 移除最大宽度限制，改用splitter控制
        self.main_splitter.addWidget(self.sidebar)
        
        # 中间区域
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # 数据Tab容器（包含Tab和搜索栏）
        data_container = QWidget()
        data_container_layout = QVBoxLayout(data_container)
        data_container_layout.setContentsMargins(0, 0, 0, 0)
        data_container_layout.setSpacing(0)
        
        # 数据表格Tab（标签靠左）
        self.data_tabs = QTabWidget()
        self.data_tabs.setTabsClosable(True)
        self.data_tabs.setMovable(True)
        self.data_tabs.setDocumentMode(True)
        # 标签靠左对齐
        self.data_tabs.tabBar().setExpanding(False)
        data_container_layout.addWidget(self.data_tabs)
        
        # 欢迎页（在数据区域显示）
        from csv_analyzer.frontend.components.welcome_page import WelcomePage
        self.welcome_page = WelcomePage(self.workspace_manager)
        self.welcome_page.open_file_requested.connect(self._on_open_file)
        self.welcome_page.new_workspace_requested.connect(lambda: self._create_new_workspace())
        self.welcome_page.workspace_selected.connect(self._switch_to_workspace)
        
        # 如果需要显示欢迎页，添加为初始Tab
        if self._show_welcome:
            self.data_tabs.addTab(self.welcome_page, "欢迎")
        
        # 列搜索栏（默认隐藏，按Cmd+F/Ctrl+F显示）
        self.column_search_bar = QWidget()
        self.column_search_bar.setVisible(False)
        search_bar_layout = QHBoxLayout(self.column_search_bar)
        search_bar_layout.setContentsMargins(4, 4, 4, 4)
        search_bar_layout.setSpacing(8)
        
        search_bar_layout.addStretch()  # 靠右显示
        
        search_label = QLabel("跳转到列:")
        search_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        search_bar_layout.addWidget(search_label)
        
        self.column_search_input = QLineEdit()
        self.column_search_input.setPlaceholderText("输入 表名.列名 或列名...")
        self.column_search_input.setFixedWidth(250)
        self.column_search_input.returnPressed.connect(self._on_column_search_enter)
        self.column_search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {VSCODE_COLORS['input_bg']};
                color: {VSCODE_COLORS['foreground']};
                border: 1px solid {VSCODE_COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border-color: {VSCODE_COLORS['input_focus_border']};
            }}
        """)
        
        # 列搜索自动补全
        self.column_completer = QCompleter()
        self.column_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.column_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.column_search_input.setCompleter(self.column_completer)
        self.column_completer.activated.connect(self._on_column_selected)
        
        search_bar_layout.addWidget(self.column_search_input)
        
        # 关闭按钮
        close_search_btn = QToolButton()
        close_search_btn.setIcon(get_icon("clear"))
        close_search_btn.setFixedSize(20, 20)
        close_search_btn.setToolTip("关闭搜索栏 (Esc)")
        close_search_btn.clicked.connect(self._hide_column_search)
        close_search_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
            }}
            QToolButton:hover {{
                background-color: {VSCODE_COLORS['hover']};
                border-radius: 4px;
            }}
        """)
        search_bar_layout.addWidget(close_search_btn)
        
        self.column_search_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-bottom: 1px solid {VSCODE_COLORS['border']};
            }}
        """)
        data_container_layout.addWidget(self.column_search_bar)
        
        # 中间垂直分割器
        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_splitter.setChildrenCollapsible(False)
        
        self.center_splitter.addWidget(data_container)
        
        # 下部：SQL编辑器
        self.sql_editor = SQLEditorWidget()
        self.sql_editor.setMinimumHeight(80)
        self.sql_editor.setMaximumHeight(400)
        self.center_splitter.addWidget(self.sql_editor)
        
        self.center_splitter.setSizes([500, 180])
        center_layout.addWidget(self.center_splitter)
        
        self.main_splitter.addWidget(center_widget)
        
        # 右侧面板：单元格检查器（替代原来的分析面板）
        self.cell_inspector = CellInspectorWidget()
        self.cell_inspector.setMinimumWidth(120)  # 降低最小宽度以便调整
        # 移除最大宽度限制，改用splitter控制
        self.main_splitter.addWidget(self.cell_inspector)
        
        # 设置拉伸因子：侧边栏(0)=固定, 中间(1)=拉伸, 右侧(0)=固定
        self.main_splitter.setStretchFactor(0, 0)  # 侧边栏不自动拉伸
        self.main_splitter.setStretchFactor(1, 1)  # 中间区域自动拉伸
        self.main_splitter.setStretchFactor(2, 0)  # 右侧面板不自动拉伸
        
        self.main_splitter.setSizes([250, 850, 320])
        
        layout.addWidget(self.main_splitter)
        main_layout.addWidget(content_widget)
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # Windows平台下默认隐藏菜单栏（使用工具栏代替）
        is_windows = platform.system() == 'Windows'
        if is_windows:
            menubar.setVisible(False)
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        open_action = QAction("打开CSV文件(&O)...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        # 最近打开的文件
        self.recent_menu = file_menu.addMenu("最近打开(&R)")
        self._update_recent_menu()
        
        file_menu.addSeparator()
        
        # 工作区菜单
        workspace_menu = file_menu.addMenu("工作区(&W)")
        
        new_workspace_action = QAction("新建工作区(&N)...", self)
        new_workspace_action.triggered.connect(lambda: self._create_new_workspace())
        workspace_menu.addAction(new_workspace_action)
        
        switch_workspace_action = QAction("切换工作区(&S)...", self)
        switch_workspace_action.triggered.connect(self._show_workspace_picker)
        workspace_menu.addAction(switch_workspace_action)
        
        workspace_menu.addSeparator()
        
        rename_workspace_action = QAction("重命名工作区(&R)...", self)
        rename_workspace_action.triggered.connect(self._rename_current_workspace)
        workspace_menu.addAction(rename_workspace_action)
        
        file_menu.addSeparator()
        
        save_workspace_action = QAction("保存工作区(&S)", self)
        save_workspace_action.setShortcut(QKeySequence("Ctrl+S"))
        save_workspace_action.triggered.connect(self._save_workspace)
        file_menu.addAction(save_workspace_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出结果(&E)...", self)
        export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        toggle_sidebar = QAction("切换侧边栏", self)
        toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_sidebar)
        
        toggle_inspector = QAction("切换检查器面板", self)
        toggle_inspector.setShortcut(QKeySequence("Ctrl+Shift+I"))
        toggle_inspector.triggered.connect(self._toggle_inspector)
        view_menu.addAction(toggle_inspector)
        
        toggle_sql = QAction("切换SQL编辑器", self)
        toggle_sql.setShortcut(QKeySequence("Ctrl+`"))
        toggle_sql.triggered.connect(self._toggle_sql_editor)
        view_menu.addAction(toggle_sql)
        
        # 查询菜单
        query_menu = menubar.addMenu("查询(&Q)")
        
        run_query = QAction("执行查询(&R)", self)
        run_query.setShortcut(QKeySequence("F5"))
        run_query.triggered.connect(self._on_execute_sql)
        query_menu.addAction(run_query)
        
        query_menu.addSeparator()
        
        save_view = QAction("保存为视图(&S)...", self)
        save_view.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_view.triggered.connect(self._on_save_view)
        query_menu.addAction(save_view) # type: ignore
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        is_macos = platform.system() == 'Darwin'
        toolbar.setIconSize(QSize(20, 20) if is_macos else QSize(20, 20))

        # macOS: 缩窄顶栏高度以保持视觉平衡
        if is_macos:
            toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            # 添加圆角到顶栏（适配无边框窗口）
            top_radius = VSCODE_COLORS.get('window_radius', '10px') if self._frameless_enabled else '0px'
            toolbar.setStyleSheet(f"""
                QToolBar {{
                    background-color: {VSCODE_COLORS['titlebar_bg']};
                    border: none;
                    spacing: 2px;
                    padding: 0px 4px;
                    min-height: 28px;
                    max-height: 28px;
                    border-top-left-radius: {top_radius};
                    border-top-right-radius: {top_radius};
                }}
                QToolButton {{
                    padding: 2px 4px;
                    border-radius: 4px;
                    background-color: transparent;
                }}
                QToolButton:hover {{
                    background-color: {VSCODE_COLORS['hover']};
                }}
                /* macOS红绿灯按钮 - 透明背景，无底色 */
                QWidget#macTrafficControls {{
                    background-color: transparent;
                }}
                QToolButton#macTrafficClose,
                QToolButton#macTrafficMin,
                QToolButton#macTrafficZoom {{
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                    min-width: 12px;
                    max-width: 12px;
                    min-height: 12px;
                    max-height: 12px;
                    background-color: transparent;
                }}
                QToolButton#macTrafficClose {{ background-color: #ff5f57; }}
                QToolButton#macTrafficMin {{ background-color: #febc2e; }}
                QToolButton#macTrafficZoom {{ background-color: #28c840; }}
                /* 悬停时显示图标 */
                QToolButton#macTrafficClose:hover {{ background-color: #ff5f57; }}
                QToolButton#macTrafficMin:hover {{ background-color: #febc2e; }}
                QToolButton#macTrafficZoom:hover {{ background-color: #28c840; }}
                QToolButton#windowClose:hover {{
                    background-color: {VSCODE_COLORS['error']};
                }}
                QToolButton#windowClose:pressed {{
                    background-color: {VSCODE_COLORS['error']};
                }}
                QToolButton:checked {{
                    background-color: {VSCODE_COLORS['selection']};
                }}
            """)
        else:
            toolbar.setStyleSheet(f"""
                QToolBar {{
                    background-color: {VSCODE_COLORS['titlebar_bg']};
                    border: none;
                    spacing: 2px;
                    padding: 0px 4px;
                    min-height: 28px;
                    max-height: 28px;
                }}
                QToolButton {{
                    padding: 2px 4px;
                    border-radius: 4px;
                    background-color: transparent;
                }}
                QToolButton:hover {{
                    background-color: {VSCODE_COLORS['hover']};
                }}
                QToolButton#windowClose:hover {{
                    background-color: {VSCODE_COLORS['error']};
                }}
                QToolButton#windowClose:pressed {{
                    background-color: {VSCODE_COLORS['error']};
                }}
                QToolButton:checked {{
                    background-color: {VSCODE_COLORS['selection']};
                }}
            """)

        # macOS：左侧红绿灯（无边框模式下自绘，悬停显示功能图标）
        if self._frameless_enabled and is_macos:
            mac_controls = QWidget()
            mac_controls.setObjectName("macTrafficControls")
            mac_layout = QHBoxLayout(mac_controls)
            mac_layout.setContentsMargins(8, 0, 8, 0)
            mac_layout.setSpacing(8)

            self._mac_btn_close = MacTrafficButton('close')
            self._mac_btn_close.setToolTip("关闭")
            self._mac_btn_close.clicked.connect(self.close)
            mac_layout.addWidget(self._mac_btn_close)

            self._mac_btn_min = MacTrafficButton('minimize')
            self._mac_btn_min.setToolTip("最小化")
            self._mac_btn_min.clicked.connect(self.showMinimized)
            mac_layout.addWidget(self._mac_btn_min)

            self._mac_btn_zoom = MacTrafficButton('zoom')
            self._mac_btn_zoom.setToolTip("最大化/还原")
            self._mac_btn_zoom.clicked.connect(self._toggle_max_restore)
            mac_layout.addWidget(self._mac_btn_zoom)

            toolbar.addWidget(mac_controls)
        
        # 打开文件
        open_btn = QAction(get_icon("folder"), "打开", self)
        open_btn.setToolTip("打开CSV文件 (Ctrl+O)")
        open_btn.triggered.connect(self._on_open_file)
        toolbar.addAction(open_btn)
        
        # 保存工作区
        save_workspace_btn = QAction(get_icon("save"), "保存工作区", self)
        save_workspace_btn.setToolTip("保存当前工作区 (Ctrl+S)")
        save_workspace_btn.triggered.connect(self._save_workspace)
        toolbar.addAction(save_workspace_btn)
        
        toolbar.addSeparator()
        
        # 执行查询
        run_btn = QAction(get_icon("play"), "执行", self)
        run_btn.setToolTip("执行SQL查询 (F5)")
        run_btn.triggered.connect(self._on_execute_sql)
        toolbar.addAction(run_btn)
        
        # 刷新
        refresh_btn = QAction(get_icon("refresh"), "刷新", self)
        refresh_btn.setToolTip("刷新数据")
        refresh_btn.triggered.connect(self._on_refresh)
        toolbar.addAction(refresh_btn)
        
        # 添加弹性空间（也作为无边框拖拽区）
        spacer_left = _WindowDragArea(self)
        spacer_left.setSizePolicy(spacer_left.sizePolicy().horizontalPolicy().Expanding,
                     spacer_left.sizePolicy().verticalPolicy().Preferred)
        toolbar.addWidget(spacer_left)
        
        # 中间：工作区搜索框
        self._setup_workspace_search(toolbar)
        
        # 添加右侧弹性空间
        spacer_right = _WindowDragArea(self)
        spacer_right.setSizePolicy(spacer_right.sizePolicy().horizontalPolicy().Expanding,
                     spacer_right.sizePolicy().verticalPolicy().Preferred)
        toolbar.addWidget(spacer_right)
        
        # 右侧：视图切换按钮
        # 侧边栏切换
        self.toggle_sidebar_btn = QAction(get_icon("panel_left"), "", self)
        self.toggle_sidebar_btn.setToolTip("切换侧边栏 (Ctrl+B)")
        self.toggle_sidebar_btn.setCheckable(True)
        self.toggle_sidebar_btn.setChecked(True)
        self.toggle_sidebar_btn.triggered.connect(self._toggle_sidebar)
        toolbar.addAction(self.toggle_sidebar_btn)
        
        # SQL编辑器切换
        self.toggle_sql_btn = QAction(get_icon("panel_bottom"), "", self)
        self.toggle_sql_btn.setToolTip("切换SQL编辑器 (Ctrl+`)")
        self.toggle_sql_btn.setCheckable(True)
        self.toggle_sql_btn.setChecked(True)
        self.toggle_sql_btn.triggered.connect(self._toggle_sql_editor)
        toolbar.addAction(self.toggle_sql_btn)
        
        # 检查器面板切换
        self.toggle_inspector_btn = QAction(get_icon("panel_right"), "", self)
        self.toggle_inspector_btn.setToolTip("切换检查器面板 (Ctrl+Shift+I)")
        self.toggle_inspector_btn.setCheckable(True)
        self.toggle_inspector_btn.setChecked(True)
        self.toggle_inspector_btn.triggered.connect(self._toggle_inspector)
        toolbar.addAction(self.toggle_inspector_btn)

        # 右侧：窗口控制按钮（非 macOS 用；macOS 使用左侧红绿灯）
        if self._frameless_enabled and (not is_macos):
            toolbar.addSeparator()

            self._win_btn_min = QToolButton()
            self._win_btn_min.setObjectName("windowMin")
            self._win_btn_min.setIcon(get_icon("window_minimize"))
            self._win_btn_min.setToolTip("最小化")
            self._win_btn_min.clicked.connect(self.showMinimized)
            toolbar.addWidget(self._win_btn_min)

            self._win_btn_max = QToolButton()
            self._win_btn_max.setObjectName("windowMax")
            self._win_btn_max.setToolTip("最大化/还原")
            self._win_btn_max.clicked.connect(self._toggle_max_restore)
            toolbar.addWidget(self._win_btn_max)

            self._win_btn_close = QToolButton()
            self._win_btn_close.setObjectName("windowClose")
            self._win_btn_close.setIcon(get_icon("window_close"))
            self._win_btn_close.setToolTip("关闭")
            self._win_btn_close.clicked.connect(self.close)
            toolbar.addWidget(self._win_btn_close)

            self._sync_max_restore_icon()
        
        self.addToolBar(toolbar)

    def _toggle_max_restore(self):
        """最大化/还原切换"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_max_restore_icon()

    def _sync_max_restore_icon(self):
        """同步最大化按钮图标"""
        if not getattr(self, "_frameless_enabled", False):
            return
        btn = getattr(self, "_win_btn_max", None)
        if btn is None:
            return
        btn.setIcon(get_icon("window_restore" if self.isMaximized() else "window_maximize"))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_max_restore_icon()
        return super().changeEvent(event)

    def eventFilter(self, watched, event):
        """全局事件过滤：实现无边框边缘缩放与边缘光标"""
        # 处理工作区搜索框事件
        if hasattr(self, 'workspace_search') and watched == self.workspace_search:
            et = event.type()
            if et == QEvent.Type.FocusIn:
                # 获得焦点时显示下拉列表
                self._show_workspace_popup()
                return False
            elif et == QEvent.Type.MouseButtonPress:
                # 点击搜索框时显示下拉列表
                self._show_workspace_popup()
                return False
            elif et == QEvent.Type.KeyPress:
                key = event.key()
                popup = getattr(self, 'workspace_popup', None)
                if popup is not None and popup.isVisible():
                    if key == Qt.Key.Key_Down:
                        current = popup.currentRow()
                        if current < popup.count() - 1:
                            popup.setCurrentRow(current + 1)
                        return True
                    elif key == Qt.Key.Key_Up:
                        current = popup.currentRow()
                        if current > 0:
                            popup.setCurrentRow(current - 1)
                        return True
                    elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        item = popup.currentItem()
                        if item and item.data(Qt.ItemDataRole.UserRole):
                            self._on_workspace_item_clicked(item)
                        return True
                    elif key == Qt.Key.Key_Escape:
                        self._hide_workspace_popup()
                        return True
        
        # 点击其他区域时收起工作区下拉
        popup = getattr(self, 'workspace_popup', None)
        if popup is not None and popup.isVisible():
            if event.type() == QEvent.Type.MouseButtonPress:
                global_pos = None
                try:
                    global_pos = event.globalPosition().toPoint()  # type: ignore[attr-defined]
                except Exception:
                    pass
                if global_pos is not None:
                    if not self._is_point_in_widget(self.workspace_search, global_pos) and not self._is_point_in_widget(popup, global_pos):
                        self._hide_workspace_popup()
        
        if not getattr(self, "_frameless_enabled", False):
            return super().eventFilter(watched, event)

        et = event.type()

        # 最大化时不提供边缘缩放
        if self.isMaximized():
            if et == QEvent.Type.MouseMove and not self._resizing:
                # 恢复默认光标
                try:
                    self.unsetCursor()
                except Exception:
                    pass
            return super().eventFilter(watched, event)

        if et in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            try:
                global_pos = event.globalPosition().toPoint()  # type: ignore[attr-defined]
                local_pos = self.mapFromGlobal(global_pos)
            except Exception:
                return super().eventFilter(watched, event)

            # 只在窗口范围内处理
            if not self.rect().contains(local_pos):
                if not self._resizing:
                    self.unsetCursor()
                return super().eventFilter(watched, event)

            edges = self._hit_test_edges(local_pos)

            if et == QEvent.Type.MouseMove:
                # 正在缩放
                if self._resizing:
                    self._apply_resize(global_pos)
                    return True

                # 未按下鼠标：更新光标提示
                if edges:
                    self._update_resize_cursor(edges)
                else:
                    self.unsetCursor()

            elif et == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton and edges:
                    self._resizing = True
                    self._resize_edges = edges
                    self._resize_start_global = global_pos
                    self._resize_start_geo = self.geometry()
                    return True

            elif et == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self._resizing:
                    self._resizing = False
                    self._resize_edges = set()
                    self.unsetCursor()
                    return True

        return super().eventFilter(watched, event)

    def _hit_test_edges(self, pos: QPoint) -> set[str]:
        """判断鼠标是否在窗口边缘（用于缩放）"""
        m = int(self._resize_margin)
        w = self.width()
        h = self.height()

        edges: set[str] = set()
        if pos.x() <= m:
            edges.add("left")
        elif pos.x() >= w - m:
            edges.add("right")

        if pos.y() <= m:
            edges.add("top")
        elif pos.y() >= h - m:
            edges.add("bottom")

        return edges

    def _update_resize_cursor(self, edges: set[str]):
        """根据边缘位置更新鼠标光标"""
        if {"left", "top"}.issubset(edges) or {"right", "bottom"}.issubset(edges):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif {"right", "top"}.issubset(edges) or {"left", "bottom"}.issubset(edges):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif "left" in edges or "right" in edges:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif "top" in edges or "bottom" in edges:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def _apply_resize(self, global_pos: QPoint):
        """按当前边缘拖拽调整窗口大小"""
        delta = global_pos - self._resize_start_global
        geo = QRect(self._resize_start_geo)

        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        if "left" in self._resize_edges:
            new_x = geo.x() + delta.x()
            new_w = geo.width() - delta.x()
            if new_w >= min_w:
                geo.setX(new_x)
                geo.setWidth(new_w)
        if "right" in self._resize_edges:
            new_w = geo.width() + delta.x()
            if new_w >= min_w:
                geo.setWidth(new_w)

        if "top" in self._resize_edges:
            new_y = geo.y() + delta.y()
            new_h = geo.height() - delta.y()
            if new_h >= min_h:
                geo.setY(new_y)
                geo.setHeight(new_h)
        if "bottom" in self._resize_edges:
            new_h = geo.height() + delta.y()
            if new_h >= min_h:
                geo.setHeight(new_h)

        self.setGeometry(geo)
    
    def _setup_workspace_search(self, toolbar):
        """设置工作区搜索框"""
        from csv_analyzer.frontend.styles.icons import get_icon
        
        # 工作区搜索容器
        search_container = QWidget()
        search_container.setObjectName("workspaceSearchContainer")
        search_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        search_container.setStyleSheet(f"""
            QWidget#workspaceSearchContainer {{
                background-color: {VSCODE_COLORS['titlebar_bg']};
            }}
        """)

        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)
        
        # 搜索框容器（带图标）
        search_box = QWidget()
        search_box.setFixedWidth(400)
        search_box.setFixedHeight(20)
        search_box_layout = QHBoxLayout(search_box)
        search_box_layout.setContentsMargins(8, 0, 8, 0)
        search_box_layout.setSpacing(6)
        self.workspace_search_box = search_box
        
        # 搜索图标
        search_icon = QLabel()
        search_icon.setPixmap(get_icon("search").pixmap(12, 12))
        search_box_layout.addWidget(search_icon)
        
        # 工作区搜索框
        self.workspace_search = QLineEdit()
        self.workspace_search.setObjectName("workspaceSearch")
        self.workspace_search.setPlaceholderText("搜索工作区...")
        self.workspace_search.setFrame(False)
        self.workspace_search.setStyleSheet(f"""
            QLineEdit#workspaceSearch {{
                background-color: transparent;
                color: {VSCODE_COLORS['foreground']};
                font-size: 10px;
                padding: 0;
                border: none;
            }}
        """)
        search_box_layout.addWidget(self.workspace_search, 1)
        
        # 搜索框容器样式（与标题栏背景融合）
        search_box.setObjectName("workspaceSearchBox")
        search_box.setStyleSheet(f"""
            QWidget#workspaceSearchBox {{
                background-color: {VSCODE_COLORS['titlebar_bg']};
                border: 1px solid gray;
                border-radius: 4px;
            }}
            QWidget#workspaceSearchBox:focus-within {{
                border-color: {VSCODE_COLORS['input_focus_border']};
                background-color: {VSCODE_COLORS['titlebar_bg']};
            }}
        """)
        
        search_layout.addWidget(search_box)
        toolbar.addWidget(search_container)
        
        # 工作区下拉列表（自定义弹出）
        self._setup_workspace_popup()
        
        # 连接信号
        self.workspace_search.textChanged.connect(self._on_workspace_search_changed)
        self.workspace_search.returnPressed.connect(self._on_workspace_search_enter)
        # 点击时显示下拉列表
        self.workspace_search.installEventFilter(self)
    
    def _setup_workspace_popup(self):
        """设置工作区下拉列表"""
        if getattr(self, 'workspace_popup', None) is not None:
            return
        # 设为主窗口子控件，避免退出阶段析构顺序问题
        self.workspace_popup = QListWidget(self)
        # 使用无边框悬浮窗，避免 Qt.Popup 自动关闭导致闪退
        self.workspace_popup.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.workspace_popup.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.workspace_popup.setMouseTracking(True)
        self.workspace_popup.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.workspace_popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.workspace_popup.setStyleSheet(f"""
            QListWidget {{
                background-color: {VSCODE_COLORS['dropdown_bg']};
                border: 1px solid {VSCODE_COLORS['border']};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                color: {VSCODE_COLORS['foreground']};
            }}
            QListWidget::item:hover {{
                background-color: {VSCODE_COLORS['hover']};
            }}
            QListWidget::item:selected {{
                background-color: {VSCODE_COLORS['selection']};
            }}
        """)
        self.workspace_popup.itemClicked.connect(self._on_workspace_item_clicked)
        self.workspace_popup.currentItemChanged.connect(self._on_workspace_popup_current_changed)
        self.workspace_popup.installEventFilter(self)
        self.workspace_popup.hide()

    def _ensure_workspace_popup(self):
        """确保下拉存在（可能在关闭时被清理）"""
        if getattr(self, 'workspace_popup', None) is None:
            self._setup_workspace_popup()
        return self.workspace_popup
    
    def _show_workspace_popup(self):
        """显示工作区下拉列表"""
        popup = self._ensure_workspace_popup()
        if popup is None:
            return
        
        popup.clear()
        
        # 获取工作区列表
        query = self.workspace_search.text().strip()
        if query:
            workspaces = self.workspace_manager.search_workspaces(query)
        else:
            workspaces = self.workspace_manager.get_recent_workspaces()
        
        # 保存映射
        self._workspace_name_to_id = {w.name: w.id for w in workspaces}
        
        if not workspaces:
            item = QListWidgetItem("没有找到工作区")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            popup.addItem(item)
        else:
            for ws in workspaces[:8]:  # 最多显示8个
                item = QListWidgetItem(f"  {ws.name}")
                item.setIcon(get_icon("folder"))
                item.setData(Qt.ItemDataRole.UserRole, ws.id)
                item.setData(Qt.ItemDataRole.UserRole + 1, ws.name)  # 保存原始名称
                popup.addItem(item)
        
        # 定位到搜索框下方（使用搜索框容器确保对齐）
        search_box = getattr(self, "workspace_search_box", self.workspace_search)
        search_global_pos = search_box.mapToGlobal(search_box.rect().bottomLeft())
        
        popup.setFixedWidth(search_box.width())
        # 至少显示两行高度，防止内容过少导致定位闪烁
        min_height = 80
        calculated_height = min(len(workspaces) * 40 + 12, 340)
        popup.setFixedHeight(max(min_height, calculated_height))
        popup.move(search_global_pos.x(), search_global_pos.y() + 6)
        popup.show()
    
    def _on_workspace_popup_current_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """下拉列表当前项变化"""
        # 恢复上一个项的文本
        if previous and previous.data(Qt.ItemDataRole.UserRole):
            name = previous.data(Qt.ItemDataRole.UserRole + 1)
            if name:
                previous.setText(f"  {name}")
        
        # 更新当前项显示"转到工作区"
        if current and current.data(Qt.ItemDataRole.UserRole):
            name = current.data(Qt.ItemDataRole.UserRole + 1)
            if name:
                current.setText(f"  转到工作区: {name}")
    
    def _hide_workspace_popup(self):
        """隐藏工作区下拉列表"""
        popup = getattr(self, 'workspace_popup', None)
        if popup is not None:
            popup.hide()

    def _is_point_in_widget(self, widget: QWidget, global_pos) -> bool:
        """判断全局坐标是否在指定widget内"""
        try:
            rect = widget.rect()
            mapped = widget.mapFromGlobal(global_pos)
            return rect.contains(mapped)
        except Exception:
            return False
    
    def _on_workspace_item_clicked(self, item):
        """点击工作区项"""
        workspace_id = item.data(Qt.ItemDataRole.UserRole)
        if workspace_id and workspace_id != self._current_workspace_id:
            self._switch_to_workspace(workspace_id)
        self.workspace_search.clear()
        self._hide_workspace_popup()
    
    def _update_workspace_completer(self):
        """更新工作区补全列表"""
        workspaces = self.workspace_manager.get_recent_workspaces()
        # 保存工作区映射
        self._workspace_name_to_id = {w.name: w.id for w in workspaces}
    
    def _on_workspace_search_changed(self, text: str):
        """工作区搜索文字改变"""
        self._update_workspace_completer()
        if self.workspace_search.hasFocus():
            self._show_workspace_popup()
    
    def _on_workspace_selected(self, name: str):
        """选择工作区"""
        workspace_id = self._workspace_name_to_id.get(name)
        if workspace_id and workspace_id != self._current_workspace_id:
            self._switch_to_workspace(workspace_id)
        self.workspace_search.clear()
        self._hide_workspace_popup()
    
    def _on_workspace_search_enter(self):
        """工作区搜索回车"""
        text = self.workspace_search.text().strip()
        if not text:
            return
        
        # 检查是否匹配现有工作区
        if text in self._workspace_name_to_id:
            self._switch_to_workspace(self._workspace_name_to_id[text])
        else:
            # 询问是否创建新工作区
            reply = QMessageBox.question(
                self, "创建工作区",
                f"工作区 \"{text}\" 不存在。\n是否创建新的工作区？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._create_new_workspace(text)
        
        self.workspace_search.clear()
    
    def _switch_to_workspace(self, workspace_id: str):
        """切换到指定工作区"""
        # 先检查当前工作区是否需要保存
        if self._workspace_dirty:
            reply = QMessageBox.question(
                self, "保存工作区",
                "当前工作区有未保存的更改。\n是否在切换前保存？",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Save:
                self._save_workspace()
        
        # 清理当前状态
        self._clear_current_state()
        
        # 加载新工作区
        self._current_workspace_id = workspace_id
        self._load_workspace_async()
        
        self._update_workspace_completer()
    
    def _create_new_workspace(self, name: str = ""):
        """创建新工作区"""
        if not name:
            name, ok = QInputDialog.getText(
                self, "新建工作区", "请输入工作区名称:",
                text="新工作区"
            )
            if not ok or not name.strip():
                return
            name = name.strip()
        
        # 创建新工作区
        config = self.workspace_manager.create_workspace(name)
        self._current_workspace_id = config.id
        self._current_workspace_name = config.name
        self._workspace_dirty = False
        
        # 清理当前状态
        self._clear_current_state()
        
        self._update_window_title()
        self._update_workspace_completer()
        self._show_status(f"已创建工作区: {name}")
    
    def _remove_welcome_page(self):
        """移除欢迎页（如果存在）"""
        for i in range(self.data_tabs.count()):
            if self.data_tabs.tabText(i) == "欢迎":
                self.data_tabs.removeTab(i)
                break
    
    def _clear_current_state(self):
        """清理当前工作区状态"""
        # 关闭所有标签页
        while self.data_tabs.count() > 0:
            self.data_tabs.removeTab(0)
        
        # 清空已加载文件
        self._loaded_files.clear()
        self._table_to_file.clear()
        self._current_table = None
        
        # 清空SQL编辑器
        self.sql_editor.set_sql("")
        
        # 刷新侧边栏
        self.sidebar.clear_tables()
        self.sidebar.clear_views()
        
        # 清空后端数据（表和视图）
        try:
            self.ipc_client.clear_all()
        except Exception as e:
            print(f"清空后端数据失败: {e}")
        
        # 重置修改标记
        self._workspace_dirty = False
    
    def _update_window_title(self):
        """更新窗口标题"""
        title = "CSV Analyzer"
        if self._current_workspace_name:
            title = f"{self._current_workspace_name} - CSV Analyzer"
        if self._workspace_dirty:
            title = f"● {title}"
        self.setWindowTitle(title)
    
    def _mark_workspace_dirty(self):
        """标记工作区已修改"""
        if not self._workspace_dirty:
            self._workspace_dirty = True
            self._update_window_title()
    
    def _show_workspace_picker(self):
        """显示工作区选择对话框"""
        from csv_analyzer.frontend.components.workspace_picker import WorkspacePickerDialog
        from PyQt6.QtWidgets import QDialog
        
        picker = WorkspacePickerDialog(self.workspace_manager, self)
        result = picker.exec()
        
        if result == QDialog.DialogCode.Accepted:
            workspace_id = picker.get_selected_workspace_id()
            if workspace_id and workspace_id != self._current_workspace_id:
                self._switch_to_workspace(workspace_id)
    
    def _rename_current_workspace(self):
        """重命名当前工作区"""
        if not self._current_workspace_id:
            QMessageBox.warning(self, "无法重命名", "当前没有打开的工作区。")
            return
        
        new_name, ok = QInputDialog.getText(
            self, "重命名工作区", "请输入新名称:",
            text=self._current_workspace_name
        )
        
        if ok and new_name.strip():
            new_name = new_name.strip()
            self.workspace_manager.rename_workspace(self._current_workspace_id, new_name)
            self._current_workspace_name = new_name
            self._update_window_title()
            self._update_workspace_completer()
            self._show_status(f"工作区已重命名为: {new_name}")
    
    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusbar = QStatusBar()
        self.statusbar.setObjectName("mainStatusBar")
        self.setStatusBar(self.statusbar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusText")
        self.statusbar.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("statusProgress")
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)
        
        # 单元格位置
        self.cell_position_label = QLabel("")
        self.cell_position_label.setObjectName("cellPosition")
        self.cell_position_label.setMinimumWidth(150)
        self.statusbar.addPermanentWidget(self.cell_position_label)
        
        # 后端状态
        self.backend_status = QLabel("后端：未启动")
        self.backend_status.setObjectName("backendStatus")
        self.statusbar.addPermanentWidget(self.backend_status)
    
    def _connect_signals(self):
        """连接信号"""
        # 侧边栏信号
        self.sidebar.table_double_clicked.connect(self._on_table_open)
        self.sidebar.view_double_clicked.connect(self._on_view_open)
        self.sidebar.table_delete_requested.connect(self._on_table_delete)
        self.sidebar.view_delete_requested.connect(self._on_view_delete)
        self.sidebar.view_export_requested.connect(self._on_export_view)
        
        # SQL编辑器信号
        self.sql_editor.execute_requested.connect(self._execute_sql)
        self.sql_editor.save_view_requested.connect(self._save_view)
        
        # Tab切换信号
        self.data_tabs.currentChanged.connect(self._on_tab_changed)
        self.data_tabs.tabCloseRequested.connect(self._on_tab_close)
    
    def _show_status(self, message: str, timeout: int = 3000):
        """显示状态消息"""
        self.status_label.setText(message)
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.status_label.setText("就绪"))
    
    def _show_progress(self, show: bool = True):
        """显示/隐藏进度条"""
        self.progress_bar.setVisible(show)
        if show:
            self.progress_bar.setRange(0, 0)  # 不确定进度
    
    def _run_async(self, func, callback, error_callback=None):
        """异步执行函数"""
        worker = AsyncWorker(func)
        worker.finished.connect(callback)
        if error_callback:
            worker.error.connect(error_callback)
        else:
            worker.error.connect(lambda e: QMessageBox.critical(self, "错误", e))
        
        # 保持引用防止被回收
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.error.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        
        worker.start()
        return worker
    
    # === 文件操作 ===
    
    def _on_open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开CSV文件",
            "",
            "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        
        if file_path:
            self._load_csv_file(file_path)
    
    def _refresh_tables(self):
        """刷新表列表"""
        def do_refresh():
            tables_resp = self.ipc_client.get_tables()
            views_resp = self.ipc_client.get_views()
            return tables_resp, views_resp
        
        def on_refreshed(result):
            tables_resp, views_resp = result
            if tables_resp.success:
                self.sidebar.update_tables(tables_resp.data)
            if views_resp.success:
                self.sidebar.update_views(views_resp.data)
        
        self._run_async(do_refresh, on_refreshed)
    
    def _on_export(self):
        """导出当前结果"""
        # 获取当前Tab的数据
        current_widget = self.data_tabs.currentWidget()
        if not isinstance(current_widget, DataTableWidget):
            QMessageBox.warning(self, "提示", "请先打开一个数据表或查询结果")
            return
        
        columns, data = current_widget.get_current_data()
        if not columns or not data:
            QMessageBox.warning(self, "提示", "当前没有可导出的数据")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为CSV",
            "",
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            self._export_data_to_csv(file_path, columns, data)
    
    def _on_export_view(self, view_name: str, sql: str):
        """导出视图为CSV"""
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"导出视图 {view_name} 为CSV",
            f"{view_name}.csv",
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        self._show_status(f"正在导出视图 {view_name}...")
        self._show_progress(True)
        
        def do_export():
            # 执行SQL获取所有数据
            return self.ipc_client.execute_query(sql, 1000000, 0)  # 获取大量数据
        
        def on_exported(response):
            self._show_progress(False)
            if response.success:
                data = response.data
                if data.get('error'):
                    QMessageBox.warning(self, "导出失败", data['error'])
                    return
                
                self._export_data_to_csv(file_path, data['columns'], data['data'])
            else:
                QMessageBox.warning(self, "导出失败", response.error or "未知错误")
        
        self._run_async(do_export, on_exported)
    
    def _export_data_to_csv(self, file_path: str, columns: list, data: list):
        """导出数据到CSV文件"""
        try:
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(columns)
                # 写入数据
                for row in data:
                    writer.writerow(row)
            self._show_status(f"已导出到: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"写入文件失败: {e}")
    
    def _on_column_jump(self, table_name: str, column_name: str):
        """跳转到指定表的列"""
        # 先确保表已打开
        tab_index = -1
        for i in range(self.data_tabs.count()):
            if self.data_tabs.tabText(i) == table_name:
                tab_index = i
                break
        
        if tab_index == -1:
            # 打开表
            self._on_table_open(table_name)
            # 延迟执行跳转
            QTimer.singleShot(500, lambda: self._jump_to_column(table_name, column_name))
        else:
            self.data_tabs.setCurrentIndex(tab_index)
            self._jump_to_column(table_name, column_name)
    
    def _jump_to_column(self, table_name: str, column_name: str):
        """跳转到指定列"""
        current_widget = self.data_tabs.currentWidget()
        if isinstance(current_widget, DataTableWidget):
            columns = current_widget.model.columns
            if column_name in columns:
                col_index = columns.index(column_name)
                # 滚动到该列
                current_widget.table_view.scrollTo(
                    current_widget.model.index(0, col_index)
                )
                # 选中第一行该列的单元格
                current_widget.table_view.setCurrentIndex(
                    current_widget.model.index(0, col_index)
                )
                self._show_status(f"已跳转到列: {column_name}")
    
    def _show_column_search(self):
        """显示列搜索栏"""
        self.column_search_bar.setVisible(True)
        self.column_search_input.setFocus()
        self.column_search_input.selectAll()
        # 更新自动补全列表
        self._update_column_completer()
    
    def _hide_column_search(self):
        """隐藏列搜索栏"""
        self.column_search_bar.setVisible(False)
        self.column_search_input.clear()
    
    def _update_column_completer(self):
        """更新列搜索自动补全列表"""
        all_columns = self.sidebar.get_all_columns()
        model = QStringListModel(all_columns)
        self.column_completer.setModel(model)
    
    def _on_column_search_enter(self):
        """列搜索回车事件"""
        text = self.column_search_input.text().strip()
        if text:
            self._on_column_selected(text)
    
    def _on_column_selected(self, text: str):
        """选择列进行跳转"""
        # 解析 "表名.列名" 格式
        if '.' in text:
            parts = text.split('.', 1)
            if len(parts) == 2:
                table_name, column_name = parts
                self._on_column_jump(table_name, column_name)
                self._hide_column_search()
    
    # === 表操作 ===
    
    def _on_table_open(self, table_name: str):
        """打开表"""
        # 检查是否已打开
        for i in range(self.data_tabs.count()):
            if self.data_tabs.tabText(i) == table_name:
                self.data_tabs.setCurrentIndex(i)
                return
        
        # 创建新的数据表格
        table_widget = DataTableWidget()
        table_widget.set_current_table(table_name)  # 设置当前表名
        
        # 使用弱引用避免widget删除后崩溃
        import weakref
        weak_widget = weakref.ref(table_widget)
        
        def on_page_changed(offset, limit):
            w = weak_widget()
            if w is not None:
                self._load_table_data(table_name, offset, limit, w)
        
        table_widget.page_changed.connect(on_page_changed)
        # 连接列右键菜单信号
        table_widget.column_sql_requested.connect(self._on_column_sql_request)
        table_widget.column_selected_for_analysis.connect(self._on_column_analysis_request)
        # 连接单元格选中信号
        table_widget.cell_selected.connect(self._on_cell_selected)
        
        # 添加Tab（左侧显示图标）
        index = self.data_tabs.addTab(table_widget, get_icon("table"), table_name)
        self.data_tabs.setCurrentIndex(index)
        
        # 加载数据
        self._current_table = table_name
        self._load_table_data(table_name, 0, 100, table_widget)
        self._load_analysis(table_name)
        
        # 更新SQL编辑器的表名列表以支持自动补全
        self._update_sql_completer()
    
    def _load_table_data(self, table_name: str, offset: int, limit: int, table_widget: DataTableWidget):
        """加载表数据"""
        self._show_status(f"加载数据: {table_name}...")
        
        import weakref
        weak_widget = weakref.ref(table_widget)
        
        def do_load():
            return self.ipc_client.get_table_data(table_name, limit, offset)
        
        def on_loaded(response):
            w = weak_widget()
            if w is None:
                return  # widget已被删除
            if response.success:
                data = response.data
                try:
                    w.set_data(
                        data['columns'],
                        data['data'],
                        data['total_rows']
                    )
                    self._show_status(f"已加载 {len(data['data'])} / {data['total_rows']} 行")
                except RuntimeError:
                    pass  # widget可能已被删除
            else:
                QMessageBox.warning(self, "加载失败", response.error or "未知错误")
        
        self._run_async(do_load, on_loaded)
    
    def _on_table_delete(self, table_name: str):
        """删除表"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除表 '{table_name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            response = self.ipc_client.drop_table(table_name)
            if response.success:
                self._show_status(f"已删除表: {table_name}")
                self._refresh_tables()
                # 关闭对应的Tab
                for i in range(self.data_tabs.count()):
                    if self.data_tabs.tabText(i) == table_name:
                        self.data_tabs.removeTab(i)
                        break
                
                # 从已加载文件列表中移除对应的文件
                if table_name in self._table_to_file:
                    filepath = self._table_to_file.pop(table_name)
                    if filepath in self._loaded_files:
                        self._loaded_files.remove(filepath)
                
                # 标记工作区已修改
                self._mark_workspace_dirty()
            else:
                QMessageBox.warning(self, "删除失败", response.error or "未知错误")
    
    # === 视图操作 ===
    
    def _on_view_open(self, view_name: str, sql: str):
        """打开视图"""
        # 在SQL编辑器中显示SQL
        self.sql_editor.set_sql(sql)
        # 执行查询并使用视图名作为Tab名
        self._execute_sql(sql, tab_name=f"视图: {view_name}")
    
    def _on_view_delete(self, view_name: str):
        """删除视图"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除视图 '{view_name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            response = self.ipc_client.send_message(
                MessageType.DELETE_VIEW,
                {"view_name": view_name}
            )
            if response.success:
                self._show_status(f"已删除视图: {view_name}")
                self._refresh_tables()
                # 标记工作区已修改
                self._mark_workspace_dirty()
            else:
                QMessageBox.warning(self, "删除失败", response.error or "未知错误")
    
    def _on_save_view(self):
        """保存当前查询为视图"""
        sql = self.sql_editor.get_sql()
        if sql.strip():
            self._save_view(sql)
    
    def _save_view(self, sql: str):
        """保存视图"""
        view_name, ok = QInputDialog.getText(
            self, "保存视图",
            "请输入视图名称:",
            text="my_view"
        )
        
        if ok and view_name:
            response = self.ipc_client.save_view(view_name, sql)
            if response.success:
                self._show_status(f"已保存视图: {view_name}")
                self._refresh_tables()
                # 标记工作区已修改
                self._mark_workspace_dirty()
            else:
                QMessageBox.warning(self, "保存失败", response.error or "未知错误")
    
    # === SQL执行 ===
    
    def _on_execute_sql(self):
        """执行SQL菜单项"""
        sql = self.sql_editor.get_sql()
        if sql.strip():
            self._execute_sql(sql)
    
    def _execute_sql(self, sql: str, tab_name: str = None):
        """执行SQL
        
        Args:
            sql: SQL查询语句
            tab_name: Tab名称，如果为None则使用默认的"查询结果"
        """
        self._show_status("执行查询中...")
        self._show_progress(True)
        
        # 保存SQL用于分页
        self._current_sql = sql
        import weakref
        
        def do_execute():
            return self.ipc_client.execute_query(sql, 1000, 0)
        
        # 如果未指定tab_name，使用默认名称并复用
        if tab_name is None:
            tab_name = "查询结果"
            reuse_tab = True
        else:
            # 如果指定了tab_name，检查是否已存在该名称的tab
            reuse_tab = False
            for i in range(self.data_tabs.count()):
                if self.data_tabs.tabText(i) == tab_name:
                    reuse_tab = True
                    break
        
        result_widget = None
        result_index = -1
        
        # 如果要复用tab，先查找是否存在
        if reuse_tab:
            for i in range(self.data_tabs.count()):
                if self.data_tabs.tabText(i) == tab_name:
                    result_widget = self.data_tabs.widget(i)
                    result_index = i
                    break

        result_widget_ref = None

        if not result_widget:
            result_widget = DataTableWidget()
            result_widget.set_current_sql(sql)  # 保存SQL用于列分析
            result_widget_ref = weakref.ref(result_widget)

            def on_page_changed(offset, limit, widget_ref=result_widget_ref):
                widget = widget_ref()
                if widget is not None:
                    self._execute_sql_page(self._current_sql, offset, limit, widget)
            result_widget.page_changed.connect(on_page_changed)
            result_widget.cell_selected.connect(self._on_cell_selected)
            index = self.data_tabs.addTab(result_widget, get_icon("view"), tab_name)
            self.data_tabs.setCurrentIndex(index)
        else:
            result_widget.set_current_sql(sql)  # 更新SQL
            result_widget_ref = weakref.ref(result_widget)
            if result_index >= 0:
                self.data_tabs.setCurrentIndex(result_index)

        def on_executed(response, widget_ref=result_widget_ref):
            self._show_progress(False)
            
            if response.success:
                data = response.data
                
                if data.get('error'):
                    QMessageBox.warning(self, "查询错误", data['error'])
                    return
                
                widget = widget_ref() if widget_ref else None
                if widget is not None:
                    try:
                        widget.set_data(
                            data['columns'],
                            data['data'],
                            data['total_rows']
                        )
                    except RuntimeError:
                        widget = None
                
                exec_time = data.get('execution_time', 0)
                self._show_status(f"查询完成: {data['total_rows']} 行, 耗时 {exec_time:.3f}s")
            else:
                QMessageBox.warning(self, "查询失败", response.error or "未知错误")
        
        self._run_async(do_execute, on_executed)
    
    def _execute_sql_page(self, sql: str, offset: int, limit: int, result_widget: DataTableWidget):
        """执行SQL分页查询"""
        import weakref
        weak_widget = weakref.ref(result_widget)
        
        def do_execute():
            return self.ipc_client.execute_query(sql, limit, offset)
        
        def on_executed(response):
            w = weak_widget()
            if w is None:
                return  # widget已被删除
            if response.success:
                data = response.data
                if not data.get('error'):
                    try:
                        w.set_data(
                            data['columns'],
                            data['data'],
                            data['total_rows']
                        )
                    except RuntimeError:
                        pass  # widget可能已被删除
        
        self._run_async(do_execute, on_executed)
    
    # === 分析功能 ===
    
    def _load_analysis(self, table_name: str):
        """加载分析数据 - 仅设置表名，等待用户选择单元格后加载列分析"""
        self.cell_inspector.set_table_name(table_name)
        # 清空之前的分析结果
        self.cell_inspector.clear()
    
    # === UI操作 ===
    
    def _on_tab_close(self, index: int):
        """关闭Tab"""
        if index >= 0 and index < self.data_tabs.count():
            # 获取widget并断开信号连接
            widget = self.data_tabs.widget(index)
            if widget is not None:
                try:
                    # 断开所有信号连接，避免后续访问已删除的widget
                    widget.blockSignals(True)
                    if hasattr(widget, 'page_changed'):
                        try:
                            widget.page_changed.disconnect()
                        except:
                            pass
                    if hasattr(widget, 'cell_selected'):
                        try:
                            widget.cell_selected.disconnect()
                        except:
                            pass
                except:
                    pass
            
            self.data_tabs.removeTab(index)
            
            # 显式删除widget
            if widget is not None:
                widget.deleteLater()

    def _on_refresh(self):
        """刷新"""
        self._refresh_tables()
        if self._current_table:
            self._load_analysis(self._current_table)
    
    def _toggle_sidebar(self):
        """切换侧边栏"""
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self.toggle_sidebar_btn.setChecked(visible)
    
    def _toggle_inspector(self):
        """切换检查器面板"""
        visible = not self.cell_inspector.isVisible()
        self.cell_inspector.setVisible(visible)
        self.toggle_inspector_btn.setChecked(visible)
    
    def _toggle_sql_editor(self):
        """切换SQL编辑器"""
        visible = not self.sql_editor.isVisible()
        self.sql_editor.setVisible(visible)
        self.toggle_sql_btn.setChecked(visible)
    
    def _update_sql_completer(self):
        """更新SQL自动补全的表名列表"""
        try:
            resp = self.ipc_client.get_tables()
            if resp.success and resp.data:
                tables_info = {}
                for table in resp.data:
                    table_name = table['name']
                    columns = [col['name'] for col in table.get('columns', [])]
                    tables_info[table_name] = columns
                self.sql_editor.set_tables(tables_info)
        except Exception as e:
            print(f"更新SQL补全表名失败: {e}")
    
    def _on_cell_selected(self, row: int, col: int, column_name: str, value):
        """处理单元格选中"""
        # 更新单元格检查器
        self.cell_inspector.set_cell_value(row, col, column_name, value)
        
        # 显示单元格位置（行、列从1开始）
        self.cell_position_label.setText(f"行: {row + 1}, 列: {col + 1} ({column_name})")
        
        # 获取当前widget进行分析
        current_widget = self.data_tabs.currentWidget()
        if isinstance(current_widget, DataTableWidget) and column_name:
            # 检查是表还是查询结果
            table_name = current_widget.get_current_table()
            current_sql = current_widget.get_current_sql()
            
            if table_name:
                # 对于表，调用后端分析整个表的列
                self._load_column_analysis_from_backend(table_name, column_name)
            elif current_sql:
                # 对于查询结果，使用SQL分析
                self._load_column_analysis_from_sql(current_sql, column_name)
            else:
                # 回退到本地分析（只分析当前页）
                self._load_column_analysis_from_widget(column_name, current_widget)
    
    def _on_tab_changed(self, index: int):
        """处理Tab切换"""
        if index < 0 or index >= self.data_tabs.count():
            self.cell_position_label.setText("")
            return
        
        # 获取当前标签的widget
        widget = self.data_tabs.widget(index)
        if isinstance(widget, DataTableWidget):
            # 连接单元格选中信号（如果还未连接）
            try:
                widget.cell_selected.disconnect(self._on_cell_selected)
            except:
                pass
            widget.cell_selected.connect(self._on_cell_selected)
            # 清除单元格位置显示
            self.cell_position_label.setText("")
    
    def _on_column_sql_request(self, table_name: str, column_name: str, sql_type: str):
        """处理列快速SQL请求"""
        if not table_name:
            table_name = self._current_table
        if not table_name:
            return
        
        # 根据sql_type生成SQL
        sql_templates = {
            "order_asc": f'SELECT * FROM "{table_name}" ORDER BY "{column_name}" ASC',
            "order_desc": f'SELECT * FROM "{table_name}" ORDER BY "{column_name}" DESC',
            "distinct": f'SELECT DISTINCT "{column_name}" FROM "{table_name}" ORDER BY "{column_name}"',
            "count": f'SELECT "{column_name}", COUNT(*) as count FROM "{table_name}" GROUP BY "{column_name}" ORDER BY count DESC',
            "group_by": f'SELECT "{column_name}", COUNT(*) as count FROM "{table_name}" GROUP BY "{column_name}" ORDER BY count DESC',
            "filter_null": f'SELECT * FROM "{table_name}" WHERE "{column_name}" IS NULL',
            "filter_not_null": f'SELECT * FROM "{table_name}" WHERE "{column_name}" IS NOT NULL',
        }
        
        sql = sql_templates.get(sql_type, "")
        if sql:
            self.sql_editor.set_sql(sql)
            self._execute_sql(sql)
    
    def _on_column_analysis_request(self, column_name: str):
        """处理列分析请求"""
        # 使用单元格检查器显示列分析
        if self._current_table:
            self._load_column_analysis(column_name)
    
    def _load_column_analysis(self, column_name: str):
        """加载列分析数据"""
        if not self._current_table:
            return
        
        def do_analyze():
            # 获取列分析数据
            return self.ipc_client.analyze_column(self._current_table, column_name)
        
        def on_analyzed(response):
            if response.success and response.data:
                self.cell_inspector.set_column_analysis(column_name, response.data)
        
        self._run_async(do_analyze, on_analyzed)
    
    def _load_column_analysis_from_backend(self, table_name: str, column_name: str):
        """从后端加载列分析数据（整个表）"""
        def do_analyze():
            return self.ipc_client.analyze_column(table_name, column_name)
        
        def on_analyzed(response):
            if response.success and response.data:
                self.cell_inspector.set_column_analysis(column_name, response.data)
            else:
                # 如果后端分析失败，回退到本地分析
                current_widget = self.data_tabs.currentWidget()
                if isinstance(current_widget, DataTableWidget):
                    self._load_column_analysis_from_widget(column_name, current_widget)
        
        self._run_async(do_analyze, on_analyzed)
    
    def _load_column_analysis_from_sql(self, sql: str, column_name: str):
        """从SQL查询加载列分析数据（整个查询结果）"""
        def do_analyze():
            return self.ipc_client.analyze_column_sql(sql, column_name)
        
        def on_analyzed(response):
            if response.success and response.data:
                self.cell_inspector.set_column_analysis(column_name, response.data)
            else:
                # 如果后端分析失败，回退到本地分析
                current_widget = self.data_tabs.currentWidget()
                if isinstance(current_widget, DataTableWidget):
                    self._load_column_analysis_from_widget(column_name, current_widget)
        
        self._run_async(do_analyze, on_analyzed)
    
    def _load_column_analysis_from_widget(self, column_name: str, widget: DataTableWidget):
        """从widget数据本地计算列分析"""
        try:
            column_data = widget.get_column_data(column_name)
            if not column_data:
                return
            
            # 本地计算统计信息
            import statistics
            
            total_rows = len(column_data)
            missing_count = sum(1 for v in column_data if v is None or str(v) == 'NULL' or str(v) == '')
            non_null_values = [v for v in column_data if v is not None and str(v) != 'NULL' and str(v) != '']
            unique_count = len(set(str(v) for v in non_null_values))
            missing_pct = (missing_count / total_rows * 100) if total_rows > 0 else 0
            
            # 判断数据类型
            numeric_values = []
            for v in non_null_values:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    pass
            
            is_numeric = len(numeric_values) > len(non_null_values) * 0.5
            
            analysis = {
                'dtype': 'numeric' if is_numeric else 'text',
                'total_rows': total_rows,
                'unique_count': unique_count,
                'missing_count': missing_count,
                'missing_percentage': missing_pct,
                'is_numeric': is_numeric,
            }
            
            # 数值统计 - 使用 numeric_stats 字典格式
            if is_numeric and numeric_values:
                numeric_stats = {
                    'min': min(numeric_values),
                    'max': max(numeric_values),
                    'mean': statistics.mean(numeric_values),
                    'median': statistics.median(numeric_values),
                }
                if len(numeric_values) > 1:
                    numeric_stats['std'] = statistics.stdev(numeric_values)
                    sorted_vals = sorted(numeric_values)
                    n = len(sorted_vals)
                    numeric_stats['q1'] = sorted_vals[n // 4]
                    numeric_stats['q3'] = sorted_vals[3 * n // 4]
                analysis['numeric_stats'] = numeric_stats
            
            # Top值统计 - 使用元组列表格式 [(value, count), ...]
            from collections import Counter
            value_counts = Counter(str(v) for v in non_null_values)
            top_values = value_counts.most_common(10)
            analysis['top_values'] = top_values  # 保持元组格式
            
            self.cell_inspector.set_column_analysis(column_name, analysis)
        except Exception as e:
            print(f"本地列分析失败: {e}")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 CSV Analyzer",
            """<h2>CSV Analyzer</h2>
            <p>版本 1.0.0</p>
            <p>一个基于PyQt6的大体积CSV查看分析工具</p>
            <p>特性:</p>
            <ul>
                <li>支持大文件（使用DuckDB引擎）</li>
                <li>SQL查询支持</li>
                <li>数据分析（缺失值、数值统计）</li>
                <li>前后端分离架构</li>
            </ul>
            """
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._shutting_down:
            event.ignore()
            return
        # 只在工作区被修改时询问保存
        if self._workspace_dirty:
            reply = QMessageBox.question(
                self, "保存工作区",
                f"工作区 \"{self._current_workspace_name}\" 有未保存的更改。\n是否保存？",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Save:
                if not self._save_workspace():
                    # 保存失败，取消关闭
                    event.ignore()
                    return
        # 标记正在退出，先隐藏前端界面
        self._shutting_down = True
        self.hide()

        # 分阶段关闭：先前端UI，后后端，再退出主进程
        QTimer.singleShot(0, self._graceful_shutdown)
        event.accept()

    def _graceful_shutdown(self):
        """分阶段关闭：先清理前端资源，再停后端，最后退出主进程"""
        # 收起并销毁弹出控件
        try:
            popup = getattr(self, 'workspace_popup', None)
            if popup:
                popup.removeEventFilter(self)
                popup.hide()
                popup.deleteLater()
                self.workspace_popup = None
        except Exception:
            pass

        # 移除事件过滤器
        try:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        except Exception:
            pass

        # 停止所有异步工作线程
        for worker in list(self._workers):
            try:
                if worker.isRunning():
                    worker.quit()
                    worker.wait(1000)
            except Exception:
                pass
        self._workers.clear()

        # 停止后端
        try:
            if hasattr(self, 'ipc_client'):
                self.ipc_client.stop()
        except Exception:
            pass

        # 退出主进程
        try:
            QTimer.singleShot(0, QApplication.quit)
        except Exception:
            pass
    
    # === 工作区管理 ===
    
    def _save_workspace(self) -> bool:
        """保存工作区，返回是否成功"""
        # 确保有工作区ID
        if not self._current_workspace_id:
            # 创建新工作区
            name, ok = QInputDialog.getText(
                self, "保存工作区", "请输入工作区名称:",
                text="新工作区"
            )
            if not ok or not name.strip():
                return False
            config = self.workspace_manager.create_workspace(name.strip())
            self._current_workspace_id = config.id
            self._current_workspace_name = config.name
        
        # 加载现有配置或创建新配置
        config = self.workspace_manager.load(self._current_workspace_id)
        if not config.id or config.id != self._current_workspace_id:
            config = WorkspaceConfig()
            config.id = self._current_workspace_id
            config.name = self._current_workspace_name
        
        # 保存已加载的文件
        config.loaded_files = self._loaded_files.copy()
        
        # 保存窗口几何信息
        config.window_geometry = {
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height()
        }
        
        # 保存分割器状态
        config.splitter_sizes = {
            'main': self.main_splitter.sizes(),
            'center': self.center_splitter.sizes()
        }
        
        # 保存面板可见性
        config.panel_visibility = {
            'sidebar': self.sidebar.isVisible(),
            'cell_inspector': self.cell_inspector.isVisible(),
            'sql_editor': self.sql_editor.isVisible()
        }
        
        # 保存当前表
        config.current_table = self._current_table
        
        # 保存SQL
        config.last_sql = self.sql_editor.get_sql()
        
        # 保存视图
        try:
            resp = self.ipc_client.get_views()
            if resp.success:
                config.views = resp.data
        except:
            pass
        
        # 执行保存
        success = self.workspace_manager.save(config)
        
        if success:
            # 清除修改标记
            self._workspace_dirty = False
            self._update_window_title()
            self._show_status(f"工作区 \"{self._current_workspace_name}\" 已保存")
            return True
        else:
            QMessageBox.warning(self, "保存失败", "无法保存工作区，请检查磁盘空间和权限。")
            return False
    
    def _load_workspace_async(self):
        """异步加载工作区 - 不阻塞UI"""
        config = self.workspace_manager.load(self._current_workspace_id)
        
        # 更新当前工作区信息
        if config.id:
            self._current_workspace_id = config.id
            self._current_workspace_name = config.name
        
        # 重置修改标记
        self._workspace_dirty = False
        self._update_window_title()
        
        # 恢复面板可见性（快速，不阻塞）
        vis = config.panel_visibility
        if 'sidebar' in vis:
            self.sidebar.setVisible(vis['sidebar'])
            self.toggle_sidebar_btn.setChecked(vis['sidebar'])
        if 'cell_inspector' in vis:
            self.cell_inspector.setVisible(vis['cell_inspector'])
            self.toggle_inspector_btn.setChecked(vis['cell_inspector'])
        if 'sql_editor' in vis:
            self.sql_editor.setVisible(vis['sql_editor'])
            self.toggle_sql_btn.setChecked(vis['sql_editor'])
        
        # 恢复分割器状态（快速，不阻塞）
        if 'main' in config.splitter_sizes:
            self.main_splitter.setSizes(config.splitter_sizes['main'])
        if 'center' in config.splitter_sizes:
            self.center_splitter.setSizes(config.splitter_sizes['center'])
        
        # 恢复SQL（快速，不阻塞）
        if config.last_sql:
            self.sql_editor.set_sql(config.last_sql)
        
        # 逐个异步加载CSV文件，避免阻塞
        files_to_load = [f for f in config.loaded_files if os.path.exists(f)]
        self._pending_files = files_to_load.copy()
        self._total_files_to_load = len(files_to_load)  # 记录总数
        self._workspace_config = config  # 保存配置用于后续恢复
        
        if files_to_load:
            self._show_status(f"正在加载工作区: 第 1/{len(files_to_load)} 个文件...", timeout=0)
            self._load_next_workspace_file()
        else:
            # 没有文件要加载，直接完成
            self._finish_workspace_load()
    
    def _load_next_workspace_file(self):
        """加载下一个工作区文件"""
        if not self._pending_files:
            self._finish_workspace_load()
            return
        
        filepath = self._pending_files.pop(0)
        total = getattr(self, '_total_files_to_load', 1)
        current = total - len(self._pending_files)
        
        self._show_status(f"正在加载: 第 {current}/{total} 个文件 - {os.path.basename(filepath)}", timeout=0)
        
        def do_load():
            return self.ipc_client.load_csv(filepath)
        
        def on_loaded(response):
            if response.success:
                table_name = response.data.get('name', os.path.basename(filepath))
                if filepath not in self._loaded_files:
                    self._loaded_files.append(filepath)
                # 记录表名到文件路径的映射
                self._table_to_file[table_name] = filepath
                self.workspace_manager.add_recent_file(filepath)
            
            # 继续加载下一个文件
            QTimer.singleShot(50, self._load_next_workspace_file)
        
        def on_error(error):
            print(f"加载文件失败: {filepath} - {error}")
            # 继续加载下一个文件
            QTimer.singleShot(50, self._load_next_workspace_file)
        
        self._run_async(do_load, on_loaded, on_error)
    
    def _finish_workspace_load(self):
        """完成工作区加载"""
        config = getattr(self, '_workspace_config', None)
        
        # 刷新表列表
        self._refresh_tables()
        self._update_recent_menu()
        self._update_sql_completer()
        
        # 更新工作区搜索补全
        if hasattr(self, '_update_workspace_completer'):
            self._update_workspace_completer()
        
        if config:
            # 恢复视图
            if config.views:
                def restore_views():
                    for view_name, sql in config.views.items():
                        try:
                            self.ipc_client.save_view(view_name, sql)
                        except:
                            pass
                    self._refresh_tables()
                QTimer.singleShot(300, restore_views)
            
            # 恢复当前表
            if config.current_table:
                QTimer.singleShot(500, lambda: self._on_table_open(config.current_table))
        
        # 确保修改标记为False
        self._workspace_dirty = False
        self._update_window_title()
        
        self._show_status("工作区已加载")
    
    def _load_workspace(self):
        """加载工作区（兼容旧调用）"""
        self._load_workspace_async()
    
    def _update_recent_menu(self):
        """更新最近打开菜单"""
        self.recent_menu.clear()
        
        recent_files = self.workspace_manager.get_recent_files()
        
        if not recent_files:
            action = QAction("(无)", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return
        
        for filepath in recent_files:
            filename = os.path.basename(filepath)
            action = QAction(filename, self)
            action.setToolTip(filepath)
            action.triggered.connect(lambda checked, f=filepath: self._load_csv_file(f))
            self.recent_menu.addAction(action)
        
        self.recent_menu.addSeparator()
        
        clear_action = QAction("清除记录", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)
    
    def _clear_recent_files(self):
        """清除最近打开记录"""
        config = self.workspace_manager.load()
        config.recent_files = []
        self.workspace_manager.save(config)
        self._update_recent_menu()
    
    def _load_csv_file(self, filepath: str, show_tab: bool = True):
        """加载CSV文件"""
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "文件不存在", f"文件 {filepath} 不存在")
            return
        
        # 加载文件前移除欢迎页
        self._remove_welcome_page()
        
        self._show_status(f"正在加载: {os.path.basename(filepath)}...")
        self._show_progress(True)
        
        def do_load():
            return self.ipc_client.load_csv(filepath)
        
        def on_loaded(response):
            self._show_progress(False)
            if response.success:
                # 后端 load_csv 返回字段是 name（真实表名）
                table_name = response.data.get('name', os.path.basename(filepath))
                
                # 添加到已加载文件
                if filepath not in self._loaded_files:
                    self._loaded_files.append(filepath)
                    # 标记工作区已修改
                    self._mark_workspace_dirty()
                
                # 记录表名到文件路径的映射
                self._table_to_file[table_name] = filepath
                
                # 添加到最近文件
                self.workspace_manager.add_recent_file(filepath)
                self._update_recent_menu()
                
                self._refresh_tables()
                self._show_status(f"已加载: {table_name}")
                self._update_sql_completer()
                
                if show_tab:
                    self._on_table_open(table_name)
            else:
                QMessageBox.warning(self, "加载失败", response.error or "未知错误")
        
        self._run_async(do_load, on_loaded)
