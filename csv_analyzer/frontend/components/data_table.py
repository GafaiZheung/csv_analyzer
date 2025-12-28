"""
数据表格组件 - 显示查询结果和表数据
支持分页和虚拟滚动
"""

from typing import List, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
    QPushButton, QLabel, QSpinBox, QComboBox, QHeaderView,
    QAbstractItemView, QFrame, QMenu, QSizePolicy
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QAction

from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class DataTableModel(QAbstractTableModel):
    """表格数据模型"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns: List[str] = []
        self._data: List[List[Any]] = []
        self._total_rows: int = 0
    
    def set_data(self, columns: List[str], data: List[List[Any]], total_rows: int):
        """设置数据"""
        self.beginResetModel()
        self._columns = columns
        self._data = data
        self._total_rows = total_rows
        self.endResetModel()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._columns)
    
    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row, col = index.row(), index.column()
        
        # 边界检查
        if row < 0 or row >= len(self._data):
            return None
        if col < 0 or col >= len(self._columns):
            return None
        if col >= len(self._data[row]):
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data[row][col]
            if value is None:
                return "NULL"
            return str(value)
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            value = self._data[row][col]
            if isinstance(value, (int, float)):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        if role == Qt.ItemDataRole.ForegroundRole:
            value = self._data[row][col]
            if value is None:
                from PyQt6.QtGui import QColor
                return QColor(VSCODE_COLORS['text_inactive'])
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section < len(self._columns):
                    return self._columns[section]
            else:
                return str(section + 1)
        return None
    
    @property
    def total_rows(self) -> int:
        return self._total_rows
    
    @property
    def columns(self) -> List[str]:
        return self._columns
    
    def get_raw_data(self) -> List[List[Any]]:
        """获取原始数据"""
        return self._data


class DataTableWidget(QWidget):
    """数据表格组件"""
    
    # 信号
    page_changed = pyqtSignal(int, int)  # offset, limit
    cell_double_clicked = pyqtSignal(int, int, str)  # row, col, value
    cell_selected = pyqtSignal(int, int, str, object)  # row, col, column_name, value
    column_sql_requested = pyqtSignal(str, str, str)  # table_name, column_name, sql_type
    column_selected_for_analysis = pyqtSignal(str)  # column_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 1
        self._page_size = 100
        self._total_rows = 0
        self._current_table = ""  # 当前表名
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 表格
        self.table_view = QTableView()
        self.model = DataTableModel()
        self.table_view.setModel(self.model)
        
        # 表格设置
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setSortingEnabled(False)
        self.table_view.setShowGrid(True)
        self.table_view.setWordWrap(False)
        
        # 表头设置
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(120)
        header.setMinimumSectionSize(60)
        # 启用列头右键菜单
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_context_menu)
        
        # 行号
        v_header = self.table_view.verticalHeader()
        v_header.setDefaultSectionSize(28)
        v_header.setMinimumSectionSize(28)
        
        # 设置表格视图可以扩展填充可用空间
        self.table_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.table_view)
        
        # 分页栏
        self.pagination_bar = self._create_pagination_bar()
        layout.addWidget(self.pagination_bar)
        
        # 连接信号
        self.table_view.doubleClicked.connect(self._on_cell_double_clicked)
        self.table_view.clicked.connect(self._on_cell_clicked)
        
        # 选择模型变化
        selection_model = self.table_view.selectionModel()
        selection_model.currentChanged.connect(self._on_selection_changed)
    
    def _create_pagination_bar(self) -> QWidget:
        """创建分页栏"""
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-top: 1px solid {VSCODE_COLORS['border']};
                padding: 4px;
            }}
        """)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        
        # 行数信息
        self.rows_label = QLabel("共 0 行")
        self.rows_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        layout.addWidget(self.rows_label)
        
        layout.addStretch()
        
        # 每页行数
        layout.addWidget(QLabel("每页:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500", "1000"])
        self.page_size_combo.setCurrentText("100")
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        layout.addWidget(self.page_size_combo)
        
        layout.addSpacing(20)
        
        # 分页导航
        self.first_btn = QPushButton()
        self.first_btn.setIcon(get_icon("first"))
        self.first_btn.setFixedWidth(32)
        self.first_btn.clicked.connect(self._go_first)
        self.first_btn.setToolTip("第一页")
        layout.addWidget(self.first_btn)
        
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(get_icon("prev"))
        self.prev_btn.setFixedWidth(32)
        self.prev_btn.clicked.connect(self._go_prev)
        self.prev_btn.setToolTip("上一页")
        layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("1 / 1")
        self.page_label.setMinimumWidth(60)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(get_icon("next"))
        self.next_btn.setFixedWidth(32)
        self.next_btn.clicked.connect(self._go_next)
        self.next_btn.setToolTip("下一页")
        layout.addWidget(self.next_btn)
        
        self.last_btn = QPushButton()
        self.last_btn.setIcon(get_icon("last"))
        self.last_btn.setFixedWidth(32)
        self.last_btn.clicked.connect(self._go_last)
        self.last_btn.setToolTip("最后一页")
        layout.addWidget(self.last_btn)
        
        # 跳转
        layout.addSpacing(10)
        layout.addWidget(QLabel("跳转:"))
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setFixedWidth(60)
        self.page_spin.valueChanged.connect(self._on_page_spin_changed)
        layout.addWidget(self.page_spin)
        
        return bar
    
    def set_data(self, columns: List[str], data: List[List[Any]], total_rows: int):
        """设置数据"""
        self._total_rows = total_rows
        self.model.set_data(columns, data, total_rows)
        self._update_pagination()
        
        # 自动调整列宽
        self._auto_resize_columns()
    
    def get_column_data(self, column_name: str) -> List[Any]:
        """获取指定列的所有数据"""
        try:
            columns = self.model.columns
            if column_name not in columns:
                return []
            col_idx = columns.index(column_name)
            raw_data = self.model.get_raw_data()
            return [row[col_idx] for row in raw_data if col_idx < len(row)]
        except:
            return []
    
    def get_current_data(self) -> tuple:
        """获取当前数据（列名，数据）"""
        return self.model.columns, self.model.get_raw_data()
    
    def _auto_resize_columns(self):
        """自动调整列宽"""
        header = self.table_view.horizontalHeader()
        for i in range(self.model.columnCount()):
            # 根据内容调整，但限制最大宽度
            self.table_view.resizeColumnToContents(i)
            current_width = header.sectionSize(i)
            if current_width > 300:
                header.resizeSection(i, 300)
            elif current_width < 80:
                header.resizeSection(i, 80)
    
    def _update_pagination(self):
        """更新分页信息"""
        total_pages = max(1, (self._total_rows + self._page_size - 1) // self._page_size)
        
        self.rows_label.setText(f"共 {self._total_rows:,} 行")
        self.page_label.setText(f"{self._current_page} / {total_pages}")
        self.page_spin.setMaximum(total_pages)
        self.page_spin.setValue(self._current_page)
        
        # 更新按钮状态
        self.first_btn.setEnabled(self._current_page > 1)
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < total_pages)
        self.last_btn.setEnabled(self._current_page < total_pages)
    
    def _emit_page_change(self):
        """发送分页变化信号"""
        offset = (self._current_page - 1) * self._page_size
        self.page_changed.emit(offset, self._page_size)
    
    def _go_first(self):
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._emit_page_change()
    
    def _go_prev(self):
        """上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._emit_page_change()
    
    def _go_next(self):
        """下一页"""
        total_pages = max(1, (self._total_rows + self._page_size - 1) // self._page_size)
        if self._current_page < total_pages:
            self._current_page += 1
            self._emit_page_change()
    
    def _go_last(self):
        """跳转到最后一页"""
        total_pages = max(1, (self._total_rows + self._page_size - 1) // self._page_size)
        if self._current_page != total_pages:
            self._current_page = total_pages
            self._emit_page_change()
    
    def _on_page_spin_changed(self, value: int):
        """页码输入变化"""
        if value != self._current_page:
            self._current_page = value
            self._emit_page_change()
    
    def _on_page_size_changed(self, text: str):
        """每页行数变化"""
        try:
            new_size = int(text)
            if new_size != self._page_size:
                self._page_size = new_size
                self._current_page = 1
                self._emit_page_change()
        except ValueError:
            pass
    
    def _on_cell_double_clicked(self, index: QModelIndex):
        """单元格双击"""
        if index.isValid():
            value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
            self.cell_double_clicked.emit(index.row(), index.column(), str(value))
    
    def _on_cell_clicked(self, index: QModelIndex):
        """单元格点击"""
        self._emit_cell_selected(index)
    
    def _on_selection_changed(self, current: QModelIndex, previous: QModelIndex):
        """选择变化"""
        self._emit_cell_selected(current)
    
    def _emit_cell_selected(self, index: QModelIndex):
        """发送单元格选中信号"""
        if index.isValid():
            row = index.row()
            col = index.column()
            value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
            column_name = self.model._columns[col] if col < len(self.model._columns) else ""
            self.cell_selected.emit(row, col, column_name, value)
    
    def _on_header_context_menu(self, pos: QPoint):
        """列头右键菜单"""
        header = self.table_view.horizontalHeader()
        column_index = header.logicalIndexAt(pos)
        
        if column_index < 0 or column_index >= len(self.model._columns):
            return
        
        column_name = self.model._columns[column_index]
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {VSCODE_COLORS['dropdown_bg']};
                border: 1px solid {VSCODE_COLORS['border']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                color: {VSCODE_COLORS['text']};
            }}
            QMenu::item:selected {{
                background-color: {VSCODE_COLORS['list_hover']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {VSCODE_COLORS['border']};
                margin: 4px 0;
            }}
        """)
        
        # 排序操作
        sort_asc = QAction(get_icon("sort_asc"), f"升序排列 ({column_name})", self)
        sort_asc.triggered.connect(lambda: self._emit_column_sql("order_asc", column_name))
        menu.addAction(sort_asc)
        
        sort_desc = QAction(get_icon("sort_desc"), f"降序排列 ({column_name})", self)
        sort_desc.triggered.connect(lambda: self._emit_column_sql("order_desc", column_name))
        menu.addAction(sort_desc)
        
        menu.addSeparator()
        
        # 查询操作
        select_distinct = QAction(get_icon("column"), f"查看唯一值 ({column_name})", self)
        select_distinct.triggered.connect(lambda: self._emit_column_sql("distinct", column_name))
        menu.addAction(select_distinct)
        
        count_action = QAction(get_icon("info"), f"统计计数 ({column_name})", self)
        count_action.triggered.connect(lambda: self._emit_column_sql("count", column_name))
        menu.addAction(count_action)
        
        group_by = QAction(get_icon("table"), f"分组统计 ({column_name})", self)
        group_by.triggered.connect(lambda: self._emit_column_sql("group_by", column_name))
        menu.addAction(group_by)
        
        menu.addSeparator()
        
        # 分析操作
        analyze_action = QAction(get_icon("chart"), f"分析此列", self)
        analyze_action.triggered.connect(lambda: self.column_selected_for_analysis.emit(column_name))
        menu.addAction(analyze_action)
        
        # 筛选操作
        filter_null = QAction(get_icon("filter"), f"筛选空值 ({column_name})", self)
        filter_null.triggered.connect(lambda: self._emit_column_sql("filter_null", column_name))
        menu.addAction(filter_null)
        
        filter_not_null = QAction(get_icon("filter"), f"筛选非空值 ({column_name})", self)
        filter_not_null.triggered.connect(lambda: self._emit_column_sql("filter_not_null", column_name))
        menu.addAction(filter_not_null)
        
        menu.exec(header.mapToGlobal(pos))
    
    def _emit_column_sql(self, sql_type: str, column_name: str):
        """发送列SQL请求信号"""
        self.column_sql_requested.emit(self._current_table, column_name, sql_type)
    
    def set_current_table(self, table_name: str):
        """设置当前表名"""
        self._current_table = table_name
    
