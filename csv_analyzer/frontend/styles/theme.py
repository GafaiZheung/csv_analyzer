"""
VSCode风格的主题样式
"""

# VSCode Dark+ 主题色
VSCODE_COLORS = {
    # 基础颜色
    "background": "#1e1e1e",
    "foreground": "#d4d4d4",
    "sidebar_bg": "#252526",
    "editor_bg": "#1e1e1e",
    "titlebar_bg": "#3c3c3c",
    "statusbar_bg": "#007acc",
    "panel_bg": "#1e1e1e",
    
    # 边框
    "border": "#3c3c3c",
    "border_light": "#464646",
    
    # 文本颜色
    "text_primary": "#d4d4d4",
    "text_secondary": "#858585",
    "text_inactive": "#6e6e6e",
    
    # 高亮颜色
    "selection": "#264f78",
    "selection_inactive": "#3a3d41",
    "highlight": "#ffffff1a",
    "hover": "#2a2d2e",
    
    # 状态颜色
    "success": "#4ec9b0",
    "warning": "#dcdcaa",
    "error": "#f14c4c",
    "info": "#3794ff",
    
    # 语法高亮
    "keyword": "#569cd6",
    "string": "#ce9178",
    "number": "#b5cea8",
    "comment": "#6a9955",
    "function": "#dcdcaa",
    "variable": "#9cdcfe",
    
    # 按钮
    "button_bg": "#0e639c",
    "button_hover": "#1177bb",
    "button_pressed": "#094771",
    
    # 输入框
    "input_bg": "#3c3c3c",
    "input_border": "#3c3c3c",
    "input_focus_border": "#007fd4",
    
    # 表格
    "table_header_bg": "#252526",
    "table_row_alt": "#2a2d2e",
    "table_border": "#3c3c3c",
    
    # 滚动条
    "scrollbar_bg": "#1e1e1e",
    "scrollbar_thumb": "#424242",
    "scrollbar_thumb_hover": "#4f4f4f",
    
    # Tab
    "tab_active_bg": "#1e1e1e",
    "tab_inactive_bg": "#2d2d2d",
    "tab_border": "#252526",
    
    # 下拉菜单
    "dropdown_bg": "#252526",
    "dropdown_border": "#454545",
    
    # 列表
    "list_hover": "#2a2d2e",
    "list_active": "#094771",
    
    # 面板
    "panel_header_bg": "#383838",
    "panel_border": "#3c3c3c",
    
    # 其他
    "text": "#cccccc",
    "icon_foreground": "#c5c5c5",
    
    # macOS Tahoe 风格圆角
    "window_radius": "10px",
}


