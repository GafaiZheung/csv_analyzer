"""
工作区管理器 - 保存和加载工作区配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class WorkspaceConfig:
    """工作区配置"""
    # 已加载的CSV文件
    loaded_files: List[str] = field(default_factory=list)
    
    # 保存的视图
    views: Dict[str, str] = field(default_factory=dict)
    
    # 窗口状态
    window_geometry: Dict[str, int] = field(default_factory=dict)
    
    # 分割器状态
    splitter_sizes: Dict[str, List[int]] = field(default_factory=dict)
    
    # 面板可见性
    panel_visibility: Dict[str, bool] = field(default_factory=lambda: {
        'sidebar': True,
        'analysis_panel': True,
        'sql_editor': True
    })
    
    # 当前选中的表
    current_table: Optional[str] = None
    
    # 最后使用的SQL
    last_sql: str = ""
    
    # 最近打开的文件
    recent_files: List[str] = field(default_factory=list)


class WorkspaceManager:
    """工作区管理器"""
    
    def __init__(self):
        self._config_dir = self._get_config_dir()
        self._workspace_file = self._config_dir / "workspace.json"
        self._recent_limit = 10
    
    def _get_config_dir(self) -> Path:
        """获取配置目录"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / 'CSVAnalyzer'
        else:  # macOS / Linux
            config_dir = Path.home() / '.config' / 'csv-analyzer'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def load(self) -> WorkspaceConfig:
        """加载工作区配置"""
        if not self._workspace_file.exists():
            return WorkspaceConfig()
        
        try:
            with open(self._workspace_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证文件是否存在
            loaded_files = data.get('loaded_files', [])
            valid_files = [f for f in loaded_files if os.path.exists(f)]
            data['loaded_files'] = valid_files
            
            return WorkspaceConfig(**data)
        except Exception as e:
            print(f"加载工作区失败: {e}")
            return WorkspaceConfig()
    
    def save(self, config: WorkspaceConfig):
        """保存工作区配置"""
        try:
            with open(self._workspace_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存工作区失败: {e}")
    
    def add_recent_file(self, filepath: str) -> List[str]:
        """添加最近打开的文件"""
        config = self.load()
        
        # 移除已存在的
        if filepath in config.recent_files:
            config.recent_files.remove(filepath)
        
        # 添加到开头
        config.recent_files.insert(0, filepath)
        
        # 限制数量
        config.recent_files = config.recent_files[:self._recent_limit]
        
        self.save(config)
        return config.recent_files
    
    def get_recent_files(self) -> List[str]:
        """获取最近打开的文件"""
        config = self.load()
        # 过滤掉不存在的文件
        return [f for f in config.recent_files if os.path.exists(f)]
    
    def clear_workspace(self):
        """清空工作区"""
        self.save(WorkspaceConfig())
