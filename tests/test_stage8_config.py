"""
第8阶段验证测试
验证配置管理器的完整性和正确性
"""

import sys
import os
import tempfile

sys.path.insert(0, '/workspace')

from utils.config_manager import (
    ConfigError,
    ConfigNotFoundError,
    ConfigValidationError,
    ConfigTypeError,
    ConfigSource,
    ConfigItem,
    ConfigSchema,
    ConfigManager,
    get_config,
    set_config,
)

from core_types.core_types import ModuleID, TaskID


def setup_config():
    """创建并初始化一个测试用的配置管理器"""
    ConfigManager.reset()
    return ConfigManager.instance()


def test_singleton():
    """测试单例模式"""
    print("测试单例模式...")
    
    ConfigManager.reset()
    c1 = ConfigManager.instance()
    c2 = ConfigManager.instance()
    
    assert c1 is c2
    
    ConfigManager.reset()
    c3 = ConfigManager.instance()
    assert c1 is not c3
    
    print("✓ 单例模式测试通过")


def test_set_and_get():
    """测试设置和获取配置"""
    print("测试设置和获取配置...")
    
    config = setup_config()
    
    config.set("key1", "value1")
    assert config.get("key1") == "value1"
    
    config.set("key2", 123)
    assert config.get("key2") == 123
    
    # 获取不存在的键
    assert config.get("nonexistent") is None
    assert config.get("nonexistent", "default") == "default"
    
    print("✓ 设置和获取配置测试通过")


def test_module_config():
    """测试模块级配置"""
    print("测试模块级配置...")
    
    config = setup_config()
    module_id = ModuleID()
    
    config.set_module_config(module_id, "module_key", "module_value")
    
    # 获取模块级配置
    value = config.get("module_key", module_id=module_id)
    assert value == "module_value"
    
    # 不指定模块ID时获取不到
    assert config.get("module_key") is None
    
    print("✓ 模块级配置测试通过")


def test_task_config():
    """测试任务级配置"""
    print("测试任务级配置...")
    
    config = setup_config()
    task_id = TaskID()
    
    config.set_task_config(task_id, "task_key", "task_value")
    
    # 获取任务级配置
    value = config.get("task_key", task_id=task_id)
    assert value == "task_value"
    
    print("✓ 任务级配置测试通过")


def test_config_priority():
    """测试配置优先级"""
    print("测试配置优先级...")
    
    config = setup_config()
    module_id = ModuleID()
    task_id = TaskID()
    
    # 设置三级配置
    config.set("priority_key", "global_value")
    config.set_module_config(module_id, "priority_key", "module_value")
    config.set_task_config(task_id, "priority_key", "task_value")
    
    # 优先级：任务级 > 模块级 > 全局
    assert config.get("priority_key") == "global_value"
    assert config.get("priority_key", module_id=module_id) == "module_value"
    assert config.get("priority_key", module_id=module_id, task_id=task_id) == "task_value"
    
    print("✓ 配置优先级测试通过")


def test_load_from_dict():
    """测试从字典加载配置"""
    print("测试从字典加载配置...")
    
    config = setup_config()
    
    data = {
        "key1": "value1",
        "key2": 123,
        "key3": True,
    }
    
    config.load_from_dict(data)
    
    assert config.get("key1") == "value1"
    assert config.get("key2") == 123
    assert config.get("key3") == True
    
    print("✓ 从字典加载配置测试通过")


def test_load_from_file():
    """测试从文件加载配置"""
    print("测试从文件加载配置...")
    
    config = setup_config()
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"file_key": "file_value", "number": 42}')
        temp_path = f.name
    
    try:
        config.load_from_file(temp_path)
        assert config.get("file_key") == "file_value"
        assert config.get("number") == 42
    finally:
        os.unlink(temp_path)
    
    print("✓ 从文件加载配置测试通过")


