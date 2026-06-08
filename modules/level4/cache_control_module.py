"""
阶段45：四级缓存控制模块
Level4CacheControlModule

职责定义：
- 缓存管理
- 缓存策略
- 缓存失效
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib

from core.base_module import ExecuteModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class CachePolicy(Enum):
    """缓存策略"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


class CacheEntryStatus(Enum):
    """缓存条目状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    EVICTED = "evicted"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    status: CacheEntryStatus = CacheEntryStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class CacheStats:
    """缓存统计"""
    total_entries: int
    total_size_bytes: int
    hit_count: int
    miss_count: int
    eviction_count: int
    hit_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "total_size_bytes": self.total_size_bytes,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "eviction_count": self.eviction_count,
            "hit_rate": self.hit_rate,
        }


class Level4CacheControlModule(ExecuteModuleBase):
    """
    四级缓存控制模块
    
    职责：
    1. 缓存管理
    2. 缓存策略
    3. 缓存失效
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4CacheControlModule"
        self._logger = Logger(f"L4CC_{self.module_id}")
        
        # 缓存存储
        self._cache: Dict[str, CacheEntry] = {}
        # 缓存统计
        self._hit_count: int = 0
        self._miss_count: int = 0
        self._eviction_count: int = 0
        # 标签索引
        self._tag_index: Dict[str, List[str]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级缓存控制模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._cache = {}
            self._hit_count = 0
            self._miss_count = 0
            self._eviction_count = 0
            self._tag_index = {}
            
            self._logger.info("四级缓存控制模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级缓存控制模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级缓存控制模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4CC_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "max_entries": 1000,
            "max_size_bytes": 10 * 1024 * 1024,  # 10MB
            "default_ttl_seconds": 300,
            "eviction_policy": "lru",
        }
        if request.task_param:
            custom_config = request.task_param.get_param("cache_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级缓存控制模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "get")
            
            if operation == "get":
                result = self._get_operation(input_data)
            elif operation == "set":
                result = self._set_operation(input_data)
            elif operation == "delete":
                result = self._delete_operation(input_data)
            elif operation == "invalidate_by_tag":
                result = self._invalidate_by_tag_operation(input_data)
            elif operation == "clear":
                result = self._clear_operation()
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "has_key":
                result = self._has_key_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级缓存控制模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4CacheControlModule",
                    "cache_summary": {
                        "total_entries": len(self._cache),
                        "hit_count": self._hit_count,
                        "miss_count": self._miss_count,
                        "hit_rate": self._hit_count / (self._hit_count + self._miss_count) if (self._hit_count + self._miss_count) > 0 else 0,
                    },
                },
                message="四级缓存控制模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级缓存控制模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4CC_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _get_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取缓存"""
        key = input_data.get("key")
        
        if key not in self._cache:
            self._miss_count += 1
            return {
                "operation": "get",
                "key": key,
                "found": False,
                "value": None,
            }
        
        entry = self._cache[key]
        
        # 检查是否过期
        if entry.expires_at and datetime.now() > entry.expires_at:
            entry.status = CacheEntryStatus.EXPIRED
            del self._cache[key]
            self._remove_from_tag_index(key)
            self._miss_count += 1
            return {
                "operation": "get",
                "key": key,
                "found": False,
                "reason": "expired",
            }
        
        # 更新访问信息
        entry.access_count += 1
        entry.last_accessed = datetime.now()
        self._hit_count += 1
        
        return {
            "operation": "get",
            "key": key,
            "found": True,
            "value": entry.value,
            "access_count": entry.access_count,
        }
    
    def _set_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """设置缓存"""
        key = input_data.get("key")
        value = input_data.get("value")
        ttl_seconds = input_data.get("ttl_seconds", self._config.get("default_ttl_seconds", 300))
        tags = input_data.get("tags", [])
        
        # 检查是否需要驱逐
        self._maybe_evict()
        
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            tags=tags,
            metadata=input_data.get("metadata", {}),
        )
        
        # 估算大小
        try:
            entry.size_bytes = len(str(value).encode('utf-8'))
        except:
            entry.size_bytes = 0
        
        self._cache[key] = entry
        
        # 更新标签索引
        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if key not in self._tag_index[tag]:
                self._tag_index[tag].append(key)
        
        return {
            "operation": "set",
            "key": key,
            "set": True,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
    
    def _maybe_evict(self) -> None:
        """可能需要驱逐条目"""
        max_entries = self._config.get("max_entries", 1000)
        max_size = self._config.get("max_size_bytes", 10 * 1024 * 1024)
        policy = self._config.get("eviction_policy", "lru")
        
        # 检查条目数
        while len(self._cache) >= max_entries:
            self._evict_one(policy)
        
        # 检查总大小
        total_size = sum(e.size_bytes for e in self._cache.values())
        while total_size > max_size and self._cache:
            self._evict_one(policy)
            total_size = sum(e.size_bytes for e in self._cache.values())
    
    def _evict_one(self, policy: str) -> None:
        """驱逐一个条目"""
        if not self._cache:
            return
        
        if policy == "lru":
            # 最少最近使用
            candidates = [e for e in self._cache.values() if e.last_accessed]
            if candidates:
                to_evict = min(candidates, key=lambda e: e.last_accessed)
            else:
                to_evict = min(self._cache.values(), key=lambda e: e.created_at)
        elif policy == "lfu":
            # 最少使用
            to_evict = min(self._cache.values(), key=lambda e: e.access_count)
        elif policy == "fifo":
            # 先进先出
            to_evict = min(self._cache.values(), key=lambda e: e.created_at)
        else:
            to_evict = next(iter(self._cache.values()))
        
        to_evict.status = CacheEntryStatus.EVICTED
        del self._cache[to_evict.key]
        self._remove_from_tag_index(to_evict.key)
        self._eviction_count += 1
    
    def _remove_from_tag_index(self, key: str) -> None:
        """从标签索引中移除"""
        for tag, keys in list(self._tag_index.items()):
            if key in keys:
                keys.remove(key)
                if not keys:
                    del self._tag_index[tag]
    
    def _delete_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """删除缓存"""
        key = input_data.get("key")
        
        if key not in self._cache:
            return {"operation": "delete", "key": key, "deleted": False}
        
        del self._cache[key]
        self._remove_from_tag_index(key)
        
        return {"operation": "delete", "key": key, "deleted": True}
    
    def _invalidate_by_tag_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """按标签失效缓存"""
        tag = input_data.get("tag")
        
        if tag not in self._tag_index:
            return {"operation": "invalidate_by_tag", "tag": tag, "invalidated": 0}
        
        keys = self._tag_index[tag].copy()
        for key in keys:
            if key in self._cache:
                del self._cache[key]
        
        del self._tag_index[tag]
        
        return {
            "operation": "invalidate_by_tag",
            "tag": tag,
            "invalidated": len(keys),
        }
    
    def _clear_operation(self) -> Dict[str, Any]:
        """清空缓存"""
        count = len(self._cache)
        self._cache.clear()
        self._tag_index.clear()
        
        return {"operation": "clear", "cleared": count}
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_size = sum(e.size_bytes for e in self._cache.values())
        total_requests = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "operation": "get_stats",
            "total_entries": len(self._cache),
            "total_size_bytes": total_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "eviction_count": self._eviction_count,
            "hit_rate": hit_rate,
            "tag_count": len(self._tag_index),
        }
    
    def _has_key_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查键是否存在"""
        key = input_data.get("key")
        exists = key in self._cache
        
        if exists:
            entry = self._cache[key]
            if entry.expires_at and datetime.now() > entry.expires_at:
                exists = False
        
        return {"operation": "has_key", "key": key, "exists": exists}
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级缓存控制模块校验开始")
        
        checks = []
        
        if isinstance(self._cache, dict):
            checks.append("cache_valid")
        if isinstance(self._tag_index, dict):
            checks.append("tag_index_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if self._config.get("max_entries", 0) > 0:
            checks.append("config_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="cache_control_validation",
                message="四级缓存控制模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="cache_control_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("cache_keys", list(self._cache.keys()))
        snapshot.set_state("stats", self._get_stats_operation())
        snapshot.metadata["module_type"] = "Level4CacheControlModule"
    
    # 公共接口
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        result = self._get_operation({"key": key})
        return result.get("value") if result.get("found") else None
    
    def set(self, key: str, value: Any, ttl_seconds: int = None, tags: List[str] = None) -> None:
        """设置缓存"""
        self._set_operation({
            "key": key,
            "value": value,
            "ttl_seconds": ttl_seconds,
            "tags": tags or [],
        })
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        result = self._delete_operation({"key": key})
        return result.get("deleted", False)
    
    def invalidate_by_tag(self, tag: str) -> int:
        """按标签失效"""
        result = self._invalidate_by_tag_operation({"tag": tag})
        return result.get("invalidated", 0)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4CacheControlModule",
    "CacheEntry",
    "CacheStats",
    "CachePolicy",
    "CacheEntryStatus",
]
