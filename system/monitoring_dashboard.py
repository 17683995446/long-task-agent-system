"""
阶段76-80：系统监控面板
System Monitoring Dashboard

职责定义：
- 系统状态监控
- 性能指标展示
- 告警管理
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum, auto

from system.module_tree import ModuleTree
from system.execution_engine import ExecutionEngine, ExecutionStatus
from core_types.core_types import ModuleID, TaskID, ModuleLevel, ModuleState
from utils.logger import Logger


class DashboardMetric:
    """面板指标"""
    
    def __init__(
        self,
        metric_id: str,
        name: str,
        value: float,
        unit: str = ""
    ):
        self.metric_id = metric_id
        self.name = name
        self.value = value
        self.unit = unit
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
        }


class SystemHealth:
    """系统健康状态"""
    
    def __init__(self):
        self.status = "healthy"
        self.score = 100
        self.issues: List[Dict[str, Any]] = []
        self.last_check = datetime.now()
    
    def add_issue(self, severity: str, message: str) -> None:
        """添加问题"""
        self.issues.append({
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })
        if severity == "critical":
            self.status = "critical"
            self.score = max(0, self.score - 30)
        elif severity == "warning":
            if self.status == "healthy":
                self.status = "warning"
            self.score = max(0, self.score - 10)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "score": self.score,
            "issues": self.issues,
            "last_check": self.last_check.isoformat(),
        }


class MonitoringDashboard:
    """
    系统监控面板
    
    负责：
    1. 系统状态监控
    2. 性能指标收集和展示
    3. 告警管理
    4. 健康检查
    """
    
    def __init__(self, module_tree: ModuleTree, execution_engine: ExecutionEngine):
        self._module_tree = module_tree
        self._execution_engine = execution_engine
        self._logger = Logger("MonitoringDashboard")
        self._metrics: Dict[str, DashboardMetric] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._health = SystemHealth()
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "module_count": self._module_tree.get_module_count(),
            "tree_depth": self._module_tree.get_tree_depth(),
            "execution_stats": self._execution_engine.get_statistics(),
        }
        
        # 按层级统计模块
        level_counts = {}
        for level in ModuleLevel:
            count = len(self._module_tree.get_modules_by_level(level))
            if count > 0:
                level_counts[level.name] = count
        metrics["module_level_distribution"] = level_counts
        
        return metrics
    
    def get_module_status(self, module_id: Optional[ModuleID] = None) -> Dict[str, Any]:
        """
        获取模块状态
        
        Args:
            module_id: 模块ID，如果为None则返回所有模块状态
        """
        if module_id:
            module = self._module_tree.get_module(module_id)
            if not module:
                return {"error": f"模块未找到: {module_id}"}
            return {
                "module_id": str(module_id),
                "name": module.module_name,
                "level": module.module_level.name,
                "state": module.module_state.name,
                "initialized": module.is_initialized,
            }
        
        # 返回所有模块状态
        modules = self._module_tree.get_all_modules()
        return {
            "modules": [
                {
                    "module_id": str(m.module_id),
                    "name": m.module_name,
                    "level": m.module_level.name,
                    "state": m.module_state.name,
                }
                for m in modules
            ]
        }
    
    def get_execution_overview(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """
        获取执行概览
        
        Args:
            time_range_minutes: 时间范围（分钟）
        """
        since = datetime.now() - timedelta(minutes=time_range_minutes)
        
        # 获取执行历史
        history = self._execution_engine.get_execution_history()
        
        # 过滤时间范围
        recent_history = [
            h for h in history
            if h.start_time and h.start_time >= since
        ]
        
        # 统计
        total = len(recent_history)
        completed = sum(1 for h in recent_history if h.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for h in recent_history if h.status == ExecutionStatus.FAILED)
        
        return {
            "time_range_minutes": time_range_minutes,
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "average_duration_ms": self._calculate_average_duration(recent_history),
        }
    
    def _calculate_average_duration(self, records: List) -> float:
        """计算平均执行时间"""
        durations = []
        for record in records:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds() * 1000
                durations.append(duration)
        return sum(durations) / len(durations) if durations else 0
    
    def check_health(self) -> SystemHealth:
        """执行健康检查"""
        self._health = SystemHealth()
        
        # 1. 检查模块状态
        from core_types.core_types import ModuleState
        modules = self._module_tree.get_all_modules()
        uninitialized = [m for m in modules if m.module_state == ModuleState.UNINITIALIZED]
        if uninitialized:
            self._health.add_issue(
                "warning",
                f"有 {len(uninitialized)} 个模块未初始化"
            )
        
        # 2. 检查执行失败率
        stats = self._execution_engine.get_statistics()
        if stats["total_executions"] > 0:
            failure_rate = stats["failed"] / stats["total_executions"]
            if failure_rate > 0.5:
                self._health.add_issue(
                    "critical",
                    f"执行失败率过高: {failure_rate:.1%}"
                )
            elif failure_rate > 0.2:
                self._health.add_issue(
                    "warning",
                    f"执行失败率偏高: {failure_rate:.1%}"
                )
        
        # 3. 检查活跃执行数
        if stats["active"] > 100:
            self._health.add_issue(
                "warning",
                f"活跃执行任务过多: {stats['active']}"
            )
        
        self._health.last_check = datetime.now()
        return self._health
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return self._health.to_dict()
    
    def create_alert(self, level: str, message: str, source: str) -> str:
        """创建告警"""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._alerts)}"
        alert = {
            "alert_id": alert_id,
            "level": level,
            "message": message,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "acknowledged": False,
        }
        self._alerts.append(alert)
        self._logger.warning(f"告警创建: [{level}] {message}")
        return alert_id
    
    def get_alerts(
        self,
        level: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """获取告警列表"""
        alerts = self._alerts
        
        if level:
            alerts = [a for a in alerts if a["level"] == level]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self._alerts:
            if alert["alert_id"] == alert_id:
                alert["acknowledged"] = True
                return True
        return False
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """获取面板摘要"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": self.collect_system_metrics(),
            "health": self.get_health_status(),
            "execution_overview": self.get_execution_overview(),
            "active_alerts": len([a for a in self._alerts if not a["acknowledged"]]),
        }
    
    def export_report(self, format: str = "json") -> Dict[str, Any]:
        """导出监控报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_dashboard_summary(),
            "module_status": self.get_module_status(),
            "alerts": self._alerts,
        }
        return report


__all__ = [
    "MonitoringDashboard",
    "DashboardMetric",
    "SystemHealth",
]
