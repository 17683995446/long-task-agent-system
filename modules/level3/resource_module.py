"""
阶段33：三级资源模块
Level3ResourceModule

职责定义：
- 资源分配与回收
- 资源配额管理
- 资源使用监控
- 资源泄漏检测
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.base_module import ControlModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    THREAD = "thread"
    CONNECTION = "connection"


@dataclass
class ResourceAllocation:
    """资源分配记录"""
    allocation_id: str
    resource_type: ResourceType
    amount: float
    owner_id: str
    allocated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    released: bool = False
    released_at: Optional[str] = None


class Level3ResourceModule(ControlModuleBase):
    """
    三级资源模块
    
    职责：
    1. 资源分配与回收
    2. 资源配额管理
    3. 资源使用监控
    4. 资源泄漏检测
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3ResourceModule"
        self._logger = Logger(f"L3R_{self.module_id}")
        
        # 资源配额
        self._quotas: Dict[ResourceType, float] = {
            ResourceType.CPU: 100.0,
            ResourceType.MEMORY: 1024.0,
            ResourceType.DISK: 10240.0,
            ResourceType.NETWORK: 1000.0,
            ResourceType.THREAD: 100.0,
            ResourceType.CONNECTION: 500.0,
        }
        
        # 已分配资源
        self._allocations: Dict[str, ResourceAllocation] = {}
        
        # 资源使用统计
        self._usage_stats: Dict[ResourceType, Dict[str, Any]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化资源模块"""
        try:
            self._logger.info("资源模块初始化开始")
            
            # 加载自定义配额
            if request.task_param:
                custom_quotas = request.task_param.get_param("resource_quotas", {})
                for rt_name, amount in custom_quotas.items():
                    try:
                        rt = ResourceType[rt_name.upper()]
                        self._quotas[rt] = amount
                    except KeyError:
                        self._logger.warning(f"未知资源类型: {rt_name}")
            
            self._logger.info(f"资源模块初始化完成，配额: {self._get_quota_summary()}")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message=f"资源模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"资源模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3R_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行资源管理"""
        self._logger.info("资源模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 检测资源泄漏
            leaks = self._detect_leaks()
            
            # 2. 回收过期资源
            reclaimed = self._reclaim_expired_resources()
            
            # 3. 更新使用统计
            self._update_usage_stats()
            
            # 4. 生成资源报告
            report = self._generate_resource_report()
            
            self._logger.info(f"资源管理完成: 泄漏={len(leaks)}, 回收={len(reclaimed)}")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "resource_report": report,
                    "leaks_detected": len(leaks),
                    "reclaimed_resources": len(reclaimed),
                    "module": "Level3ResourceModule",
                },
                message="资源模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"资源模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3R_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _detect_leaks(self) -> List[str]:
        """检测资源泄漏"""
        leaks = []
        now = datetime.now()
        
        for alloc_id, alloc in self._allocations.items():
            if alloc.released:
                continue
            
            # 检查是否过期
            if alloc.expires_at:
                expires = datetime.fromisoformat(alloc.expires_at)
                if now > expires:
                    leaks.append(alloc_id)
        
        return leaks
    
    def _reclaim_expired_resources(self) -> List[str]:
        """回收过期资源"""
        reclaimed = []
        leaks = self._detect_leaks()
        
        for alloc_id in leaks:
            if alloc_id in self._allocations:
                self._allocations[alloc_id].released = True
                self._allocations[alloc_id].released_at = datetime.now().isoformat()
                reclaimed.append(alloc_id)
                self._logger.info(f"回收过期资源: {alloc_id}")
        
        return reclaimed
    
    def _update_usage_stats(self) -> None:
        """更新使用统计"""
        for rt in ResourceType:
            total_allocated = sum(
                alloc.amount for alloc in self._allocations.values()
                if alloc.resource_type == rt and not alloc.released
            )
            quota = self._quotas.get(rt, 0)
            
            self._usage_stats[rt] = {
                "quota": quota,
                "allocated": total_allocated,
                "available": max(0, quota - total_allocated),
                "usage_rate": total_allocated / quota if quota > 0 else 0,
            }
    
    def _generate_resource_report(self) -> Dict[str, Any]:
        """生成资源报告"""
        return {
            "quotas": {rt.value: amount for rt, amount in self._quotas.items()},
            "usage_stats": {rt.value: stats for rt, stats in self._usage_stats.items()},
            "total_allocations": len(self._allocations),
            "active_allocations": sum(1 for a in self._allocations.values() if not a.released),
            "released_allocations": sum(1 for a in self._allocations.values() if a.released),
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验资源模块"""
        self._logger.info("资源模块校验开始")
        
        checks = []
        
        # 1. 校验配额
        if all(q > 0 for q in self._quotas.values()):
            checks.append("quotas_valid")
        
        # 2. 校验使用率在合理范围
        self._update_usage_stats()
        overused = [rt for rt, stats in self._usage_stats.items() if stats["usage_rate"] > 1.0]
        if not overused:
            checks.append("usage_valid")
        
        # 3. 校验模块层级
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        all_passed = len(checks) == 3
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="resource_validation",
                message="资源模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="resource_validation",
                message=f"校验失败: {checks}, 超用资源: {overused}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建资源模块快照"""
        snapshot.set_state("quotas", {rt.value: amount for rt, amount in self._quotas.items()})
        snapshot.set_state("allocations", {
            aid: {
                "resource_type": alloc.resource_type.value,
                "amount": alloc.amount,
                "owner_id": alloc.owner_id,
                "released": alloc.released,
            }
            for aid, alloc in self._allocations.items()
        })
        snapshot.set_state("usage_stats", {rt.value: stats for rt, stats in self._usage_stats.items()})
        snapshot.metadata["module_type"] = "Level3ResourceModule"
    
    # 公共接口
    def allocate(self, resource_type: str, amount: float, owner_id: str, expires_minutes: int = 60) -> Optional[str]:
        """分配资源"""
        try:
            rt = ResourceType[resource_type.upper()]
            
            # 检查配额
            self._update_usage_stats()
            stats = self._usage_stats.get(rt, {})
            if stats.get("available", 0) < amount:
                self._logger.warning(f"资源不足: {resource_type} 可用={stats.get('available', 0)}, 请求={amount}")
                return None
            
            alloc_id = f"alloc_{datetime.now().isoformat()}_{owner_id}"
            allocation = ResourceAllocation(
                allocation_id=alloc_id,
                resource_type=rt,
                amount=amount,
                owner_id=owner_id,
                expires_at=(datetime.now() + __import__('datetime').timedelta(minutes=expires_minutes)).isoformat(),
            )
            self._allocations[alloc_id] = allocation
            self._logger.info(f"资源分配成功: {alloc_id}")
            return alloc_id
            
        except Exception as e:
            self._logger.error(f"资源分配失败: {e}")
            return None
    
    def release(self, allocation_id: str) -> bool:
        """释放资源"""
        if allocation_id in self._allocations:
            self._allocations[allocation_id].released = True
            self._allocations[allocation_id].released_at = datetime.now().isoformat()
            self._logger.info(f"资源释放成功: {allocation_id}")
            return True
        return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        self._update_usage_stats()
        return {rt.value: stats for rt, stats in self._usage_stats.items()}
    
    def _get_quota_summary(self) -> str:
        """获取配额摘要"""
        return ", ".join(f"{rt.value}={amount}" for rt, amount in self._quotas.items())


__all__ = ["Level3ResourceModule", "ResourceType", "ResourceAllocation"]
