"""
超长任务Agent树形双生子模块化执行系统 - 状态快照基础实现
Snapshot Base Implementation for Long-Task Agent Twin-Module Execution System

阶段10：状态快照基础实现
遵循原则：图难于其易，为大于其细
核心约束：支持状态快照创建、恢复、完整性校验
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import json
import hashlib
import threading
import uuid

from core_types.core_types import ModuleID, TaskID, SnapshotData, CheckpointData


# =============================================================================
# 1. 快照类型枚举 (Snapshot Type Enumeration)
# =============================================================================

class SnapshotType(Enum):
    """
    快照类型枚举
    """
    FULL = auto()        # 完整快照
    DELTA = auto()       # 增量快照
    MINIMAL = auto()     # 最小快照
    CHECKPOINT = auto()  # 检查点快照


# =============================================================================
# 2. 快照状态枚举 (Snapshot State Enumeration)
# =============================================================================

class SnapshotState(Enum):
    """
    快照状态枚举
    """
    CREATING = auto()    # 创建中
    VALID = auto()       # 有效
    INVALID = auto()     # 无效
    RESTORING = auto()   # 恢复中
    CORRUPTED = auto()   # 已损坏


# =============================================================================
# 3. 快照元数据 (Snapshot Metadata)
# =============================================================================

@dataclass
class SnapshotMetadata:
    """
    快照元数据
    存储快照的描述信息
    """
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    snapshot_type: SnapshotType = SnapshotType.FULL
    snapshot_version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    module_id: Optional[ModuleID] = None
    module_name: str = ""
    task_id: Optional[TaskID] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_type": self.snapshot_type.name,
            "snapshot_version": self.snapshot_version,
            "created_at": self.created_at.isoformat(),
            "module_id": str(self.module_id) if self.module_id else None,
            "module_name": self.module_name,
            "task_id": str(self.task_id) if self.task_id else None,
            "description": self.description,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotMetadata":
        """从字典创建"""
        return cls(
            snapshot_id=data.get("snapshot_id", uuid.uuid4().hex[:16]),
            snapshot_type=SnapshotType[data.get("snapshot_type", "FULL")],
            snapshot_version=data.get("snapshot_version", "1.0"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            module_name=data.get("module_name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
        )


# =============================================================================
# 4. 快照校验结果 (Snapshot Validation Result)
# =============================================================================

@dataclass
class SnapshotValidationResult:
    """
    快照校验结果
    """
    valid: bool
    snapshot_id: str
    checks: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_check(self, check_name: str, passed: bool) -> None:
        """添加校验结果"""
        self.checks[check_name] = passed
        if not passed:
            self.valid = False
    
    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)


# =============================================================================
# 5. 快照管理器基类 (Snapshot Base)
# =============================================================================

class SnapshotBase:
    """
    快照管理器基类
    
    提供状态快照的基础功能：
    1. 创建快照
    2. 恢复快照
    3. 校验快照完整性
    4. 版本管理
    5. 校验和计算
    
    使用方式：
        snapshot_manager = SnapshotBase()
        
        # 创建快照
        snapshot = snapshot_manager.create_snapshot(state_data)
        
        # 校验快照
        result = snapshot_manager.validate_snapshot(snapshot)
        
        # 恢复快照
        restored_state = snapshot_manager.restore_from_snapshot(snapshot)
    """
    
    # 当前快照版本
    CURRENT_VERSION = "1.0"
    
    # 兼容的版本列表
    COMPATIBLE_VERSIONS = ["1.0"]
    
    def __init__(self):
        """初始化快照管理器"""
        self._lock = threading.RLock()
        self._snapshot_history: List[SnapshotData] = []
        self._max_history_size: int = 100
    
    # =====================================================================
    # 快照创建
    # =====================================================================
    
    def create_snapshot(
        self,
        state_data: Dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        module_id: Optional[ModuleID] = None,
        module_name: str = "",
        task_id: Optional[TaskID] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> SnapshotData:
        """
        创建快照
        
        Args:
            state_data: 状态数据
            snapshot_type: 快照类型
            module_id: 模块ID
            module_name: 模块名称
            task_id: 任务ID
            description: 描述
            tags: 标签列表
            
        Returns:
            SnapshotData: 快照数据
        """
        with self._lock:
            # 创建元数据
            metadata = SnapshotMetadata(
                snapshot_type=snapshot_type,
                module_id=module_id,
                module_name=module_name,
                task_id=task_id,
                description=description,
                tags=tags or [],
            )
            
            # 创建快照数据
            snapshot = SnapshotData(
                module_id=module_id or ModuleID(),
                snapshot_id=metadata.snapshot_id,
                snapshot_version=self.CURRENT_VERSION,
                state_data=self._serialize_state(state_data),
                metadata={
                    "type": snapshot_type.name,
                    "module_name": module_name,
                    "description": description,
                    "tags": tags or [],
                    "created_at": datetime.now().isoformat(),
                },
            )
            
            # 计算校验和
            checksum = self._calculate_checksum(snapshot.state_data)
            snapshot.metadata["checksum"] = checksum
            
            # 添加到历史
            self._add_to_history(snapshot)
            
            return snapshot
    
    def _serialize_state(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        序列化状态数据
        
        Args:
            state_data: 原始状态数据
            
        Returns:
            Dict[str, Any]: 序列化后的数据
        """
        serialized = {}
        for key, value in state_data.items():
            try:
                # 尝试JSON序列化来验证数据可序列化
                json.dumps(value, default=str)
                serialized[key] = value
            except (TypeError, ValueError):
                # 不可序列化的值转为字符串
                serialized[key] = str(value)
        return serialized
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """
        计算校验和
        
        Args:
            data: 数据
            
        Returns:
            str: 校验和（MD5）
        """
        try:
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(json_str.encode('utf-8')).hexdigest()
        except Exception:
            return ""
    
    def _add_to_history(self, snapshot: SnapshotData) -> None:
        """添加快照到历史"""
        self._snapshot_history.append(snapshot)
        if len(self._snapshot_history) > self._max_history_size:
            self._snapshot_history.pop(0)
    
    # =====================================================================
    # 快照恢复
    # =====================================================================
    
    def restore_from_snapshot(
        self,
        snapshot: SnapshotData,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        从快照恢复状态
        
        Args:
            snapshot: 快照数据
            validate: 是否校验快照
            
        Returns:
            Dict[str, Any]: 恢复的状态数据
            
        Raises:
            ValueError: 快照校验失败
        """
        with self._lock:
            # 校验快照
            if validate:
                result = self.validate_snapshot(snapshot)
                if not result.valid:
                    raise ValueError(f"快照校验失败: {result.errors}")
            
            # 检查版本兼容性
            if not self._is_version_compatible(snapshot.snapshot_version):
                raise ValueError(
                    f"快照版本不兼容: {snapshot.snapshot_version}, "
                    f"兼容版本: {self.COMPATIBLE_VERSIONS}"
                )
            
            # 返回状态数据
            return self._deserialize_state(snapshot.state_data)
    
    def _deserialize_state(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        反序列化状态数据
        
        Args:
            state_data: 序列化的状态数据
            
        Returns:
            Dict[str, Any]: 反序列化后的数据
        """
        # 默认实现直接返回
        # 子类可重写以实现自定义反序列化
        return state_data.copy()
    
    def _is_version_compatible(self, version: str) -> bool:
        """
        检查版本兼容性
        
        Args:
            version: 版本号
            
        Returns:
            bool: 是否兼容
        """
        return version in self.COMPATIBLE_VERSIONS
    
    # =====================================================================
    # 快照校验
    # =====================================================================
    
    def validate_snapshot(self, snapshot: SnapshotData) -> SnapshotValidationResult:
        """
        校验快照完整性
        
        Args:
            snapshot: 快照数据
            
        Returns:
            SnapshotValidationResult: 校验结果
        """
        result = SnapshotValidationResult(
            valid=True,
            snapshot_id=snapshot.snapshot_id,
        )
        
        # 校验1：快照ID
        if not snapshot.snapshot_id:
            result.add_check("snapshot_id", False)
            result.add_error("快照ID为空")
        else:
            result.add_check("snapshot_id", True)
        
        # 校验2：快照版本
        if not snapshot.snapshot_version:
            result.add_check("snapshot_version", False)
            result.add_error("快照版本为空")
        elif not self._is_version_compatible(snapshot.snapshot_version):
            result.add_check("snapshot_version", False)
            result.add_error(f"快照版本不兼容: {snapshot.snapshot_version}")
        else:
            result.add_check("snapshot_version", True)
        
        # 校验3：状态数据
        if snapshot.state_data is None:
            result.add_check("state_data", False)
            result.add_error("状态数据为空")
        else:
            result.add_check("state_data", True)
        
        # 校验4：校验和
        if "checksum" in snapshot.metadata:
            expected_checksum = snapshot.metadata["checksum"]
            actual_checksum = self._calculate_checksum(snapshot.state_data)
            if expected_checksum != actual_checksum:
                result.add_check("checksum", False)
                result.add_error(f"校验和不匹配: 期望 {expected_checksum}, 实际 {actual_checksum}")
            else:
                result.add_check("checksum", True)
        else:
            result.add_warning("快照缺少校验和")
        
        # 校验5：创建时间
        if "created_at" in snapshot.metadata:
            try:
                datetime.fromisoformat(snapshot.metadata["created_at"])
                result.add_check("created_at", True)
            except ValueError:
                result.add_check("created_at", False)
                result.add_error("创建时间格式无效")
        else:
            result.add_warning("快照缺少创建时间")
        
        return result
    
    def quick_validate(self, snapshot: SnapshotData) -> bool:
        """
        快速校验快照（仅校验校验和）
        
        Args:
            snapshot: 快照数据
            
        Returns:
            bool: 是否有效
        """
        if "checksum" not in snapshot.metadata:
            return False
        
        expected = snapshot.metadata["checksum"]
        actual = self._calculate_checksum(snapshot.state_data)
        return expected == actual
    
    # =====================================================================
    # 快照历史管理
    # =====================================================================
    
    def get_snapshot_history(
        self,
        limit: int = 10,
        snapshot_type: Optional[SnapshotType] = None,
    ) -> List[SnapshotData]:
        """
        获取快照历史
        
        Args:
            limit: 最大数量
            snapshot_type: 快照类型过滤器
            
        Returns:
            List[SnapshotData]: 快照列表
        """
        with self._lock:
            history = self._snapshot_history.copy()
        
        if snapshot_type:
            history = [
                s for s in history
                if s.metadata.get("type") == snapshot_type.name
            ]
        
        return history[-limit:]
    
    def get_latest_snapshot(self) -> Optional[SnapshotData]:
        """
        获取最新快照
        
        Returns:
            Optional[SnapshotData]: 最新快照
        """
        with self._lock:
            if self._snapshot_history:
                return self._snapshot_history[-1]
            return None
    
    def clear_history(self) -> int:
        """
        清除快照历史
        
        Returns:
            int: 清除的快照数量
        """
        with self._lock:
            count = len(self._snapshot_history)
            self._snapshot_history.clear()
            return count
    
    # =====================================================================
    # 增量快照支持
    # =====================================================================
    
    def create_delta_snapshot(
        self,
        current_state: Dict[str, Any],
        base_snapshot: SnapshotData,
        module_id: Optional[ModuleID] = None,
        module_name: str = "",
        task_id: Optional[TaskID] = None,
    ) -> SnapshotData:
        """
        创建增量快照
        
        Args:
            current_state: 当前状态
            base_snapshot: 基础快照
            module_id: 模块ID
            module_name: 模块名称
            task_id: 任务ID
            
        Returns:
            SnapshotData: 增量快照
        """
        # 计算差异
        delta = self._compute_delta(current_state, base_snapshot.state_data)
        
        # 创建增量快照
        snapshot = self.create_snapshot(
            state_data=delta,
            snapshot_type=SnapshotType.DELTA,
            module_id=module_id,
            module_name=module_name,
            task_id=task_id,
            description=f"增量快照，基于 {base_snapshot.snapshot_id}",
        )
        
        # 记录基础快照ID
        snapshot.metadata["base_snapshot_id"] = base_snapshot.snapshot_id
        
        return snapshot
    
    def _compute_delta(
        self,
        current: Dict[str, Any],
        base: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        计算状态差异
        
        Args:
            current: 当前状态
            base: 基础状态
            
        Returns:
            Dict[str, Any]: 差异
        """
        delta = {
            "added": {},
            "modified": {},
            "removed": [],
        }
        
        # 找出新增和修改的键
        for key, value in current.items():
            if key not in base:
                delta["added"][key] = value
            elif base[key] != value:
                delta["modified"][key] = {
                    "old": base[key],
                    "new": value,
                }
        
        # 找出删除的键
        for key in base:
            if key not in current:
                delta["removed"].append(key)
        
        return delta
    
    def apply_delta(
        self,
        base_state: Dict[str, Any],
        delta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        应用增量到基础状态
        
        Args:
            base_state: 基础状态
            delta: 增量
            
        Returns:
            Dict[str, Any]: 合并后的状态
        """
        result = base_state.copy()
        
        # 应用新增
        for key, value in delta.get("added", {}).items():
            result[key] = value
        
        # 应用修改
        for key, change in delta.get("modified", {}).items():
            result[key] = change["new"]
        
        # 应用删除
        for key in delta.get("removed", []):
            result.pop(key, None)
        
        return result
    
    # =====================================================================
    # 快照导出/导入
    # =====================================================================
    
    def export_snapshot(self, snapshot: SnapshotData) -> str:
        """
        导出快照为JSON字符串
        
        Args:
            snapshot: 快照数据
            
        Returns:
            str: JSON字符串
        """
        export_data = {
            "snapshot_id": snapshot.snapshot_id,
            "module_id": str(snapshot.module_id),
            "snapshot_version": snapshot.snapshot_version,
            "state_data": snapshot.state_data,
            "metadata": snapshot.metadata,
            "created_at": snapshot.created_at.isoformat(),
        }
        return json.dumps(export_data, ensure_ascii=False, indent=2)
    
    def import_snapshot(self, json_str: str) -> SnapshotData:
        """
        从JSON字符串导入快照
        
        Args:
            json_str: JSON字符串
            
        Returns:
            SnapshotData: 快照数据
        """
        data = json.loads(json_str)
        
        return SnapshotData(
            module_id=ModuleID(data.get("module_id", "")),
            snapshot_id=data["snapshot_id"],
            snapshot_version=data.get("snapshot_version", "1.0"),
            state_data=data.get("state_data", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )
    
    # =====================================================================
    # 工具方法
    # =====================================================================
    
    def get_snapshot_info(self, snapshot: SnapshotData) -> Dict[str, Any]:
        """
        获取快照信息
        
        Args:
            snapshot: 快照数据
            
        Returns:
            Dict[str, Any]: 快照信息
        """
        # 计算快照大小
        json_str = json.dumps(snapshot.state_data, default=str)
        size_bytes = len(json_str.encode('utf-8'))
        
        return {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_version": snapshot.snapshot_version,
            "module_id": str(snapshot.module_id),
            "type": snapshot.metadata.get("type", "UNKNOWN"),
            "size_bytes": size_bytes,
            "created_at": snapshot.metadata.get("created_at", ""),
            "has_checksum": "checksum" in snapshot.metadata,
            "state_keys": list(snapshot.state_data.keys()),
        }
    
    def __repr__(self) -> str:
        return f"SnapshotBase(history_size={len(self._snapshot_history)})"


# =============================================================================
# 6. 检查点管理器 (Checkpoint Manager)
# =============================================================================

class CheckpointManager:
    """
    检查点管理器
    
    管理任务执行过程中的检查点，支持断点续跑
    """
    
    def __init__(self):
        """初始化检查点管理器"""
        self._checkpoints: Dict[TaskID, CheckpointData] = {}
        self._lock = threading.RLock()
    
    def save_checkpoint(
        self,
        task_id: TaskID,
        current_step: int,
        total_steps: int,
        module_snapshots: Dict[str, SnapshotData],
        execution_context: Dict[str, Any],
    ) -> CheckpointData:
        """
        保存检查点
        
        Args:
            task_id: 任务ID
            current_step: 当前步骤
            total_steps: 总步骤数
            module_snapshots: 模块快照字典
            execution_context: 执行上下文
            
        Returns:
            CheckpointData: 检查点数据
        """
        with self._lock:
            checkpoint = CheckpointData(
                task_id=task_id,
                current_step=current_step,
                total_steps=total_steps,
                module_snapshots=module_snapshots,
                execution_context=execution_context,
            )
            
            self._checkpoints[task_id] = checkpoint
            return checkpoint
    
    def load_checkpoint(self, task_id: TaskID) -> Optional[CheckpointData]:
        """
        加载检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[CheckpointData]: 检查点数据
        """
        with self._lock:
            return self._checkpoints.get(task_id)
    
    def has_checkpoint(self, task_id: TaskID) -> bool:
        """
        检查是否存在检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否存在
        """
        with self._lock:
            return task_id in self._checkpoints
    
    def remove_checkpoint(self, task_id: TaskID) -> bool:
        """
        移除检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功移除
        """
        with self._lock:
            if task_id in self._checkpoints:
                del self._checkpoints[task_id]
                return True
            return False
    
    def clear_all(self) -> int:
        """
        清除所有检查点
        
        Returns:
            int: 清除的数量
        """
        with self._lock:
            count = len(self._checkpoints)
            self._checkpoints.clear()
            return count
    
    def get_all_task_ids(self) -> List[TaskID]:
        """
        获取所有有检查点的任务ID
        
        Returns:
            List[TaskID]: 任务ID列表
        """
        with self._lock:
            return list(self._checkpoints.keys())


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 枚举
    "SnapshotType",
    "SnapshotState",
    
    # 数据类
    "SnapshotMetadata",
    "SnapshotValidationResult",
    
    # 快照管理器
    "SnapshotBase",
    
    # 检查点管理器
    "CheckpointManager",
]
