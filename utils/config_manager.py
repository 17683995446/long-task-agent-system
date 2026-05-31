"""
超长任务Agent树形双生子模块化执行系统 - 配置管理实现
Config Manager Implementation for Long-Task Agent Twin-Module Execution System

阶段8：配置管理实现
遵循原则：图难于其易，为大于其细
核心约束：分层配置管理，支持全局/模块级/任务级
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import json
import os
import threading

from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. 配置异常类型 (Config Exception Types)
# =============================================================================

class ConfigError(Exception):
    """配置基础异常"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置未找到异常"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误异常"""
    pass


class ConfigTypeError(ConfigError):
    """配置类型错误异常"""
    pass


# =============================================================================
# 2. 配置来源枚举 (Config Source Enumeration)
# =============================================================================

class ConfigSource(Enum):
    """
    配置来源枚举
    """
    DEFAULT = auto()      # 默认值
    FILE = auto()         # 配置文件
    ENVIRONMENT = auto()  # 环境变量
    CODE = auto()         # 代码设置
    RUNTIME = auto()      # 运行时动态设置


# =============================================================================
# 3. 配置项 (Config Item)
# =============================================================================

@dataclass
class ConfigItem:
    """
    配置项
    存储单个配置的完整信息
    """
    key: str
    value: Any
    source: ConfigSource = ConfigSource.DEFAULT
    description: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source.name,
            "description": self.description,
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# 4. 配置模式 (Config Schema)
# =============================================================================

@dataclass
class ConfigSchema:
    """
    配置模式
    定义配置项的验证规则
    """
    key: str
    type: type
    required: bool = False
    default: Any = None
    description: str = ""
    validator: Optional[callable] = None
    
    def validate(self, value: Any) -> bool:
        """
        验证配置值
        
        Args:
            value: 配置值
            
        Returns:
            bool: 是否有效
        """
        if value is None:
            return not self.required
        
        if not isinstance(value, self.type):
            return False
        
        if self.validator:
            return self.validator(value)
        
        return True


# =============================================================================
# 5. 配置管理器 (Config Manager)
# =============================================================================

class ConfigManager:
    """
    配置管理器
    
    提供分层配置管理：
    1. 全局配置
    2. 模块级配置
    3. 任务级配置
    
    支持配置来源追踪和验证
    
    使用方式：
        config = ConfigManager.instance()
        config.load_from_file("config.json")
        value = config.get("key", default="default_value")
    """
    
    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """私有初始化"""
        # 全局配置
        self._global_config: Dict[str, ConfigItem] = {}
        
        # 模块级配置
        self._module_config: Dict[ModuleID, Dict[str, ConfigItem]] = {}
        
        # 任务级配置
        self._task_config: Dict[TaskID, Dict[str, ConfigItem]] = {}
        
        # 配置模式
        self._schemas: Dict[str, ConfigSchema] = {}
        
        # 线程锁
        self._lock = threading.RLock()
    
    # =====================================================================
    # 单例模式
    # =====================================================================
    
    @classmethod
    def instance(cls) -> "ConfigManager":
        """
        获取配置管理器单例
        
        Returns:
            ConfigManager: 配置管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """重置配置管理器（仅用于测试）"""
        cls._instance = None
    
    # =====================================================================
    # 配置加载
    # =====================================================================
    
    def load_from_file(self, filepath: str, source: ConfigSource = ConfigSource.FILE) -> None:
        """
        从文件加载配置
        
        Args:
            filepath: 配置文件路径
            source: 配置来源
            
        Raises:
            ConfigNotFoundError: 文件不存在
            ConfigValidationError: 配置格式错误
        """
        if not os.path.exists(filepath):
            raise ConfigNotFoundError(f"配置文件不存在: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._load_dict(data, source)
            
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"配置文件JSON格式错误: {e}")
    
    def load_from_dict(self, data: Dict[str, Any], source: ConfigSource = ConfigSource.CODE) -> None:
        """
        从字典加载配置
        
        Args:
            data: 配置字典
            source: 配置来源
        """
        self._load_dict(data, source)
    
    def load_from_environment(self, prefix: str = "AGENT_") -> None:
        """
        从环境变量加载配置
        
        Args:
            prefix: 环境变量前缀
        """
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                
                # 尝试解析值类型
                parsed_value = self._parse_value(value)
                
                self.set(config_key, parsed_value, ConfigSource.ENVIRONMENT)
    
    def _load_dict(self, data: Dict[str, Any], source: ConfigSource) -> None:
        """内部方法：从字典加载配置"""
        with self._lock:
            for key, value in data.items():
                self._set_global(key, value, source)
    
    def _parse_value(self, value: str) -> Any:
        """解析字符串值为合适类型"""
        # 尝试解析为整数
        try:
            return int(value)
        except ValueError:
            pass
        
        # 尝试解析为浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 尝试解析为布尔值
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # 尝试解析为JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # 返回字符串
        return value
    
    # =====================================================================
    # 配置设置
    # =====================================================================
    
    def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.RUNTIME,
        description: str = "",
    ) -> None:
        """
        设置全局配置
        
        Args:
            key: 配置键
            value: 配置值
            source: 配置来源
            description: 描述
        """
        self._set_global(key, value, source, description)
    
    def set_module_config(
        self,
        module_id: ModuleID,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.RUNTIME,
    ) -> None:
        """
        设置模块级配置
        
        Args:
            module_id: 模块ID
            key: 配置键
            value: 配置值
            source: 配置来源
        """
        with self._lock:
            if module_id not in self._module_config:
                self._module_config[module_id] = {}
            
            self._module_config[module_id][key] = ConfigItem(
                key=key,
                value=value,
                source=source,
            )
    
    def set_task_config(
        self,
        task_id: TaskID,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.RUNTIME,
    ) -> None:
        """
        设置任务级配置
        
        Args:
            task_id: 任务ID
            key: 配置键
            value: 配置值
            source: 配置来源
        """
        with self._lock:
            if task_id not in self._task_config:
                self._task_config[task_id] = {}
            
            self._task_config[task_id][key] = ConfigItem(
                key=key,
                value=value,
                source=source,
            )
    
    def _set_global(
        self,
        key: str,
        value: Any,
        source: ConfigSource,
        description: str = "",
    ) -> None:
        """内部方法：设置全局配置"""
        with self._lock:
            self._global_config[key] = ConfigItem(
                key=key,
                value=value,
                source=source,
                description=description,
            )
    
    # =====================================================================
    # 配置获取
    # =====================================================================
    
    def get(
        self,
        key: str,
        default: Any = None,
        module_id: Optional[ModuleID] = None,
        task_id: Optional[TaskID] = None,
    ) -> Any:
        """
        获取配置值
        
        优先级：任务级 > 模块级 > 全局 > 默认值
        
        Args:
            key: 配置键
            default: 默认值
            module_id: 模块ID（获取模块级配置）
            task_id: 任务ID（获取任务级配置）
            
        Returns:
            Any: 配置值
        """
        with self._lock:
            # 1. 尝试获取任务级配置
            if task_id and task_id in self._task_config:
                if key in self._task_config[task_id]:
                    return self._task_config[task_id][key].value
            
            # 2. 尝试获取模块级配置
            if module_id and module_id in self._module_config:
                if key in self._module_config[module_id]:
                    return self._module_config[module_id][key].value
            
            # 3. 尝试获取全局配置
            if key in self._global_config:
                return self._global_config[key].value
            
            # 4. 返回默认值
            return default
    
    def get_item(
        self,
        key: str,
        module_id: Optional[ModuleID] = None,
        task_id: Optional[TaskID] = None,
    ) -> Optional[ConfigItem]:
        """
        获取配置项（包含元数据）
        
        Args:
            key: 配置键
            module_id: 模块ID
            task_id: 任务ID
            
        Returns:
            Optional[ConfigItem]: 配置项
        """
        with self._lock:
            if task_id and task_id in self._task_config:
                if key in self._task_config[task_id]:
                    return self._task_config[task_id][key]
            
            if module_id and module_id in self._module_config:
                if key in self._module_config[module_id]:
                    return self._module_config[module_id][key]
            
            if key in self._global_config:
                return self._global_config[key]
            
            return None
    
    def get_required(self, key: str) -> Any:
        """
        获取必需配置
        
        Args:
            key: 配置键
            
        Returns:
            Any: 配置值
            
        Raises:
            ConfigNotFoundError: 配置不存在
        """
        value = self.get(key)
        if value is None:
            raise ConfigNotFoundError(f"必需配置不存在: {key}")
        return value
    
    def get_typed(self, key: str, expected_type: type, default: Any = None) -> Any:
        """
        获取指定类型的配置
        
        Args:
            key: 配置键
            expected_type: 期望类型
            default: 默认值
            
        Returns:
            Any: 配置值
            
        Raises:
            ConfigTypeError: 类型不匹配
        """
        value = self.get(key, default)
        if value is not None and not isinstance(value, expected_type):
            raise ConfigTypeError(
                f"配置 {key} 类型错误: 期望 {expected_type.__name__}, "
                f"实际 {type(value).__name__}"
            )
        return value
    
    # =====================================================================
    # 配置模式（验证）
    # =====================================================================
    
    def register_schema(self, schema: ConfigSchema) -> None:
        """
        注册配置模式
        
        Args:
            schema: 配置模式
        """
        with self._lock:
            self._schemas[schema.key] = schema
    
    def validate_config(self, key: str, value: Any) -> bool:
        """
        验证配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            bool: 是否有效
        """
        with self._lock:
            schema = self._schemas.get(key)
            if schema:
                return schema.validate(value)
            return True
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        验证所有配置
        
        Returns:
            Dict[str, List[str]]: 错误信息字典
        """
        errors = {}
        
        with self._lock:
            # 验证全局配置
            for key, item in self._global_config.items():
                if not self.validate_config(key, item.value):
                    errors[key] = [f"配置值无效: {item.value}"]
            
            # 验证模块级配置
            for module_id, config in self._module_config.items():
                for key, item in config.items():
                    if not self.validate_config(key, item.value):
                        errors[f"{module_id}.{key}"] = [f"配置值无效: {item.value}"]
            
            # 验证任务级配置
            for task_id, config in self._task_config.items():
                for key, item in config.items():
                    if not self.validate_config(key, item.value):
                        errors[f"{task_id}.{key}"] = [f"配置值无效: {item.value}"]
        
        return errors
    
    # =====================================================================
    # 配置删除
    # =====================================================================
    
    def remove(self, key: str) -> bool:
        """
        删除全局配置
        
        Args:
            key: 配置键
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            if key in self._global_config:
                del self._global_config[key]
                return True
            return False
    
    def remove_module_config(self, module_id: ModuleID, key: str) -> bool:
        """
        删除模块级配置
        
        Args:
            module_id: 模块ID
            key: 配置键
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            if module_id in self._module_config:
                if key in self._module_config[module_id]:
                    del self._module_config[module_id][key]
                    return True
            return False
    
    def clear(self) -> None:
        """清除所有配置"""
        with self._lock:
            self._global_config.clear()
            self._module_config.clear()
            self._task_config.clear()
    
    # =====================================================================
    # 配置导出
    # =====================================================================
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """
        导出所有配置为字典
        
        Args:
            include_metadata: 是否包含元数据
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        with self._lock:
            if include_metadata:
                return {
                    "global": {
                        key: item.to_dict()
                        for key, item in self._global_config.items()
                    },
                    "modules": {
                        str(mid): {
                            key: item.to_dict()
                            for key, item in config.items()
                        }
                        for mid, config in self._module_config.items()
                    },
                    "tasks": {
                        str(tid): {
                            key: item.to_dict()
                            for key, item in config.items()
                        }
                        for tid, config in self._task_config.items()
                    },
                }
            else:
                return {
                    "global": {
                        key: item.value
                        for key, item in self._global_config.items()
                    },
                    "modules": {
                        str(mid): {
                            key: item.value
                            for key, item in config.items()
                        }
                        for mid, config in self._module_config.items()
                    },
                    "tasks": {
                        str(tid): {
                            key: item.value
                            for key, item in config.items()
                        }
                        for tid, config in self._task_config.items()
                    },
                }
    
    def save_to_file(self, filepath: str, include_metadata: bool = False) -> None:
        """
        保存配置到文件
        
        Args:
            filepath: 文件路径
            include_metadata: 是否包含元数据
        """
        data = self.to_dict(include_metadata)
        
        dir_path = os.path.dirname(filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # =====================================================================
    # 查询方法
    # =====================================================================
    
    def has_key(self, key: str) -> bool:
        """检查是否存在配置键"""
        with self._lock:
            return key in self._global_config
    
    def has_module_key(self, module_id: ModuleID, key: str) -> bool:
        """检查是否存在模块级配置键"""
        with self._lock:
            return (
                module_id in self._module_config
                and key in self._module_config[module_id]
            )
    
    def get_all_keys(self) -> List[str]:
        """获取所有全局配置键"""
        with self._lock:
            return list(self._global_config.keys())
    
    def get_module_keys(self, module_id: ModuleID) -> List[str]:
        """获取模块的所有配置键"""
        with self._lock:
            if module_id in self._module_config:
                return list(self._module_config[module_id].keys())
            return []
    
    def get_statistics(self) -> Dict[str, int]:
        """
        获取配置统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        with self._lock:
            return {
                "global_count": len(self._global_config),
                "module_count": len(self._module_config),
                "task_count": len(self._task_config),
                "schema_count": len(self._schemas),
            }
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"ConfigManager("
            f"global={stats['global_count']}, "
            f"modules={stats['module_count']}, "
            f"tasks={stats['task_count']}"
            f")"
        )


# =============================================================================
# 6. 便捷函数
# =============================================================================

def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置的便捷函数
    
    Args:
        key: 配置键
        default: 默认值
        
    Returns:
        Any: 配置值
    """
    return ConfigManager.instance().get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    设置配置的便捷函数
    
    Args:
        key: 配置键
        value: 配置值
    """
    ConfigManager.instance().set(key, value)


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 异常类型
    "ConfigError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "ConfigTypeError",
    
    # 枚举
    "ConfigSource",
    
    # 数据类
    "ConfigItem",
    "ConfigSchema",
    
    # 配置管理器
    "ConfigManager",
    
    # 便捷函数
    "get_config",
    "set_config",
]
