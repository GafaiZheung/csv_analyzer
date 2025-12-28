"""
SQL自动补全器 - 提供SQL关键字和表/列名补全
"""

from typing import List, Optional, Dict
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit
from PyQt6.QtCore import Qt, QStringListModel, QRect
from PyQt6.QtGui import QTextCursor


class SQLCompleter(QCompleter):
    """SQL自动补全器"""
    
    # SQL关键字
    SQL_KEYWORDS = [
        # 基本查询
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "LIKE", "BETWEEN",
        "IS", "NULL", "AS", "DISTINCT", "ALL", "TOP", "LIMIT", "OFFSET",
        # 排序和分组
        "ORDER", "BY", "ASC", "DESC", "GROUP", "HAVING",
        # 连接
        "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "ON",
        # 集合操作
        "UNION", "EXCEPT", "INTERSECT",
        # 条件
        "CASE", "WHEN", "THEN", "ELSE", "END",
        # 数据操作
        "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
        # DDL
        "CREATE", "TABLE", "VIEW", "INDEX", "DROP", "ALTER",
        # 其他
        "EXISTS", "TRUE", "FALSE", "WITH", "RECURSIVE",
        # 窗口函数
        "OVER", "PARTITION", "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD",
    ]
    
    # SQL函数
    SQL_FUNCTIONS = [
        # 聚合函数
        "COUNT(", "SUM(", "AVG(", "MIN(", "MAX(", "TOTAL(",
        "GROUP_CONCAT(", "MEDIAN(", "STDDEV(", "VARIANCE(",
        # 数学函数
        "ABS(", "ROUND(", "FLOOR(", "CEIL(", "CEILING(", "SQRT(", "POWER(", "MOD(",
        "RANDOM(", "SIGN(", "LOG(", "LN(", "EXP(",
        # 字符串函数
        "LENGTH(", "LOWER(", "UPPER(", "TRIM(", "LTRIM(", "RTRIM(",
        "SUBSTR(", "SUBSTRING(", "REPLACE(", "CONCAT(", "INSTR(",
        "LEFT(", "RIGHT(", "REPEAT(", "REVERSE(",
        # 转换函数
        "CAST(", "COALESCE(", "NULLIF(", "IFNULL(", "TYPEOF(",
        # 日期函数
        "DATE(", "TIME(", "DATETIME(", "STRFTIME(",
        "YEAR(", "MONTH(", "DAY(", "HOUR(", "MINUTE(", "SECOND(",
        # 条件函数
        "IIF(", "CASE",
        # 分析函数
        "FIRST(", "LAST(", "LIST(",
        "QUANTILE(", "QUANTILE_CONT(", "PERCENTILE(",
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._tables: Dict[str, List[str]] = {}  # table_name -> [columns]
        self._views: List[str] = []
        
        # 设置补全模式
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        
        # 初始化模型
        self._update_model()
    
    def set_tables(self, tables: Dict[str, List[str]]):
        """
        设置表和列信息
        
        Args:
            tables: {table_name: [column_names]}
        """
        self._tables = tables
        self._update_model()
    
    def set_views(self, views: List[str]):
        """设置视图列表"""
        self._views = views
        self._update_model()
    
    def _update_model(self):
        """更新补全模型"""
        completions = []
        
        # 添加关键字
        completions.extend(self.SQL_KEYWORDS)
        completions.extend([kw.lower() for kw in self.SQL_KEYWORDS])
        
        # 添加函数
        completions.extend(self.SQL_FUNCTIONS)
        completions.extend([f.lower() for f in self.SQL_FUNCTIONS])
        
        # 添加表名
        for table_name in self._tables.keys():
            completions.append(table_name)
            completions.append(f'"{table_name}"')
        
        # 添加列名（带表名前缀和不带）
        for table_name, columns in self._tables.items():
            for col in columns:
                completions.append(col)
                completions.append(f'"{col}"')
                completions.append(f"{table_name}.{col}")
                completions.append(f'"{table_name}"."{col}"')
        
        # 添加视图
        completions.extend(self._views)
        
        # 去重并排序
        completions = sorted(set(completions))
        
        model = QStringListModel(completions, self)
        self.setModel(model)
    
    def get_completions_for_context(self, text: str, cursor_pos: int) -> List[str]:
        """
        根据上下文获取补全建议
        
        Args:
            text: 当前文本
            cursor_pos: 光标位置
            
        Returns:
            补全建议列表
        """
        # 获取当前词
        word_start = cursor_pos
        while word_start > 0 and text[word_start - 1] not in ' \t\n,()[]':
            word_start -= 1
        
        current_word = text[word_start:cursor_pos].upper()
        
        # 分析上下文
        text_before = text[:cursor_pos].upper()
        
        completions = []
        
        # 在FROM后面，建议表名
        if 'FROM' in text_before and not any(kw in text_before.split('FROM')[-1] for kw in ['WHERE', 'GROUP', 'ORDER', 'JOIN']):
            completions.extend(self._tables.keys())
            completions.extend(self._views)
        
        # 在SELECT后面，建议列名和函数
        elif 'SELECT' in text_before and 'FROM' not in text_before:
            completions.extend(self.SQL_FUNCTIONS)
            for columns in self._tables.values():
                completions.extend(columns)
        
        # 在WHERE/AND/OR后面，建议列名
        elif any(kw in text_before.split()[-2:] if len(text_before.split()) >= 2 else False 
                 for kw in ['WHERE', 'AND', 'OR']):
            for columns in self._tables.values():
                completions.extend(columns)
        
        # 在ORDER BY后面，建议列名
        elif 'ORDER BY' in text_before:
            for columns in self._tables.values():
                completions.extend(columns)
            completions.extend(['ASC', 'DESC'])
        
        # 在GROUP BY后面，建议列名
        elif 'GROUP BY' in text_before:
            for columns in self._tables.values():
                completions.extend(columns)
        
        # 默认返回所有
        else:
            completions.extend(self.SQL_KEYWORDS)
            completions.extend(self.SQL_FUNCTIONS)
            completions.extend(self._tables.keys())
        
        # 过滤匹配当前词的
        if current_word:
            completions = [c for c in completions if current_word in c.upper()]
        
        return sorted(set(completions))


class CompletableTextEdit:
    """为文本编辑器添加自动补全功能的Mixin"""
    
    def setup_completer(self, completer: SQLCompleter):
        """设置补全器"""
        self._completer = completer
        self._completer.setWidget(self)
        self._completer.activated.connect(self._insert_completion)
    
    def _insert_completion(self, completion: str):
        """插入补全文本"""
        cursor = self.textCursor()
        
        # 删除已输入的部分
        cursor.movePosition(QTextCursor.MoveOperation.StartOfWord, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        # 插入补全
        cursor.insertText(completion)
        
        self.setTextCursor(cursor)
    
    def _get_word_under_cursor(self) -> str:
        """获取光标下的词"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfWord, QTextCursor.MoveMode.KeepAnchor)
        return cursor.selectedText()
    
    def _show_completer(self):
        """显示补全器"""
        if not hasattr(self, '_completer'):
            return
        
        prefix = self._get_word_under_cursor()
        
        if len(prefix) < 1:
            self._completer.popup().hide()
            return
        
        self._completer.setCompletionPrefix(prefix)
        
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        
        # 计算弹出位置
        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(
            popup.sizeHintForColumn(0)
            + popup.verticalScrollBar().sizeHint().width()
        )
        
        self._completer.complete(cursor_rect)
