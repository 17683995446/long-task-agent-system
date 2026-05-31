"""
阶段12测试：长期持久化存储测试
Test Stage 12: Long-Term Storage Tests

测试范围：
1. DataSerializer序列化/反序列化
2. StorageMetadata元数据
3. StorageResult操作结果
4. LongTermStorage核心功能
5. 模块级隔离存储
6. 快照存储
7. 数据完整性校验
8. 原子写入安全性
"""

import unittest
import tempfile
import shutil
import json
import threading

import sys
sys.path.insert(0, '/workspace')

from state.long_term_storage import (
    StorageFormat,
    StorageMetadata,
    StorageResult,
    DataSerializer,
    LongTermStorage,
)
from core_types.core_types import ModuleID


# =============================================================================
# 1. DataSerializer测试
# =============================================================================

class TestDataSerializer(unittest.TestCase):
    """测试数据序列化器"""

    def test_serialize_dict(self):
        """测试字典序列化"""
        data = {"key": "value", "number": 42}
        raw = DataSerializer.serialize(data)

        self.assertIsInstance(raw, bytes)
        self.assertIn(b"key", raw)

    def test_deserialize(self):
        """测试反序列化"""
        original = {"name": "test", "items": [1, 2, 3]}
        raw = DataSerializer.serialize(original)
        result = DataSerializer.deserialize(raw)

        self.assertEqual(result, original)

    def test_serialize_deserialize_roundtrip(self):
        """测试序列化-反序列化往返"""
        original = {
            "string": "hello",
            "int": 123,
            "float": 3.14,
            "bool": True,
            "null": None,
            "nested": {"a": 1},
            "list": [1, 2, 3],
        }
        raw = DataSerializer.serialize(original)
        result = DataSerializer.deserialize(raw)

        self.assertEqual(result, original)

    def test_compute_checksum(self):
        """测试校验和计算"""
        data1 = b"hello world"
        data2 = b"hello world"
        data3 = b"hello different"

        checksum1 = DataSerializer.compute_checksum(data1)
        checksum2 = DataSerializer.compute_checksum(data2)
        checksum3 = DataSerializer.compute_checksum(data3)

        # 相同数据产生相同校验和
        self.assertEqual(checksum1, checksum2)
        # 不同数据产生不同校验和
        self.assertNotEqual(checksum1, checksum3)
        # 校验和为64位十六进制字符串
        self.assertEqual(len(checksum1), 64)

    def test_validate_checksum(self):
        """测试校验和验证"""
        data = b"test data"
        checksum = DataSerializer.compute_checksum(data)

        self.assertTrue(DataSerializer.validate_checksum(data, checksum))
        self.assertFalse(DataSerializer.validate_checksum(data, "wrong_checksum"))


# =============================================================================
# 2. StorageMetadata测试
# =============================================================================