def test_load_from_environment():
    """测试从环境变量加载配置"""
    print("测试从环境变量加载配置...")
    
    config = setup_config()
    
    # 设置测试环境变量
    os.environ["AGENT_TEST_KEY"] = "env_value"
    os.environ["AGENT_TEST_NUMBER"] = "100"
    os.environ["AGENT_TEST_BOOL"] = "true"
    
    try:
        config.load_from_environment()
        
        assert config.get("test_key") == "env_value"
        assert config.get("test_number") == 100  # 自动解析为整数
        assert config.get("test_bool") == True  # 自动解析为布尔值
    finally:
        del os.environ["AGENT_TEST_KEY"]
        del os.environ["AGENT_TEST_NUMBER"]
        del os.environ["AGENT_TEST_BOOL"]
    
    print("✓ 从环境变量加载配置测试通过")


def test_config_item():
    """测试配置项"""
    print("测试配置项...")
    
    item = ConfigItem(
        key="test_key",
        value="test_value",
        source=ConfigSource.CODE,
        description="测试配置",
    )
    
    assert item.key == "test_key"
    assert item.value == "test_value"
    assert item.source == ConfigSource.CODE
    
    item_dict = item.to_dict()
    assert item_dict["key"] == "test_key"
    assert item_dict["source"] == "CODE"
    
    print("✓ 配置项测试通过")


def test_config_schema():
    """测试配置模式"""
    print("测试配置模式...")
    
    schema = ConfigSchema(
        key="port",
        type=int,
        required=True,
        default=8080,
        description="端口号",
    )
    
    # 验证正确类型
    assert schema.validate(8080) == True
    
    # 验证错误类型
    assert schema.validate("8080") == False
    
    # 验证None（required=True时不允许）
    assert schema.validate(None) == False
    
    print("✓ 配置模式测试通过")


def test_schema_with_validator():
    """测试带验证器的配置模式"""
    print("测试带验证器的配置模式...")
    
    def validate_port(value):
        return 1 <= value <= 65535
    
    schema = ConfigSchema(
        key="port",
        type=int,
        validator=validate_port,
    )
    
    assert schema.validate(8080) == True
    assert schema.validate(0) == False
    assert schema.validate(70000) == False
    
    print("✓ 带验证器的配置模式测试通过")


def test_register_and_validate_schema():
    """测试注册和验证配置模式"""
    print("测试注册和验证配置模式...")
    
    config = setup_config()
    
    schema = ConfigSchema(key="timeout", type=int)
    config.register_schema(schema)
    
    # 验证配置值
    assert config.validate_config("timeout", 30) == True
    assert config.validate_config("timeout", "30") == False
    
    print("✓ 注册和验证配置模式测试通过")


def test_get_required():
    """测试获取必需配置"""
    print("测试获取必需配置...")
    
    config = setup_config()
    
    config.set("required_key", "value")
    
    # 获取存在的必需配置
    value = config.get_required("required_key")
    assert value == "value"
    
    # 获取不存在的必需配置
    try:
        config.get_required("nonexistent")
        assert False, "应该抛出ConfigNotFoundError"
    except ConfigNotFoundError:
        pass
    
    print("✓ 获取必需配置测试通过")


def test_get_typed():
    """测试获取指定类型的配置"""
    print("测试获取指定类型的配置...")
    
    config = setup_config()
    
    config.set("int_key", 42)
    config.set("str_key", "hello")
    
    # 正确类型
    assert config.get_typed("int_key", int) == 42
    assert config.get_typed("str_key", str) == "hello"
    
    # 错误类型
    try:
        config.get_typed("int_key", str)
        assert False, "应该抛出ConfigTypeError"
    except ConfigTypeError:
        pass
    
    print("✓ 获取指定类型的配置测试通过")


