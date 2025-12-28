"""
数据分析面板组件 - 显示统计信息、缺失值、数值分布等
"""

from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QComboBox, QProgressBar, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class StatCard(QFrame):
    """统计卡片"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._setup_ui(title, value, subtitle)
    
    def _setup_ui(self, title: str, value: str, subtitle: str):
        """设置UI"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border: 1px solid {VSCODE_COLORS['border']};
                border-radius: 4px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {VSCODE_COLORS['text_secondary']};
            font-size: 11px;
            text-transform: uppercase;
        """)
        layout.addWidget(title_label)
        
        # 值
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            color: {VSCODE_COLORS['foreground']};
            font-size: 24px;
            font-weight: bold;
        """)
        layout.addWidget(self.value_label)
        
        # 副标题
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"""
                color: {VSCODE_COLORS['text_secondary']};
                font-size: 11px;
            """)
            layout.addWidget(subtitle_label)
    
    def set_value(self, value: str):
        """设置值"""
        self.value_label.setText(value)


class MissingValueBar(QWidget):
    """缺失值条形图"""
    
    def __init__(self, column: str, percentage: float, count: int, parent=None):
        super().__init__(parent)
        self._setup_ui(column, percentage, count)
    
    def _setup_ui(self, column: str, percentage: float, count: int):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        
        # 列名
        col_label = QLabel(column)
        col_label.setFixedWidth(150)
        col_label.setStyleSheet(f"color: {VSCODE_COLORS['foreground']};")
        layout.addWidget(col_label)
        
        # 进度条
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(percentage))
        progress.setTextVisible(False)
        progress.setFixedHeight(16)
        
        # 根据比例设置颜色
        if percentage > 50:
            color = VSCODE_COLORS['error']
        elif percentage > 20:
            color = VSCODE_COLORS['warning']
        else:
            color = VSCODE_COLORS['success']
        
        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {VSCODE_COLORS['input_bg']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(progress, 1)
        
        # 百分比
        pct_label = QLabel(f"{percentage:.1f}%")
        pct_label.setFixedWidth(60)
        pct_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        pct_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        layout.addWidget(pct_label)
        
        # 计数
        count_label = QLabel(f"({count:,})")
        count_label.setFixedWidth(80)
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        count_label.setStyleSheet(f"color: {VSCODE_COLORS['text_inactive']};")
        layout.addWidget(count_label)


class AnalysisPanelWidget(QWidget):
    """数据分析面板"""
    
    refresh_requested = pyqtSignal(str)  # table_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_table = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 头部
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab面板
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # 概览标签页
        self.overview_tab = self._create_overview_tab()
        self.tabs.addTab(self.overview_tab, get_icon("chart"), "概览")
        
        # 缺失值标签页
        self.missing_tab = self._create_missing_tab()
        self.tabs.addTab(self.missing_tab, get_icon("search"), "缺失值")
        
        # 数值统计标签页
        self.numeric_tab = self._create_numeric_tab()
        self.tabs.addTab(self.numeric_tab, get_icon("info"), "数值统计")
        
        # 列详情标签页
        self.columns_tab = self._create_columns_tab()
        self.tabs.addTab(self.columns_tab, get_icon("column"), "列详情")
        
        layout.addWidget(self.tabs)
    
    def _create_header(self) -> QWidget:
        """创建头部"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-bottom: 1px solid {VSCODE_COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        
        self.title_label = QLabel("数据分析")
        self.title_label.setStyleSheet(f"""
            color: {VSCODE_COLORS['foreground']};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(get_icon("refresh"))
        self.refresh_btn.setProperty("secondary", True)
        self.refresh_btn.clicked.connect(self._on_refresh)
        layout.addWidget(self.refresh_btn)
        
        return header
    
    def _create_overview_tab(self) -> QWidget:
        """创建概览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 统计卡片
        cards_layout = QHBoxLayout()
        
        self.row_count_card = StatCard("总行数", "0")
        cards_layout.addWidget(self.row_count_card)
        
        self.column_count_card = StatCard("总列数", "0")
        cards_layout.addWidget(self.column_count_card)
        
        self.missing_card = StatCard("缺失值", "0", "总缺失单元格")
        cards_layout.addWidget(self.missing_card)
        
        self.memory_card = StatCard("内存使用", "0 MB")
        cards_layout.addWidget(self.memory_card)
        
        layout.addLayout(cards_layout)
        
        # 数据类型分布
        dtype_group = QGroupBox("数据类型分布")
        dtype_layout = QVBoxLayout(dtype_group)
        self.dtype_table = QTableWidget()
        self.dtype_table.setColumnCount(2)
        self.dtype_table.setHorizontalHeaderLabels(["类型", "列数"])
        self.dtype_table.horizontalHeader().setStretchLastSection(True)
        self.dtype_table.setMaximumHeight(200)
        dtype_layout.addWidget(self.dtype_table)
        
        layout.addWidget(dtype_group)
        layout.addStretch()
        
        return widget
    
    def _create_missing_tab(self) -> QWidget:
        """创建缺失值标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        widget = QWidget()
        self.missing_layout = QVBoxLayout(widget)
        self.missing_layout.setContentsMargins(16, 16, 16, 16)
        
        # 摘要
        self.missing_summary = QLabel()
        self.missing_summary.setStyleSheet(f"""
            color: {VSCODE_COLORS['foreground']};
            font-size: 14px;
            padding: 10px;
            background-color: {VSCODE_COLORS['sidebar_bg']};
            border-radius: 4px;
        """)
        self.missing_layout.addWidget(self.missing_summary)
        
        # 缺失值列表容器
        self.missing_list_widget = QWidget()
        self.missing_list_layout = QVBoxLayout(self.missing_list_widget)
        self.missing_list_layout.setContentsMargins(0, 10, 0, 0)
        self.missing_layout.addWidget(self.missing_list_widget)
        
        self.missing_layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_numeric_tab(self) -> QWidget:
        """创建数值统计标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 数值统计表格
        self.numeric_table = QTableWidget()
        self.numeric_table.setColumnCount(9)
        self.numeric_table.setHorizontalHeaderLabels([
            "列名", "最小值", "最大值", "平均值", "中位数", 
            "标准差", "Q1", "Q3", "缺失率"
        ])
        
        header = self.numeric_table.horizontalHeader()
        for i in range(9):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.numeric_table)
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_columns_tab(self) -> QWidget:
        """创建列详情标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 列选择
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("选择列:"))
        self.column_combo = QComboBox()
        self.column_combo.setMinimumWidth(200)
        self.column_combo.currentTextChanged.connect(self._on_column_selected)
        select_layout.addWidget(self.column_combo)
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        # 列详情
        self.column_detail_widget = QWidget()
        self.column_detail_layout = QVBoxLayout(self.column_detail_widget)
        layout.addWidget(self.column_detail_widget)
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def set_table_name(self, table_name: str):
        """设置当前表名"""
        self._current_table = table_name
        self.title_label.setText(f"数据分析 - {table_name}")
    
    def update_stats(self, stats: Dict[str, Any]):
        """更新统计信息"""
        if not stats:
            return
        
        # 更新概览
        self.row_count_card.set_value(f"{stats.get('row_count', 0):,}")
        self.column_count_card.set_value(str(stats.get('column_count', 0)))
        
        # 计算总缺失值
        null_summary = stats.get('null_summary', {})
        total_missing = sum(null_summary.values())
        self.missing_card.set_value(f"{total_missing:,}")
        
        # 内存使用
        memory_bytes = stats.get('memory_usage', 0)
        if memory_bytes >= 1024 * 1024:
            memory_str = f"{memory_bytes / (1024*1024):.1f} MB"
        elif memory_bytes >= 1024:
            memory_str = f"{memory_bytes / 1024:.1f} KB"
        else:
            memory_str = f"{memory_bytes} B"
        self.memory_card.set_value(memory_str)
        
        # 数据类型分布
        dtype_summary = stats.get('dtype_summary', {})
        self.dtype_table.setRowCount(len(dtype_summary))
        for i, (dtype, count) in enumerate(dtype_summary.items()):
            self.dtype_table.setItem(i, 0, QTableWidgetItem(dtype))
            self.dtype_table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        # 更新列选择
        columns = stats.get('columns', [])
        self.column_combo.clear()
        for col in columns:
            self.column_combo.addItem(col.get('name', ''))
    
    def update_missing_report(self, report: Dict[str, Any]):
        """更新缺失值报告"""
        if not report:
            return
        
        # 更新摘要
        summary = report.get('summary', {})
        total_cells = summary.get('total_cells', 0)
        total_missing = summary.get('total_missing', 0)
        missing_pct = summary.get('missing_percentage', 0)
        
        self.missing_summary.setText(
            f"共 {total_cells:,} 个单元格，其中 {total_missing:,} 个缺失 ({missing_pct:.2f}%)"
        )
        
        # 清除旧的缺失值条
        while self.missing_list_layout.count():
            item = self.missing_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加新的缺失值条
        columns = report.get('columns', [])
        for col in sorted(columns, key=lambda x: x.get('null_percentage', 0), reverse=True):
            if col.get('null_count', 0) > 0:
                bar = MissingValueBar(
                    col.get('name', ''),
                    col.get('null_percentage', 0),
                    col.get('null_count', 0)
                )
                self.missing_list_layout.addWidget(bar)
    
    def update_numeric_summary(self, summary: Dict[str, Any]):
        """更新数值统计"""
        if not summary:
            return
        
        columns = summary.get('columns', [])
        self.numeric_table.setRowCount(len(columns))
        
        for i, col in enumerate(columns):
            self.numeric_table.setItem(i, 0, QTableWidgetItem(col.get('name', '')))
            self.numeric_table.setItem(i, 1, QTableWidgetItem(self._format_number(col.get('min'))))
            self.numeric_table.setItem(i, 2, QTableWidgetItem(self._format_number(col.get('max'))))
            self.numeric_table.setItem(i, 3, QTableWidgetItem(self._format_number(col.get('mean'))))
            self.numeric_table.setItem(i, 4, QTableWidgetItem(self._format_number(col.get('median'))))
            self.numeric_table.setItem(i, 5, QTableWidgetItem(self._format_number(col.get('std'))))
            self.numeric_table.setItem(i, 6, QTableWidgetItem(self._format_number(col.get('q1'))))
            self.numeric_table.setItem(i, 7, QTableWidgetItem(self._format_number(col.get('q3'))))
            self.numeric_table.setItem(i, 8, QTableWidgetItem(f"{col.get('null_percentage', 0):.1f}%"))
    
    def update_column_detail(self, detail: Dict[str, Any]):
        """更新列详情"""
        # 清除旧内容
        while self.column_detail_layout.count():
            item = self.column_detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not detail or 'error' in detail:
            return
        
        # 基本信息
        info_label = QLabel(f"""
        <b>列名:</b> {detail.get('column_name', '')}<br>
        <b>数据类型:</b> {detail.get('dtype', '')}
        """)
        info_label.setStyleSheet(f"color: {VSCODE_COLORS['foreground']};")
        self.column_detail_layout.addWidget(info_label)
        
        # 频率分布（分类列）或直方图（数值列）
        if 'frequency' in detail:
            freq_group = QGroupBox("频率分布 (Top 50)")
            freq_layout = QVBoxLayout(freq_group)
            
            freq_table = QTableWidget()
            freq_table.setColumnCount(2)
            freq_table.setHorizontalHeaderLabels(["值", "计数"])
            freq_table.horizontalHeader().setStretchLastSection(True)
            
            freq_data = detail['frequency']
            freq_table.setRowCount(len(freq_data))
            for i, item in enumerate(freq_data):
                freq_table.setItem(i, 0, QTableWidgetItem(str(item.get('value', ''))))
                freq_table.setItem(i, 1, QTableWidgetItem(str(item.get('count', 0))))
            
            freq_layout.addWidget(freq_table)
            self.column_detail_layout.addWidget(freq_group)
        
        elif 'histogram' in detail:
            hist_group = QGroupBox("数值分布")
            hist_layout = QVBoxLayout(hist_group)
            
            hist_data = detail['histogram']
            info = QLabel(f"""
            最小值: {hist_data.get('min', 0):.4f}<br>
            最大值: {hist_data.get('max', 0):.4f}<br>
            箱数: {hist_data.get('bins', 0)}
            """)
            hist_layout.addWidget(info)
            
            self.column_detail_layout.addWidget(hist_group)
    
    def _format_number(self, value) -> str:
        """格式化数字"""
        if value is None:
            return "-"
        try:
            if abs(value) >= 1000000:
                return f"{value:.2e}"
            elif abs(value) >= 1:
                return f"{value:,.2f}"
            else:
                return f"{value:.4f}"
        except:
            return str(value)
    
    def _on_refresh(self):
        """刷新"""
        if self._current_table:
            self.refresh_requested.emit(self._current_table)
    
    def _on_column_selected(self, column_name: str):
        """选择列"""
        # 这里会触发列详情的加载
        pass
