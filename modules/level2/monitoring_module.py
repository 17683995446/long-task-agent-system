"""
阶段23：二级监控模块
Level 2 Monitoring Module

职责定义：
- 性能指标收集
- 状态监控
- 告警生成
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum, auto

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


class MetricType(Enum):
    """指标类型"""
    COUNTER = auto()    # 计数器
    GAUGE = auto()      # 仪表盘
    HISTOGRAM = auto()  # 直方图
    TIMER = auto()      # 计时器


class AlertLevel(Enum):
    """告警级别"""
    INFO = auto()      # 信息
    WARNING = auto()   # 警告
    ERROR = auto()     # 错误
    CRITICAL = auto()  # 严重


class Metric:
    """指标定义"""
    
    def __init__(
        self,
        metric_id: str,
        name: str,
        metric_type: MetricType,
        unit: str = "",
        labels: Dict[str, str] = None
    ):
        self.metric_id = metric_id
        self.name = name
        self.metric_type = metric_type
        self.unit = unit
        self.labels = labels or {}
        self.values: List[Dict[str, Any]] = []
    
    def record(self, value: float, timestamp: datetime = None) -> None:
        """记录指标值"""
        self.values.append({
            "value": value,
            "timestamp": (timestamp or datetime.now()).isoformat(),
        })
    
    def get_latest(self) -> Optional[float]:
        """获取最新值"""
        if self.values:
            return self.values[-1]["value"]
        return None
    
    def get_average(self, last_n: int = 10) -> float:
        """获取平均值"""
        if not self.values:
            return 0.0
        recent = self.values[-last_n:]
        return sum(v["value"] for v in recent) / len(recent)


class Alert:
    """告警定义"""
    
    def __init__(
        self,
        alert_id: str,
        name: str,
        level: AlertLevel,
        message: str,
        metric_id: Optional[str] = None
    ):
        self.alert_id = alert_id
        self.name = name
        self.level = level
        self.message = message
        self.metric_id = metric_id
        self.created_at = datetime.now()
        self.acknowledged = False
        self.resolved = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "level": self.level.name,
            "message": self.message,
            "metric_id": self.metric_id,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }


class Level2MonitoringModule(ControlModuleBase):
    """
    二级监控模块
    
    职责：
    1. 性能指标收集
    2. 系统状态监控
    3. 告警生成与管理
    4. 监控数据聚合
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL2
        self._state.module_name = "Level2MonitoringModule"
        self._logger = Logger(f"L2Monitoring_{self.module_id}")
        
        # 指标存储
        self._metrics: Dict[str, Metric] = {}
        
        # 告警管理
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        
        # 监控配置
        self._monitoring_config: Dict[str, Any] = {
            "collection_interval": 60,
            "retention_days": 7,
            "alert_thresholds": {
                "cpu_percent": 80,
                "memory_percent": 85,
                "error_rate": 0.05,
            }
        }
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化监控模块"""
        try:
            self._logger.info("二级监控模块初始化开始")
            
            # 1. 初始化指标存储
            self._metrics = {}
            
            # 2. 初始化告警管理
            self._alerts = {}
            self._alert_history = []
            
            # 3. 注册默认指标
            self._register_default_metrics()
            
            self._logger.info("二级监控模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="二级监控模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"二级监控模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L2M_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _register_default_metrics(self) -> None:
        """注册默认指标"""
        default_metrics = [
            Metric("task_count", "任务计数", MetricType.COUNTER),
            Metric("execution_time", "执行时间", MetricType.TIMER, "ms"),
            Metric("error_rate", "错误率", MetricType.GAUGE, "percent"),
            Metric("memory_usage", "内存使用", MetricType.GAUGE, "MB"),
        ]
        for metric in default_metrics:
            self._metrics[metric.metric_id] = metric
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行监控逻辑"""
        self._logger.info("二级监控模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 收集指标
            self._collect_metrics()
            
            # 2. 检查告警阈值
            new_alerts = self._check_alert_thresholds()
            
            # 3. 生成监控报告
            report = self._generate_monitoring_report()
            
            self._logger.info("二级监控模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "monitoring_report": report,
                    "new_alerts": [a.to_dict() for a in new_alerts],
                    "metrics_collected": len(self._metrics),
                },
                message="监控数据收集完成"
            )
            
        except Exception as e:
            self._logger.error(f"二级监控模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L2M_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _collect_metrics(self) -> None:
        """收集指标"""
        # 模拟指标收集
        import random
        
        if "task_count" in self._metrics:
            self._metrics["task_count"].record(random.randint(1, 100))
        
        if "execution_time" in self._metrics:
            self._metrics["execution_time"].record(random.randint(10, 1000))
        
        if "error_rate" in self._metrics:
            self._metrics["error_rate"].record(random.random() * 0.1)
        
        if "memory_usage" in self._metrics:
            self._metrics["memory_usage"].record(random.randint(100, 800))
    
    def _check_alert_thresholds(self) -> List[Alert]:
        """检查告警阈值"""
        new_alerts = []
        thresholds = self._monitoring_config.get("alert_thresholds", {})
        
        # 检查错误率
        error_metric = self._metrics.get("error_rate")
        if error_metric:
            latest = error_metric.get_latest()
            if latest and latest > thresholds.get("error_rate", 0.05):
                alert = Alert(
                    alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    name="高错误率告警",
                    level=AlertLevel.ERROR,
                    message=f"错误率超过阈值: {latest:.2%}",
                    metric_id="error_rate"
                )
                self._alerts[alert.alert_id] = alert
                self._alert_history.append(alert)
                new_alerts.append(alert)
        
        return new_alerts
    
    def _generate_monitoring_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_metrics": len(self._metrics),
            "active_alerts": len([a for a in self._alerts.values() if not a.resolved]),
            "metrics_summary": {
                mid: {
                    "latest": m.get_latest(),
                    "average": m.get_average(),
                }
                for mid, m in self._metrics.items()
            },
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验监控模块"""
        self._logger.info("二级监控模块校验开始")
        
        checks = []
        
        # 1. 校验指标存储
        if isinstance(self._metrics, dict):
            checks.append("metrics_storage_valid")
        
        # 2. 校验告警管理
        if isinstance(self._alerts, dict):
            checks.append("alerts_management_valid")
        
        # 3. 校验配置
        if "collection_interval" in self._monitoring_config:
            checks.append("config_valid")
        
        all_passed = len(checks) == 3
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="level2_monitoring_validation",
                message="二级监控模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="level2_monitoring_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("metrics_count", len(self._metrics))
        snapshot.set_state("alerts_count", len(self._alerts))
        snapshot.set_state("config", self._monitoring_config)
        snapshot.metadata["module_type"] = "Level2MonitoringModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def register_metric(self, metric: Metric) -> None:
        """注册指标"""
        self._metrics[metric.metric_id] = metric
        self._logger.info(f"指标已注册: {metric.metric_id}")
    
    def record_metric(self, metric_id: str, value: float) -> bool:
        """记录指标值"""
        metric = self._metrics.get(metric_id)
        if metric:
            metric.record(value)
            return True
        return False
    
    def get_metric(self, metric_id: str) -> Optional[Metric]:
        """获取指标"""
        return self._metrics.get(metric_id)
    
    def create_alert(
        self,
        name: str,
        level: AlertLevel,
        message: str,
        metric_id: Optional[str] = None
    ) -> str:
        """创建告警"""
        alert = Alert(
            alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._alerts)}",
            name=name,
            level=level,
            message=message,
            metric_id=metric_id
        )
        self._alerts[alert.alert_id] = alert
        self._alert_history.append(alert)
        self._logger.warning(f"告警已创建: {alert.alert_id} - {name}")
        return alert.alert_id
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.acknowledged = True
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.resolved = True
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活动告警"""
        return [a for a in self._alerts.values() if not a.resolved]
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        return self._generate_monitoring_report()


__all__ = [
    "Level2MonitoringModule",
    "Metric",
    "MetricType",
    "Alert",
    "AlertLevel",
]
