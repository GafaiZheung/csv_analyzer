"""
进程间通信模块 - 实现前后端分离的通信机制
使用多进程和队列实现线程安全的数据传输
"""

import json
import queue
import threading
import multiprocessing as mp
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import traceback


class MessageType(Enum):
    """消息类型"""
    # 文件操作
    LOAD_CSV = "load_csv"
    DROP_TABLE = "drop_table"
    GET_TABLES = "get_tables"
    GET_TABLE_INFO = "get_table_info"
    
    # 查询操作
    EXECUTE_QUERY = "execute_query"
    GET_TABLE_DATA = "get_table_data"
    
    # 视图操作
    SAVE_VIEW = "save_view"
    GET_VIEWS = "get_views"
    DELETE_VIEW = "delete_view"
    
    # 分析操作
    ANALYZE_TABLE = "analyze_table"
    ANALYZE_COLUMN = "analyze_column"
    GET_MISSING_REPORT = "get_missing_report"
    GET_NUMERIC_SUMMARY = "get_numeric_summary"
    GET_COLUMN_DISTRIBUTION = "get_column_distribution"
    
    # 导出操作
    EXPORT_CSV = "export_csv"
    
    # 系统消息
    SHUTDOWN = "shutdown"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class Message:
    """消息结构"""
    id: str
    type: MessageType
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "payload": self.payload
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            payload=data["payload"]
        )


@dataclass
class Response:
    """响应结构"""
    request_id: str
    success: bool
    data: Any
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


