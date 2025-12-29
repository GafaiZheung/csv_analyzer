"""
数据分析模块 - 提供数据统计和分析功能
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import threading

import numpy as np


@dataclass
class ColumnStats:
    """列统计信息"""
    name: str
    dtype: str
    total_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    
    # 数值类型专用
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_value: Optional[float] = None
    q1_value: Optional[float] = None
    q3_value: Optional[float] = None
    
    # 字符串类型专用
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    
    # 频率分布（Top 10）
    top_values: Optional[List[Dict[str, Any]]] = None


@dataclass
class TableStats:
    """表统计信息"""
    table_name: str
    row_count: int
    column_count: int
    memory_usage: int  # bytes
    columns: List[ColumnStats]
    null_summary: Dict[str, int]  # column -> null count
    dtype_summary: Dict[str, int]  # dtype -> count


class DataAnalyzer:
    """
    数据分析器
    提供各种数据统计和分析功能
    """
    
    def __init__(self, engine):
        """
        初始化分析器
        
        Args:
            engine: DataEngine实例
        """
        self._engine = engine
        self._lock = threading.Lock()
        self._cache: Dict[str, TableStats] = {}
    
    def analyze_table(self, table_name: str, force_refresh: bool = False) -> TableStats:
        """
        分析表的统计信息
        
        Args:
            table_name: 表名
            force_refresh: 是否强制刷新缓存
            
        Returns:
            TableStats: 表统计信息
        """
        with self._lock:
            # 检查缓存
            if not force_refresh and table_name in self._cache:
                return self._cache[table_name]
            
            table_info = self._engine.get_table_info(table_name)
            if not table_info:
                raise ValueError(f"表不存在: {table_name}")
            
            columns_stats = []
            null_summary = {}
            dtype_summary = {}
            
            for col_info in table_info.columns:
                col_name = col_info['name']
                col_dtype = col_info['dtype']
                
                # 统计数据类型
                dtype_category = self._categorize_dtype(col_dtype)
                dtype_summary[dtype_category] = dtype_summary.get(dtype_category, 0) + 1
                
                # 分析列
                col_stats = self._analyze_column(table_name, col_name, col_dtype)
                columns_stats.append(col_stats)
                
                # 空值汇总
                null_summary[col_name] = col_stats.null_count
            
            # 计算内存使用（估算）
            memory_usage = self._estimate_memory_usage(table_name)
            
            table_stats = TableStats(
                table_name=table_name,
                row_count=table_info.row_count,
                column_count=len(table_info.columns),
                memory_usage=memory_usage,
                columns=columns_stats,
                null_summary=null_summary,
                dtype_summary=dtype_summary
            )
            
            # 缓存结果
            self._cache[table_name] = table_stats
            
            return table_stats
    
    def _categorize_dtype(self, dtype: str) -> str:
        """将DuckDB数据类型分类"""
        dtype_lower = dtype.lower()
        
        if any(t in dtype_lower for t in ['int', 'bigint', 'smallint', 'tinyint']):
            return 'integer'
        elif any(t in dtype_lower for t in ['float', 'double', 'decimal', 'numeric', 'real']):
            return 'float'
        elif any(t in dtype_lower for t in ['varchar', 'char', 'text', 'string']):
            return 'string'
        elif any(t in dtype_lower for t in ['date', 'time', 'timestamp']):
            return 'datetime'
        elif 'bool' in dtype_lower:
            return 'boolean'
        else:
            return 'other'
    
    def _is_numeric_dtype(self, dtype: str) -> bool:
        """判断是否为数值类型"""
        category = self._categorize_dtype(dtype)
        return category in ('integer', 'float')
    
    def _analyze_column(
        self, 
        table_name: str, 
        col_name: str, 
        col_dtype: str
    ) -> ColumnStats:
        """分析单列的统计信息"""
        conn = self._engine._conn
        
        # 基础统计
        base_stats = conn.execute(f'''
            SELECT 
                COUNT(*) as total_count,
                COUNT("{col_name}") as non_null_count,
                COUNT(DISTINCT "{col_name}") as unique_count
            FROM "{table_name}"
        ''').fetchone()
        
        total_count = base_stats[0]
        non_null_count = base_stats[1]
        null_count = total_count - non_null_count
        unique_count = base_stats[2]
        
        null_percentage = (null_count / total_count * 100) if total_count > 0 else 0
        unique_percentage = (unique_count / total_count * 100) if total_count > 0 else 0
        
        col_stats = ColumnStats(
            name=col_name,
            dtype=col_dtype,
            total_count=total_count,
            null_count=null_count,
            null_percentage=round(null_percentage, 2),
            unique_count=unique_count,
            unique_percentage=round(unique_percentage, 2)
        )
        
        # 数值类型的额外统计
        if self._is_numeric_dtype(col_dtype):
            try:
                numeric_stats = conn.execute(f'''
                    SELECT 
                        MIN("{col_name}") as min_val,
                        MAX("{col_name}") as max_val,
                        AVG("{col_name}") as mean_val,
                        MEDIAN("{col_name}") as median_val,
                        STDDEV("{col_name}") as std_val,
                        QUANTILE_CONT("{col_name}", 0.25) as q1_val,
                        QUANTILE_CONT("{col_name}", 0.75) as q3_val
                    FROM "{table_name}"
                    WHERE "{col_name}" IS NOT NULL
                ''').fetchone()
                
                col_stats.min_value = self._safe_float(numeric_stats[0])
                col_stats.max_value = self._safe_float(numeric_stats[1])
                col_stats.mean_value = self._safe_float(numeric_stats[2])
                col_stats.median_value = self._safe_float(numeric_stats[3])
                col_stats.std_value = self._safe_float(numeric_stats[4])
                col_stats.q1_value = self._safe_float(numeric_stats[5])
                col_stats.q3_value = self._safe_float(numeric_stats[6])
            except Exception as e:
                print(f"计算数值统计时出错: {e}")
        
        # 字符串类型的额外统计
        elif self._categorize_dtype(col_dtype) == 'string':
            try:
                string_stats = conn.execute(f'''
                    SELECT 
                        MIN(LENGTH("{col_name}")) as min_len,
                        MAX(LENGTH("{col_name}")) as max_len,
                        AVG(LENGTH("{col_name}")) as avg_len
                    FROM "{table_name}"
                    WHERE "{col_name}" IS NOT NULL
                ''').fetchone()
                
                col_stats.min_length = string_stats[0]
                col_stats.max_length = string_stats[1]
                col_stats.avg_length = round(string_stats[2], 2) if string_stats[2] else None
            except Exception as e:
                print(f"计算字符串统计时出错: {e}")
        
        # 获取Top 10频率值
        try:
            top_values = conn.execute(f'''
                SELECT "{col_name}" as value, COUNT(*) as count
                FROM "{table_name}"
                WHERE "{col_name}" IS NOT NULL
                GROUP BY "{col_name}"
                ORDER BY count DESC
                LIMIT 10
            ''').fetchall()
            
            col_stats.top_values = [
                {"value": str(row[0]), "count": row[1]} 
                for row in top_values
            ]
        except Exception as e:
            print(f"获取Top值时出错: {e}")
        
        return col_stats
    
    def _safe_float(self, value) -> Optional[float]:
        """安全转换为float"""
        if value is None:
            return None
        try:
            result = float(value)
            if np.isnan(result) or np.isinf(result):
                return None
            return round(result, 4)
        except (TypeError, ValueError):
            return None
    
    def _estimate_memory_usage(self, table_name: str) -> int:
        """估算表的内存使用"""
        table_info = self._engine.get_table_info(table_name)
        if not table_info:
            return 0
        
        # 简单估算：每行约100字节 * 行数
        return table_info.row_count * 100
    
    def analyze_column(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """
        分析指定列的详细统计信息
        
        Args:
            table_name: 表名
            column_name: 列名
            
        Returns:
            Dict: 列分析结果
        """
        table_info = self._engine.get_table_info(table_name)
        if not table_info:
            raise ValueError(f"表不存在: {table_name}")
        
        # 查找列信息
        col_info = None
        for col in table_info.columns:
            if col['name'] == column_name:
                col_info = col
                break
        
        if not col_info:
            raise ValueError(f"列不存在: {column_name}")
        
        col_dtype = col_info['dtype']
        col_stats = self._analyze_column(table_name, column_name, col_dtype)
        
        # 转换为前端友好的格式
        result = {
            "column_name": column_name,
            "dtype": col_dtype,
            "total_rows": col_stats.total_count,
            "unique_count": col_stats.unique_count,
            "missing_count": col_stats.null_count,
            "missing_percentage": col_stats.null_percentage,
            "is_numeric": self._is_numeric_dtype(col_dtype),
            "top_values": []
        }
        
        # 添加Top值
        if col_stats.top_values:
            result["top_values"] = [
                (item["value"], item["count"]) 
                for item in col_stats.top_values
            ]
        
        # 如果是数值类型，添加数值统计
        if result["is_numeric"]:
            result["numeric_stats"] = {
                "min": col_stats.min_value,
                "max": col_stats.max_value,
                "mean": col_stats.mean_value,
                "median": col_stats.median_value,
                "std": col_stats.std_value,
                "q1": col_stats.q1_value,
                "q3": col_stats.q3_value
            }
        
        # 如果是字符串类型，添加长度统计
        if self._categorize_dtype(col_dtype) == 'string':
            result["string_stats"] = {
                "min_length": col_stats.min_length,
                "max_length": col_stats.max_length,
                "avg_length": col_stats.avg_length
            }
        
        return result
    
    def analyze_column_from_sql(self, sql: str, column_name: str) -> Dict[str, Any]:
        """
        通过SQL查询分析指定列的详细统计信息
        
        Args:
            sql: SQL查询语句
            column_name: 列名
            
        Returns:
            Dict: 列分析结果
        """
        conn = self._engine._conn
        
        # 使用子查询包装原SQL
        subquery = f"({sql}) AS _subquery"
        
        try:
            # 基础统计
            base_stats = conn.execute(f'''
                SELECT 
                    COUNT(*) as total_count,
                    COUNT("{column_name}") as non_null_count,
                    COUNT(DISTINCT "{column_name}") as unique_count
                FROM {subquery}
            ''').fetchone()
            
            total_count = base_stats[0]
            non_null_count = base_stats[1]
            null_count = total_count - non_null_count
            unique_count = base_stats[2]
            
            null_percentage = (null_count / total_count * 100) if total_count > 0 else 0
            
            result = {
                "column_name": column_name,
                "dtype": "unknown",
                "total_rows": total_count,
                "unique_count": unique_count,
                "missing_count": null_count,
                "missing_percentage": round(null_percentage, 2),
                "is_numeric": False,
                "top_values": []
            }
            
            # 尝试数值统计
            try:
                numeric_stats = conn.execute(f'''
                    SELECT 
                        MIN(CAST("{column_name}" AS DOUBLE)) as min_val,
                        MAX(CAST("{column_name}" AS DOUBLE)) as max_val,
                        AVG(CAST("{column_name}" AS DOUBLE)) as mean_val,
                        MEDIAN(CAST("{column_name}" AS DOUBLE)) as median_val,
                        STDDEV(CAST("{column_name}" AS DOUBLE)) as std_val,
                        QUANTILE_CONT(CAST("{column_name}" AS DOUBLE), 0.25) as q1_val,
                        QUANTILE_CONT(CAST("{column_name}" AS DOUBLE), 0.75) as q3_val
                    FROM {subquery}
                    WHERE "{column_name}" IS NOT NULL
                ''').fetchone()
                
                if numeric_stats[0] is not None:
                    result["is_numeric"] = True
                    result["dtype"] = "numeric"
                    result["numeric_stats"] = {
                        "min": self._safe_float(numeric_stats[0]),
                        "max": self._safe_float(numeric_stats[1]),
                        "mean": self._safe_float(numeric_stats[2]),
                        "median": self._safe_float(numeric_stats[3]),
                        "std": self._safe_float(numeric_stats[4]),
                        "q1": self._safe_float(numeric_stats[5]),
                        "q3": self._safe_float(numeric_stats[6])
                    }
            except Exception:
                # 不是数值类型，跳过
                result["dtype"] = "text"
            
            # 获取Top值
            try:
                top_result = conn.execute(f'''
                    SELECT "{column_name}" as value, COUNT(*) as count
                    FROM {subquery}
                    WHERE "{column_name}" IS NOT NULL
                    GROUP BY "{column_name}"
                    ORDER BY count DESC
                    LIMIT 10
                ''').fetchall()
                
                result["top_values"] = [
                    (str(row[0]) if row[0] is not None else "NULL", row[1])
                    for row in top_result
                ]
            except Exception as e:
                print(f"获取Top值时出错: {e}")
            
            return result
            
        except Exception as e:
            print(f"分析SQL列时出错: {e}")
            raise ValueError(f"分析列失败: {e}")
    
    def get_missing_value_report(self, table_name: str) -> Dict[str, Any]:
        """
        获取缺失值报告
        
        Returns:
            Dict: 缺失值统计报告
        """
        stats = self.analyze_table(table_name)
        
        report = {
            "table_name": table_name,
            "total_rows": stats.row_count,
            "total_columns": stats.column_count,
            "columns": [],
            "summary": {
                "total_cells": stats.row_count * stats.column_count,
                "total_missing": 0,
                "missing_percentage": 0
            }
        }
        
        total_missing = 0
        
        for col in stats.columns:
            col_report = {
                "name": col.name,
                "null_count": col.null_count,
                "null_percentage": col.null_percentage,
                "has_missing": col.null_count > 0
            }
            report["columns"].append(col_report)
            total_missing += col.null_count
        
        report["summary"]["total_missing"] = total_missing
        total_cells = stats.row_count * stats.column_count
        if total_cells > 0:
            report["summary"]["missing_percentage"] = round(
                total_missing / total_cells * 100, 2
            )
        
        return report
    
    def get_numeric_summary(self, table_name: str) -> Dict[str, Any]:
        """
        获取数值列汇总报告
        
        Returns:
            Dict: 数值列统计报告
        """
        stats = self.analyze_table(table_name)
        
        numeric_columns = []
        
        for col in stats.columns:
            if self._is_numeric_dtype(col.dtype):
                numeric_columns.append({
                    "name": col.name,
                    "dtype": col.dtype,
                    "min": col.min_value,
                    "max": col.max_value,
                    "mean": col.mean_value,
                    "median": col.median_value,
                    "std": col.std_value,
                    "q1": col.q1_value,
                    "q3": col.q3_value,
                    "null_count": col.null_count,
                    "null_percentage": col.null_percentage
                })
        
        return {
            "table_name": table_name,
            "numeric_column_count": len(numeric_columns),
            "columns": numeric_columns
        }
    
    def get_column_distribution(
        self, 
        table_name: str, 
        column_name: str, 
        bins: int = 20
    ) -> Dict[str, Any]:
        """
        获取列的分布信息
        
        Args:
            table_name: 表名
            column_name: 列名
            bins: 直方图箱数
            
        Returns:
            Dict: 分布信息
        """
        conn = self._engine._conn
        
        # 获取列类型
        col_info = None
        table_info = self._engine.get_table_info(table_name)
        if table_info:
            for col in table_info.columns:
                if col['name'] == column_name:
                    col_info = col
                    break
        
        if not col_info:
            return {"error": f"列不存在: {column_name}"}
        
        result = {
            "table_name": table_name,
            "column_name": column_name,
            "dtype": col_info['dtype']
        }
        
        if self._is_numeric_dtype(col_info['dtype']):
            # 数值列：计算直方图
            try:
                min_max = conn.execute(f'''
                    SELECT MIN("{column_name}"), MAX("{column_name}")
                    FROM "{table_name}"
                    WHERE "{column_name}" IS NOT NULL
                ''').fetchone()
                
                min_val, max_val = min_max
                
                if min_val is not None and max_val is not None:
                    bin_width = (max_val - min_val) / bins if max_val != min_val else 1
                    
                    histogram_data = conn.execute(f'''
                        SELECT 
                            FLOOR(("{column_name}" - {min_val}) / {bin_width}) as bin,
                            COUNT(*) as count
                        FROM "{table_name}"
                        WHERE "{column_name}" IS NOT NULL
                        GROUP BY bin
                        ORDER BY bin
                    ''').fetchall()
                    
                    result["histogram"] = {
                        "bins": bins,
                        "min": float(min_val),
                        "max": float(max_val),
                        "bin_width": float(bin_width),
                        "data": [{"bin": int(row[0]) if row[0] else 0, "count": row[1]} for row in histogram_data]
                    }
            except Exception as e:
                result["error"] = str(e)
        else:
            # 分类列：计算频率
            try:
                freq_data = conn.execute(f'''
                    SELECT "{column_name}" as value, COUNT(*) as count
                    FROM "{table_name}"
                    GROUP BY "{column_name}"
                    ORDER BY count DESC
                    LIMIT 50
                ''').fetchall()
                
                result["frequency"] = [
                    {"value": str(row[0]) if row[0] is not None else "NULL", "count": row[1]}
                    for row in freq_data
                ]
            except Exception as e:
                result["error"] = str(e)
        
        return result
    
    def clear_cache(self, table_name: Optional[str] = None):
        """清除缓存"""
        with self._lock:
            if table_name:
                if table_name in self._cache:
                    del self._cache[table_name]
            else:
                self._cache.clear()
