"""
SQL编辑器组件 - 带语法高亮的SQL编辑器
"""

from typing import Dict, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QSplitter, QFrame, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QStringListModel
from PyQt6.QtGui import (
    QFont, QTextCharFormat, QColor, QSyntaxHighlighter,
    QTextDocument, QKeySequence, QShortcut, QTextCursor
)

from csv_analyzer.frontend.styles.theme import VSCODE_COLORS
from csv_analyzer.frontend.styles.icons import get_icon


class SQLHighlighter(QSyntaxHighlighter):
    """SQL语法高亮器"""
    
    def __init__(self, parent: QTextDocument = None):
        super().__init__(parent)
        self._init_rules()
    
    def _init_rules(self):
        """初始化高亮规则"""
        self.rules = []
        
        # SQL关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(VSCODE_COLORS['keyword']))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE',
            'ORDER', 'BY', 'ASC', 'DESC', 'GROUP', 'HAVING', 'JOIN',
            'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS', 'ON',
            'AS', 'DISTINCT', 'ALL', 'TOP', 'LIMIT', 'OFFSET',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE',
            'CREATE', 'TABLE', 'VIEW', 'INDEX', 'DROP', 'ALTER',
            'NULL', 'IS', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN', 'THEN',
            'ELSE', 'END', 'UNION', 'EXCEPT', 'INTERSECT',
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CAST', 'COALESCE',
            'TRUE', 'FALSE', 'WITH', 'RECURSIVE', 'OVER', 'PARTITION',
            'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LAG', 'LEAD'
        ]
        
        for keyword in keywords:
            pattern = QRegularExpression(r'\b' + keyword + r'\b', 
                                          QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.rules.append((pattern, keyword_format))
        
        # 函数
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(VSCODE_COLORS['function']))
        
        functions = [
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'FLOOR', 'CEIL',
            'ABS', 'SQRT', 'POWER', 'LENGTH', 'LOWER', 'UPPER', 'TRIM',
            'SUBSTR', 'SUBSTRING', 'REPLACE', 'CONCAT', 'COALESCE',
            'NULLIF', 'IFNULL', 'DATE', 'TIME', 'DATETIME', 'STRFTIME',
            'TYPEOF', 'CAST', 'PRINTF', 'INSTR', 'HEX', 'QUOTE',
            'RANDOM', 'TOTAL', 'GROUP_CONCAT', 'MEDIAN', 'STDDEV',
            'QUANTILE', 'QUANTILE_CONT', 'FIRST', 'LAST', 'LIST'
        ]
        
        for func in functions:
            pattern = QRegularExpression(r'\b' + func + r'\s*\(', 
                                          QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.rules.append((pattern, function_format))
        
        # 字符串（单引号）
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(VSCODE_COLORS['string']))
        self.rules.append((QRegularExpression(r"'[^']*'"), string_format))
        
        # 字符串（双引号 - 标识符）
        identifier_format = QTextCharFormat()
        identifier_format.setForeground(QColor(VSCODE_COLORS['variable']))
        self.rules.append((QRegularExpression(r'"[^"]*"'), identifier_format))
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(VSCODE_COLORS['number']))
        self.rules.append((QRegularExpression(r'\b\d+\.?\d*\b'), number_format))
        
        # 运算符
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor(VSCODE_COLORS['foreground']))
        self.rules.append((QRegularExpression(r'[=<>!]+|[+\-*/%]'), operator_format))
        
        # 注释（单行）
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(VSCODE_COLORS['comment']))
        comment_format.setFontItalic(True)
        self.rules.append((QRegularExpression(r'--[^\n]*'), comment_format))
        
        # 注释（多行）
        self.multi_comment_format = comment_format
    
    def highlightBlock(self, text: str):
        """高亮文本块"""
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        
        # 处理多行注释
        self._highlight_multiline_comments(text)
    
    def _highlight_multiline_comments(self, text: str):
        """处理多行注释"""
        start_expr = QRegularExpression(r'/\*')
        end_expr = QRegularExpression(r'\*/')
        
        self.setCurrentBlockState(0)
        
        start_index = 0
        if self.previousBlockState() != 1:
            match = start_expr.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1
        
        while start_index >= 0:
            end_match = end_expr.match(text, start_index)
            
            if end_match.hasMatch():
                comment_length = end_match.capturedEnd() - start_index
            else:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            
            self.setFormat(start_index, comment_length, self.multi_comment_format)
            
            match = start_expr.match(text, start_index + comment_length)
            start_index = match.capturedStart() if match.hasMatch() else -1


