"""
阶段11测试：短期状态缓存测试
Test Stage 11: Short-Term Cache Tests

测试范围：
1. CacheItem基本功能
2. CacheStats统计信息
3. ShortTermCache核心功能
4. ModuleCacheManager模块隔离
5. 线程安全性
6. TTL和LRU淘汰策略
"""

import unittest
import time
import threading
from datetime import datetime, timedelta

import sys
sys.path.insert(0, '/workspace')

from state.short_term_cache import (
    CacheItem,
    CacheStats,
    ShortTermCache,
    ModuleCacheManager,
)
from core_types.core_types import ModuleID, ModuleType


# =============================================================================
# 1. CacheItem测试
# =============================================================================

class TestCacheItem(unittest.TestCase):
    """测试缓存项"""
    
    def test_cache_item_creation(self):
        """测试缓存项创建"""
        item = CacheItem(key="test_key", value="test_value")
        
        self.assertEqual(item.key, "test_key")
        self.assertEqual(item.value, "test_value")
        self.assertEqual(item.access_count, 0)
        self.assertIsNone(item.expires_at)
    
    def test_cache_item_with_ttl(self):
        """测试带TTL的缓存项"""
        expires_at = datetime.now() + timedelta(seconds=60)
        item = CacheItem(
            key="test_key",
            value="test_value",
            expires_at=expires_at
        )
        
        self.assertIsNotNone(item.expires_at)
        self.assertFalse(item.is_expired())
    
    def test_cache_item_expired(self):
        """测试过期检测"""
        expires_at = datetime.now() - timedelta(seconds=1)
        item = CacheItem(
            key="test_key",
            value="test_value",
            expires_at=expires_at
        )
        
        self.assertTrue(item.is_expired())
    
    def test_cache_item_touch(self):
        """测试访问更新"""
        item = CacheItem(key="test_key", value="test_value")
        
        original_accessed = item.last_accessed
        time.sleep(0.01)
        item.touch()
        
        self.assertEqual(item.access_count, 1)
        self.assertGreater(item.last_accessed, original_accessed)
    
    def test_cache_item_age(self):
        """测试存在时长计算"""
        item = CacheItem(key="test_key", value="test_value")
        time.sleep(0.1)
        
        age = item.get_age_seconds()
        self.assertGreaterEqual(age, 0.1)
    
    def test_cache_item_idle(self):
        """测试空闲时长计算"""
        item = CacheItem(key="test_key", value="test_value")
        time.sleep(0.1)
        
        idle = item.get_idle_seconds()
        self.assertGreaterEqual(idle, 0.1)


# =============================================================================
# 2. CacheStats测试
# =============================================================================

class TestCacheStats(unittest.TestCase):
    """测试缓存统计"""
    
    def test_stats_initial(self):
        """测试初始统计"""
        stats = CacheStats(max_size=100)
        
        self.assertEqual(stats.hits, 0)
        self.assertEqual(stats.misses, 0)
        self.assertEqual(stats.evictions, 0)
        self.assertEqual(stats.expirations, 0)
        self.assertEqual(stats.max_size, 100)
    
    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        stats = CacheStats(hits=80, misses=20)
        
        self.assertAlmostEqual(stats.hit_rate, 0.8, places=2)
        self.assertAlmostEqual(stats.miss_rate, 0.2, places=2)
    
    def test_hit_rate_zero(self):
        """测试零访问时的命中率"""
        stats = CacheStats()
        
        self.assertEqual(stats.hit_rate, 0.0)
        self.assertEqual(stats.miss_rate, 1.0)
    
    def test_stats_to_dict(self):
        """测试转换为字典"""
        stats = CacheStats(hits=80, misses=20, max_size=100)
        data = stats.to_dict()
        
        self.assertEqual(data["hits"], 80)
        self.assertEqual(data["misses"], 20)
        self.assertEqual(data["max_size"], 100)
        self.assertEqual(data["hit_rate"], "80.00%")


# =============================================================================
# 3. ShortTermCache测试
# =============================================================================

