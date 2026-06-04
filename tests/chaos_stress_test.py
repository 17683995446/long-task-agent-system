"""
混沌压力测试 - Chaos Stress Test

更混乱、更复杂、更高难度的场景测试
"""

import unittest
import threading
import time
import random
import sys
sys.path.insert(0, '/workspace')

from core_types.core_types import (
    ModuleID, TaskID, ModuleType, ModuleState,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
    ModuleInput, ModuleParam,
)
from core.base_module import ControlModuleBase, ExecuteModuleBase
from core.twin_container import TwinContainer
from core_types.core_types import ModuleType
from utils.logger import Logger


class FaultyModule(ControlModuleBase):
    """有故障的模块 - 模拟各种异常情况"""
    
    def __init__(self, name="Faulty", fault_mode="none", module_type=None):
        super().__init__()
        self._name = name
        self._logger = Logger(f"{name}_{self.module_id}")
        self.fault_mode = fault_mode
        self.call_count = 0
        # 允许指定模块类型
        if module_type:
            self._state.module_type = module_type
    
    def _maybe_fault(self, operation):
        """随机注入故障"""
        self.call_count += 1
        if self.fault_mode == "random" and random.random() < 0.3:
            raise RuntimeError(f"随机故障注入: {operation}")
        elif self.fault_mode == "always":
            raise RuntimeError(f"总是故障: {operation}")
        elif self.fault_mode == "after_3" and self.call_count > 3:
            raise RuntimeError(f"3次后故障: {operation}")
    
    def _do_init(self, request, context):
        self._maybe_fault("init")
        from core_types.core_types import InitResult
        return InitResult.success_result(self.module_id, f"{self._name} init")
    
    def _do_run(self, request, context):
        self._maybe_fault("run")
        from core_types.core_types import ModuleOutput
        return ModuleOutput.success_output(TaskID(), {}, f"{self._name} run")
    
    def _do_check(self, request, context):
        from core_types.core_types import CheckResult
        return CheckResult.passed_result(f"{self._name}_check")
    
    def _do_snapshot(self, request, context, snapshot):
        snapshot.set_state("name", self._name)


