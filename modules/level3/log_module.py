"""
阶段40：三级日志模块
Level3LogModule

职责定义：
- 日志收集
- 日志分析
- 日志归档
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re

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


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogArchiveStatus(Enum):
    """日志归档状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    PURGED = "purged"


@dataclass
class LogEntry:
    """日志条目"""
    log_id: str
    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "context": self.context,
            "tags": self.tags,
            "trace_id": self.trace_id,
        }


@dataclass
class LogArchive:
    """日志归档"""
    archive_id: str
    name: str
    created_at: datetime
    log_count: int
    size_bytes: int
    date_range_start: datetime
    date_range_end: datetime
    status: LogArchiveStatus = LogArchiveStatus.ACTIVE
    filters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "archive_id": self.archive_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "log_count": self.log_count,
            "size_bytes": self.size_bytes,
            "date_range_start": self.date_range_start.isoformat(),
            "date_range_end": self.date_range_end.isoformat(),
            "status": self.status.value,
            "filters": self.filters,
        }


@dataclass
class LogAnalysisResult:
    """日志分析结果"""
    analysis_id: str
    timestamp: datetime
    total_logs: int
    level_distribution: Dict[str, int] = field(default_factory=dict)
    source_distribution: Dict[str, int] = field(default_factory=dict)
    time_series: Dict[str, int] = field(default_factory=dict)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "timestamp": self.timestamp.isoformat(),
            "total_logs": self.total_logs,
            "level_distribution": self.level_distribution,
            "source_distribution": self.source_distribution,
            "time_series": self.time_series,
            "patterns": self.patterns,
            "anomalies": self.anomalies,
        }


