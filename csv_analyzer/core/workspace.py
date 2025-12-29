"""
工作区管理器 - 保存和加载工作区配置
支持多工作区、工作区命名和搜索
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class WorkspaceConfig:
    """工作区配置"""
    # 工作区ID
    id: str = ""
    
    # 工作区名称
    name: str = "未命名工作区"
    
    # 最后修改时间
    last_modified: str = ""
    
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
    
    # 最近打开的文件（全局，不属于特定工作区）
    recent_files: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.last_modified:
            self.last_modified = datetime.now().isoformat()


@dataclass 
class WorkspaceInfo:
    """工作区简要信息（用于列表显示）"""
    id: str
    name: str
    last_modified: str
    file_count: int = 0
    
    @classmethod
    def from_config(cls, config: WorkspaceConfig) -> 'WorkspaceInfo':
        return cls(
            id=config.id,
            name=config.name,
            last_modified=config.last_modified,
            file_count=len(config.loaded_files)
        )


class WorkspaceManager:
    """工作区管理器"""
    
    def __init__(self):
        self._config_dir = self._get_config_dir()
        self._workspaces_dir = self._config_dir / "workspaces"
        self._workspaces_dir.mkdir(parents=True, exist_ok=True)
        self._global_config_file = self._config_dir / "global_config.json"
        self._recent_limit = 10
        self._max_recent_workspaces = 20
    
    def _get_config_dir(self) -> Path:
        """获取配置目录"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / 'CSVAnalyzer'
        else:  # macOS / Linux
            config_dir = Path.home() / '.config' / 'csv-analyzer'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _get_workspace_file(self, workspace_id: str) -> Path:
        """获取工作区文件路径"""
        return self._workspaces_dir / f"{workspace_id}.json"
    
    def _load_global_config(self) -> Dict[str, Any]:
        """加载全局配置"""
        if not self._global_config_file.exists():
            return {
                'recent_files': [],
                'recent_workspaces': [],
                'last_workspace_id': None
            }
        
        try:
            with open(self._global_config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载全局配置失败: {e}")
            return {
                'recent_files': [],
                'recent_workspaces': [],
                'last_workspace_id': None
            }
    
    def _save_global_config(self, config: Dict[str, Any]):
        """保存全局配置"""
        try:
            with open(self._global_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存全局配置失败: {e}")
    
    # === 工作区操作 ===
    
    def create_workspace(self, name: str = "未命名工作区") -> WorkspaceConfig:
        """创建新工作区"""
        config = WorkspaceConfig(name=name)
        config.id = str(uuid.uuid4())
        config.last_modified = datetime.now().isoformat()
        self.save(config)
        self._add_recent_workspace(config.id, name)
        return config
    
    def load(self, workspace_id: Optional[str] = None) -> WorkspaceConfig:
        """加载工作区配置"""
        # 如果没有指定ID，尝试加载最后使用的工作区
        if workspace_id is None:
            global_config = self._load_global_config()
            workspace_id = global_config.get('last_workspace_id')
        
        if workspace_id is None:
            return WorkspaceConfig()
        
        workspace_file = self._get_workspace_file(workspace_id)
        if not workspace_file.exists():
            return WorkspaceConfig()
        
        try:
            with open(workspace_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证文件是否存在
            loaded_files = data.get('loaded_files', [])
            valid_files = [f for f in loaded_files if os.path.exists(f)]
            data['loaded_files'] = valid_files
            
            return WorkspaceConfig(**data)
        except Exception as e:
            print(f"加载工作区失败: {e}")
            return WorkspaceConfig()
    
    def save(self, config: WorkspaceConfig) -> bool:
        """保存工作区配置，返回是否成功"""
        try:
            # 更新修改时间
            config.last_modified = datetime.now().isoformat()
            
            workspace_file = self._get_workspace_file(config.id)
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2, ensure_ascii=False)
            
            # 更新最后使用的工作区
            global_config = self._load_global_config()
            global_config['last_workspace_id'] = config.id
            self._save_global_config(global_config)
            
            # 更新最近工作区列表
            self._add_recent_workspace(config.id, config.name)
            
            return True
        except Exception as e:
            print(f"保存工作区失败: {e}")
            return False
    
    def delete_workspace(self, workspace_id: str):
        """删除工作区"""
        workspace_file = self._get_workspace_file(workspace_id)
        if workspace_file.exists():
            workspace_file.unlink()
        
        # 从最近工作区中移除
        global_config = self._load_global_config()
        recent = global_config.get('recent_workspaces', [])
        global_config['recent_workspaces'] = [w for w in recent if w.get('id') != workspace_id]
        
        # 如果删除的是最后使用的工作区，清除它
        if global_config.get('last_workspace_id') == workspace_id:
            global_config['last_workspace_id'] = None
        
        self._save_global_config(global_config)
    
    def rename_workspace(self, workspace_id: str, new_name: str):
        """重命名工作区"""
        config = self.load(workspace_id)
        if config.id == workspace_id:
            config.name = new_name
            self.save(config)
    
    def list_workspaces(self) -> List[WorkspaceInfo]:
        """列出所有工作区"""
        workspaces = []
        
        for workspace_file in self._workspaces_dir.glob("*.json"):
            try:
                with open(workspace_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                config = WorkspaceConfig(**data)
                workspaces.append(WorkspaceInfo.from_config(config))
            except Exception as e:
                print(f"读取工作区失败: {workspace_file} - {e}")
        
        # 按最后修改时间排序
        workspaces.sort(key=lambda w: w.last_modified, reverse=True)
        return workspaces
    
    def search_workspaces(self, query: str) -> List[WorkspaceInfo]:
        """搜索工作区（按名称）"""
        query = query.lower().strip()
        if not query:
            return self.get_recent_workspaces()
        
        all_workspaces = self.list_workspaces()
        return [w for w in all_workspaces if query in w.name.lower()]
    
    # === 最近工作区 ===
    
    def _add_recent_workspace(self, workspace_id: str, name: str):
        """添加到最近工作区列表"""
        global_config = self._load_global_config()
        recent = global_config.get('recent_workspaces', [])
        
        # 移除已存在的
        recent = [w for w in recent if w.get('id') != workspace_id]
        
        # 添加到开头
        recent.insert(0, {
            'id': workspace_id,
            'name': name,
            'timestamp': datetime.now().isoformat()
        })
        
        # 限制数量
        recent = recent[:self._max_recent_workspaces]
        
        global_config['recent_workspaces'] = recent
        self._save_global_config(global_config)
    
    def get_recent_workspaces(self) -> List[WorkspaceInfo]:
        """获取最近使用的工作区"""
        global_config = self._load_global_config()
        recent = global_config.get('recent_workspaces', [])
        
        workspaces = []
        for item in recent:
            workspace_id = item.get('id')
            if not workspace_id:
                continue
            
            workspace_file = self._get_workspace_file(workspace_id)
            if not workspace_file.exists():
                continue
            
            try:
                with open(workspace_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                config = WorkspaceConfig(**data)
                workspaces.append(WorkspaceInfo.from_config(config))
            except Exception:
                pass
        
        return workspaces
    
    def get_last_workspace_id(self) -> Optional[str]:
        """获取最后使用的工作区ID"""
        global_config = self._load_global_config()
        return global_config.get('last_workspace_id')
    
    def set_last_workspace_id(self, workspace_id: Optional[str]):
        """设置最后使用的工作区ID"""
        global_config = self._load_global_config()
        global_config['last_workspace_id'] = workspace_id
        self._save_global_config(global_config)
    
    # === 最近文件（全局） ===
    
    def add_recent_file(self, filepath: str) -> List[str]:
        """添加最近打开的文件"""
        global_config = self._load_global_config()
        recent_files = global_config.get('recent_files', [])
        
        # 移除已存在的
        if filepath in recent_files:
            recent_files.remove(filepath)
        
        # 添加到开头
        recent_files.insert(0, filepath)
        
        # 限制数量
        recent_files = recent_files[:self._recent_limit]
        
        global_config['recent_files'] = recent_files
        self._save_global_config(global_config)
        
        return recent_files
    
    def get_recent_files(self) -> List[str]:
        """获取最近打开的文件"""
        global_config = self._load_global_config()
        recent_files = global_config.get('recent_files', [])
        # 过滤掉不存在的文件
        return [f for f in recent_files if os.path.exists(f)]
    
    def clear_workspace(self, workspace_id: str):
        """清空指定工作区"""
        config = self.load(workspace_id)
        if config.id == workspace_id:
            config.loaded_files = []
            config.views = {}
            config.current_table = None
            config.last_sql = ""
            self.save(config)
    
    # === 兼容旧版本：迁移单文件工作区 ===
    
    def migrate_legacy_workspace(self):
        """迁移旧版本的单文件工作区"""
        legacy_file = self._config_dir / "workspace.json"
        if not legacy_file.exists():
            return None
        
        try:
            with open(legacy_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 创建新工作区
            config = WorkspaceConfig(**data)
            if not config.id:
                config.id = str(uuid.uuid4())
            if not config.name or config.name == "未命名工作区":
                config.name = "导入的工作区"
            
            self.save(config)
            
            # 迁移最近文件
            if data.get('recent_files'):
                global_config = self._load_global_config()
                global_config['recent_files'] = data['recent_files']
                self._save_global_config(global_config)
            
            # 重命名旧文件
            legacy_file.rename(legacy_file.with_suffix('.json.bak'))
            
            return config.id
        except Exception as e:
            print(f"迁移旧工作区失败: {e}")
            return None