class TestStorageMetadata(unittest.TestCase):
    """测试存储元数据"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        meta = StorageMetadata(
            module_id="module_001",
            task_id="task_001",
            version="1.0",
        )

        self.assertEqual(meta.module_id, "module_001")
        self.assertEqual(meta.version, "1.0")

    def test_metadata_to_dict(self):
        """测试元数据转字典"""
        meta = StorageMetadata(
            module_id="module_001",
            checksum="abc123",
            size_bytes=1024,
        )
        data = meta.to_dict()

        self.assertEqual(data["module_id"], "module_001")
        self.assertEqual(data["checksum"], "abc123")
        self.assertEqual(data["size_bytes"], 1024)

    def test_metadata_from_dict(self):
        """测试从字典创建元数据"""
        data = {
            "module_id": "module_001",
            "task_id": "task_001",
            "checksum": "abc123",
            "size_bytes": 2048,
            "version": "1.0",
            "format": "json",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        meta = StorageMetadata.from_dict(data)

        self.assertEqual(meta.module_id, "module_001")
        self.assertEqual(meta.size_bytes, 2048)


# =============================================================================
# 3. StorageResult测试
# =============================================================================

class TestStorageResult(unittest.TestCase):
    """测试存储操作结果"""

    def test_ok_result(self):
        """测试成功结果"""
        result = StorageResult.ok(path="/tmp/test.json", size_bytes=100, checksum="abc")

        self.assertTrue(result.success)
        self.assertEqual(result.message, "操作成功")
        self.assertEqual(result.path, "/tmp/test.json")
        self.assertEqual(result.size_bytes, 100)
        self.assertIsNotNone(result.timestamp)

    def test_fail_result(self):
        """测试失败结果"""
        result = StorageResult.fail("文件不存在")

        self.assertFalse(result.success)
        self.assertEqual(result.message, "文件不存在")


# =============================================================================
# 4. LongTermStorage核心测试
# =============================================================================

class TestLongTermStorage(unittest.TestCase):
    """测试长期持久化存储"""

    def setUp(self):
        """每个测试前创建临时存储目录"""
        self.temp_dir = tempfile.mkdtemp(prefix="lts_test_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)

    def tearDown(self):
        """每个测试后清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directory(self):
        """测试初始化创建目录"""
        self.assertTrue(self.storage._storage_root.exists())
        self.assertTrue(
            (self.storage._storage_root / "metadata.json").exists()
        )

    def test_save_and_load(self):
        """测试基本存取"""
        data = {"name": "test", "value": 42}
        result = self.storage.save("test_key", data)

        self.assertTrue(result.success)

        loaded, load_result = self.storage.load("test_key")
        self.assertTrue(load_result.success)
        self.assertEqual(loaded, data)

    def test_load_nonexistent(self):
        """测试加载不存在的数据"""
        loaded, result = self.storage.load("nonexistent")

        self.assertFalse(result.success)
        self.assertIsNone(loaded)

    def test_save_overwrite(self):
        """测试覆盖保存"""
        self.storage.save("key1", {"version": 1})
        self.storage.save("key1", {"version": 2})

        loaded, _ = self.storage.load("key1")
        self.assertEqual(loaded["version"], 2)

    def test_delete(self):
        """测试删除"""
        self.storage.save("key1", {"data": "test"})
        result = self.storage.delete("key1")

        self.assertTrue(result.success)
        self.assertFalse(self.storage.exists("key1"))

    def test_delete_nonexistent(self):
        """测试删除不存在的数据"""
        result = self.storage.delete("nonexistent")
        self.assertFalse(result.success)

    def test_exists(self):
        """测试存在性检查"""
        self.assertFalse(self.storage.exists("key1"))

        self.storage.save("key1", {"data": "test"})
        self.assertTrue(self.storage.exists("key1"))

    def test_save_complex_data(self):
        """测试保存复杂数据结构"""
        data = {
            "string": "hello",
            "int": 123,
            "float": 3.14,
            "bool": True,
            "null": None,
            "nested": {"a": {"b": {"c": 1}}},
            "list": [1, 2, {"x": "y"}],
        }
        self.storage.save("complex", data)

        loaded, _ = self.storage.load("complex")
        self.assertEqual(loaded, data)

    def test_checksum_validation(self):
        """测试校验和验证"""
        data = {"important": "data"}
        self.storage.save("key1", data)

        # 正常加载应成功
        loaded, result = self.storage.load("key1", validate=True)
        self.assertTrue(result.success)

    def test_checksum_validation_corrupted(self):
        """测试损坏数据的校验"""
        data = {"important": "data"}
        self.storage.save("key1", data)

        # 手动损坏文件
        file_path = self.storage._resolve_path("key1", None, "data")
        with open(file_path, "w") as f:
            f.write('{"corrupted": true}')

        # 加载应失败
        loaded, result = self.storage.load("key1", validate=True)
        self.assertFalse(result.success)

    def test_skip_validation(self):
        """测试跳过校验"""
        data = {"important": "data"}
        self.storage.save("key1", data)

        # 损坏文件
        file_path = self.storage._resolve_path("key1", None, "data")
        with open(file_path, "w") as f:
            f.write('{"corrupted": true}')

        # 跳过校验应能加载
        loaded, result = self.storage.load("key1", validate=False)
        self.assertTrue(result.success)
        self.assertEqual(loaded, {"corrupted": True})


# =============================================================================
# 5. 批量操作测试
# =============================================================================