def get_main_stylesheet() -> str:
    """获取主样式表"""
    colors = VSCODE_COLORS
    
    return f"""
    /* 全局样式 - macOS Tahoe圆角窗口 */
    QMainWindow {{
        background-color: transparent;
        color: {colors['foreground']};
    }}
    
    QMainWindow > QWidget#centralWidget {{
        background-color: {colors['background']};
        border-radius: {colors['window_radius']};
    }}
    
    QWidget {{
        background-color: {colors['background']};
        color: {colors['foreground']};
        font-size: 13px;
    }}
    
    /* 菜单栏 */
    QMenuBar {{
        background-color: {colors['titlebar_bg']};
        color: {colors['foreground']};
        border: none;
        padding: 2px 0px;
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 4px 8px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {colors['highlight']};
    }}
    
    QMenu {{
        background-color: {colors['sidebar_bg']};
        color: {colors['foreground']};
        border: 1px solid {colors['border']};
        padding: 4px 0px;
    }}
    
    QMenu::item {{
        padding: 6px 30px 6px 20px;
    }}
    
    QMenu::item:selected {{
        background-color: {colors['selection']};
    }}
    
    QMenu::separator {{
        height: 1px;
        background-color: {colors['border']};
        margin: 4px 10px;
    }}
    
    /* 工具栏 */
    QToolBar {{
        background-color: {colors['titlebar_bg']};
        border: none;
        spacing: 2px;
        padding: 2px;
    }}
    
    QToolButton {{
        background-color: transparent;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        color: {colors['foreground']};
    }}
    
    QToolButton:hover {{
        background-color: {colors['hover']};
    }}
    
    QToolButton:pressed {{
        background-color: {colors['selection']};
    }}
    
    /* 状态栏 - 底部圆角 */
    QStatusBar {{
        background-color: {colors['statusbar_bg']};
        color: white;
        border: none;
        min-height: 22px;
        padding: 0px 12px;
        border-bottom-left-radius: {colors['window_radius']};
        border-bottom-right-radius: {colors['window_radius']};
    }}
    
    QStatusBar::item {{
        border: none;
    }}

    QLabel#statusText {{
        color: white;
        padding: 0px;
        margin: 0px;
    }}

    QLabel#backendStatus {{
        color: white;
        padding: 0px;
        margin: 0px;
    }}
    
    /* 分割器 */
    QSplitter::handle {{
        background-color: {colors['border']};
    }}
    
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    
    /* 滚动条 */
    QScrollBar:vertical {{
        background-color: {colors['scrollbar_bg']};
        width: 14px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {colors['scrollbar_thumb']};
        min-height: 30px;
        border-radius: 7px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {colors['scrollbar_thumb_hover']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    QScrollBar:horizontal {{
        background-color: {colors['scrollbar_bg']};
        height: 14px;
        margin: 0;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {colors['scrollbar_thumb']};
        min-width: 30px;
        border-radius: 7px;
        margin: 2px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {colors['scrollbar_thumb_hover']};
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    
    /* Tab Widget */
    QTabWidget::tab-bar {{
        left: 0px;
        background-color: {colors['editor_bg']};
    }}

    QTabWidget::pane {{
        border: 1px solid {colors['border']};
        background-color: {colors['editor_bg']};
    }}

    QTabBar {{
        background-color: {colors['editor_bg']};
        border: none;
    }}

    QTabBar::scroller {{
        background-color: {colors['editor_bg']};
        border: none;
    }}
    
    QTabBar::tab {{
        background-color: {colors['tab_inactive_bg']};
        color: {colors['text_secondary']};
        border: none;
        padding: 8px 16px;
        min-width: 100px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {colors['tab_active_bg']};
        color: {colors['foreground']};
        border-top: 2px solid {colors['statusbar_bg']};
    }}
    
    QTabBar::tab:hover:!selected {{
        background-color: {colors['hover']};
    }}
    
    /* 按钮 */
    QPushButton {{
        background-color: {colors['button_bg']};
        color: white;
        border: none;
        border-radius: 2px;
        padding: 6px 14px;
        min-width: 80px;
    }}
    
    QPushButton:hover {{
        background-color: {colors['button_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {colors['button_pressed']};
    }}
    
    QPushButton:disabled {{
        background-color: {colors['border']};
        color: {colors['text_inactive']};
    }}
    
    /* 次要按钮 */
    QPushButton[secondary="true"] {{
        background-color: transparent;
        color: {colors['foreground']};
        border: 1px solid {colors['border']};
    }}
    
    QPushButton[secondary="true"]:hover {{
        background-color: {colors['hover']};
        border-color: {colors['border_light']};
    }}
    
    /* 输入框 */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {colors['input_bg']};
        color: {colors['foreground']};
        border: 1px solid {colors['input_border']};
        border-radius: 2px;
        padding: 4px 8px;
        selection-background-color: {colors['selection']};
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {colors['input_focus_border']};
    }}
    
    /* 下拉框 */
    QComboBox {{
        background-color: {colors['input_bg']};
        color: {colors['foreground']};
        border: 1px solid {colors['input_border']};
        border-radius: 2px;
        padding: 4px 8px;
        min-width: 100px;
    }}
    
    QComboBox:hover {{
        border-color: {colors['border_light']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {colors['foreground']};
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {colors['sidebar_bg']};
        color: {colors['foreground']};
        border: 1px solid {colors['border']};
        selection-background-color: {colors['selection']};
    }}
    
    /* 列表视图 */
    QListView, QListWidget {{
        background-color: {colors['sidebar_bg']};
        color: {colors['foreground']};
        border: none;
        outline: none;
    }}
    
    QListView::item, QListWidget::item {{
        padding: 6px 12px;
        border: none;
    }}
    
    QListView::item:selected, QListWidget::item:selected {{
        background-color: {colors['selection']};
    }}
    
    QListView::item:hover:!selected, QListWidget::item:hover:!selected {{
        background-color: {colors['hover']};
    }}
    
    /* 树视图 */
    QTreeView, QTreeWidget {{
        background-color: {colors['sidebar_bg']};
        color: {colors['foreground']};
        border: none;
        outline: none;
    }}
    
    QTreeView::item, QTreeWidget::item {{
        padding: 4px 8px;
        border: none;
    }}
    
    QTreeView::item:selected, QTreeWidget::item:selected {{
        background-color: {colors['selection']};
    }}
    
    QTreeView::item:hover:!selected, QTreeWidget::item:hover:!selected {{
        background-color: {colors['hover']};
    }}
    
    QTreeView::branch, QTreeWidget::branch {{
        background-color: transparent;
    }}
    
    /* 折叠状态 - 向右箭头 */
    QTreeView::branch:has-children:!has-siblings:closed,
    QTreeView::branch:closed:has-children:has-siblings,
    QTreeWidget::branch:has-children:!has-siblings:closed,
    QTreeWidget::branch:closed:has-children:has-siblings {{
        border-image: none;
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0iIzg1ODU4NSI+PHBhdGggZD0iTTYgNGw0IDQtNCA0eiIvPjwvc3ZnPg==);
    }}
    
    /* 展开状态 - 向下箭头 */
    QTreeView::branch:open:has-children:!has-siblings,
    QTreeView::branch:open:has-children:has-siblings,
    QTreeWidget::branch:open:has-children:!has-siblings,
    QTreeWidget::branch:open:has-children:has-siblings {{
        border-image: none;
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0iIzg1ODU4NSI+PHBhdGggZD0iTTQgNmw0IDQgNC00eiIvPjwvc3ZnPg==);
    }}
    
    /* 表格视图 */
    QTableView, QTableWidget {{
        background-color: {colors['editor_bg']};
        color: {colors['foreground']};
        gridline-color: {colors['table_border']};
        border: none;
        selection-background-color: {colors['selection']};
    }}
    
    QTableView::item, QTableWidget::item {{
        padding: 4px 8px;
    }}
    
    QTableView::item:alternate, QTableWidget::item:alternate {{
        background-color: {colors['table_row_alt']};
    }}
    
    QHeaderView::section {{
        background-color: {colors['table_header_bg']};
        color: {colors['foreground']};
        border: none;
        border-right: 1px solid {colors['table_border']};
        border-bottom: 1px solid {colors['table_border']};
        padding: 6px 10px;
        font-weight: 500;
    }}
    
    QHeaderView::section:hover {{
        background-color: {colors['hover']};
    }}
    
    /* 分组框 */
    QGroupBox {{
        color: {colors['foreground']};
        border: 1px solid {colors['border']};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 10px;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 5px;
        background-color: {colors['background']};
    }}
    
    /* 进度条 */
    QProgressBar {{
        background-color: {colors['input_bg']};
        border: none;
        border-radius: 2px;
        text-align: center;
        color: {colors['foreground']};
    }}
    
    QProgressBar::chunk {{
        background-color: {colors['statusbar_bg']};
        border-radius: 2px;
    }}

    /* 状态栏进度条（更接近 VSCode：细、扁、无文字） */
    QProgressBar#statusProgress {{
        background-color: {colors['highlight']};
        border: 1px solid {colors['highlight']};
        border-radius: 3px;
        padding: 0px;
    }}

    QProgressBar#statusProgress::chunk {{
        background-color: {colors['foreground']};
        border-radius: 3px;
    }}
    
    /* 工具提示 */
    QToolTip {{
        background-color: {colors['sidebar_bg']};
        color: {colors['foreground']};
        border: 1px solid {colors['border']};
        padding: 4px 8px;
    }}
    
    /* 标签 */
    QLabel {{
        background-color: transparent;
    }}
    
    /* 复选框 */
    QCheckBox {{
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {colors['border']};
        border-radius: 2px;
        background-color: {colors['input_bg']};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {colors['statusbar_bg']};
        border-color: {colors['statusbar_bg']};
    }}
    
    /* 对话框 */
    QDialog {{
        background-color: {colors['background']};
    }}
    
    /* 消息框 */
    QMessageBox {{
        background-color: {colors['background']};
    }}
    """


def get_sql_editor_stylesheet() -> str:
    """获取SQL编辑器样式"""
    colors = VSCODE_COLORS
    
    return f"""
    QPlainTextEdit {{
        background-color: {colors['editor_bg']};
        color: {colors['foreground']};
        font-family: "Menlo", "Consolas", "Monaco", "Courier New", monospace;
        font-size: 14px;
        line-height: 1.5;
        border: none;
        padding: 10px;
        selection-background-color: {colors['selection']};
    }}
    """


def get_sidebar_stylesheet() -> str:
    """获取侧边栏样式"""
    colors = VSCODE_COLORS
    
    return f"""
    QWidget#sidebar {{
        background-color: {colors['sidebar_bg']};
        border-right: 1px solid {colors['border']};
    }}
    
    QLabel#sectionTitle {{
        color: {colors['text_secondary']};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 10px 12px 6px 12px;
    }}
    """