class TestShortTermCache(unittest.TestCase):
    """测试短期缓存"""
    
    def setUp(self):
        """每个测试前创建新缓存"""
        self.cache = ShortTermCache(max_size=100, default_ttl=300)
    
    def tearDown(self):
        """每个测试后清理缓存"""
        self.cache.clear()
    
    def test_set_and_get(self):
        """测试基本存取"""
        self.cache.set("key1", "value1")
        value = self.cache.get("key1")
        
        self.assertEqual(value, "value1")
    
    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        value = self.cache.get("nonexistent")
        
        self.assertIsNone(value)
    
    def test_get_with_default(self):
        """测试带默认值的获取"""
        value = self.cache.get("nonexistent", default="default_value")
        
        self.assertEqual(value, "default_value")
    
    def test_update_existing_key(self):
        """测试更新已存在的键"""
        self.cache.set("key1", "value1")
        self.cache.set("key1", "value2")
        value = self.cache.get("key1")
        
        self.assertEqual(value, "value2")
    
    def test_delete(self):
        """测试删除"""
        self.cache.set("key1", "value1")
        result = self.cache.delete("key1")
        
        self.assertTrue(result)
        self.assertIsNone(self.cache.get("key1"))
    
    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        result = self.cache.delete("nonexistent")
        
        self.assertFalse(result)
    
    def test_exists(self):
        """测试存在性检查"""
        self.cache.set("key1", "value1")
        
        self.assertTrue(self.cache.exists("key1"))
        self.assertFalse(self.cache.exists("nonexistent"))
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        self.cache.set("key1", "value1", ttl=0.1)
        
        # 立即获取应该存在
        self.assertEqual(self.cache.get("key1"), "value1")
        
        # 等待过期
        time.sleep(0.2)
        
        # 过期后应该返回None
        self.assertIsNone(self.cache.get("key1"))
    
    def test_lru_eviction(self):
        """测试LRU淘汰"""
        cache = ShortTermCache(max_size=3, default_ttl=None)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 访问key1使其成为最近使用
        cache.get("key1")
        
        # 添加第4个，应该淘汰key2（最久未使用）
        cache.set("key4", "value4")
        
        self.assertIsNotNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))  # 被淘汰
        self.assertIsNotNone(cache.get("key3"))
        self.assertIsNotNone(cache.get("key4"))
    
    def test_size_and_empty(self):
        """测试大小和空检查"""
        self.assertEqual(self.cache.size(), 0)
        self.assertTrue(self.cache.is_empty())
        
        self.cache.set("key1", "value1")
        
        self.assertEqual(self.cache.size(), 1)
        self.assertFalse(self.cache.is_empty())
    
    def test_is_full(self):
        """测试满检查"""
        cache = ShortTermCache(max_size=2)
        
        self.assertFalse(cache.is_full())
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        self.assertTrue(cache.is_full())
    
    def test_clear(self):
        """测试清空"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        count = self.cache.clear()
        
        self.assertEqual(count, 2)
        self.assertEqual(self.cache.size(), 0)
    
    def test_set_many_and_get_many(self):
        """测试批量操作"""
        items = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        
        self.cache.set_many(items)
        
        result = self.cache.get_many(["key1", "key2", "nonexistent"])
        
        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["key2"], "value2")
        self.assertNotIn("nonexistent", result)
    
    def test_delete_many(self):
        """测试批量删除"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")
        
        count = self.cache.delete_many(["key1", "key2", "nonexistent"])
        
        self.assertEqual(count, 2)
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        self.assertIsNotNone(self.cache.get("key3"))
    
    def test_keys_values_items(self):
        """测试获取键值对"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        keys = self.cache.keys()
        values = self.cache.values()
        items = self.cache.items()
        
        self.assertIn("key1", keys)
        self.assertIn("key2", keys)
        self.assertIn("value1", values)
        self.assertIn("value2", values)
        self.assertIn(("key1", "value1"), items)
        self.assertIn(("key2", "value2"), items)
    
    def test_stats_tracking(self):
        """测试统计信息跟踪"""
        self.cache.set("key1", "value1")
        
        # 命中
        self.cache.get("key1")
        self.cache.get("key1")
        
        # 未命中
        self.cache.get("nonexistent")
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats.hits, 2)
        self.assertEqual(stats.misses, 1)
        self.assertEqual(stats.hit_rate, 2/3)
    
    def test_reset_stats(self):
        """测试重置统计"""
        self.cache.set("key1", "value1")
        self.cache.get("key1")
        
        self.cache.reset_stats()
        stats = self.cache.get_stats()
        
        self.assertEqual(stats.hits, 0)
        self.assertEqual(stats.misses, 0)
    
    def test_get_item_info(self):
        """测试获取项信息"""
        self.cache.set("key1", "value1")
        self.cache.get("key1")
        
        info = self.cache.get_item_info("key1")
        
        self.assertIsNotNone(info)
        self.assertEqual(info["key"], "key1")
        self.assertEqual(info["access_count"], 1)
    
    def test_set_and_get_ttl(self):
        """测试TTL管理"""
        self.cache.set("key1", "value1", ttl=60)
        
        remaining = self.cache.get_ttl("key1")
        
        self.assertIsNotNone(remaining)
        self.assertLessEqual(remaining, 60)
        self.assertGreater(remaining, 55)
    
    def test_persist(self):
        """测试持久化（移除TTL）"""
        self.cache.set("key1", "value1", ttl=60)
        
        result = self.cache.persist("key1")
        ttl = self.cache.get_ttl("key1")
        
        self.assertTrue(result)
        self.assertIsNone(ttl)
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with ShortTermCache() as cache:
            cache.set("key1", "value1")
            self.assertEqual(cache.get("key1"), "value1")
        
        # 退出后缓存应该被清空
        # 这里只是测试不抛出异常
    
    def test_contains(self):
        """测试in操作符"""
        self.cache.set("key1", "value1")
        
        self.assertIn("key1", self.cache)
        self.assertNotIn("nonexistent", self.cache)
    
    def test_len(self):
        """测试len操作符"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.assertEqual(len(self.cache), 2)