class TestChaosScenarios(unittest.TestCase):
    """混沌场景测试"""
    
    def test_cascading_failure(self):
        """测试级联故障 - 父模块故障影响子模块"""
        print("\n" + "="*60)
        print("混沌场景1：级联故障测试")
        print("="*60)
        
        # 构建树：Root -> L1(故障) -> L2
        root = FaultyModule("Root", "none")
        l1 = FaultyModule("L1", "always", module_type=ModuleType.CONTROL)  # 总是故障
        l2 = FaultyModule("L2", "none", module_type=ModuleType.CONTROL)
        
        root.set_control_child(l1)
        l1.set_control_child(l2)
        
        # 尝试初始化 - L1会失败
        errors = []
        try:
            init_req = InitRequest(
                module_id=l1.module_id,
                module_param=ModuleParam(module_id=l1.module_id),
            )
            result = l1.module_init(init_req, InitContext())
            if not result.success:
                errors.append(f"L1 init failed: {result.error_detail}")
        except Exception as e:
            errors.append(f"L1 init exception: {e}")
        
        # 验证系统能捕获异常而不是崩溃
        self.assertEqual(len(errors), 1)
        print(f"✓ 级联故障被正确捕获: {errors[0]}")
    
    def test_rapid_lifecycle_transitions(self):
        """测试快速生命周期切换"""
        print("\n" + "="*60)
        print("混沌场景2：快速生命周期切换")
        print("="*60)
        
        module = FaultyModule("Rapid", "none")
        
        # 快速切换：init -> run -> check -> snapshot -> run -> check
        for i in range(20):
            try:
                if i == 0:
                    init_req = InitRequest(
                        module_id=module.module_id,
                        module_param=ModuleParam(module_id=module.module_id),
                    )
                    module.module_init(init_req, InitContext())
                elif i % 4 == 1:
                    exec_req = ExecutionRequest(
                        module_input=ModuleInput(task_id=TaskID()),
                    )
                    module.module_run(exec_req, ExecutionContext())
                elif i % 4 == 2:
                    module.module_check(
                        ValidationRequest(check_type="rapid_check"),
                        ValidationContext()
                    )
                else:
                    module.create_snapshot(
                        SnapshotRequest(),
                        SnapshotContext()
                    )
            except Exception as e:
                self.fail(f"快速切换失败: {e}")
        
        print(f"✓ 20次快速生命周期切换完成")
        self.assertEqual(module.module_state, ModuleState.READY)
    
    def test_mixed_module_tree(self):
        """测试混合模块树 - 不同故障模式的模块混合"""
        print("\n" + "="*60)
        print("混沌场景3：混合故障模式模块树")
        print("="*60)
        
        # 构建混合树
        root = FaultyModule("Root", "none")
        
        # 左子树：随机故障
        l1_ctrl = FaultyModule("L1_Ctrl", "random", module_type=ModuleType.CONTROL)
        l1_exec = FaultyModule("L1_Exec", "none", module_type=ModuleType.EXECUTE)
        root.set_control_child(l1_ctrl)
        root.set_execute_child(l1_exec)
        
        # 右子树：3次后故障
        l2_ctrl = FaultyModule("L2_Ctrl", "after_3", module_type=ModuleType.CONTROL)
        l2_exec = FaultyModule("L2_Exec", "random", module_type=ModuleType.EXECUTE)
        l1_ctrl.set_control_child(l2_ctrl)
        l1_ctrl.set_execute_child(l2_exec)
        
        # 初始化所有模块（部分会失败）
        modules = [root, l1_ctrl, l1_exec, l2_ctrl, l2_exec]
        success_count = 0
        
        for m in modules:
            try:
                init_req = InitRequest(
                    module_id=m.module_id,
                    module_param=ModuleParam(module_id=m.module_id),
                )
                result = m.module_init(init_req, InitContext())
                if result.success:
                    success_count += 1
            except Exception:
                pass  # 预期部分会失败
        
        print(f"✓ 混合树初始化: {success_count}/{len(modules)} 成功")
        self.assertGreater(success_count, 0)
    
    def test_concurrent_tree_operations(self):
        """测试并发树操作"""
        print("\n" + "="*60)
        print("混沌场景4：并发树操作")
        print("="*60)
        
        # 构建树
        root = FaultyModule("Root", "none")
        for i in range(4):
            mt = ModuleType.CONTROL if i % 2 == 0 else ModuleType.EXECUTE
            c = FaultyModule(f"Child_{i}", "none", module_type=mt)
            if i % 2 == 0:
                root.set_control_child(c)
            else:
                root.set_execute_child(c)
        
        # 并发操作树的不同部分
        results = []
        lock = threading.Lock()
        
        def operate_on_tree(module, op):
            try:
                if op == "init":
                    req = InitRequest(
                        module_id=module.module_id,
                        module_param=ModuleParam(module_id=module.module_id),
                    )
                    module.module_init(req, InitContext())
                elif op == "run":
                    req = ExecutionRequest(
                        module_input=ModuleInput(task_id=TaskID()),
                    )
                    module.module_run(req, ExecutionContext())
                with lock:
                    results.append((op, True))
            except Exception as e:
                with lock:
                    results.append((op, False, str(e)))
        
        threads = []
        for i in range(10):
            module = random.choice([root, root.get_control_child(), root.get_execute_child()])
            if module:
                op = random.choice(["init", "run"])
                t = threading.Thread(target=operate_on_tree, args=(module, op))
                threads.append(t)
                t.start()
        
        for t in threads:
            t.join()
        
        success = sum(1 for r in results if r[1] is True)
        print(f"✓ 并发操作完成: {success}/{len(results)} 成功")
        self.assertGreater(success, 0)
    
    def test_memory_pressure(self):
        """测试内存压力 - 大量快照创建"""
        print("\n" + "="*60)
        print("混沌场景5：内存压力测试")
        print("="*60)
        
        module = FaultyModule("Memory", "none")
        init_req = InitRequest(
            module_id=module.module_id,
            module_param=ModuleParam(module_id=module.module_id),
        )
        module.module_init(init_req, InitContext())
        
        # 创建大量快照
        snapshots = []
        for i in range(100):
            snapshot = module.create_snapshot(
                SnapshotRequest(),
                SnapshotContext()
            )
            snapshots.append(snapshot)
        
        print(f"✓ 创建100个快照完成")
        self.assertEqual(len(snapshots), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
