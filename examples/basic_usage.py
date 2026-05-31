"""
阶段96-100：使用示例
Basic Usage Example

展示如何使用LongTaskAgent系统的基本功能
"""

import sys
sys.path.insert(0, '/workspace')

from system.module_tree import ModuleTreeBuilder
from system.execution_engine import ExecutionEngine
from system.monitoring_dashboard import MonitoringDashboard
from core_types.core_types import TaskID, ModuleInput, ModuleParam
from interfaces.module_interface import InitRequest, InitContext


def main():
    """主函数"""
    print("=" * 60)
    print("LongTaskAgent 使用示例")
    print("=" * 60)

    # 1. 构建模块树
    print("\n1. 构建模块树...")
    builder = ModuleTreeBuilder()
    tree = builder.build_standard_tree()
    print(f"   模块树构建完成，共 {tree.get_module_count()} 个模块")
    print(f"   树深度: {tree.get_tree_depth()}")

    # 2. 初始化所有模块
    print("\n2. 初始化所有模块...")
    for module in tree.get_all_modules():
        init_request = InitRequest(
            module_id=module.module_id,
            module_param=ModuleParam(module_id=module.module_id),
        )
        result = module.module_init(init_request, InitContext())
        status = "✓" if result.success else "✗"
        print(f"   {status} {module.module_name}")

    # 3. 创建执行引擎
    print("\n3. 创建执行引擎...")
    engine = ExecutionEngine(tree)
    print("   执行引擎创建完成")

    # 4. 创建监控面板
    print("\n4. 创建监控面板...")
    dashboard = MonitoringDashboard(tree, engine)
    print("   监控面板创建完成")

    # 5. 执行一些任务
    print("\n5. 执行任务...")
    for i in range(3):
        task_id = TaskID(f"example_task_{i}")
        module_input = ModuleInput(
            task_id=task_id,
            data={"iteration": i, "message": f"任务 {i}"}
        )
        record = engine.execute_task(task_id, module_input)
        print(f"   任务 {i}: {record.status.name}")

    # 6. 查看系统指标
    print("\n6. 系统指标...")
    metrics = dashboard.collect_system_metrics()
    print(f"   模块数量: {metrics['module_count']}")
    print(f"   树深度: {metrics['tree_depth']}")
    print(f"   执行统计: {metrics['execution_stats']}")

    # 7. 健康检查
    print("\n7. 健康检查...")
    health = dashboard.check_health()
    print(f"   状态: {health.status}")
    print(f"   健康分数: {health.score}")
    if health.issues:
        print(f"   问题: {len(health.issues)} 个")
        for issue in health.issues:
            print(f"     - [{issue['severity']}] {issue['message']}")
    else:
        print("   没有问题")

    # 8. 获取执行统计
    print("\n8. 执行统计...")
    stats = engine.get_statistics()
    print(f"   总执行数: {stats['total_executions']}")
    print(f"   成功: {stats['completed']}")
    print(f"   失败: {stats['failed']}")
    print(f"   成功率: {stats['success_rate']:.1%}")

    # 9. 打印模块树
    print("\n9. 模块树结构...")
    print(tree.print_tree())

    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