class BackendWorker:
    """
    后端工作进程
    在独立进程中运行，处理所有数据操作
    """
    
    def __init__(self, request_queue: mp.Queue, response_queue: mp.Queue):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.running = True
        self.engine = None
        self.analyzer = None
    
    def run(self):
        """主循环"""
        # 延迟导入，确保在子进程中初始化
        from csv_analyzer.backend.engine import DataEngine
        from csv_analyzer.backend.analyzer import DataAnalyzer
        
        self.engine = DataEngine()
        self.analyzer = DataAnalyzer(self.engine)
        
        while self.running:
            try:
                # 等待请求
                message_dict = self.request_queue.get(timeout=0.1)
                message = Message.from_dict(message_dict)
                
                # 处理消息
                response = self._handle_message(message)
                
                # 发送响应
                self.response_queue.put(response.to_dict())
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Backend worker error: {e}")
                traceback.print_exc()
        
        # 清理
        if self.engine:
            self.engine.close()
    
    def _handle_message(self, message: Message) -> Response:
        """处理消息"""
        try:
            handler = getattr(self, f"_handle_{message.type.value}", None)
            if handler:
                result = handler(message.payload)
                return Response(
                    request_id=message.id,
                    success=True,
                    data=result
                )
            else:
                return Response(
                    request_id=message.id,
                    success=False,
                    data=None,
                    error=f"Unknown message type: {message.type.value}"
                )
        except Exception as e:
            traceback.print_exc()
            return Response(
                request_id=message.id,
                success=False,
                data=None,
                error=str(e)
            )
    
    # 文件操作处理器
    def _handle_load_csv(self, payload: Dict) -> Dict:
        table_info = self.engine.load_csv(
            payload["file_path"],
            payload.get("table_name")
        )
        return {
            "name": table_info.name,
            "file_path": table_info.file_path,
            "row_count": table_info.row_count,
            "columns": table_info.columns,
            "file_size": table_info.file_size,
            "encoding": table_info.encoding
        }
    
    def _handle_drop_table(self, payload: Dict) -> bool:
        return self.engine.drop_table(payload["table_name"])
    
    def _handle_get_tables(self, payload: Dict) -> list:
        tables = self.engine.get_tables()
        return [
            {
                "name": t.name,
                "file_path": t.file_path,
                "row_count": t.row_count,
                "columns": t.columns,
                "file_size": t.file_size,
                "encoding": t.encoding
            }
            for t in tables
        ]
    
    def _handle_get_table_info(self, payload: Dict) -> Optional[Dict]:
        table_info = self.engine.get_table_info(payload["table_name"])
        if table_info:
            return {
                "name": table_info.name,
                "file_path": table_info.file_path,
                "row_count": table_info.row_count,
                "columns": table_info.columns,
                "file_size": table_info.file_size,
                "encoding": table_info.encoding
            }
        return None
    
    # 查询操作处理器
    def _handle_execute_query(self, payload: Dict) -> Dict:
        result = self.engine.execute_query(
            payload["sql"],
            payload.get("limit", 1000),
            payload.get("offset", 0)
        )
        return {
            "columns": result.columns,
            "data": result.data,
            "row_count": result.row_count,
            "total_rows": result.total_rows,
            "execution_time": result.execution_time,
            "error": result.error
        }
    
    def _handle_get_table_data(self, payload: Dict) -> Dict:
        result = self.engine.get_table_data(
            payload["table_name"],
            payload.get("limit", 1000),
            payload.get("offset", 0)
        )
        return {
            "columns": result.columns,
            "data": result.data,
            "row_count": result.row_count,
            "total_rows": result.total_rows,
            "execution_time": result.execution_time,
            "error": result.error
        }
    
    # 视图操作处理器
    def _handle_save_view(self, payload: Dict) -> bool:
        return self.engine.save_view(
            payload["view_name"],
            payload["sql"]
        )
    
    def _handle_get_views(self, payload: Dict) -> Dict:
        return self.engine.get_views()
    
    def _handle_delete_view(self, payload: Dict) -> bool:
        return self.engine.delete_view(payload["view_name"])
    
    # 分析操作处理器
    def _handle_analyze_table(self, payload: Dict) -> Dict:
        stats = self.analyzer.analyze_table(
            payload["table_name"],
            payload.get("force_refresh", False)
        )
        return {
            "table_name": stats.table_name,
            "row_count": stats.row_count,
            "column_count": stats.column_count,
            "memory_usage": stats.memory_usage,
            "columns": [asdict(col) for col in stats.columns],
            "null_summary": stats.null_summary,
            "dtype_summary": stats.dtype_summary
        }
    
    def _handle_analyze_column(self, payload: Dict) -> Dict:
        """处理列分析请求"""
        table_name = payload["table_name"]
        column_name = payload["column_name"]
        
        return self.analyzer.analyze_column(table_name, column_name)
    
    def _handle_get_missing_report(self, payload: Dict) -> Dict:
        return self.analyzer.get_missing_value_report(payload["table_name"])
    
    def _handle_get_numeric_summary(self, payload: Dict) -> Dict:
        return self.analyzer.get_numeric_summary(payload["table_name"])
    
    def _handle_get_column_distribution(self, payload: Dict) -> Dict:
        return self.analyzer.get_column_distribution(
            payload["table_name"],
            payload["column_name"],
            payload.get("bins", 20)
        )
    
    # 导出操作处理器
    def _handle_export_csv(self, payload: Dict) -> bool:
        return self.engine.export_to_csv(
            payload["sql_or_table"],
            payload["output_path"],
            payload.get("is_sql", False)
        )
    
    def _handle_shutdown(self, payload: Dict):
        self.running = False
        return True


def run_backend_worker(request_queue: mp.Queue, response_queue: mp.Queue):
    """后端工作进程入口函数"""
    worker = BackendWorker(request_queue, response_queue)
    worker.run()


