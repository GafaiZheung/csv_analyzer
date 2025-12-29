"""
单元格检查器组件 - 显示选中单元格的详细信息和列分析
"""

from typing import Any, Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTextEdit, QSplitter, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class CellValuePanel(QFrame):
    """单元格值显示面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-bottom: 1px solid {VSCODE_COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        title = QLabel("单元格值")
        title.setStyleSheet(f"""
            color: {VSCODE_COLORS['text_secondary']};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 位置标签
        self.position_label = QLabel("")
        self.position_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        header_layout.addWidget(self.position_label)
        
        layout.addLayout(header_layout)
        
        # 列名标签
        self.column_label = QLabel("未选择")
        self.column_label.setStyleSheet(f"""
            color: {VSCODE_COLORS['info']};
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(self.column_label)
        
        # 值显示区域
        self.value_display = QTextEdit()
        self.value_display.setReadOnly(True)
        self.value_display.setMaximumHeight(100)
        self.value_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {VSCODE_COLORS['input_bg']};
                color: {VSCODE_COLORS['foreground']};
                border: 1px solid {VSCODE_COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        self.value_display.setPlaceholderText("选择单元格查看值...")
        layout.addWidget(self.value_display)
        
        # 类型和长度信息
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(self.info_label)
    
    def set_cell_value(self, row: int, col: int, column_name: str, value: Any):
        """设置单元格值"""
        self.position_label.setText(f"行 {row + 1}, 列 {col + 1}")
        self.column_label.setText(column_name)
        
        value_str = str(value) if value is not None else "<NULL>"
        self.value_display.setText(value_str)
        
        # 显示类型和长度
        type_name = type(value).__name__ if value is not None else "NoneType"
        length = len(str(value)) if value is not None else 0
        self.info_label.setText(f"类型: {type_name} | 长度: {length}")
    
    def clear(self):
        """清空显示"""
        self.position_label.setText("")
        self.column_label.setText("未选择")
        self.value_display.clear()
        self.info_label.setText("")


class ColumnAnalysisPanel(QFrame):
    """列分析面板"""
    
    refresh_requested = pyqtSignal(str)  # column_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_column = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题栏
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-bottom: 1px solid {VSCODE_COLORS['border']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        title = QLabel("列分析")
        title.setStyleSheet(f"""
            color: {VSCODE_COLORS['text_secondary']};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.column_name_label = QLabel("")
        self.column_name_label.setStyleSheet(f"""
            color: {VSCODE_COLORS['info']};
            font-weight: bold;
        """)
        header_layout.addWidget(self.column_name_label)
        
        layout.addWidget(header)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(12)
        
        # 基础统计
        self._create_basic_stats()
        
        # 缺失值
        self._create_missing_stats()
        
        # 数值统计（仅对数值列显示）
        self._create_numeric_stats()
        
        # 唯一值
        self._create_unique_stats()
        
        self.content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_stat_row(self, label: str, value_label_name: str) -> QHBoxLayout:
        """创建统计行"""
        row = QHBoxLayout()
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        row.addWidget(label_widget)
        
        row.addStretch()
        
        value_widget = QLabel("-")
        value_widget.setStyleSheet(f"color: {VSCODE_COLORS['foreground']}; font-weight: bold;")
        setattr(self, value_label_name, value_widget)
        row.addWidget(value_widget)
        
        return row
    
    def _create_section_title(self, title: str) -> QLabel:
        """创建节标题"""
        label = QLabel(title)
        label.setStyleSheet(f"""
            color: {VSCODE_COLORS['foreground']};
            font-size: 12px;
            font-weight: bold;
            padding-top: 8px;
        """)
        return label
    
    def _create_basic_stats(self):
        """创建基础统计"""
        self.content_layout.addWidget(self._create_section_title("基础信息"))
        
        self.content_layout.addLayout(self._create_stat_row("数据类型:", "dtype_value"))
        self.content_layout.addLayout(self._create_stat_row("总行数:", "total_rows_value"))
        self.content_layout.addLayout(self._create_stat_row("唯一值数:", "unique_count_value"))
    
    def _create_missing_stats(self):
        """创建缺失值统计"""
        self.content_layout.addWidget(self._create_section_title("缺失值"))
        
        self.content_layout.addLayout(self._create_stat_row("缺失数量:", "missing_count_value"))
        self.content_layout.addLayout(self._create_stat_row("缺失比例:", "missing_pct_value"))
        
        # 缺失值进度条
        self.missing_bar = QProgressBar()
        self.missing_bar.setRange(0, 100)
        self.missing_bar.setValue(0)
        self.missing_bar.setTextVisible(False)
        self.missing_bar.setFixedHeight(8)
        self.missing_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {VSCODE_COLORS['input_bg']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {VSCODE_COLORS['warning']};
                border-radius: 4px;
            }}
        """)
        self.content_layout.addWidget(self.missing_bar)
    
    def _create_numeric_stats(self):
        """创建数值统计"""
        self.numeric_section_title = self._create_section_title("数值统计")
        self.content_layout.addWidget(self.numeric_section_title)
        
        self.numeric_stats_widget = QWidget()
        numeric_layout = QVBoxLayout(self.numeric_stats_widget)
        numeric_layout.setContentsMargins(0, 0, 0, 0)
        numeric_layout.setSpacing(4)
        
        numeric_layout.addLayout(self._create_stat_row("最小值:", "min_value"))
        numeric_layout.addLayout(self._create_stat_row("最大值:", "max_value"))
        numeric_layout.addLayout(self._create_stat_row("平均值:", "mean_value"))
        numeric_layout.addLayout(self._create_stat_row("中位数:", "median_value"))
        numeric_layout.addLayout(self._create_stat_row("标准差:", "std_value"))
        numeric_layout.addLayout(self._create_stat_row("Q1 (25%):", "q1_value"))
        numeric_layout.addLayout(self._create_stat_row("Q3 (75%):", "q3_value"))
        
        self.content_layout.addWidget(self.numeric_stats_widget)
    
    def _create_unique_stats(self):
        """创建唯一值统计"""
        self.content_layout.addWidget(self._create_section_title("常见值 (Top 10)"))
        
        self.top_values_table = QTableWidget()
        self.top_values_table.setColumnCount(2)
        self.top_values_table.setHorizontalHeaderLabels(["值", "计数"])
        self.top_values_table.horizontalHeader().setStretchLastSection(True)
        self.top_values_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_values_table.setMaximumHeight(200)
        self.top_values_table.setAlternatingRowColors(True)
        self.content_layout.addWidget(self.top_values_table)
    
    def set_column_analysis(self, column_name: str, analysis: Dict[str, Any]):
        """设置列分析结果"""
        self._current_column = column_name
        self.column_name_label.setText(column_name)
        
        # 基础信息
        self.dtype_value.setText(str(analysis.get('dtype', '-')))
        self.total_rows_value.setText(f"{analysis.get('total_rows', 0):,}")
        self.unique_count_value.setText(f"{analysis.get('unique_count', 0):,}")
        
        # 缺失值
        missing_count = analysis.get('missing_count', 0)
        missing_pct = analysis.get('missing_percentage', 0)
        self.missing_count_value.setText(f"{missing_count:,}")
        self.missing_pct_value.setText(f"{missing_pct:.2f}%")
        self.missing_bar.setValue(int(missing_pct))
        
        # 更新进度条颜色
        if missing_pct > 50:
            color = VSCODE_COLORS['error']
        elif missing_pct > 20:
            color = VSCODE_COLORS['warning']
        else:
            color = VSCODE_COLORS['success']
        self.missing_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {VSCODE_COLORS['input_bg']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        
        # 数值统计（如果是数值列）
        is_numeric = analysis.get('is_numeric', False)
        self.numeric_section_title.setVisible(is_numeric)
        self.numeric_stats_widget.setVisible(is_numeric)
        
        if is_numeric:
            numeric = analysis.get('numeric_stats', {})
            self.min_value.setText(self._format_number(numeric.get('min')))
            self.max_value.setText(self._format_number(numeric.get('max')))
            self.mean_value.setText(self._format_number(numeric.get('mean')))
            self.median_value.setText(self._format_number(numeric.get('median')))
            self.std_value.setText(self._format_number(numeric.get('std')))
            self.q1_value.setText(self._format_number(numeric.get('q1')))
            self.q3_value.setText(self._format_number(numeric.get('q3')))
        
        # 常见值
        top_values = analysis.get('top_values', [])
        self.top_values_table.setRowCount(len(top_values))
        for i, (value, count) in enumerate(top_values):
            self.top_values_table.setItem(i, 0, QTableWidgetItem(str(value)))
            self.top_values_table.setItem(i, 1, QTableWidgetItem(f"{count:,}"))
    
    def _format_number(self, value) -> str:
        """格式化数字"""
        if value is None:
            return "-"
        try:
            if isinstance(value, float):
                if abs(value) >= 1000:
                    return f"{value:,.2f}"
                else:
                    return f"{value:.4f}"
            return str(value)
        except:
            return str(value)
    
    def clear(self):
        """清空分析"""
        self.column_name_label.setText("")
        self.dtype_value.setText("-")
        self.total_rows_value.setText("-")
        self.unique_count_value.setText("-")
        self.missing_count_value.setText("-")
        self.missing_pct_value.setText("-")
        self.missing_bar.setValue(0)
        self.top_values_table.setRowCount(0)


class CellInspectorWidget(QWidget):
    """单元格检查器组件 - 包含单元格值和列分析"""
    
    refresh_requested = pyqtSignal(str)  # table_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_table = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 分割器：上部单元格值，下部列分析
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上部：单元格值面板
        self.cell_panel = CellValuePanel()
        splitter.addWidget(self.cell_panel)
        
        # 下部：列分析面板
        self.column_panel = ColumnAnalysisPanel()
        splitter.addWidget(self.column_panel)
        
        splitter.setSizes([150, 400])
        
        layout.addWidget(splitter)
    
    def set_cell_value(self, row: int, col: int, column_name: str, value: Any):
        """设置单元格值"""
        self.cell_panel.set_cell_value(row, col, column_name, value)
    
    def set_column_analysis(self, column_name: str, analysis: Dict[str, Any]):
        """设置列分析"""
        self.column_panel.set_column_analysis(column_name, analysis)
    
    def set_table_name(self, table_name: str):
        """设置当前表名"""
        self._current_table = table_name
    
    def clear(self):
        """清空所有"""
        self.cell_panel.clear()
        self.column_panel.clear()
