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
    QApplication, QToolButton, QFrame, QTabBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QEvent, QRect
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPainter, QColor, QPen

from csv_analyzer.core.ipc import IPCClient, MessageType
from csv_analyzer.core.workspace import WorkspaceManager, WorkspaceConfig
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
    
    def __init__(self):
        super().__init__()
        
        # IPC客户端
        self.ipc_client = IPCClient()
        
        # 工作区管理器
        self.workspace_manager = WorkspaceManager()
        
        # 当前状态
        self._current_table: Optional[str] = None
        self._workers: list = []
        self._loaded_files: List[str] = []

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
        
        # 启动后端
        self._start_backend()
        
        # 加载工作区
        QTimer.singleShot(500, self._load_workspace)
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("CSV Analyzer")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

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
        
        # 侧边栏
        self.sidebar = SidebarWidget()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(400)
        self.main_splitter.addWidget(self.sidebar)
        
        # 中间区域
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        # 中间垂直分割器
        self.center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 数据表格Tab（标签靠左）
        self.data_tabs = QTabWidget()
        # 使用自定义关闭按钮（只显示当前Tab的关闭按钮）
        self.data_tabs.setTabsClosable(False)
        self.data_tabs.setMovable(True)
        self.data_tabs.setDocumentMode(True)
        self.data_tabs.currentChanged.connect(lambda _: self._update_tab_close_buttons())
        # 标签靠左对齐
        self.data_tabs.tabBar().setExpanding(False)
        self.center_splitter.addWidget(self.data_tabs)
        
        # 下部：SQL编辑器
        self.sql_editor = SQLEditorWidget()
        self.sql_editor.setMinimumHeight(100)
        self.sql_editor.setMaximumHeight(400)
        self.center_splitter.addWidget(self.sql_editor)
        
        self.center_splitter.setSizes([500, 180])
        center_layout.addWidget(self.center_splitter)
        
        self.main_splitter.addWidget(center_widget)
        
        # 右侧面板：单元格检查器（替代原来的分析面板）
        self.cell_inspector = CellInspectorWidget()
        self.cell_inspector.setMinimumWidth(280)
        self.cell_inspector.setMaximumWidth(450)
        self.main_splitter.addWidget(self.cell_inspector)
        
        self.main_splitter.setSizes([250, 850, 320])
        
        layout.addWidget(self.main_splitter)
        main_layout.addWidget(content_widget)
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
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
        toolbar.setIconSize(QSize(16, 16) if is_macos else QSize(16, 16))

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
                    padding: 0px 8px;
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
                    spacing: 4px;
                    padding: 0px 8px;
                }}
                QToolButton {{
                    padding: 2px 8px;
                    border-radius: 4px;
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
        spacer = _WindowDragArea(self)
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,
                     spacer.sizePolicy().verticalPolicy().Preferred)
        toolbar.addWidget(spacer)
        
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
        
        # SQL编辑器信号
        self.sql_editor.execute_requested.connect(self._execute_sql)
        self.sql_editor.save_view_requested.connect(self._save_view)
    
    def _start_backend(self):
        """启动后端"""
        try:
            self.ipc_client.start()
            self.backend_status.setText("后端：运行中")
            self._show_status("后端服务已启动")
        except Exception as e:
            self.backend_status.setText("后端：启动失败")
            QMessageBox.critical(self, "错误", f"后端启动失败: {e}")
    
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
        """导出结果"""
        # TODO: 实现导出功能
        pass
    
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
        table_widget.page_changed.connect(
            lambda offset, limit: self._load_table_data(table_name, offset, limit, table_widget)
        )
        # 连接列右键菜单信号
        table_widget.column_sql_requested.connect(self._on_column_sql_request)
        table_widget.column_selected_for_analysis.connect(self._on_column_analysis_request)
        # 连接单元格选中信号
        table_widget.cell_selected.connect(self._on_cell_selected)
        
        # 添加Tab（左侧显示图标）
        index = self.data_tabs.addTab(table_widget, get_icon("table"), table_name)
        self.data_tabs.setCurrentIndex(index)
        self._attach_tab_close_button(index)
        self._update_tab_close_buttons()
        
        # 加载数据
        self._current_table = table_name
        self._load_table_data(table_name, 0, 100, table_widget)
        self._load_analysis(table_name)
        
        # 更新SQL编辑器的表名列表以支持自动补全
        self._update_sql_completer()
    
    def _load_table_data(self, table_name: str, offset: int, limit: int, table_widget: DataTableWidget):
        """加载表数据"""
        self._show_status(f"加载数据: {table_name}...")
        
        def do_load():
            return self.ipc_client.get_table_data(table_name, limit, offset)
        
        def on_loaded(response):
            if response.success:
                data = response.data
                table_widget.set_data(
                    data['columns'],
                    data['data'],
                    data['total_rows']
                )
                self._show_status(f"已加载 {len(data['data'])} / {data['total_rows']} 行")
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
            else:
                QMessageBox.warning(self, "删除失败", response.error or "未知错误")
    
    # === 视图操作 ===
    
    def _on_view_open(self, view_name: str, sql: str):
        """打开视图"""
        # 在SQL编辑器中显示SQL
        self.sql_editor.set_sql(sql)
        # 执行查询
        self._execute_sql(sql)
    
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
            else:
                QMessageBox.warning(self, "保存失败", response.error or "未知错误")
    
    # === SQL执行 ===
    
    def _on_execute_sql(self):
        """执行SQL菜单项"""
        sql = self.sql_editor.get_sql()
        if sql.strip():
            self._execute_sql(sql)
    
    def _execute_sql(self, sql: str):
        """执行SQL"""
        self._show_status("执行查询中...")
        self._show_progress(True)
        
        def do_execute():
            return self.ipc_client.execute_query(sql, 1000, 0)
        
        def on_executed(response):
            self._show_progress(False)
            
            if response.success:
                data = response.data
                
                if data.get('error'):
                    QMessageBox.warning(self, "查询错误", data['error'])
                    return
                
                # 创建或更新结果Tab
                tab_name = "查询结果"
                
                # 查找已有的结果Tab
                result_widget = None
                for i in range(self.data_tabs.count()):
                    if self.data_tabs.tabText(i) == tab_name:
                        result_widget = self.data_tabs.widget(i)
                        self.data_tabs.setCurrentIndex(i)
                        break
                
                if not result_widget:
                    result_widget = DataTableWidget()
                    result_widget.page_changed.connect(
                        lambda offset, limit: self._execute_sql_page(sql, offset, limit, result_widget)
                    )
                    index = self.data_tabs.addTab(result_widget, get_icon("view"), tab_name)
                    self.data_tabs.setCurrentIndex(index)
                    self._attach_tab_close_button(index)
                    self._update_tab_close_buttons()
                
                result_widget.set_data(
                    data['columns'],
                    data['data'],
                    data['total_rows']
                )
                
                exec_time = data.get('execution_time', 0)
                self._show_status(f"查询完成: {data['total_rows']} 行, 耗时 {exec_time:.3f}s")
            else:
                QMessageBox.warning(self, "查询失败", response.error or "未知错误")
        
        self._run_async(do_execute, on_executed)
    
    def _execute_sql_page(self, sql: str, offset: int, limit: int, result_widget: DataTableWidget):
        """执行SQL分页查询"""
        def do_execute():
            return self.ipc_client.execute_query(sql, limit, offset)
        
        def on_executed(response):
            if response.success:
                data = response.data
                if not data.get('error'):
                    result_widget.set_data(
                        data['columns'],
                        data['data'],
                        data['total_rows']
                    )
        
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
        self.data_tabs.removeTab(index)
        self._update_tab_close_buttons()

    def _attach_tab_close_button(self, index: int):
        """给Tab添加右侧关闭按钮"""
        tab_bar = self.data_tabs.tabBar()
        close_btn = QToolButton(tab_bar)
        close_btn.setAutoRaise(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setIcon(get_icon("clear", size=14))
        close_btn.setToolTip("关闭")
        close_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                padding: 0px;
            }}
            QToolButton:hover {{
                background: {VSCODE_COLORS['hover']};
                border-radius: 4px;
            }}
        """)
        # 动态计算所在 tab index，避免 Tab 可移动导致 index 变化
        def _close_current_tab():
            pt = close_btn.mapTo(tab_bar, close_btn.rect().center())
            tab_index = tab_bar.tabAt(pt)
            if tab_index >= 0:
                self._on_tab_close(tab_index)

        close_btn.clicked.connect(_close_current_tab)
        tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_btn)

    def _update_tab_close_buttons(self):
        """当前Tab关闭按钮常亮，其它Tab隐藏"""
        tab_bar = self.data_tabs.tabBar()
        current = self.data_tabs.currentIndex()
        for i in range(self.data_tabs.count()):
            btn = tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if btn is not None:
                btn.setVisible(i == current)
    
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
        
        # 加载列分析
        if column_name and self._current_table:
            self._load_column_analysis(column_name)
    
    def _on_column_sql_request(self, table_name: str, column_name: str, sql_type: str):
        """处理列快速SQL请求"""
        if not table_name:
            table_name = self._current_table
        if not table_name:
            return
        
        # 根据sql_type生成SQL
        sql_templates = {
            "order_asc": f'SELECT * FROM "{table_name}" ORDER BY "{column_name}" ASC LIMIT 1000',
            "order_desc": f'SELECT * FROM "{table_name}" ORDER BY "{column_name}" DESC LIMIT 1000',
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
        # 自动保存工作区
        self._save_workspace()
        
        # 停止后端
        try:
            self.ipc_client.stop()
        except:
            pass
        
        event.accept()
    
    # === 工作区管理 ===
    
    def _save_workspace(self):
        """保存工作区"""
        config = WorkspaceConfig()
        
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
        
        self.workspace_manager.save(config)
        self._show_status("工作区已保存")
    
    def _load_workspace(self):
        """加载工作区"""
        config = self.workspace_manager.load()
        
        # 恢复面板可见性
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
        
        # 恢复分割器状态
        if 'main' in config.splitter_sizes:
            self.main_splitter.setSizes(config.splitter_sizes['main'])
        if 'center' in config.splitter_sizes:
            self.center_splitter.setSizes(config.splitter_sizes['center'])
        
        # 恢复SQL
        if config.last_sql:
            self.sql_editor.set_sql(config.last_sql)
        
        # 加载之前的CSV文件
        for filepath in config.loaded_files:
            if os.path.exists(filepath):
                self._load_csv_file(filepath, show_tab=False)
        
        # 恢复当前表
        if config.current_table:
            QTimer.singleShot(500, lambda: self._on_table_open(config.current_table))
        
        self._show_status("工作区已加载")
    
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