class TestBatchOperations(unittest.TestCase):
    """测试批量操作"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lts_batch_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_many(self):
        """测试批量保存"""
        items = {
            "key1": {"value": 1},
            "key2": {"value": 2},
            "key3": {"value": 3},
        }
        results = self.storage.save_many(items)

        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r.success)

    def test_load_many(self):
        """测试批量加载"""
        items = {
            "key1": {"value": 1},
            "key2": {"value": 2},
        }
        self.storage.save_many(items)

        result = self.storage.load_many(["key1", "key2", "nonexistent"])

        self.assertEqual(len(result), 2)
        self.assertIn("key1", result)
        self.assertIn("key2", result)
        self.assertNotIn("nonexistent", result)

    def test_list_keys(self):
        """测试列出键"""
        self.storage.save("key1", {"v": 1})
        self.storage.save("key2", {"v": 2})

        keys = self.storage.list_keys()

        self.assertIn("key1", keys)
        self.assertIn("key2", keys)


# =============================================================================
# 6. 模块级隔离测试
# =============================================================================

class TestModuleIsolation(unittest.TestCase):
    """测试模块级隔离存储"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lts_module_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)
        self.module1 = ModuleID("module_001")
        self.module2 = ModuleID("module_002")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_module_state_save_load(self):
        """测试模块状态存取"""
        state = {"status": "running", "progress": 50}
        result = self.storage.save_module_state(self.module1, state)

        self.assertTrue(result.success)

        loaded, load_result = self.storage.load_module_state(self.module1)
        self.assertTrue(load_result.success)
        self.assertEqual(loaded, state)

    def test_module_config_save_load(self):
        """测试模块配置存取"""
        config = {"timeout": 30, "retries": 3}
        result = self.storage.save_module_config(self.module1, config)

        self.assertTrue(result.success)

        loaded, _ = self.storage.load_module_config(self.module1)
        self.assertEqual(loaded, config)

    def test_module_isolation(self):
        """测试模块间数据隔离"""
        self.storage.save("key1", {"module": "one"}, self.module1)
        self.storage.save("key1", {"module": "two"}, self.module2)

        data1, _ = self.storage.load("key1", self.module1)
        data2, _ = self.storage.load("key1", self.module2)

        self.assertEqual(data1["module"], "one")
        self.assertEqual(data2["module"], "two")

    def test_module_data_not_visible_globally(self):
        """测试模块数据对全局不可见"""
        self.storage.save("key1", {"secret": True}, self.module1)

        # 全局加载应找不到
        loaded, result = self.storage.load("key1", module_id=None)
        self.assertFalse(result.success)

    def test_delete_module_storage(self):
        """测试删除模块存储"""
        self.storage.save_module_state(self.module1, {"status": "active"})
        self.storage.save("key1", {"data": 1}, self.module1)

        result = self.storage.delete_module_storage(self.module1)
        self.assertTrue(result.success)

        # 模块数据应全部清除
        _, state_result = self.storage.load_module_state(self.module1)
        self.assertFalse(state_result.success)

    def test_list_keys_with_module(self):
        """测试模块级键列表"""
        self.storage.save("key1", {"v": 1}, self.module1)
        self.storage.save("key2", {"v": 2}, self.module1)

        keys = self.storage.list_keys(self.module1)
        self.assertIn("key1", keys)
        self.assertIn("key2", keys)


# =============================================================================
# 7. 快照操作测试
# =============================================================================