def test_remove_config():
    """测试删除配置"""
    print("测试删除配置...")
    
    config = setup_config()
    
    config.set("key_to_remove", "value")
    assert config.has_key("key_to_remove") == True
    
    result = config.remove("key_to_remove")
    assert result == True
    assert config.has_key("key_to_remove") == False
    
    # 删除不存在的键
    result = config.remove("nonexistent")
    assert result == False
    
    print("✓ 删除配置测试通过")


def test_clear():
    """测试清除所有配置"""
    print("测试清除所有配置...")
    
    config = setup_config()
    
    config.set("key1", "value1")
    config.set("key2", "value2")
    
    assert config.get_all_keys() == ["key1", "key2"]
    
    config.clear()
    
    assert config.get_all_keys() == []
    
    print("✓ 清除所有配置测试通过")


def test_to_dict():
    """测试导出为字典"""
    print("测试导出为字典...")
    
    config = setup_config()
    
    config.set("key1", "value1")
    config.set("key2", 123)
    
    data = config.to_dict()
    
    assert data["global"]["key1"] == "value1"
    assert data["global"]["key2"] == 123
    
    # 包含元数据
    data_with_meta = config.to_dict(include_metadata=True)
    assert "source" in data_with_meta["global"]["key1"]
    
    print("✓ 导出为字典测试通过")


def test_save_and_load_file():
    """测试保存和加载文件"""
    print("测试保存和加载文件...")
    
    config1 = setup_config()
    
    config1.set("save_key", "save_value")
    config1.set("save_number", 999)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        # 保存配置（不包含元数据，只保存值）
        config1.save_to_file(temp_path, include_metadata=False)
        
        # 加载到新配置管理器
        ConfigManager.reset()
        config2 = ConfigManager.instance()
        
        # 手动读取并加载global部分的配置
        import json
        with open(temp_path, 'r') as f:
            data = json.load(f)
        # 加载global部分的配置
        if "global" in data:
            config2.load_from_dict(data["global"])
        
        assert config2.get("save_key") == "save_value"
        assert config2.get("save_number") == 999
    finally:
        os.unlink(temp_path)
    
    print("✓ 保存和加载文件测试通过")


def test_statistics():
    """测试统计信息"""
    print("测试统计信息...")
    
    config = setup_config()
    
    config.set("key1", "value1")
    config.set("key2", "value2")
    
    module_id = ModuleID()
    config.set_module_config(module_id, "module_key", "value")
    
    stats = config.get_statistics()
    
    assert stats["global_count"] == 2
    assert stats["module_count"] == 1
    assert stats["task_count"] == 0
    
    print("✓ 统计信息测试通过")


def test_get_config_helper():
    """测试get_config便捷函数"""
    print("测试get_config便捷函数...")
    
    ConfigManager.reset()
    
    set_config("helper_key", "helper_value")
    
    value = get_config("helper_key")
    assert value == "helper_value"
    
    print("✓ get_config便捷函数测试通过")


def test_config_source():
    """测试配置来源"""
    print("测试配置来源...")
    
    config = setup_config()
    
    config.set("runtime_key", "runtime_value", source=ConfigSource.RUNTIME)
    
    item = config.get_item("runtime_key")
    assert item is not None
    assert item.source == ConfigSource.RUNTIME
    
    print("✓ 配置来源测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第8阶段验证测试 - 配置管理实现")
    print("=" * 60)
    print()
    
    tests = [
        test_singleton,
        test_set_and_get,
        test_module_config,
        test_task_config,
        test_config_priority,
        test_load_from_dict,
        test_load_from_file,
        test_load_from_environment,
        test_config_item,
        test_config_schema,
        test_schema_with_validator,
        test_register_and_validate_schema,
        test_get_required,
        test_get_typed,
        test_remove_config,
        test_clear,
        test_to_dict,
        test_save_and_load_file,
        test_statistics,
        test_get_config_helper,
        test_config_source,
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
        print("✓ 第8阶段验证通过！")
        return True
    else:
        print("✗ 第8阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