class IPCClient:
    """
    IPC客户端 - 在前端进程中使用
    负责与后端工作进程通信
    """
    
    def __init__(self):
        self.request_queue: Optional[mp.Queue] = None
        self.response_queue: Optional[mp.Queue] = None
        self.backend_process: Optional[mp.Process] = None
        self._request_id_counter = 0
        self._pending_requests: Dict[str, threading.Event] = {}
        self._responses: Dict[str, Response] = {}
        self._response_listener: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
    
    def start(self):
        """启动后端进程"""
        if self.backend_process is not None:
            return
        
        # 创建通信队列
        self.request_queue = mp.Queue()
        self.response_queue = mp.Queue()
        
        # 启动后端进程
        self.backend_process = mp.Process(
            target=run_backend_worker,
            args=(self.request_queue, self.response_queue)
        )
        self.backend_process.start()
        
        # 启动响应监听线程
        self._running = True
        self._response_listener = threading.Thread(
            target=self._listen_responses,
            daemon=True
        )
        self._response_listener.start()
    
    def stop(self):
        """停止后端进程"""
        if self.backend_process is None:
            return
        
        self._running = False
        
        # 发送关闭消息
        try:
            self.send_message(MessageType.SHUTDOWN, {})
        except:
            pass
        
        # 等待进程结束
        self.backend_process.join(timeout=5)
        
        if self.backend_process.is_alive():
            self.backend_process.terminate()
        
        self.backend_process = None
    
    def _listen_responses(self):
        """监听响应的线程"""
        while self._running:
            try:
                response_dict = self.response_queue.get(timeout=0.1)
                response = Response(
                    request_id=response_dict["request_id"],
                    success=response_dict["success"],
                    data=response_dict["data"],
                    error=response_dict.get("error")
                )
                
                with self._lock:
                    self._responses[response.request_id] = response
                    if response.request_id in self._pending_requests:
                        self._pending_requests[response.request_id].set()
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Response listener error: {e}")
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        with self._lock:
            self._request_id_counter += 1
            return f"req_{self._request_id_counter}"
    
    def send_message(
        self, 
        msg_type: MessageType, 
        payload: Dict,
        timeout: float = 30.0
    ) -> Response:
        """
        发送消息并等待响应
        
        Args:
            msg_type: 消息类型
            payload: 消息负载
            timeout: 超时时间（秒）
            
        Returns:
            Response: 响应对象
        """
        request_id = self._generate_request_id()
        
        message = Message(
            id=request_id,
            type=msg_type,
            payload=payload
        )
        
        # 创建等待事件
        event = threading.Event()
        with self._lock:
            self._pending_requests[request_id] = event
        
        # 发送请求
        self.request_queue.put(message.to_dict())
        
        # 等待响应
        if event.wait(timeout=timeout):
            with self._lock:
                response = self._responses.pop(request_id, None)
                del self._pending_requests[request_id]
            
            if response:
                return response
        
        # 超时
        with self._lock:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            if request_id in self._responses:
                del self._responses[request_id]
        
        return Response(
            request_id=request_id,
            success=False,
            data=None,
            error="Request timeout"
        )
    
    # 便捷方法
    def load_csv(self, file_path: str, table_name: str = None) -> Response:
        """加载CSV文件"""
        return self.send_message(
            MessageType.LOAD_CSV,
            {"file_path": file_path, "table_name": table_name}
        )
    
    def get_tables(self) -> Response:
        """获取所有表"""
        return self.send_message(MessageType.GET_TABLES, {})
    
    def get_table_data(
        self, 
        table_name: str, 
        limit: int = 1000, 
        offset: int = 0
    ) -> Response:
        """获取表数据"""
        return self.send_message(
            MessageType.GET_TABLE_DATA,
            {"table_name": table_name, "limit": limit, "offset": offset}
        )
    
    def execute_query(
        self, 
        sql: str, 
        limit: int = 1000, 
        offset: int = 0
    ) -> Response:
        """执行SQL查询"""
        return self.send_message(
            MessageType.EXECUTE_QUERY,
            {"sql": sql, "limit": limit, "offset": offset}
        )
    
    def save_view(self, view_name: str, sql: str) -> Response:
        """保存视图"""
        return self.send_message(
            MessageType.SAVE_VIEW,
            {"view_name": view_name, "sql": sql}
        )
    
    def get_views(self) -> Response:
        """获取所有视图"""
        return self.send_message(MessageType.GET_VIEWS, {})
    
    def analyze_table(self, table_name: str) -> Response:
        """分析表"""
        return self.send_message(
            MessageType.ANALYZE_TABLE,
            {"table_name": table_name}
        )
    
    def analyze_column(self, table_name: str, column_name: str) -> Response:
        """分析列"""
        return self.send_message(
            MessageType.ANALYZE_COLUMN,
            {"table_name": table_name, "column_name": column_name}
        )
    
    def get_missing_report(self, table_name: str) -> Response:
        """获取缺失值报告"""
        return self.send_message(
            MessageType.GET_MISSING_REPORT,
            {"table_name": table_name}
        )
    
    def get_numeric_summary(self, table_name: str) -> Response:
        """获取数值汇总"""
        return self.send_message(
            MessageType.GET_NUMERIC_SUMMARY,
            {"table_name": table_name}
        )
    
    def drop_table(self, table_name: str) -> Response:
        """删除表"""
        return self.send_message(
            MessageType.DROP_TABLE,
            {"table_name": table_name}
        )
