"""
超长任务Agent树形双生子模块化执行系统 - 短期状态缓存实现
Short-Term Cache Implementation for Long-Task Agent Twin-Module Execution System

阶段11：短期状态缓存实现
遵循原则：图难于其易，为大于其细
核心约束：内存缓存，TTL过期，LRU淘汰，线程安全
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import time

from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. 缓存项 (Cache Item)
# =============================================================================

@dataclass
class CacheItem:
    """
    缓存项
    存储单个缓存条目的完整信息
    """
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """更新访问信息"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def get_age_seconds(self) -> float:
        """获取存在时长（秒）"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_seconds(self) -> float:
        """获取空闲时长（秒）"""
        return (datetime.now() - self.last_accessed).total_seconds()


# =============================================================================
# 2. 缓存统计 (Cache Statistics)
# =============================================================================

@dataclass
class CacheStats:
    """
    缓存统计信息
    """
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total
    
    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": f"{self.hit_rate:.2%}",
            "miss_rate": f"{self.miss_rate:.2%}",
        }


# =============================================================================
# 3. 短期状态缓存 (Short-Term Cache)
# =============================================================================

class ShortTermCache:
    """
    短期状态缓存
    
    提供内存状态存储，支持：
    1. TTL过期机制
    2. LRU淘汰策略
    3. 线程安全
    4. 统计信息
    
    使用方式：
        cache = ShortTermCache(max_size=1000, default_ttl=300)
        
        # 存储
        cache.set("key", value, ttl=60)
        
        # 获取
        value = cache.get("key")
        
        # 删除
        cache.delete("key")
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = 300,
        cleanup_interval: int = 60,
    ):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒），None表示永不过期
            cleanup_interval: 清理间隔（秒）
        """
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        
        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheItem] = OrderedDict()
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = CacheStats(max_size=max_size)
        
        # 最后清理时间
        self._last_cleanup = datetime.now()
    
    # =====================================================================
    # 基本操作
    # =====================================================================
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        设置缓存值
        
        Args:
            key: 键
            value: 值
            ttl: TTL（秒），None使用默认值
        """
        with self._lock:
            # 清理过期项
            self._cleanup_if_needed()
            
            # 计算过期时间
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            elif self._default_ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=self._default_ttl)
            
            # 创建或更新缓存项
            item = CacheItem(
                key=key,
                value=value,
                expires_at=expires_at,
            )
            
            # 如果键已存在，先删除旧项
            if key in self._cache:
                del self._cache[key]
            
            # 检查是否需要淘汰
            self._evict_if_needed()
            
            # 添加新项（添加到末尾表示最新）
            self._cache[key] = item
            self._stats.size = len(self._cache)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        with self._lock:
            item = self._cache.get(key)
            
            if item is None:
                self._stats.misses += 1
                return default
            
            # 检查是否过期
            if item.is_expired():
                del self._cache[key]
                self._stats.expirations += 1
                self._stats.misses += 1
                self._stats.size = len(self._cache)
                return default
            
            # 更新访问信息
            item.touch()
            
            # 移动到末尾（LRU）
            self._cache.move_to_end(key)
            
            self._stats.hits += 1
            return item.value
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 键
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键
            
        Returns:
            bool: 是否存在
        """
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return False
            
            # 检查是否过期
            if item.is_expired():
                del self._cache[key]
                self._stats.expirations += 1
                self._stats.size = len(self._cache)
                return False
            
            return True
    
    # =====================================================================
    # 批量操作
    # =====================================================================
    
    def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        批量设置
        
        Args:
            items: 键值对字典
            ttl: TTL（秒）
        """
        for key, value in items.items():
            self.set(key, value, ttl)
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取
        
        Args:
            keys: 键列表
            
        Returns:
            Dict[str, Any]: 存在的键值对
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def delete_many(self, keys: List[str]) -> int:
        """
        批量删除
        
        Args:
            keys: 键列表
            
        Returns:
            int: 删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count
    
    # =====================================================================
    # 清理和淘汰
    # =====================================================================
    
    def _cleanup_if_needed(self) -> None:
        """如果需要，执行清理"""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() >= self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now
    
    def _cleanup_expired(self) -> int:
        """
        清理过期项
        
        Returns:
            int: 清理的数量
        """
        expired_keys = [
            key for key, item in self._cache.items()
            if item.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats.expirations += 1
        
        if expired_keys:
            self._stats.size = len(self._cache)
        
        return len(expired_keys)
    
    def _evict_if_needed(self) -> None:
        """如果需要，执行LRU淘汰"""
        while len(self._cache) >= self._max_size:
            # 淘汰最久未使用的（OrderedDict的第一个）
            key, item = self._cache.popitem(last=False)
            self._stats.evictions += 1
    
    def cleanup(self) -> int:
        """
        手动清理过期项
        
        Returns:
            int: 清理的数量
        """
        with self._lock:
            return self._cleanup_expired()
    
    def clear(self) -> int:
        """
        清空缓存
        
        Returns:
            int: 清空的数量
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.size = 0
            return count
    
    # =====================================================================
    # 查询方法
    # =====================================================================
    
    def keys(self) -> List[str]:
        """
        获取所有键
        
        Returns:
            List[str]: 键列表
        """
        with self._lock:
            # 清理过期项
            self._cleanup_expired()
            return list(self._cache.keys())
    
    def values(self) -> List[Any]:
        """
        获取所有值
        
        Returns:
            List[Any]: 值列表
        """
        with self._lock:
            self._cleanup_expired()
            return [item.value for item in self._cache.values()]
    
    def items(self) -> List[Tuple[str, Any]]:
        """
        获取所有键值对
        
        Returns:
            List[Tuple[str, Any]]: 键值对列表
        """
        with self._lock:
            self._cleanup_expired()
            return [(key, item.value) for key, item in self._cache.items()]
    
    def size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            int: 当前条目数
        """
        with self._lock:
            return len(self._cache)
    
    def is_full(self) -> bool:
        """
        检查是否已满
        
        Returns:
            bool: 是否已满
        """
        return self.size() >= self._max_size
    
    def is_empty(self) -> bool:
        """
        检查是否为空
        
        Returns:
            bool: 是否为空
        """
        return self.size() == 0
    
    # =====================================================================
    # 统计信息
    # =====================================================================
    
    def get_stats(self) -> CacheStats:
        """
        获取统计信息
        
        Returns:
            CacheStats: 统计信息
        """
        with self._lock:
            self._stats.size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations,
                size=self._stats.size,
                max_size=self._max_size,
            )
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats.hits = 0
            self._stats.misses = 0
            self._stats.evictions = 0
            self._stats.expirations = 0
    
    # =====================================================================
    # 缓存项信息
    # =====================================================================
    
    def get_item_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存项信息
        
        Args:
            key: 键
            
        Returns:
            Optional[Dict[str, Any]]: 缓存项信息
        """
        with self._lock:
            item = self._cache.get(key)
            if item is None or item.is_expired():
                return None
            
            return {
                "key": item.key,
                "created_at": item.created_at.isoformat(),
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                "access_count": item.access_count,
                "last_accessed": item.last_accessed.isoformat(),
                "age_seconds": item.get_age_seconds(),
                "idle_seconds": item.get_idle_seconds(),
            }
    
    def get_all_items_info(self) -> List[Dict[str, Any]]:
        """
        获取所有缓存项信息
        
        Returns:
            List[Dict[str, Any]]: 缓存项信息列表
        """
        with self._lock:
            self._cleanup_expired()
            return [
                {
                    "key": item.key,
                    "access_count": item.access_count,
                    "age_seconds": item.get_age_seconds(),
                }
                for item in self._cache.values()
            ]
    
    # =====================================================================
    # TTL管理
    # =====================================================================
    
    def set_ttl(self, key: str, ttl: int) -> bool:
        """
        设置项的TTL
        
        Args:
            key: 键
            ttl: TTL（秒）
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            item = self._cache.get(key)
            if item is None or item.is_expired():
                return False
            
            item.expires_at = datetime.now() + timedelta(seconds=ttl)
            return True
    
    def get_ttl(self, key: str) -> Optional[int]:
        """
        获取项的剩余TTL
        
        Args:
            key: 键
            
        Returns:
            Optional[int]: 剩余秒数，None表示永不过期
        """
        with self._lock:
            item = self._cache.get(key)
            if item is None or item.is_expired():
                return None
            
            if item.expires_at is None:
                return None
            
            remaining = (item.expires_at - datetime.now()).total_seconds()
            return max(0, int(remaining))
    
    def persist(self, key: str) -> bool:
        """
        移除项的TTL（设为永不过期）
        
        Args:
            key: 键
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            item = self._cache.get(key)
            if item is None or item.is_expired():
                return False
            
            item.expires_at = None
            return True
    
    # =====================================================================
    # 上下文管理器支持
    # =====================================================================
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.clear()
        return False
    
    def __repr__(self) -> str:
        return f"ShortTermCache(size={self.size()}/{self._max_size})"
    
    def __len__(self) -> int:
        return self.size()
    
    def __contains__(self, key: str) -> bool:
        return self.exists(key)


