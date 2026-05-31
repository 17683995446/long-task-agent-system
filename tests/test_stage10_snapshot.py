"""
第10阶段验证测试
验证状态快照基础的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from state.snapshot_base import (
    SnapshotType,
    SnapshotState,
    SnapshotMetadata,
    SnapshotValidationResult,
    SnapshotBase,
    CheckpointManager,
)

from core_types.core_types import ModuleID, TaskID, SnapshotData


def test_snapshot_type():
    """测试快照类型枚举"""
    print("测试快照类型枚举...")
    
    assert SnapshotType.FULL is not None
    assert SnapshotType.DELTA is not None
    assert SnapshotType.MINIMAL is not None
    assert SnapshotType.CHECKPOINT is not None
    
    print("✓ 快照类型枚举测试通过")


def test_snapshot_state():
    """测试快照状态枚举"""
    print("测试快照状态枚举...")
    
    assert SnapshotState.CREATING is not None
    assert SnapshotState.VALID is not None
    assert SnapshotState.INVALID is not None
    assert SnapshotState.RESTORING is not None
    
    print("✓ 快照状态枚举测试通过")


def test_snapshot_metadata():
    """测试快照元数据"""
    print("测试快照元数据...")
    
    module_id = ModuleID()
    task_id = TaskID()
    
    metadata = SnapshotMetadata(
        snapshot_type=SnapshotType.FULL,
        module_id=module_id,
        module_name="TestModule",
        task_id=task_id,
        description="测试快照",
        tags=["test", "important"],
    )
    
    assert metadata.snapshot_type == SnapshotType.FULL
    assert metadata.module_name == "TestModule"
    assert metadata.description == "测试快照"
    assert len(metadata.tags) == 2
    
    # 测试转换为字典
    metadata_dict = metadata.to_dict()
    assert metadata_dict["snapshot_type"] == "FULL"
    assert metadata_dict["module_name"] == "TestModule"
    
    # 测试从字典创建
    restored = SnapshotMetadata.from_dict(metadata_dict)
    assert restored.snapshot_type == SnapshotType.FULL
    assert restored.module_name == "TestModule"
    
    print("✓ 快照元数据测试通过")


def test_snapshot_validation_result():
    """测试快照校验结果"""
    print("测试快照校验结果...")
    
    result = SnapshotValidationResult(
        valid=True,
        snapshot_id="test_snapshot",
    )
    
    assert result.valid == True
    
    # 添加通过的校验
    result.add_check("check1", True)
    assert result.valid == True
    
    # 添加失败的校验
    result.add_check("check2", False)
    assert result.valid == False
    
    # 添加错误
    result.add_error("发生错误")
    assert len(result.errors) == 1
    assert result.valid == False
    
    # 添加警告
    result.add_warning("这是一个警告")
    assert len(result.warnings) == 1
    
    print("✓ 快照校验结果测试通过")


def test_create_snapshot():
    """测试创建快照"""
    print("测试创建快照...")
    
    snapshot_base = SnapshotBase()
    module_id = ModuleID()
    
    state_data = {
        "counter": 100,
        "name": "test",
        "items": [1, 2, 3],
    }
    
    snapshot = snapshot_base.create_snapshot(
        state_data=state_data,
        snapshot_type=SnapshotType.FULL,
        module_id=module_id,
        module_name="TestModule",
        description="测试快照",
    )
    
    assert snapshot.snapshot_id is not None
    assert snapshot.snapshot_version == "1.0"
    assert snapshot.state_data["counter"] == 100
    assert snapshot.state_data["name"] == "test"
    assert "checksum" in snapshot.metadata
    
    print("✓ 创建快照测试通过")


def test_restore_snapshot():
    """测试恢复快照"""
    print("测试恢复快照...")
    
    snapshot_base = SnapshotBase()
    module_id = ModuleID()
    
    state_data = {
        "counter": 100,
        "name": "test",
    }
    
    snapshot = snapshot_base.create_snapshot(
        state_data=state_data,
        module_id=module_id,
    )
    
    # 恢复快照
    restored_state = snapshot_base.restore_from_snapshot(snapshot)
    
    assert restored_state["counter"] == 100
    assert restored_state["name"] == "test"
    
    print("✓ 恢复快照测试通过")


def test_validate_snapshot():
    """测试校验快照"""
    print("测试校验快照...")
    
    snapshot_base = SnapshotBase()
    module_id = ModuleID()
    
    state_data = {"key": "value"}
    
    snapshot = snapshot_base.create_snapshot(
        state_data=state_data,
        module_id=module_id,
    )
    
    # 校验有效快照
    result = snapshot_base.validate_snapshot(snapshot)
    assert result.valid == True
    assert len(result.errors) == 0
    
    print("✓ 校验快照测试通过")


def test_validate_invalid_snapshot():
    """测试校验无效快照"""
    print("测试校验无效快照...")
    
    snapshot_base = SnapshotBase()
    
    # 创建无效快照（缺少校验和）
    snapshot = SnapshotData(
        module_id=ModuleID(),
        snapshot_id="invalid",
        snapshot_version="1.0",
        state_data={"key": "value"},
        metadata={},  # 缺少校验和
    )
    
    result = snapshot_base.validate_snapshot(snapshot)
    # 应该有警告但没有错误
    assert len(result.warnings) > 0
    
    print("✓ 校验无效快照测试通过")


def test_quick_validate():
    """测试快速校验"""
    print("测试快速校验...")
    
    snapshot_base = SnapshotBase()
    
    state_data = {"key": "value"}
    
    snapshot = snapshot_base.create_snapshot(state_data=state_data)
    
    # 快速校验应该通过
    assert snapshot_base.quick_validate(snapshot) == True
    
    # 修改数据后应该失败
    snapshot.state_data["key"] = "modified"
    assert snapshot_base.quick_validate(snapshot) == False
    
    print("✓ 快速校验测试通过")


def test_snapshot_history():
    """测试快照历史"""
    print("测试快照历史...")
    
    snapshot_base = SnapshotBase()
    
    # 创建多个快照
    for i in range(5):
        snapshot_base.create_snapshot(
            state_data={"counter": i},
            description=f"快照 {i}",
        )
    
    # 获取历史
    history = snapshot_base.get_snapshot_history(limit=3)
    assert len(history) == 3
    
    # 获取最新快照
    latest = snapshot_base.get_latest_snapshot()
    assert latest is not None
    assert latest.state_data["counter"] == 4
    
    # 清除历史
    count = snapshot_base.clear_history()
    assert count == 5
    assert snapshot_base.get_latest_snapshot() is None
    
    print("✓ 快照历史测试通过")


def test_delta_snapshot():
    """测试增量快照"""
    print("测试增量快照...")
    
    snapshot_base = SnapshotBase()
    
    # 创建基础状态和快照
    base_state = {"a": 1, "b": 2, "c": 3}
    base_snapshot = snapshot_base.create_snapshot(
        state_data=base_state,
        snapshot_type=SnapshotType.FULL,
    )
    
    # 修改状态
    current_state = {"a": 1, "b": 20, "d": 4}  # b修改，c删除，d新增
    
    # 创建增量快照
    delta_snapshot = snapshot_base.create_delta_snapshot(
        current_state=current_state,
        base_snapshot=base_snapshot,
    )
    
    assert delta_snapshot.metadata.get("type") == "DELTA"
    assert "base_snapshot_id" in delta_snapshot.metadata
    
    # 验证增量数据
    delta = delta_snapshot.state_data
    assert "added" in delta
    assert "modified" in delta
    assert "removed" in delta
    assert delta["added"]["d"] == 4
    assert delta["modified"]["b"]["new"] == 20
    assert "c" in delta["removed"]
    
    print("✓ 增量快照测试通过")


def test_apply_delta():
    """测试应用增量"""
    print("测试应用增量...")
    
    snapshot_base = SnapshotBase()
    
    base_state = {"a": 1, "b": 2, "c": 3}
    delta = {
        "added": {"d": 4},
        "modified": {"b": {"old": 2, "new": 20}},
        "removed": ["c"],
    }
    
    # 应用增量
    result = snapshot_base.apply_delta(base_state, delta)
    
    assert result["a"] == 1  # 未改变
    assert result["b"] == 20  # 已修改
    assert "c" not in result  # 已删除
    assert result["d"] == 4  # 已新增
    
    print("✓ 应用增量测试通过")


def test_export_import_snapshot():
    """测试导出导入快照"""
    print("测试导出导入快照...")
    
    snapshot_base = SnapshotBase()
    module_id = ModuleID()
    
    state_data = {"key": "value", "number": 123}
    
    snapshot = snapshot_base.create_snapshot(
        state_data=state_data,
        module_id=module_id,
        module_name="TestModule",
    )
    
    # 导出
    json_str = snapshot_base.export_snapshot(snapshot)
    assert "snapshot_id" in json_str
    assert "state_data" in json_str
    
    # 导入
    imported = snapshot_base.import_snapshot(json_str)
    assert imported.snapshot_id == snapshot.snapshot_id
    assert imported.state_data["key"] == "value"
    assert imported.state_data["number"] == 123
    
    print("✓ 导出导入快照测试通过")


def test_get_snapshot_info():
    """测试获取快照信息"""
    print("测试获取快照信息...")
    
    snapshot_base = SnapshotBase()
    
    state_data = {"key1": "value1", "key2": "value2"}
    
    snapshot = snapshot_base.create_snapshot(
        state_data=state_data,
        description="测试快照",
    )
    
    info = snapshot_base.get_snapshot_info(snapshot)
    
    assert info["snapshot_id"] == snapshot.snapshot_id
    assert info["snapshot_version"] == "1.0"
    assert info["size_bytes"] > 0
    assert info["has_checksum"] == True
    assert len(info["state_keys"]) == 2
    
    print("✓ 获取快照信息测试通过")


def test_checkpoint_manager():
    """测试检查点管理器"""
    print("测试检查点管理器...")
    
    manager = CheckpointManager()
    task_id = TaskID()
    module_id = ModuleID()
    
    # 创建模块快照
    snapshot = SnapshotData(
        module_id=module_id,
        state_data={"state": "data"},
    )
    
    # 保存检查点
    checkpoint = manager.save_checkpoint(
        task_id=task_id,
        current_step=50,
        total_steps=100,
        module_snapshots={"module1": snapshot},
        execution_context={"context": "data"},
    )
    
    assert checkpoint.task_id == task_id
    assert checkpoint.current_step == 50
    assert checkpoint.total_steps == 100
    
    # 检查是否存在
    assert manager.has_checkpoint(task_id) == True
    
    # 加载检查点
    loaded = manager.load_checkpoint(task_id)
    assert loaded is not None
    assert loaded.current_step == 50
    
    # 获取所有任务ID
    all_ids = manager.get_all_task_ids()
    assert len(all_ids) == 1
    
    # 移除检查点
    result = manager.remove_checkpoint(task_id)
    assert result == True
    assert manager.has_checkpoint(task_id) == False
    
    print("✓ 检查点管理器测试通过")


def test_version_compatibility():
    """测试版本兼容性"""
    print("测试版本兼容性...")
    
    snapshot_base = SnapshotBase()
    
    # 创建当前版本快照
    snapshot = snapshot_base.create_snapshot(state_data={"key": "value"})
    assert snapshot.snapshot_version == "1.0"
    
    # 恢复应该成功（版本兼容）
    restored = snapshot_base.restore_from_snapshot(snapshot)
    assert restored is not None
    
    print("✓ 版本兼容性测试通过")


def test_incompatible_version():
    """测试不兼容版本"""
    print("测试不兼容版本...")
    
    snapshot_base = SnapshotBase()
    
    # 创建不兼容版本的快照
    snapshot = SnapshotData(
        module_id=ModuleID(),
        snapshot_id="test",
        snapshot_version="2.0",  # 不兼容版本
        state_data={"key": "value"},
        metadata={"checksum": "dummy"},
    )
    
    # 恢复应该失败
    try:
        snapshot_base.restore_from_snapshot(snapshot)
        assert False, "应该抛出ValueError"
    except ValueError as e:
        assert "不兼容" in str(e)
    
    print("✓ 不兼容版本测试通过")


def test_serialization():
    """测试序列化"""
    print("测试序列化...")
    
    snapshot_base = SnapshotBase()
    
    # 包含各种类型的数据
    state_data = {
        "string": "hello",
        "integer": 123,
        "float": 3.14,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"nested": "value"},
        "none": None,
    }
    
    snapshot = snapshot_base.create_snapshot(state_data=state_data)
    
    # 所有数据应该被正确序列化
    assert snapshot.state_data["string"] == "hello"
    assert snapshot.state_data["integer"] == 123
    assert snapshot.state_data["float"] == 3.14
    assert snapshot.state_data["boolean"] == True
    
    print("✓ 序列化测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第10阶段验证测试 - 状态快照基础实现")
    print("=" * 60)
    print()
    
    tests = [
        test_snapshot_type,
        test_snapshot_state,
        test_snapshot_metadata,
        test_snapshot_validation_result,
        test_create_snapshot,
        test_restore_snapshot,
        test_validate_snapshot,
        test_validate_invalid_snapshot,
        test_quick_validate,
        test_snapshot_history,
        test_delta_snapshot,
        test_apply_delta,
        test_export_import_snapshot,
        test_get_snapshot_info,
        test_checkpoint_manager,
        test_version_compatibility,
        test_incompatible_version,
        test_serialization,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 60)
    print(f"测试完成: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("✓ 第10阶段验证通过！")
        return True
    else:
        print("✗ 第10阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
