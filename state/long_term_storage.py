"""
超长任务Agent树形双生子模块化执行系统 - 长期持久化存储实现
Long-Term Storage Implementation for Long-Task Agent Twin-Module Execution System

阶段12：长期持久化存储实现
遵循原则：图难于其易，为大于其细
核心约束：磁盘持久化，序列化/反序列化，数据完整性校验，模块级隔离
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import json
import hashlib
import threading
import shutil
import os
import tempfile

from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. 存储格式枚举 (Storage Format Enumeration)
# =============================================================================

class StorageFormat(Enum):
    """存储格式枚举"""
    JSON = auto()       # JSON格式
    BINARY = auto()     # 二进制格式（预留）


# =============================================================================
# 2. 存储元数据 (Storage Metadata)
# =============================================================================

@dataclass
class StorageMetadata:
    """
    存储元数据
    记录每次存储的附加信息
    """
    module_id: str = ""
    task_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    version: str = "1.0"
    format: str = "json"
    checksum: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "module_id": self.module_id,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "format": self.format,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorageMetadata":
        """从字典创建"""
        return cls(**data)


# =============================================================================
# 3. 存储操作结果 (Storage Operation Result)
# =============================================================================

@dataclass
class StorageResult:
    """
    存储操作结果
    """
    success: bool = True
    message: str = ""
    path: str = ""
    size_bytes: int = 0
    checksum: str = ""
    timestamp: str = ""

    @classmethod
    def ok(cls, path: str = "", size_bytes: int = 0, checksum: str = "") -> "StorageResult":
        """创建成功结果"""
        return cls(
            success=True,
            message="操作成功",
            path=path,
            size_bytes=size_bytes,
            checksum=checksum,
            timestamp=datetime.now().isoformat(),
        )

    @classmethod
    def fail(cls, message: str) -> "StorageResult":
        """创建失败结果"""
        return cls(
            success=False,
            message=message,
            timestamp=datetime.now().isoformat(),
        )


# =============================================================================
# 4. 数据序列化器 (Data Serializer)
# =============================================================================

class DataSerializer:
    """
    数据序列化器
    负责数据的序列化和反序列化，支持校验和计算
    """

    @staticmethod
    def serialize(data: Any) -> bytes:
        """
        序列化数据为字节

        Args:
            data: 要序列化的数据（须为JSON可序列化类型）

        Returns:
            bytes: 序列化后的字节
        """
        json_str = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        return json_str.encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Any:
        """
        从字节反序列化数据

        Args:
            raw: 字节数据

        Returns:
            Any: 反序列化的数据
        """
        json_str = raw.decode("utf-8")
        return json.loads(json_str)

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        """
        计算数据的SHA256校验和

        Args:
            data: 字节数据

        Returns:
            str: 十六进制校验和
        """
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def validate_checksum(data: bytes, expected: str) -> bool:
        """
        验证数据校验和

        Args:
            data: 字节数据
            expected: 期望的校验和

        Returns:
            bool: 是否匹配
        """
        return DataSerializer.compute_checksum(data) == expected


# =============================================================================
# 5. 长期持久化存储 (Long-Term Storage)
# =============================================================================

class LongTermStorage:
    """
    长期持久化存储

    提供磁盘级别的数据持久化能力，支持：
    1. JSON序列化/反序列化
    2. SHA256数据完整性校验
    3. 模块级存储隔离（每个模块一个子目录）
    4. 线程安全
    5. 原子写入（先写临时文件再重命名）
    6. 版本管理

    目录结构：
        storage_root/
        ├── metadata.json          # 全局元数据
        ├── module_xxx/            # 模块级目录
        │   ├── state.json         # 模块状态
        │   ├── config.json        # 模块配置
        │   └── data/              # 模块数据目录
        │       ├── item_1.json
        │       └── item_2.json
        └── snapshots/             # 快照目录
            └── snap_xxx.json
    """

    def __init__(
        self,
        storage_root: str = "./storage",
        version: str = "1.0",
    ):
        """
        初始化长期存储

        Args:
            storage_root: 存储根目录路径
            version: 存储版本号
        """
        self._storage_root = Path(storage_root)
        self._version = version
        self._lock = threading.RLock()

        # 确保根目录存在
        self._storage_root.mkdir(parents=True, exist_ok=True)

        # 初始化全局元数据
        self._init_global_metadata()

    # =====================================================================
    # 初始化
    # =====================================================================

    def _init_global_metadata(self) -> None:
        """初始化全局元数据文件"""
        meta_path = self._storage_root / "metadata.json"
        if not meta_path.exists():
            meta = {
                "version": self._version,
                "created_at": datetime.now().isoformat(),
                "modules": [],
            }
            self._write_json_file(meta_path, meta)

    # =====================================================================
    # 核心存储操作
    # =====================================================================

    def save(
        self,
        key: str,
        data: Any,
        module_id: Optional[ModuleID] = None,
        category: str = "data",
    ) -> StorageResult:
        """
        保存数据到磁盘

        Args:
            key: 数据键
            data: 要保存的数据（须为JSON可序列化类型）
            module_id: 模块ID（可选，用于隔离存储）
            category: 数据分类（data/config/state）

        Returns:
            StorageResult: 操作结果
        """
        with self._lock:
            try:
                # 确定存储路径
                file_path = self._resolve_path(key, module_id, category)

                # 序列化
                raw = DataSerializer.serialize(data)
                checksum = DataSerializer.compute_checksum(raw)

                # 原子写入
                self._atomic_write(file_path, raw)

                # 写入校验和元数据文件
                self._write_file_metadata(file_path, checksum, len(raw))

                # 更新模块元数据
                self._update_module_metadata(module_id, key, category, checksum, len(raw))

                return StorageResult.ok(
                    path=str(file_path),
                    size_bytes=len(raw),
                    checksum=checksum,
                )
            except Exception as e:
                return StorageResult.fail(f"保存失败: {str(e)}")

    def load(
        self,
        key: str,
        module_id: Optional[ModuleID] = None,
        category: str = "data",
        validate: bool = True,
    ) -> Tuple[Any, StorageResult]:
        """
        从磁盘加载数据

        Args:
            key: 数据键
            module_id: 模块ID
            category: 数据分类
            validate: 是否校验数据完整性

        Returns:
            Tuple[Any, StorageResult]: (数据, 操作结果)
        """
        with self._lock:
            try:
                file_path = self._resolve_path(key, module_id, category)

                if not file_path.exists():
                    return None, StorageResult.fail(f"文件不存在: {key}")

                # 读取文件
                raw = file_path.read_bytes()

                # 校验完整性
                if validate:
                    meta = self._get_stored_metadata(file_path)
                    if meta and meta.checksum:
                        if not DataSerializer.validate_checksum(raw, meta.checksum):
                            return None, StorageResult.fail(
                                f"数据完整性校验失败: {key}"
                            )

                # 反序列化
                data = DataSerializer.deserialize(raw)

                return data, StorageResult.ok(
                    path=str(file_path),
                    size_bytes=len(raw),
                )
            except Exception as e:
                return None, StorageResult.fail(f"加载失败: {str(e)}")

    def delete(
        self,
        key: str,
        module_id: Optional[ModuleID] = None,
        category: str = "data",
    ) -> StorageResult:
        """
        删除磁盘数据

        Args:
            key: 数据键
            module_id: 模块ID
            category: 数据分类

        Returns:
            StorageResult: 操作结果
        """
        with self._lock:
            try:
                file_path = self._resolve_path(key, module_id, category)

                if not file_path.exists():
                    return StorageResult.fail(f"文件不存在: {key}")

                file_path.unlink()
                return StorageResult.ok(path=str(file_path))
            except Exception as e:
                return StorageResult.fail(f"删除失败: {str(e)}")

    def exists(
        self,
        key: str,
        module_id: Optional[ModuleID] = None,
        category: str = "data",
    ) -> bool:
        """
        检查数据是否存在

        Args:
            key: 数据键
            module_id: 模块ID
            category: 数据分类

        Returns:
            bool: 是否存在
        """
        with self._lock:
            file_path = self._resolve_path(key, module_id, category)
            return file_path.exists()

    # =====================================================================
    # 批量操作
    # =====================================================================

    def save_many(
        self,
        items: Dict[str, Any],
        module_id: Optional[ModuleID] = None,
        category: str = "data",
    ) -> List[StorageResult]:
        """
        批量保存

        Args:
            items: 键值对字典
            module_id: 模块ID
            category: 数据分类

        Returns:
            List[StorageResult]: 操作结果列表
        """
        results = []
        for key, data in items.items():
            results.append(self.save(key, data, module_id, category))
        return results

    def load_many(
        self,
        keys: List[str],
        module_id: Optional[ModuleID] = None,
        category: str = "data",
    ) -> Dict[str, Any]:
        """
        批量加载

        Args:
            keys: 键列表
            module_id: 模块ID
            category: 数据分类

        Returns:
            Dict[str, Any]: 成功加载的键值对
        """
        result = {}
        for key in keys:
            data, res = self.load(key, module_id, category)
            if res.success and data is not None:
                result[key] = data
        return result

    def list_keys(
        self,
        module_id: Optional[ModuleID] = None,
        category: str = "data",
    ) -> List[str]:
        """
        列出指定分类下的所有键

        Args:
            module_id: 模块ID
            category: 数据分类

        Returns:
            List[str]: 键列表
        """
        with self._lock:
            dir_path = self._resolve_category_dir(module_id, category)
            if not dir_path.exists():
                return []

            return [
                f.stem for f in dir_path.iterdir()
                if f.is_file() and f.suffix == ".json"
            ]

    # =====================================================================
    # 模块级操作
    # =====================================================================

    def save_module_state(
        self,
        module_id: ModuleID,
        state: Dict[str, Any],
    ) -> StorageResult:
        """
        保存模块状态

        Args:
            module_id: 模块ID
            state: 模块状态字典

        Returns:
            StorageResult: 操作结果
        """
        return self.save("state", state, module_id, category="state")

    def load_module_state(
        self,
        module_id: ModuleID,
    ) -> Tuple[Optional[Dict[str, Any]], StorageResult]:
        """
        加载模块状态

        Args:
            module_id: 模块ID

        Returns:
            Tuple[Optional[Dict], StorageResult]: (状态字典, 操作结果)
        """
        return self.load("state", module_id, category="state")

    def save_module_config(
        self,
        module_id: ModuleID,
        config: Dict[str, Any],
    ) -> StorageResult:
        """
        保存模块配置

        Args:
            module_id: 模块ID
            config: 配置字典

        Returns:
            StorageResult: 操作结果
        """
        return self.save("config", config, module_id, category="config")

    def load_module_config(
        self,
        module_id: ModuleID,
    ) -> Tuple[Optional[Dict[str, Any]], StorageResult]:
        """
        加载模块配置

        Args:
            module_id: 模块ID

        Returns:
            Tuple[Optional[Dict], StorageResult]: (配置字典, 操作结果)
        """
        return self.load("config", module_id, category="config")

    def delete_module_storage(self, module_id: ModuleID) -> StorageResult:
        """
        删除模块的整个存储目录

        Args:
            module_id: 模块ID

        Returns:
            StorageResult: 操作结果
        """
        with self._lock:
            try:
                module_dir = self._resolve_module_dir(module_id)
                if not module_dir.exists():
                    return StorageResult.fail(f"模块目录不存在: {module_id}")

                shutil.rmtree(module_dir)
                return StorageResult.ok(path=str(module_dir))
            except Exception as e:
                return StorageResult.fail(f"删除模块存储失败: {str(e)}")

    # =====================================================================
    # 快照操作
    # =====================================================================

    def save_snapshot(
        self,
        snapshot_id: str,
        data: Dict[str, Any],
    ) -> StorageResult:
        """
        保存快照

        Args:
            snapshot_id: 快照ID
            data: 快照数据

        Returns:
            StorageResult: 操作结果
        """
        return self.save(snapshot_id, data, category="snapshots")

    def load_snapshot(
        self,
        snapshot_id: str,
    ) -> Tuple[Optional[Dict[str, Any]], StorageResult]:
        """
        加载快照

        Args:
            snapshot_id: 快照ID

        Returns:
            Tuple[Optional[Dict], StorageResult]: (快照数据, 操作结果)
        """
        return self.load(snapshot_id, category="snapshots")

    def list_snapshots(self) -> List[str]:
        """
        列出所有快照ID

        Returns:
            List[str]: 快照ID列表
        """
        return self.list_keys(category="snapshots")

    def delete_snapshot(self, snapshot_id: str) -> StorageResult:
        """
        删除快照

        Args:
            snapshot_id: 快照ID

        Returns:
            StorageResult: 操作结果
        """
        return self.delete(snapshot_id, category="snapshots")

    # =====================================================================
    # 存储管理
    # =====================================================================

    def get_storage_size(self) -> int:
        """
        获取存储总大小（字节）

        Returns:
            int: 总字节数
        """
        with self._lock:
            total = 0
            for f in self._storage_root.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total

    def get_module_count(self) -> int:
        """
        获取已存储的模块数量

        Returns:
            int: 模块数量
        """
        with self._lock:
            count = 0
            for item in self._storage_root.iterdir():
                if item.is_dir() and item.name.startswith("module_"):
                    count += 1
            return count

    def cleanup_orphaned_files(self) -> int:
        """
        清理孤立文件（无对应元数据的文件）

        Returns:
            int: 清理的文件数
        """
        with self._lock:
            cleaned = 0
            # 遍历所有.json文件，检查是否有对应元数据
            for f in self._storage_root.rglob("*.json"):
                if f.name == "metadata.json":
                    continue
                # 检查文件是否可正常解析
                try:
                    raw = f.read_bytes()
                    DataSerializer.deserialize(raw)
                except Exception:
                    f.unlink()
                    cleaned += 1
            return cleaned

    def clear_all(self) -> StorageResult:
        """
        清空所有存储数据

        Returns:
            StorageResult: 操作结果
        """
        with self._lock:
            try:
                # 保留根目录，删除所有内容
                for item in self._storage_root.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)

                # 重新初始化元数据
                self._init_global_metadata()
                return StorageResult.ok(path=str(self._storage_root))
            except Exception as e:
                return StorageResult.fail(f"清空存储失败: {str(e)}")

    # =====================================================================
    # 路径解析（内部方法）
    # =====================================================================

    def _resolve_module_dir(self, module_id: Optional[ModuleID]) -> Path:
        """解析模块目录路径"""
        if module_id is None:
            return self._storage_root / "_global"
        return self._storage_root / str(module_id)

    def _resolve_category_dir(
        self,
        module_id: Optional[ModuleID],
        category: str,
    ) -> Path:
        """解析分类目录路径"""
        module_dir = self._resolve_module_dir(module_id)
        if category in ("data", "config", "state"):
            return module_dir
        elif category == "snapshots":
            return self._storage_root / "snapshots"
        else:
            return module_dir / category

    def _resolve_path(
        self,
        key: str,
        module_id: Optional[ModuleID],
        category: str,
    ) -> Path:
        """解析完整文件路径"""
        dir_path = self._resolve_category_dir(module_id, category)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path / f"{key}.json"

    # =====================================================================
    # 文件写入（内部方法）
    # =====================================================================

    def _atomic_write(self, file_path: Path, data: bytes) -> None:
        """
        原子写入文件
        先写入临时文件，成功后重命名，防止写入中断导致数据损坏

        Args:
            file_path: 目标文件路径
            data: 字节数据
        """
        # 写入临时文件
        fd, tmp_path = tempfile.mkstemp(
            dir=file_path.parent,
            suffix=".tmp",
        )
        try:
            os.write(fd, data)
            os.close(fd)
            # 原子重命名
            os.replace(tmp_path, str(file_path))
        except Exception:
            # 清理临时文件
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _write_json_file(self, file_path: Path, data: Any) -> None:
        """写入JSON文件"""
        raw = DataSerializer.serialize(data)
        self._atomic_write(file_path, raw)

    # =====================================================================
    # 元数据管理（内部方法）
    # =====================================================================

    def _get_stored_metadata(self, file_path: Path) -> Optional[StorageMetadata]:
        """获取已存储文件的元数据"""
        meta_path = file_path.parent / f"{file_path.stem}.meta"
        if not meta_path.exists():
            return None

        try:
            raw = meta_path.read_bytes()
            data = DataSerializer.deserialize(raw)
            return StorageMetadata.from_dict(data)
        except Exception:
            return None

    def _write_file_metadata(
        self, file_path: Path, checksum: str, size_bytes: int,
    ) -> None:
        """写入文件级校验和元数据"""
        meta_path = file_path.parent / f"{file_path.stem}.meta"
        meta = StorageMetadata(
            checksum=checksum,
            size_bytes=size_bytes,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=self._version,
            format="json",
        )
        self._write_json_file(meta_path, meta.to_dict())

    def _update_module_metadata(
        self,
        module_id: Optional[ModuleID],
        key: str,
        category: str,
        checksum: str,
        size_bytes: int,
    ) -> None:
        """更新模块元数据"""
        if module_id is None:
            return

        meta_path = self._resolve_module_dir(module_id) / "module_meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取现有元数据
        if meta_path.exists():
            try:
                raw = meta_path.read_bytes()
                meta = DataSerializer.deserialize(raw)
            except Exception:
                meta = {}
        else:
            meta = {}

        now = datetime.now().isoformat()
        entry_key = f"{category}/{key}"
        meta[entry_key] = {
            "checksum": checksum,
            "size_bytes": size_bytes,
            "updated_at": now,
        }
        meta["module_id"] = str(module_id)
        meta["last_updated"] = now

        self._write_json_file(meta_path, meta)

    # =====================================================================
    # 魔术方法
    # =====================================================================

    def __repr__(self) -> str:
        return f"LongTermStorage(root={self._storage_root}, version={self._version})"


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 枚举
    "StorageFormat",
    # 数据类
    "StorageMetadata",
    "StorageResult",
    # 序列化器
    "DataSerializer",
    # 存储
    "LongTermStorage",
]
