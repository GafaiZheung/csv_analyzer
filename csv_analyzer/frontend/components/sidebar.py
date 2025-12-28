"""
侧边栏组件 - 显示已加载的表和视图
类似Navicat的导航面板
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu, QPushButton, QLineEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QFont

from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class SidebarWidget(QWidget):
    """侧边栏组件"""
    
    # 信号
    table_selected = pyqtSignal(str)  # 表名
    table_double_clicked = pyqtSignal(str)  # 双击表
    view_selected = pyqtSignal(str, str)  # 视图名, SQL
    view_double_clicked = pyqtSignal(str, str)  # 双击视图
    table_delete_requested = pyqtSignal(str)  # 请求删除表
    view_delete_requested = pyqtSignal(str)  # 请求删除视图
    refresh_requested = pyqtSignal()  # 请求刷新
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._setup_ui()
        self._tables = {}
        self._views = {}
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 搜索框
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(8, 8, 8, 8)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索表和视图...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_container)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {VSCODE_COLORS['border']};")
        layout.addWidget(line)
        
        # 表区域
        tables_header = QLabel("表 (TABLES)")
        tables_header.setObjectName("sectionTitle")
        tables_header.setStyleSheet(f"""
            color: {VSCODE_COLORS['text_secondary']};
            font-size: 11px;
            font-weight: 600;
            padding: 10px 12px 6px 12px;
        """)
        layout.addWidget(tables_header)
        
        self.tables_tree = QTreeWidget()
        self.tables_tree.setHeaderHidden(True)
        self.tables_tree.setIndentation(18)  # 增加缩进以便展开图标可见
        self.tables_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tables_tree.customContextMenuRequested.connect(self._show_table_context_menu)
        self.tables_tree.itemClicked.connect(self._on_table_clicked)
        self.tables_tree.itemDoubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.tables_tree)
        
        # 视图区域
        views_header = QLabel("视图 (VIEWS)")
        views_header.setObjectName("sectionTitle")
        views_header.setStyleSheet(f"""
            color: {VSCODE_COLORS['text_secondary']};
            font-size: 11px;
            font-weight: 600;
            padding: 10px 12px 6px 12px;
        """)
        layout.addWidget(views_header)
        
        self.views_tree = QTreeWidget()
        self.views_tree.setHeaderHidden(True)
        self.views_tree.setIndentation(18)  # 增加缩进以便展开图标可见
        self.views_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.views_tree.customContextMenuRequested.connect(self._show_view_context_menu)
        self.views_tree.itemClicked.connect(self._on_view_clicked)
        self.views_tree.itemDoubleClicked.connect(self._on_view_double_clicked)
        layout.addWidget(self.views_tree)
        
        # 设置样式
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-right: 1px solid {VSCODE_COLORS['border']};
            }}
        """)
    
    def update_tables(self, tables: list):
        """更新表列表"""
        self.tables_tree.clear()
        self._tables.clear()
        
        for table in tables:
            item = QTreeWidgetItem()
            table_name = table['name']
            row_count = table.get('row_count', 0)
            col_count = len(table.get('columns', []))
            
            item.setText(0, f"{table_name}")
            item.setIcon(0, get_icon("table"))
            item.setToolTip(0, f"表: {table_name}\n行数: {row_count:,}\n列数: {col_count}")
            item.setData(0, Qt.ItemDataRole.UserRole, table_name)
            
            # 添加列作为子节点
            for col in table.get('columns', []):
                col_item = QTreeWidgetItem()
                col_name = col['name']
                col_type = col['dtype']
                col_item.setText(0, f"{col_name} ({col_type})")
                col_item.setIcon(0, get_icon("column"))
                col_item.setData(0, Qt.ItemDataRole.UserRole, f"{table_name}.{col_name}")
                item.addChild(col_item)
            
            self.tables_tree.addTopLevelItem(item)
            self._tables[table_name] = table
    
    def update_views(self, views: dict):
        """更新视图列表"""
        self.views_tree.clear()
        self._views.clear()
        
        for view_name, sql in views.items():
            item = QTreeWidgetItem()
            item.setText(0, f"{view_name}")
            item.setIcon(0, get_icon("view"))
            item.setToolTip(0, f"视图: {view_name}\nSQL: {sql[:100]}...")
            item.setData(0, Qt.ItemDataRole.UserRole, view_name)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, sql)
            
            self.views_tree.addTopLevelItem(item)
            self._views[view_name] = sql
    
    def _on_search(self, text: str):
        """搜索过滤"""
        text = text.lower()
        
        # 过滤表
        for i in range(self.tables_tree.topLevelItemCount()):
            item = self.tables_tree.topLevelItem(i)
            table_name = item.data(0, Qt.ItemDataRole.UserRole)
            visible = text in table_name.lower() if text else True
            item.setHidden(not visible)
        
        # 过滤视图
        for i in range(self.views_tree.topLevelItemCount()):
            item = self.views_tree.topLevelItem(i)
            view_name = item.data(0, Qt.ItemDataRole.UserRole)
            visible = text in view_name.lower() if text else True
            item.setHidden(not visible)
    
    def _on_table_clicked(self, item: QTreeWidgetItem, column: int):
        """点击表项"""
        # 只处理顶级项（表）
        if item.parent() is None:
            table_name = item.data(0, Qt.ItemDataRole.UserRole)
            if table_name:
                self.table_selected.emit(table_name)
    
    def _on_table_double_clicked(self, item: QTreeWidgetItem, column: int):
        """双击表项"""
        if item.parent() is None:
            table_name = item.data(0, Qt.ItemDataRole.UserRole)
            if table_name:
                self.table_double_clicked.emit(table_name)
    
    def _on_view_clicked(self, item: QTreeWidgetItem, column: int):
        """点击视图项"""
        view_name = item.data(0, Qt.ItemDataRole.UserRole)
        sql = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if view_name and sql:
            self.view_selected.emit(view_name, sql)
    
    def _on_view_double_clicked(self, item: QTreeWidgetItem, column: int):
        """双击视图项"""
        view_name = item.data(0, Qt.ItemDataRole.UserRole)
        sql = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if view_name and sql:
            self.view_double_clicked.emit(view_name, sql)
    
    def _show_table_context_menu(self, position):
        """显示表的右键菜单"""
        item = self.tables_tree.itemAt(position)
        if not item or item.parent() is not None:
            return
        
        table_name = item.data(0, Qt.ItemDataRole.UserRole)
        if not table_name:
            return
        
        menu = QMenu(self)
        
        open_action = menu.addAction("打开表")
        open_action.triggered.connect(lambda: self.table_double_clicked.emit(table_name))
        
        menu.addSeparator()
        
        query_action = menu.addAction("新建查询")
        query_action.triggered.connect(lambda: self._create_query_for_table(table_name))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("删除表")
        delete_action.triggered.connect(lambda: self.table_delete_requested.emit(table_name))
        
        menu.exec(self.tables_tree.mapToGlobal(position))
    
    def _show_view_context_menu(self, position):
        """显示视图的右键菜单"""
        item = self.views_tree.itemAt(position)
        if not item:
            return
        
        view_name = item.data(0, Qt.ItemDataRole.UserRole)
        sql = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not view_name:
            return
        
        menu = QMenu(self)
        
        open_action = menu.addAction("打开视图")
        open_action.triggered.connect(lambda: self.view_double_clicked.emit(view_name, sql))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("删除视图")
        delete_action.triggered.connect(lambda: self.view_delete_requested.emit(view_name))
        
        menu.exec(self.views_tree.mapToGlobal(position))
    
    def _create_query_for_table(self, table_name: str):
        """为表创建查询"""
        sql = f'SELECT * FROM "{table_name}"'
        self.view_double_clicked.emit(f"Query_{table_name}", sql)