class Level3LogModule(ExecuteModuleBase):
    """
    三级日志模块
    
    职责：
    1. 日志收集
    2. 日志分析
    3. 日志归档
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3LogModule"
        self._logger = Logger(f"L3L_{self.module_id}")
        
        # 日志存储
        self._logs: List[LogEntry] = []
        # 归档存储
        self._archives: Dict[str, LogArchive] = {}
        # 分析结果
        self._analysis_results: List[LogAnalysisResult] = {}
        # 日志收集器配置
        self._collectors: Dict[str, Dict[str, Any]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级日志模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._logs = []
            self._archives = {}
            self._analysis_results = {}
            self._collectors = {}
            
            # 3. 加载默认收集器
            self._load_default_collectors()
            
            self._logger.info("三级日志模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级日志模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级日志模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3L_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "max_logs": 50000,
            "auto_archive": True,
            "archive_after_days": 7,
            "retention_days": 30,
            "min_level": "debug",
        }
        if request.task_param:
            custom_config = request.task_param.get_param("log_config", {})
            self._config.update(custom_config)
    
    def _load_default_collectors(self) -> None:
        """加载默认日志收集器"""
        self._collectors = {
            "system": {
                "enabled": True,
                "source_pattern": "system.*",
                "min_level": "info",
            },
            "application": {
                "enabled": True,
                "source_pattern": "app.*",
                "min_level": "debug",
            },
            "error": {
                "enabled": True,
                "source_pattern": ".*",
                "min_level": "error",
            },
        }
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级日志模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "collect")
            
            if operation == "collect":
                result = self._collect_operation(input_data)
            elif operation == "query":
                result = self._query_operation(input_data)
            elif operation == "analyze":
                result = self._analyze_operation(input_data)
            elif operation == "archive":
                result = self._archive_operation(input_data)
            elif operation == "get_archive":
                result = self._get_archive_operation(input_data)
            elif operation == "list_archives":
                result = self._list_archives_operation()
            elif operation == "purge":
                result = self._purge_operation(input_data)
            elif operation == "configure_collector":
                result = self._configure_collector_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级日志模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3LogModule",
                    "log_summary": {
                        "total_logs": len(self._logs),
                        "total_archives": len(self._archives),
                        "total_analyses": len(self._analysis_results),
                        "active_collectors": len([c for c in self._collectors.values() if c.get("enabled")]),
                    },
                },
                message="三级日志模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级日志模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3L_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _collect_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """收集日志"""
        import uuid
        
        level = LogLevel(input_data.get("level", "info"))
        min_level = LogLevel(self._config.get("min_level", "debug"))
        
        # 级别过滤
        if self._level_value(level) < self._level_value(min_level):
            return {
                "operation": "collect",
                "filtered": True,
                "reason": f"日志级别 {level.value} 低于最小级别 {min_level.value}",
            }
        
        log = LogEntry(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            level=level,
            source=input_data.get("source", "unknown"),
            message=input_data.get("message", ""),
            context=input_data.get("context", {}),
            tags=input_data.get("tags", []),
            trace_id=input_data.get("trace_id"),
        )
        self._logs.append(log)
        
        # 检查最大日志数
        max_logs = self._config.get("max_logs", 50000)
        if len(self._logs) > max_logs:
            # 归档旧日志
            if self._config.get("auto_archive", True):
                self._auto_archive_old_logs()
            else:
                self._logs = self._logs[-max_logs:]
        
        return {
            "operation": "collect",
            "log_id": log.log_id,
            "collected": True,
            "total_logs": len(self._logs),
        }
    
    def _level_value(self, level: LogLevel) -> int:
        """获取日志级别数值"""
        values = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4,
        }
        return values.get(level, 0)
    
    def _auto_archive_old_logs(self) -> None:
        """自动归档旧日志"""
        archive_after_days = self._config.get("archive_after_days", 7)
        cutoff = datetime.now() - timedelta(days=archive_after_days)
        
        old_logs = [log for log in self._logs if log.timestamp < cutoff]
        if old_logs:
            self._create_archive_from_logs(old_logs, f"auto_archive_{datetime.now().strftime('%Y%m%d')}")
            self._logs = [log for log in self._logs if log.timestamp >= cutoff]
    
    def _query_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """查询日志"""
        filters = input_data.get("filters", {})
        limit = input_data.get("limit", 100)
        offset = input_data.get("offset", 0)
        
        filtered_logs = self._logs
        
        # 级别过滤
        if "level" in filters:
            filtered_logs = [log for log in filtered_logs if log.level.value == filters["level"]]
        if "min_level" in filters:
            min_level = LogLevel(filters["min_level"])
            filtered_logs = [log for log in filtered_logs if self._level_value(log.level) >= self._level_value(min_level)]
        
        # 源过滤
        if "source" in filters:
            filtered_logs = [log for log in filtered_logs if log.source == filters["source"]]
        if "source_pattern" in filters:
            pattern = re.compile(filters["source_pattern"])
            filtered_logs = [log for log in filtered_logs if pattern.match(log.source)]
        
        # 消息过滤
        if "message_contains" in filters:
            filtered_logs = [log for log in filtered_logs if filters["message_contains"] in log.message]
        if "message_pattern" in filters:
            pattern = re.compile(filters["message_pattern"])
            filtered_logs = [log for log in filtered_logs if pattern.search(log.message)]
        
        # 标签过滤
        if "tags" in filters:
            tags = set(filters["tags"])
            filtered_logs = [log for log in filtered_logs if tags.intersection(set(log.tags))]
        
        # 时间过滤
        if "start_time" in filters:
            start = datetime.fromisoformat(filters["start_time"])
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start]
        if "end_time" in filters:
            end = datetime.fromisoformat(filters["end_time"])
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end]
        
        # 排序
        filtered_logs = sorted(filtered_logs, key=lambda l: l.timestamp, reverse=True)
        
        total = len(filtered_logs)
        paginated = filtered_logs[offset:offset + limit]
        
        return {
            "operation": "query",
            "total": total,
            "returned": len(paginated),
            "offset": offset,
            "limit": limit,
            "logs": [log.to_dict() for log in paginated],
        }
    
    def _analyze_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析日志"""
        import uuid
        
        analysis_id = str(uuid.uuid4())
        
        # 确定分析范围
        filters = input_data.get("filters", {})
        logs_to_analyze = self._logs
        
        if "start_time" in filters:
            start = datetime.fromisoformat(filters["start_time"])
            logs_to_analyze = [log for log in logs_to_analyze if log.timestamp >= start]
        if "end_time" in filters:
            end = datetime.fromisoformat(filters["end_time"])
            logs_to_analyze = [log for log in logs_to_analyze if log.timestamp <= end]
        if "level" in filters:
            logs_to_analyze = [log for log in logs_to_analyze if log.level.value == filters["level"]]
        if "source" in filters:
            logs_to_analyze = [log for log in logs_to_analyze if log.source == filters["source"]]
        
        # 级别分布
        level_distribution: Dict[str, int] = {}
        for log in logs_to_analyze:
            level_distribution[log.level.value] = level_distribution.get(log.level.value, 0) + 1
        
        # 源分布
        source_distribution: Dict[str, int] = {}
        for log in logs_to_analyze:
            source_distribution[log.source] = source_distribution.get(log.source, 0) + 1
        
        # 时间序列（按小时）
        time_series: Dict[str, int] = {}
        for log in logs_to_analyze:
            hour_key = log.timestamp.strftime("%Y-%m-%d %H:00")
            time_series[hour_key] = time_series.get(hour_key, 0) + 1
        
        # 模式检测（简单的重复消息检测）
        message_counts: Dict[str, int] = {}
        for log in logs_to_analyze:
            message_counts[log.message] = message_counts.get(log.message, 0) + 1
        
        patterns = [
            {"message": msg, "count": count, "type": "repeated_message"}
            for msg, count in message_counts.items()
            if count > 1
        ]
        patterns = sorted(patterns, key=lambda p: p["count"], reverse=True)[:10]
        
        # 异常检测（错误率突增）
        anomalies = []
        error_logs = [log for log in logs_to_analyze if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        if len(error_logs) > len(logs_to_analyze) * 0.1:  # 错误率超过10%
            anomalies.append({
                "type": "high_error_rate",
                "error_count": len(error_logs),
                "total_count": len(logs_to_analyze),
                "error_rate": len(error_logs) / len(logs_to_analyze) if logs_to_analyze else 0,
                "message": "错误率超过10%",
            })
        
        result = LogAnalysisResult(
            analysis_id=analysis_id,
            timestamp=datetime.now(),
            total_logs=len(logs_to_analyze),
            level_distribution=level_distribution,
            source_distribution=source_distribution,
            time_series=time_series,
            patterns=patterns,
            anomalies=anomalies,
        )
        self._analysis_results[analysis_id] = result
        
        return {
            "operation": "analyze",
            "analysis_id": analysis_id,
            "analysis": result.to_dict(),
        }
    
    def _archive_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """归档日志"""
        filters = input_data.get("filters", {})
        name = input_data.get("name", f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        logs_to_archive = self._logs
        
        if "start_time" in filters:
            start = datetime.fromisoformat(filters["start_time"])
            logs_to_archive = [log for log in logs_to_archive if log.timestamp >= start]
        if "end_time" in filters:
            end = datetime.fromisoformat(filters["end_time"])
            logs_to_archive = [log for log in logs_to_archive if log.timestamp <= end]
        if "level" in filters:
            logs_to_archive = [log for log in logs_to_archive if log.level.value == filters["level"]]
        if "source" in filters:
            logs_to_archive = [log for log in logs_to_archive if log.source == filters["source"]]
        
        if not logs_to_archive:
            return {"operation": "archive", "error": "没有符合条件的日志可归档", "success": False}
        
        archive = self._create_archive_from_logs(logs_to_archive, name, filters)
        
        # 从活跃日志中移除已归档的
        archived_ids = {log.log_id for log in logs_to_archive}
        self._logs = [log for log in self._logs if log.log_id not in archived_ids]
        
        return {
            "operation": "archive",
            "archive_id": archive.archive_id,
            "name": archive.name,
            "log_count": archive.log_count,
            "archived": True,
        }
    
    def _create_archive_from_logs(self, logs: List[LogEntry], name: str,
                                   filters: Dict[str, Any] = None) -> LogArchive:
        """从日志创建归档"""
        import uuid
        
        archive = LogArchive(
            archive_id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(),
            log_count=len(logs),
            size_bytes=sum(len(log.message.encode('utf-8')) for log in logs),
            date_range_start=min(log.timestamp for log in logs) if logs else datetime.now(),
            date_range_end=max(log.timestamp for log in logs) if logs else datetime.now(),
            filters=filters or {},
        )
        self._archives[archive.archive_id] = archive
        return archive
    
    def _get_archive_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取归档信息"""
        archive_id = input_data.get("archive_id")
        if not archive_id or archive_id not in self._archives:
            return {"operation": "get_archive", "error": "归档不存在"}
        
        archive = self._archives[archive_id]
        return {
            "operation": "get_archive",
            "archive": archive.to_dict(),
        }
    
    def _list_archives_operation(self) -> Dict[str, Any]:
        """列出所有归档"""
        archives = sorted(self._archives.values(), key=lambda a: a.created_at, reverse=True)
        return {
            "operation": "list_archives",
            "total": len(archives),
            "archives": [a.to_dict() for a in archives],
        }
    
    def _purge_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """清理日志"""
        older_than_days = input_data.get("older_than_days")
        level = input_data.get("level")
        
        logs_before = len(self._logs)
        
        if older_than_days:
            cutoff = datetime.now() - timedelta(days=older_than_days)
            self._logs = [log for log in self._logs if log.timestamp >= cutoff]
        
        if level:
            self._logs = [log for log in self._logs if log.level.value != level]
        
        logs_after = len(self._logs)
        purged = logs_before - logs_after
        
        return {
            "operation": "purge",
            "purged_count": purged,
            "remaining_count": logs_after,
        }
    
    def _configure_collector_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """配置日志收集器"""
        collector_name = input_data.get("collector_name")
        config = input_data.get("config", {})
        
        if collector_name in self._collectors:
            self._collectors[collector_name].update(config)
        else:
            self._collectors[collector_name] = config
        
        return {
            "operation": "configure_collector",
            "collector_name": collector_name,
            "config": self._collectors[collector_name],
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级日志模块校验开始")
        
        checks = []
        
        # 1. 校验日志存储
        if isinstance(self._logs, list):
            checks.append("logs_valid")
        
        # 2. 校验归档存储
        if isinstance(self._archives, dict):
            checks.append("archives_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验收集器
        if isinstance(self._collectors, dict):
            checks.append("collectors_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="log_validation",
                message="三级日志模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="log_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("log_count", len(self._logs))
        snapshot.set_state("archive_count", len(self._archives))
        snapshot.set_state("analysis_count", len(self._analysis_results))
        snapshot.set_state("collectors", list(self._collectors.keys()))
        snapshot.metadata["module_type"] = "Level3LogModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def collect_log(self, level: LogLevel, source: str, message: str,
                    context: Dict[str, Any] = None, tags: List[str] = None,
                    trace_id: Optional[str] = None) -> LogEntry:
        """收集日志"""
        import uuid
        log = LogEntry(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            level=level,
            source=source,
            message=message,
            context=context or {},
            tags=tags or [],
            trace_id=trace_id,
        )
        self._logs.append(log)
        return log
    
    def query_logs(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[LogEntry]:
        """查询日志"""
        result = self._query_operation({"filters": filters or {}, "limit": limit})
        # 返回原始日志对象（简化处理）
        return self._logs[:limit]
    
    def analyze_logs(self, filters: Dict[str, Any] = None) -> LogAnalysisResult:
        """分析日志"""
        result = self._analyze_operation({"filters": filters or {}})
        analysis_id = result.get("analysis_id")
        return self._analysis_results.get(analysis_id)
    
    def archive_logs(self, name: str, filters: Dict[str, Any] = None) -> LogArchive:
        """归档日志"""
        result = self._archive_operation({"name": name, "filters": filters or {}})
        archive_id = result.get("archive_id")
        return self._archives.get(archive_id)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3LogModule",
    "LogEntry",
    "LogLevel",
    "LogArchive",
    "LogArchiveStatus",
    "LogAnalysisResult",
]