class TestSnapshotOperations(unittest.TestCase):
    """测试快照操作"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lts_snap_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_snapshot(self):
        """测试快照存取"""
        snapshot = {
            "snapshot_id": "snap_001",
            "timestamp": "2026-01-01T00:00:00",
            "state": {"progress": 75},
        }
        result = self.storage.save_snapshot("snap_001", snapshot)

        self.assertTrue(result.success)

        loaded, _ = self.storage.load_snapshot("snap_001")
        self.assertEqual(loaded["snapshot_id"], "snap_001")
        self.assertEqual(loaded["state"]["progress"], 75)

    def test_list_snapshots(self):
        """测试列出快照"""
        self.storage.save_snapshot("snap_001", {"id": 1})
        self.storage.save_snapshot("snap_002", {"id": 2})

        snapshots = self.storage.list_snapshots()

        self.assertIn("snap_001", snapshots)
        self.assertIn("snap_002", snapshots)

    def test_delete_snapshot(self):
        """测试删除快照"""
        self.storage.save_snapshot("snap_001", {"id": 1})
        result = self.storage.delete_snapshot("snap_001")

        self.assertTrue(result.success)
        self.assertNotIn("snap_001", self.storage.list_snapshots())


# =============================================================================
# 8. 存储管理测试
# =============================================================================

class TestStorageManagement(unittest.TestCase):
    """测试存储管理功能"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lts_mgmt_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_storage_size(self):
        """测试获取存储大小"""
        self.storage.save("key1", {"data": "x" * 100})

        size = self.storage.get_storage_size()
        self.assertGreater(size, 0)

    def test_get_module_count(self):
        """测试获取模块数量"""
        self.storage.save("key1", {"v": 1}, ModuleID("module_001"))
        self.storage.save("key1", {"v": 2}, ModuleID("module_002"))

        count = self.storage.get_module_count()
        self.assertEqual(count, 2)

    def test_clear_all(self):
        """测试清空所有存储"""
        self.storage.save("key1", {"v": 1})
        self.storage.save("key2", {"v": 2})

        result = self.storage.clear_all()
        self.assertTrue(result.success)

        self.assertFalse(self.storage.exists("key1"))
        self.assertFalse(self.storage.exists("key2"))

    def test_cleanup_orphaned_files(self):
        """测试清理孤立文件"""
        # 正常保存一个文件
        self.storage.save("key1", {"v": 1})

        # 创建一个损坏的文件
        corrupted = self.storage._storage_root / "corrupted.json"
        corrupted.write_text("not valid json {{{")

        cleaned = self.storage.cleanup_orphaned_files()
        self.assertEqual(cleaned, 1)
        self.assertFalse(corrupted.exists())


# =============================================================================
# 9. 线程安全测试
# =============================================================================

class TestThreadSafety(unittest.TestCase):
    """测试线程安全性"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lts_thread_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_save(self):
        """测试并发写入"""
        errors = []

        def writer(thread_id):
            try:
                for i in range(50):
                    self.storage.save(
                        f"t{thread_id}_key{i}",
                        {"thread": thread_id, "i": i},
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)

    def test_concurrent_read_write(self):
        """测试并发读写"""
        # 预填充
        for i in range(20):
            self.storage.save(f"key{i}", {"value": i})

        errors = []

        def writer():
            try:
                for i in range(20):
                    self.storage.save(f"key{i}", {"value": i * 2})
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(20):
                    self.storage.load(f"key{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)


# =============================================================================
# 10. 集成测试
# =============================================================================

class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="lts_integ_")
        self.storage = LongTermStorage(storage_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_module_lifecycle(self):
        """测试模块完整生命周期"""
        module = ModuleID("task_001_control")

        # 1. 保存配置
        config = {"timeout": 60, "max_retries": 5}
        self.storage.save_module_config(module, config)

        # 2. 保存初始状态
        state = {"status": "initialized", "progress": 0}
        self.storage.save_module_state(module, state)

        # 3. 保存中间数据
        self.storage.save("intermediate", {"step": 1, "result": "ok"}, module)

        # 4. 创建检查点快照
        snapshot = {"state": state, "data": {"step": 1}}
        self.storage.save_snapshot("checkpoint_001", snapshot)

        # 5. 更新状态
        updated_state = {"status": "running", "progress": 50}
        self.storage.save_module_state(module, updated_state)

        # 6. 验证所有数据
        loaded_config, _ = self.storage.load_module_config(module)
        self.assertEqual(loaded_config["timeout"], 60)

        loaded_state, _ = self.storage.load_module_state(module)
        self.assertEqual(loaded_state["progress"], 50)

        loaded_data, _ = self.storage.load("intermediate", module)
        self.assertEqual(loaded_data["step"], 1)

        loaded_snap, _ = self.storage.load_snapshot("checkpoint_001")
        self.assertEqual(loaded_snap["state"]["progress"], 0)

        # 7. 清理
        self.storage.delete_module_storage(module)
        self.storage.delete_snapshot("checkpoint_001")

        _, state_result = self.storage.load_module_state(module)
        self.assertFalse(state_result.success)


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
