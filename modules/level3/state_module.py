"""
阶段37：三级状态模块
Level3StateModule

职责定义：
- 状态机管理
- 状态转换
- 状态持久化
"""

from typing import Optional, Dict, Any, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

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


class StateMachineStatus(Enum):
    """状态机状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class State:
    """状态定义"""
    state_id: str
    name: str
    description: str = ""
    is_initial: bool = False
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    entry_actions: List[str] = field(default_factory=list)
    exit_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "name": self.name,
            "description": self.description,
            "is_initial": self.is_initial,
            "is_final": self.is_final,
            "metadata": self.metadata,
            "entry_actions": self.entry_actions,
            "exit_actions": self.exit_actions,
        }


@dataclass
class Transition:
    """状态转换定义"""
    transition_id: str
    from_state: str
    to_state: str
    event: str
    condition: Optional[str] = None
    actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "event": self.event,
            "condition": self.condition,
            "actions": self.actions,
            "metadata": self.metadata,
        }


@dataclass
class StateMachine:
    """状态机"""
    machine_id: str
    name: str
    states: Dict[str, State] = field(default_factory=dict)
    transitions: List[Transition] = field(default_factory=list)
    current_state: Optional[str] = None
    status: StateMachineStatus = StateMachineStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "name": self.name,
            "current_state": self.current_state,
            "status": self.status.value,
            "state_count": len(self.states),
            "transition_count": len(self.transitions),
            "created_at": self.created_at.isoformat(),
            "state_history": self.state_history,
            "metadata": self.metadata,
        }


@dataclass
class StateSnapshot:
    """状态快照"""
    snapshot_id: str
    machine_id: str
    state_id: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "machine_id": self.machine_id,
            "state_id": self.state_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class Level3StateModule(ExecuteModuleBase):
    """
    三级状态模块
    
    职责：
    1. 状态机管理
    2. 状态转换
    3. 状态持久化
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3StateModule"
        self._logger = Logger(f"L3ST_{self.module_id}")
        
        # 状态机存储
        self._state_machines: Dict[str, StateMachine] = {}
        # 当前活跃状态机
        self._active_machine: Optional[StateMachine] = None
        # 状态快照
        self._state_snapshots: List[StateSnapshot] = {}
        # 状态持久化存储
        self._persisted_states: Dict[str, Dict[str, Any]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("三级状态模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._state_machines = {}
            self._active_machine = None
            self._state_snapshots = {}
            self._persisted_states = {}
            
            self._logger.info("三级状态模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="三级状态模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级状态模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3ST_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "auto_persist": True,
            "max_history_per_machine": 100,
            "validate_transitions": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("state_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("三级状态模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_machine")
            
            if operation == "create_machine":
                result = self._create_machine_operation(input_data)
            elif operation == "add_state":
                result = self._add_state_operation(input_data)
            elif operation == "add_transition":
                result = self._add_transition_operation(input_data)
            elif operation == "trigger_event":
                result = self._trigger_event_operation(input_data)
            elif operation == "get_machine":
                result = self._get_machine_operation(input_data)
            elif operation == "persist_state":
                result = self._persist_state_operation(input_data)
            elif operation == "restore_state":
                result = self._restore_state_operation(input_data)
            elif operation == "get_history":
                result = self._get_history_operation(input_data)
            elif operation == "list_machines":
                result = self._list_machines_operation()
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("三级状态模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level3StateModule",
                    "state_summary": {
                        "total_machines": len(self._state_machines),
                        "active_machine": self._active_machine.machine_id if self._active_machine else None,
                        "total_snapshots": len(self._state_snapshots),
                    },
                },
                message="三级状态模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"三级状态模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3ST_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_machine_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建状态机"""
        import uuid
        
        machine_id = str(uuid.uuid4())
        machine = StateMachine(
            machine_id=machine_id,
            name=input_data.get("name", f"machine_{machine_id[:8]}"),
            metadata=input_data.get("metadata", {}),
        )
        self._state_machines[machine_id] = machine
        self._active_machine = machine
        
        return {
            "operation": "create_machine",
            "machine_id": machine_id,
            "name": machine.name,
            "created": True,
        }
    
    def _add_state_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加状态"""
        machine_id = input_data.get("machine_id")
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "add_state", "error": "状态机不存在", "success": False}
        
        machine = self._state_machines[machine_id]
        state_id = input_data.get("state_id")
        
        state = State(
            state_id=state_id,
            name=input_data.get("name", state_id),
            description=input_data.get("description", ""),
            is_initial=input_data.get("is_initial", False),
            is_final=input_data.get("is_final", False),
            metadata=input_data.get("metadata", {}),
            entry_actions=input_data.get("entry_actions", []),
            exit_actions=input_data.get("exit_actions", []),
        )
        machine.states[state_id] = state
        
        # 如果是初始状态，设置当前状态
        if state.is_initial and machine.current_state is None:
            machine.current_state = state_id
            machine.status = StateMachineStatus.RUNNING
            self._record_state_change(machine_id, None, state_id, "initialization")
        
        return {
            "operation": "add_state",
            "machine_id": machine_id,
            "state_id": state_id,
            "success": True,
        }
    
    def _add_transition_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加转换"""
        machine_id = input_data.get("machine_id")
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "add_transition", "error": "状态机不存在", "success": False}
        
        machine = self._state_machines[machine_id]
        from_state = input_data.get("from_state")
        to_state = input_data.get("to_state")
        
        # 验证状态存在
        if self._config.get("validate_transitions", True):
            if from_state not in machine.states:
                return {"operation": "add_transition", "error": f"源状态 {from_state} 不存在", "success": False}
            if to_state not in machine.states:
                return {"operation": "add_transition", "error": f"目标状态 {to_state} 不存在", "success": False}
        
        import uuid
        transition = Transition(
            transition_id=str(uuid.uuid4()),
            from_state=from_state,
            to_state=to_state,
            event=input_data.get("event", "default"),
            condition=input_data.get("condition"),
            actions=input_data.get("actions", []),
            metadata=input_data.get("metadata", {}),
        )
        machine.transitions.append(transition)
        
        return {
            "operation": "add_transition",
            "machine_id": machine_id,
            "transition_id": transition.transition_id,
            "from_state": from_state,
            "to_state": to_state,
            "success": True,
        }
    
    def _trigger_event_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """触发事件进行状态转换"""
        machine_id = input_data.get("machine_id")
        event = input_data.get("event")
        
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "trigger_event", "error": "状态机不存在", "success": False}
        
        machine = self._state_machines[machine_id]
        
        if machine.current_state is None:
            return {"operation": "trigger_event", "error": "当前状态未设置", "success": False}
        
        # 查找匹配的转换
        matching_transitions = [
            t for t in machine.transitions
            if t.from_state == machine.current_state and t.event == event
        ]
        
        if not matching_transitions:
            return {
                "operation": "trigger_event",
                "error": f"从状态 '{machine.current_state}' 没有针对事件 '{event}' 的转换",
                "current_state": machine.current_state,
                "success": False,
            }
        
        # 执行第一个匹配的转换
        transition = matching_transitions[0]
        old_state = machine.current_state
        new_state = transition.to_state
        
        # 执行退出动作
        if old_state in machine.states:
            for action in machine.states[old_state].exit_actions:
                self._logger.info(f"执行退出动作: {action}")
        
        machine.current_state = new_state
        
        # 执行进入动作
        if new_state in machine.states:
            for action in machine.states[new_state].entry_actions:
                self._logger.info(f"执行进入动作: {action}")
        
        # 执行转换动作
        for action in transition.actions:
            self._logger.info(f"执行转换动作: {action}")
        
        # 记录状态变更
        self._record_state_change(machine_id, old_state, new_state, event)
        
        # 检查是否到达终止状态
        if new_state in machine.states and machine.states[new_state].is_final:
            machine.status = StateMachineStatus.COMPLETED
        
        # 自动持久化
        if self._config.get("auto_persist", True):
            self._persist_machine_state(machine_id)
        
        return {
            "operation": "trigger_event",
            "machine_id": machine_id,
            "event": event,
            "from_state": old_state,
            "to_state": new_state,
            "transition_id": transition.transition_id,
            "success": True,
        }
    
    def _get_machine_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取状态机信息"""
        machine_id = input_data.get("machine_id")
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "get_machine", "error": "状态机不存在"}
        
        machine = self._state_machines[machine_id]
        return {
            "operation": "get_machine",
            "machine": machine.to_dict(),
            "states": {sid: s.to_dict() for sid, s in machine.states.items()},
            "transitions": [t.to_dict() for t in machine.transitions],
        }
    
    def _persist_state_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """持久化状态"""
        machine_id = input_data.get("machine_id")
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "persist_state", "error": "状态机不存在", "success": False}
        
        result = self._persist_machine_state(machine_id)
        return {
            "operation": "persist_state",
            "machine_id": machine_id,
            **result,
        }
    
    def _persist_machine_state(self, machine_id: str) -> Dict[str, Any]:
        """持久化状态机状态"""
        machine = self._state_machines[machine_id]
        import uuid
        
        snapshot = StateSnapshot(
            snapshot_id=str(uuid.uuid4()),
            machine_id=machine_id,
            state_id=machine.current_state or "",
            timestamp=datetime.now(),
            data={
                "current_state": machine.current_state,
                "status": machine.status.value,
                "state_history": machine.state_history,
                "metadata": machine.metadata,
            },
        )
        self._state_snapshots[snapshot.snapshot_id] = snapshot
        self._persisted_states[machine_id] = snapshot.data
        
        return {
            "snapshot_id": snapshot.snapshot_id,
            "persisted": True,
            "timestamp": snapshot.timestamp.isoformat(),
        }
    
    def _restore_state_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """恢复状态"""
        machine_id = input_data.get("machine_id")
        snapshot_id = input_data.get("snapshot_id")
        
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "restore_state", "error": "状态机不存在", "success": False}
        
        machine = self._state_machines[machine_id]
        
        if snapshot_id and snapshot_id in self._state_snapshots:
            snapshot = self._state_snapshots[snapshot_id]
            machine.current_state = snapshot.data.get("current_state")
            machine.status = StateMachineStatus(snapshot.data.get("status", "idle"))
            machine.state_history = snapshot.data.get("state_history", [])
            machine.metadata = snapshot.data.get("metadata", {})
        elif machine_id in self._persisted_states:
            data = self._persisted_states[machine_id]
            machine.current_state = data.get("current_state")
            machine.status = StateMachineStatus(data.get("status", "idle"))
            machine.state_history = data.get("state_history", [])
            machine.metadata = data.get("metadata", {})
        else:
            return {"operation": "restore_state", "error": "没有找到可恢复的状态", "success": False}
        
        return {
            "operation": "restore_state",
            "machine_id": machine_id,
            "restored_state": machine.current_state,
            "success": True,
        }
    
    def _get_history_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取状态历史"""
        machine_id = input_data.get("machine_id")
        limit = input_data.get("limit", 50)
        
        if not machine_id or machine_id not in self._state_machines:
            return {"operation": "get_history", "error": "状态机不存在"}
        
        machine = self._state_machines[machine_id]
        history = machine.state_history[-limit:] if machine.state_history else []
        
        return {
            "operation": "get_history",
            "machine_id": machine_id,
            "total_entries": len(machine.state_history),
            "returned": len(history),
            "history": history,
        }
    
    def _list_machines_operation(self) -> Dict[str, Any]:
        """列出所有状态机"""
        return {
            "operation": "list_machines",
            "machines": [
                {
                    "machine_id": m.machine_id,
                    "name": m.name,
                    "current_state": m.current_state,
                    "status": m.status.value,
                    "state_count": len(m.states),
                }
                for m in self._state_machines.values()
            ],
        }
    
    def _record_state_change(self, machine_id: str, from_state: Optional[str],
                             to_state: str, event: str) -> None:
        """记录状态变更"""
        machine = self._state_machines[machine_id]
        entry = {
            "from_state": from_state,
            "to_state": to_state,
            "event": event,
            "timestamp": datetime.now().isoformat(),
        }
        machine.state_history.append(entry)
        
        # 限制历史记录大小
        max_history = self._config.get("max_history_per_machine", 100)
        if len(machine.state_history) > max_history:
            machine.state_history = machine.state_history[-max_history:]
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("三级状态模块校验开始")
        
        checks = []
        
        # 1. 校验状态机存储
        if isinstance(self._state_machines, dict):
            checks.append("machines_valid")
        
        # 2. 校验快照存储
        if isinstance(self._state_snapshots, dict):
            checks.append("snapshots_valid")
        
        # 3. 校验模块状态
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        # 4. 校验持久化配置
        if self._config.get("auto_persist", False) is not None:
            checks.append("persist_config_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="state_validation",
                message="三级状态模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="state_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("machines", {
            mid: m.to_dict() for mid, m in self._state_machines.items()
        })
        snapshot.set_state("active_machine", self._active_machine.machine_id if self._active_machine else None)
        snapshot.set_state("snapshot_count", len(self._state_snapshots))
        snapshot.set_state("persisted_states", list(self._persisted_states.keys()))
        snapshot.metadata["module_type"] = "Level3StateModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def create_state_machine(self, name: str, metadata: Dict[str, Any] = None) -> StateMachine:
        """创建状态机"""
        import uuid
        machine = StateMachine(
            machine_id=str(uuid.uuid4()),
            name=name,
            metadata=metadata or {},
        )
        self._state_machines[machine.machine_id] = machine
        self._active_machine = machine
        return machine
    
    def get_state_machine(self, machine_id: str) -> Optional[StateMachine]:
        """获取状态机"""
        return self._state_machines.get(machine_id)
    
    def trigger_event(self, machine_id: str, event: str) -> Dict[str, Any]:
        """触发事件"""
        return self._trigger_event_operation({"machine_id": machine_id, "event": event})
    
    def get_state_history(self, machine_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取状态历史"""
        result = self._get_history_operation({"machine_id": machine_id, "limit": limit})
        return result.get("history", [])
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level3StateModule",
    "State",
    "Transition",
    "StateMachine",
    "StateMachineStatus",
    "StateSnapshot",
]
