"""
数据处理引擎 - 负责加载和管理大体积CSV文件
使用DuckDB作为内存数据库，支持高效的SQL查询
"""

import os
import json
import threading
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import duckdb
import polars as pl
import chardet


@dataclass
class TableInfo:
    """表信息"""
    name: str
    file_path: str
    row_count: int
    columns: List[Dict[str, str]]  # [{"name": str, "dtype": str}]
    file_size: int
    encoding: str


@dataclass
class QueryResult:
    """查询结果"""
    columns: List[str]
    data: List[List[Any]]
    row_count: int
    total_rows: int
    execution_time: float
    error: Optional[str] = None


class DataEngine:
    """
    数据处理引擎
    在独立线程中运行，处理所有数据操作
    """
    
    def __init__(self):
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._tables: Dict[str, TableInfo] = {}
        self._views: Dict[str, str] = {}  # view_name -> sql
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """初始化DuckDB内存数据库"""
        self._conn = duckdb.connect(":memory:")
        # 配置DuckDB以优化大文件处理
        self._conn.execute("SET threads TO 4")
        self._conn.execute("SET memory_limit = '4GB'")
    
    def _detect_encoding(self, file_path: str) -> str:
        """检测文件编码"""
        with open(file_path, 'rb') as f:
            raw_data = f.read(100000)  # 读取前100KB检测编码
            result = chardet.detect(raw_data)
            return result.get('encoding', 'utf-8') or 'utf-8'
    
    def _sanitize_table_name(self, name: str) -> str:
        """清理表名，确保是有效的SQL标识符"""
        # 移除文件扩展名
        name = Path(name).stem
        # 替换非法字符
        name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        # 确保不以数字开头
        if name and name[0].isdigit():
            name = 't_' + name
        return name or 'table_1'
    
    def load_csv(self, file_path: str, table_name: Optional[str] = None) -> TableInfo:
        """
        加载CSV文件到数据库
        
        Args:
            file_path: CSV文件路径
            table_name: 可选的表名，默认使用文件名
            
        Returns:
            TableInfo: 加载的表信息
        """
        with self._lock:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 检测编码
            encoding = self._detect_encoding(file_path)
            
            # 生成表名
            if not table_name:
                table_name = self._sanitize_table_name(os.path.basename(file_path))
            
            # 确保表名唯一
            original_name = table_name
            counter = 1
            while table_name in self._tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # 使用DuckDB直接读取CSV（支持大文件流式读取）
            try:
                self._conn.execute(f"""
                    CREATE TABLE "{table_name}" AS 
                    SELECT * FROM read_csv_auto(
                        '{file_path}',
                        header=true,
                        ignore_errors=true,
                        sample_size=10000
                    )
                """)
            except Exception as e:
                # 尝试使用不同的编码
                self._conn.execute(f"""
                    CREATE TABLE "{table_name}" AS 
                    SELECT * FROM read_csv_auto(
                        '{file_path}',
                        header=true,
                        ignore_errors=true,
                        encoding='{encoding}'
                    )
                """)
            
            # 获取表信息
            row_count = self._conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            
            columns_info = self._conn.execute(
                f"DESCRIBE \"{table_name}\""
            ).fetchall()
            
            columns = [
                {"name": col[0], "dtype": col[1]} 
                for col in columns_info
            ]
            
            file_size = os.path.getsize(file_path)
            
            table_info = TableInfo(
                name=table_name,
                file_path=file_path,
                row_count=row_count,
                columns=columns,
                file_size=file_size,
                encoding=encoding
            )
            
            self._tables[table_name] = table_info
            return table_info
    
    def get_tables(self) -> List[TableInfo]:
        """获取所有已加载的表"""
        with self._lock:
            return list(self._tables.values())
    
    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """获取指定表的信息"""
        with self._lock:
            return self._tables.get(table_name)
    
    def execute_query(
        self, 
        sql: str, 
        limit: int = 1000,
        offset: int = 0
    ) -> QueryResult:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            limit: 返回的最大行数
            offset: 偏移量（用于分页）
            
        Returns:
            QueryResult: 查询结果
        """
        import time
        
        with self._lock:
            start_time = time.time()
            
            try:
                # 检查是否是SELECT语句
                sql_upper = sql.strip().upper()
                
                if sql_upper.startswith('SELECT'):
                    # 首先获取总行数
                    count_sql = f"SELECT COUNT(*) FROM ({sql}) AS _count_query"
                    total_rows = self._conn.execute(count_sql).fetchone()[0]
                    
                    # 添加分页
                    paginated_sql = f"{sql} LIMIT {limit} OFFSET {offset}"
                    result = self._conn.execute(paginated_sql)
                    
                    columns = [desc[0] for desc in result.description]
                    data = [list(row) for row in result.fetchall()]
                    
                    execution_time = time.time() - start_time
                    
                    return QueryResult(
                        columns=columns,
                        data=data,
                        row_count=len(data),
                        total_rows=total_rows,
                        execution_time=execution_time
                    )
                else:
                    # 非SELECT语句直接执行
                    self._conn.execute(sql)
                    execution_time = time.time() - start_time
                    
                    return QueryResult(
                        columns=[],
                        data=[],
                        row_count=0,
                        total_rows=0,
                        execution_time=execution_time
                    )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return QueryResult(
                    columns=[],
                    data=[],
                    row_count=0,
                    total_rows=0,
                    execution_time=execution_time,
                    error=str(e)
                )
    
    def get_table_data(
        self, 
        table_name: str, 
        limit: int = 1000,
        offset: int = 0
    ) -> QueryResult:
        """获取表数据（带分页）"""
        sql = f'SELECT * FROM "{table_name}"'
        return self.execute_query(sql, limit, offset)
    
    def save_view(self, view_name: str, sql: str) -> bool:
        """
        保存查询为视图
        
        Args:
            view_name: 视图名称
            sql: SQL查询语句
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                # 在DuckDB中创建视图
                self._conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS {sql}')
                self._views[view_name] = sql
                return True
            except Exception as e:
                print(f"创建视图失败: {e}")
                return False
    
    def get_views(self) -> Dict[str, str]:
        """获取所有视图"""
        with self._lock:
            return self._views.copy()
    
    def delete_view(self, view_name: str) -> bool:
        """删除视图"""
        with self._lock:
            try:
                self._conn.execute(f'DROP VIEW IF EXISTS "{view_name}"')
                if view_name in self._views:
                    del self._views[view_name]
                return True
            except Exception as e:
                print(f"删除视图失败: {e}")
                return False
    
    def drop_table(self, table_name: str) -> bool:
        """删除表"""
        with self._lock:
            try:
                self._conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                if table_name in self._tables:
                    del self._tables[table_name]
                return True
            except Exception as e:
                print(f"删除表失败: {e}")
                return False
    
    def export_to_csv(
        self, 
        sql_or_table: str, 
        output_path: str,
        is_sql: bool = False
    ) -> bool:
        """
        导出数据到CSV
        
        Args:
            sql_or_table: SQL查询或表名
            output_path: 输出文件路径
            is_sql: 是否为SQL查询
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            try:
                if is_sql:
                    query = sql_or_table
                else:
                    query = f'SELECT * FROM "{sql_or_table}"'
                
                self._conn.execute(f"""
                    COPY ({query}) TO '{output_path}' (HEADER, DELIMITER ',')
                """)
                return True
            except Exception as e:
                print(f"导出失败: {e}")
                return False
    
    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