# =============================================================================
# 4. 模块级缓存管理器 (Module Cache Manager)
# =============================================================================

class ModuleCacheManager:
    """
    模块级缓存管理器
    
    为每个模块提供独立的缓存空间
    """
    
    def __init__(
        self,
        max_size_per_module: int = 100,
        default_ttl: Optional[int] = 300,
    ):
        """
        初始化
        
        Args:
            max_size_per_module: 每个模块的最大缓存条目数
            default_ttl: 默认TTL（秒）
        """
        self._max_size_per_module = max_size_per_module
        self._default_ttl = default_ttl
        self._caches: Dict[ModuleID, ShortTermCache] = {}
        self._lock = threading.RLock()
    
    def get_cache(self, module_id: ModuleID) -> ShortTermCache:
        """
        获取模块的缓存
        
        Args:
            module_id: 模块ID
            
        Returns:
            ShortTermCache: 缓存实例
        """
        with self._lock:
            if module_id not in self._caches:
                self._caches[module_id] = ShortTermCache(
                    max_size=self._max_size_per_module,
                    default_ttl=self._default_ttl,
                )
            return self._caches[module_id]
    
    def remove_cache(self, module_id: ModuleID) -> bool:
        """
        移除模块的缓存
        
        Args:
            module_id: 模块ID
            
        Returns:
            bool: 是否成功
        """
        with self._lock:
            if module_id in self._caches:
                del self._caches[module_id]
                return True
            return False
    
    def clear_all(self) -> int:
        """
        清除所有模块的缓存
        
        Returns:
            int: 清除的模块数
        """
        with self._lock:
            count = len(self._caches)
            for cache in self._caches.values():
                cache.clear()
            self._caches.clear()
            return count
    
    def get_all_module_ids(self) -> List[ModuleID]:
        """
        获取所有有缓存的模块ID
        
        Returns:
            List[ModuleID]: 模块ID列表
        """
        with self._lock:
            return list(self._caches.keys())
    
    def get_total_stats(self) -> Dict[str, Any]:
        """
        获取所有模块的总统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            total_hits = 0
            total_misses = 0
            total_size = 0
            
            for cache in self._caches.values():
                stats = cache.get_stats()
                total_hits += stats.hits
                total_misses += stats.misses
                total_size += stats.size
            
            total = total_hits + total_misses
            hit_rate = total_hits / total if total > 0 else 0.0
            
            return {
                "module_count": len(self._caches),
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_size": total_size,
                "hit_rate": f"{hit_rate:.2%}",
            }


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 数据类
    "CacheItem",
    "CacheStats",
    
    # 缓存
    "ShortTermCache",
    
    # 模块缓存管理器
    "ModuleCacheManager",
]