# =============================================================================
# 4. 线程安全测试
# =============================================================================

class TestThreadSafety(unittest.TestCase):
    """测试线程安全性"""
    
    def test_concurrent_set(self):
        """测试并发写入"""
        cache = ShortTermCache(max_size=1000)
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(100):
                    cache.set(f"thread{thread_id}_key{i}", f"value{i}")
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
        self.assertEqual(cache.size(), 1000)
    
    def test_concurrent_get_set(self):
        """测试并发读写"""
        cache = ShortTermCache()
        
        # 预填充数据
        for i in range(100):
            cache.set(f"key{i}", f"value{i}")
        
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    cache.set(f"key{i}", f"new_value{i}")
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for i in range(100):
                    cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)
        
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)


# =============================================================================
# 5. ModuleCacheManager测试
# =============================================================================

class TestModuleCacheManager(unittest.TestCase):
    """测试模块缓存管理器"""
    
    def setUp(self):
        """每个测试前创建新管理器"""
        self.manager = ModuleCacheManager(max_size_per_module=50, default_ttl=300)
    
    def tearDown(self):
        """每个测试后清理"""
        self.manager.clear_all()
    
    def test_get_cache_for_module(self):
        """测试获取模块缓存"""
        module_id = ModuleID("module_001")
        
        cache = self.manager.get_cache(module_id)
        
        self.assertIsInstance(cache, ShortTermCache)
        
        # 再次获取应该是同一个实例
        cache2 = self.manager.get_cache(module_id)
        self.assertIs(cache, cache2)
    
    def test_module_isolation(self):
        """测试模块间隔离"""
        module1 = ModuleID("module_001")
        module2 = ModuleID("module_002")
        
        cache1 = self.manager.get_cache(module1)
        cache2 = self.manager.get_cache(module2)
        
        cache1.set("key1", "module1_value")
        cache2.set("key1", "module2_value")
        
        self.assertEqual(cache1.get("key1"), "module1_value")
        self.assertEqual(cache2.get("key1"), "module2_value")
    
    def test_remove_cache(self):
        """测试移除模块缓存"""
        module_id = ModuleID("module_001")
        
        self.manager.get_cache(module_id).set("key1", "value1")
        result = self.manager.remove_cache(module_id)
        
        self.assertTrue(result)
        
        # 重新获取应该是新实例
        cache = self.manager.get_cache(module_id)
        self.assertIsNone(cache.get("key1"))
    
    def test_clear_all(self):
        """测试清除所有缓存"""
        module1 = ModuleID("module_001")
        module2 = ModuleID("module_002")
        
        self.manager.get_cache(module1).set("key1", "value1")
        self.manager.get_cache(module2).set("key1", "value1")
        
        count = self.manager.clear_all()
        
        self.assertEqual(count, 2)
    
    def test_get_all_module_ids(self):
        """测试获取所有模块ID"""
        module1 = ModuleID("module_001")
        module2 = ModuleID("module_002")
        
        self.manager.get_cache(module1)
        self.manager.get_cache(module2)
        
        ids = self.manager.get_all_module_ids()
        
        self.assertIn(module1, ids)
        self.assertIn(module2, ids)
    
    def test_get_total_stats(self):
        """测试获取总统计信息"""
        module1 = ModuleID("module_001")
        module2 = ModuleID("module_002")
        
        cache1 = self.manager.get_cache(module1)
        cache2 = self.manager.get_cache(module2)
        
        cache1.set("key1", "value1")
        cache1.get("key1")
        cache1.get("nonexistent")
        
        cache2.set("key1", "value1")
        cache2.get("key1")
        
        stats = self.manager.get_total_stats()
        
        self.assertEqual(stats["module_count"], 2)
        self.assertEqual(stats["total_hits"], 2)
        self.assertEqual(stats["total_misses"], 1)


# =============================================================================
# 6. 集成测试
# =============================================================================

class TestCacheIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 创建模块缓存管理器
        manager = ModuleCacheManager(max_size_per_module=100)
        
        # 创建模块ID
        control_module = ModuleID("task_001_control")
        execute_module = ModuleID("task_001_execute")
        
        # 获取各自缓存
        control_cache = manager.get_cache(control_module)
        execute_cache = manager.get_cache(execute_module)
        
        # 模拟控制模块存储任务状态
        control_cache.set("task_status", "running")
        control_cache.set("current_stage", 5)
        
        # 模拟执行模块存储中间结果
        execute_cache.set("intermediate_result", {"data": [1, 2, 3]})
        
        # 验证数据隔离
        self.assertEqual(control_cache.get("task_status"), "running")
        self.assertIsNone(execute_cache.get("task_status"))
        
        # 验证统计信息
        control_stats = control_cache.get_stats()
        self.assertEqual(control_stats.size, 2)
        
        # 清理
        manager.clear_all()


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