class SQLEditor(QPlainTextEdit):
    """SQL编辑器"""
    
    execute_requested = pyqtSignal(str)  # 执行SQL请求
    
    # SQL关键字和函数用于自动补全
    SQL_KEYWORDS = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "LIKE", "BETWEEN",
        "IS", "NULL", "AS", "DISTINCT", "ALL", "TOP", "LIMIT", "OFFSET",
        "ORDER", "BY", "ASC", "DESC", "GROUP", "HAVING",
        "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "ON",
        "UNION", "EXCEPT", "INTERSECT", "CASE", "WHEN", "THEN", "ELSE", "END",
        "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
        "CREATE", "TABLE", "VIEW", "INDEX", "DROP", "ALTER",
        "EXISTS", "TRUE", "FALSE", "WITH", "RECURSIVE",
        "OVER", "PARTITION", "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD",
    ]
    
    SQL_FUNCTIONS = [
        "COUNT()", "SUM()", "AVG()", "MIN()", "MAX()", "TOTAL()",
        "ABS()", "ROUND()", "FLOOR()", "CEIL()", "SQRT()", "POWER()",
        "LENGTH()", "LOWER()", "UPPER()", "TRIM()", "SUBSTR()", "REPLACE()", "CONCAT()",
        "CAST()", "COALESCE()", "NULLIF()", "IFNULL()",
        "DATE()", "TIME()", "DATETIME()", "STRFTIME()",
        "MEDIAN()", "STDDEV()", "QUANTILE()", "GROUP_CONCAT()",
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tables: Dict[str, List[str]] = {}
        self._completer: QCompleter = None
        self._setup_editor()
        self._setup_shortcuts()
        self._setup_completer()
    
    def _setup_editor(self):
        """设置编辑器"""
        # 字体 - 使用跨平台兼容的等宽字体
        import platform
        if platform.system() == 'Windows':
            font = QFont("Consolas", 11)
        elif platform.system() == 'Darwin':
            font = QFont("Menlo", 13)
        else:
            font = QFont("Monospace", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        # 确保字体大小有效
        if font.pointSize() <= 0:
            font.setPointSize(11)
        self.setFont(font)
        
        # Tab设置
        self.setTabStopDistance(40)
        
        # 行号区域宽度
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # 语法高亮
        self.highlighter = SQLHighlighter(self.document())
        
        # 占位符
        self.setPlaceholderText("输入SQL查询语句...\n\n示例:\nSELECT * FROM table_name\nWHERE column > 100\nLIMIT 1000\n\n提示: 输入时会自动补全")
        
        # 样式
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {VSCODE_COLORS['editor_bg']};
                color: {VSCODE_COLORS['foreground']};
                border: none;
                padding: 10px;
                selection-background-color: {VSCODE_COLORS['selection']};
            }}
        """)
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+Enter 执行
        execute_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        execute_shortcut.activated.connect(self._on_execute)
        
        # F5 执行
        execute_f5 = QShortcut(QKeySequence("F5"), self)
        execute_f5.activated.connect(self._on_execute)
        
        # Ctrl+Space 触发补全
        complete_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        complete_shortcut.activated.connect(self._trigger_completion)
    
    def _setup_completer(self):
        """设置自动补全"""
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.activated.connect(self._insert_completion)
        
        # 设置补全弹出样式
        popup = self._completer.popup()
        popup.setStyleSheet(f"""
            QListView {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                color: {VSCODE_COLORS['foreground']};
                border: 1px solid {VSCODE_COLORS['border']};
                selection-background-color: {VSCODE_COLORS['selection']};
            }}
        """)
        
        self._update_completer_model()
    
    def _update_completer_model(self):
        """更新补全模型"""
        completions = []
        
        # 添加关键字（大小写）
        for kw in self.SQL_KEYWORDS:
            completions.append(kw)
            completions.append(kw.lower())
        
        # 添加函数
        completions.extend(self.SQL_FUNCTIONS)
        completions.extend([f.lower() for f in self.SQL_FUNCTIONS])
        
        # 添加表和列
        for table_name, columns in self._tables.items():
            completions.append(table_name)
            completions.append(f'"{table_name}"')
            for col in columns:
                completions.append(col)
                completions.append(f'"{col}"')
                completions.append(f"{table_name}.{col}")
        
        model = QStringListModel(sorted(set(completions)), self._completer)
        self._completer.setModel(model)
    
    def set_tables(self, tables: Dict[str, List[str]]):
        """设置表信息用于自动补全"""
        self._tables = tables
        self._update_completer_model()
    
    def _get_word_under_cursor(self) -> str:
        """获取光标下的词"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()
    
    def _trigger_completion(self):
        """触发自动补全"""
        self._show_completer()
    
    def _show_completer(self):
        """显示补全器"""
        prefix = self._get_word_under_cursor()
        
        if not prefix:
            self._completer.popup().hide()
            return
        
        self._completer.setCompletionPrefix(prefix)
        
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        
        # 计算弹出位置
        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(
            min(300, popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width())
        )
        
        self._completer.complete(cursor_rect)
    
    def _insert_completion(self, completion: str):
        """插入补全文本"""
        cursor = self.textCursor()
        
        # 选择当前词
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.removeSelectedText()
        
        # 插入补全
        cursor.insertText(completion)
        self.setTextCursor(cursor)
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        # 如果补全器弹出，处理特殊按键
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, 
                               Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                event.ignore()
                return
        
        super().keyPressEvent(event)
        
        # 自动触发补全
        if event.text() and event.text().isalnum() or event.text() == '_':
            prefix = self._get_word_under_cursor()
            if len(prefix) >= 2:  # 至少输入2个字符才触发
                self._show_completer()
            else:
                self._completer.popup().hide()
        elif event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Backspace):
            self._completer.popup().hide()
    
    def _on_execute(self):
        """执行SQL"""
        sql = self.get_selected_or_all()
        if sql.strip():
            self.execute_requested.emit(sql)
    
    def get_selected_or_all(self) -> str:
        """获取选中的SQL或全部SQL"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return cursor.selectedText().replace('\u2029', '\n')
        return self.toPlainText()


class SQLEditorWidget(QWidget):
    """SQL编辑器组件（带工具栏）"""
    
    execute_requested = pyqtSignal(str)
    save_view_requested = pyqtSignal(str)  # SQL
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tables: Dict[str, List[str]] = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 编辑器 (先创建，因为工具栏需要引用它)
        self.editor = SQLEditor()
        self.editor.execute_requested.connect(self.execute_requested.emit)
        
        # 工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # 添加编辑器到布局
        layout.addWidget(self.editor)
    
    def _create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QFrame()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {VSCODE_COLORS['sidebar_bg']};
                border-bottom: 1px solid {VSCODE_COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # 执行按钮
        self.run_btn = QPushButton(" 执行")
        self.run_btn.setIcon(get_icon("play", VSCODE_COLORS['success']))
        self.run_btn.setToolTip("执行SQL (Ctrl+Enter 或 F5)")
        self.run_btn.clicked.connect(self._on_execute)
        layout.addWidget(self.run_btn)
        
        # 保存为视图
        self.save_view_btn = QPushButton(" 保存为视图")
        self.save_view_btn.setIcon(get_icon("save"))
        self.save_view_btn.setToolTip("将当前查询保存为视图")
        self.save_view_btn.setProperty("secondary", True)
        self.save_view_btn.clicked.connect(self._on_save_view)
        layout.addWidget(self.save_view_btn)
        
        # 格式化按钮
        self.format_btn = QPushButton(" 格式化")
        self.format_btn.setIcon(get_icon("format"))
        self.format_btn.setProperty("secondary", True)
        self.format_btn.clicked.connect(self._on_format)
        layout.addWidget(self.format_btn)
        
        # 清空按钮
        self.clear_btn = QPushButton(" 清空")
        self.clear_btn.setIcon(get_icon("clear"))
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.clicked.connect(self.editor.clear)
        layout.addWidget(self.clear_btn)
        
        layout.addStretch()
        
        # 提示
        hint_label = QLabel("Ctrl+Enter 执行 | Ctrl+Space 补全")
        hint_label.setStyleSheet(f"color: {VSCODE_COLORS['text_secondary']};")
        layout.addWidget(hint_label)
        
        return toolbar
    
    def _on_execute(self):
        """执行SQL"""
        sql = self.editor.get_selected_or_all()
        if sql.strip():
            self.execute_requested.emit(sql)
    
    def _on_save_view(self):
        """保存为视图"""
        sql = self.editor.get_selected_or_all()
        if sql.strip():
            self.save_view_requested.emit(sql)
    
    def _on_format(self):
        """格式化SQL"""
        sql = self.editor.toPlainText()
        formatted = self._format_sql(sql)
        self.editor.setPlainText(formatted)
    
    def _format_sql(self, sql: str) -> str:
        """简单的SQL格式化"""
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ORDER BY', 
            'GROUP BY', 'HAVING', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
            'INNER JOIN', 'OUTER JOIN', 'ON', 'LIMIT', 'OFFSET',
            'UNION', 'EXCEPT', 'INTERSECT', 'INSERT INTO', 'VALUES',
            'UPDATE', 'SET', 'DELETE FROM', 'CREATE TABLE', 'CREATE VIEW'
        ]
        
        # 规范化空白
        sql = ' '.join(sql.split())
        
        # 在关键字前添加换行
        for kw in sorted(keywords, key=len, reverse=True):
            sql = sql.replace(f' {kw} ', f'\n{kw} ')
            sql = sql.replace(f' {kw.lower()} ', f'\n{kw} ')
        
        # 清理多余空行
        lines = [line.strip() for line in sql.split('\n') if line.strip()]
        
        return '\n'.join(lines)
    
    def set_sql(self, sql: str):
        """设置SQL内容"""
        self.editor.setPlainText(sql)
    
    def get_sql(self) -> str:
        """获取SQL内容"""
        return self.editor.toPlainText()
    
    def set_tables(self, tables: Dict[str, List[str]]):
        """设置表信息用于自动补全"""
        self._tables = tables
        self.editor.set_tables(tables)
