#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PubMed2Zhihu - 命令行入口

用法:
    python run.py search "关键词"              # 执行PubMed搜索（Step 1-4）
    python run.py status [项目名]              # 查看项目状态
    python run.py list                        # 列出所有项目
    python run.py step <项目名> <步骤号>       # 执行指定步骤
    python run.py collect <项目名>            # 收集总结（Step 5）
    python run.py report <项目名>             # 生成HTML报告（Step 6）
"""
import sys
import os
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager
from src.core.processor import PubMedProcessor


def cmd_search(args):
    """执行PubMed搜索（Step 1-3）"""
    try:
        processor = PubMedProcessor()
        result = processor.execute_steps_1_to_3(args.query)
        
        if result['success']:
            print("\n" + "=" * 60)
            print(f"处理完成!")
            print(f"项目路径: {result['project_path']}")
            print("=" * 60)
            print("\n下一步操作:")
            print(f"  1. 查看项目状态: python run.py status")
            print(f"  2. 生成Prompt:   python run.py step <项目名> 4")
            print(f"  3. 收集总结:     python run.py collect <项目名>")
            return 0
        else:
            print(f"\n处理失败: {result.get('error', '未知错误')}")
            return 1
            
    except Exception as e:
        print(f"\n执行异常: {str(e)}")
        return 1


def cmd_status(args):
    """查看项目状态"""
    config = Config()
    logger = Logger("run")
    file_manager = FileManager(config, logger)
    
    if args.project:
        # 查看指定项目
        project_path = os.path.join(config.get('basic', 'output_dir'), args.project)
        if not os.path.exists(project_path):
            logger.error(f"项目不存在: {args.project}")
            return 1
        
        summary = file_manager.get_project_summary(project_path)
        if summary:
            logger.info(f"项目: {args.project}")
            logger.info(f"状态: {summary.get('status', '未知')}")
            logger.info(f"当前步骤: {summary.get('current_step', '未知')}")
            logger.info(f"搜索关键词: {summary.get('search_query', '未知')}")
            logger.info(f"最后更新: {summary.get('last_updated', '未知')}")
        else:
            logger.warning(f"项目 {args.project} 无状态信息")
    else:
        # 列出所有项目
        projects = file_manager.list_projects()
        if projects:
            logger.info(f"共有 {len(projects)} 个项目:")
            for p in projects:
                status = p.get('status', '未知')
                logger.info(f"  - {p['name']} [{status}]")
        else:
            logger.info("暂无项目")
    
    return 0


def cmd_list(args):
    """列出所有项目"""
    config = Config()
    logger = Logger("run")
    file_manager = FileManager(config, logger)
    
    projects = file_manager.list_projects()
    if projects:
        logger.info(f"共有 {len(projects)} 个项目:")
        print()
        for p in projects:
            status = p.get('status', '未知')
            query = p.get('search_query', '')
            print(f"  项目: {p['name']}")
            print(f"  状态: {status}")
            if query:
                print(f"  关键词: {query}")
            print(f"  修改时间: {p.get('modified_time', '未知')[:19]}")
            print("-" * 40)
    else:
        logger.info("暂无项目")
    
    return 0


def cmd_step(args):
    """执行指定步骤"""
    try:
        config = Config()
        logger = Logger("run")
        
        # 获取项目路径
        project_path = os.path.join(config.get('basic', 'output_dir'), args.project)
        if not os.path.exists(project_path):
            logger.error(f"项目不存在: {args.project}")
            return 1
        
        processor = PubMedProcessor()
        result = processor.execute_step(project_path, args.step_num)
        
        if result['success']:
            logger.success(f"步骤 {args.step_num} 执行完成")
            return 0
        else:
            logger.error(f"步骤 {args.step_num} 执行失败: {result.get('error', '未知错误')}")
            return 1
            
    except Exception as e:
        logger = Logger("run")
        logger.error(f"执行异常: {str(e)}")
        return 1


def cmd_collect(args):
    """收集总结"""
    logger = Logger("run")
    logger.info(f"收集项目 {args.project} 的总结")
    logger.info("此功能将在Step 5实现后可用")
    # TODO: 实现总结收集
    return 0


def cmd_report(args):
    """生成HTML报告"""
    logger = Logger("run")
    logger.info(f"生成项目 {args.project} 的HTML报告")
    logger.info("此功能将在Step 6实现后可用")
    # TODO: 实现报告生成
    return 0


def cmd_test(args):
    """测试基础架构"""
    logger = Logger("run")
    
    logger.info("=" * 50)
    logger.info("PubMed2Zhihu 基础架构测试")
    logger.info("=" * 50)
    
    # 测试配置加载
    try:
        config = Config()
        logger.success("配置文件加载成功")
        logger.info(f"  输出目录: {config.get('basic', 'output_dir')}")
        logger.info(f"  最大结果数: {config.get_int('basic', 'max_results')}")
    except Exception as e:
        logger.error(f"配置文件加载失败: {e}")
        return 1
    
    # 测试文件管理器
    try:
        file_manager = FileManager(config, logger)
        logger.success("文件管理器初始化成功")
        
        # 测试创建项目目录
        test_project = file_manager.create_project_directory("test_project")
        logger.success(f"测试项目目录创建成功: {test_project}")
        
        # 测试保存JSON
        test_data = {"test": "data", "number": 123}
        test_json_path = os.path.join(test_project, "test.json")
        file_manager.save_json(test_json_path, test_data)
        logger.success("JSON保存测试成功")
        
        # 测试加载JSON
        loaded_data = file_manager.load_json(test_json_path)
        if loaded_data == test_data:
            logger.success("JSON加载测试成功")
        else:
            logger.error("JSON加载测试失败: 数据不匹配")
            return 1
        
    except Exception as e:
        logger.error(f"文件管理器测试失败: {e}")
        return 1
    
    # 测试日志系统
    logger.info("测试日志级别: info")
    logger.warning("测试日志级别: warning")
    logger.success("测试日志级别: success")
    logger.progress(5, 10, "测试进度条")
    
    logger.info("=" * 50)
    logger.success("所有基础架构测试通过!")
    logger.info("=" * 50)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='PubMed2Zhihu - PubMed论文检索与总结工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python run.py search "cancer immunotherapy"
    python run.py list
    python run.py status 20241231_120000_cancer
    python run.py test
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='执行PubMed搜索')
    search_parser.add_argument('query', type=str, help='搜索关键词')
    search_parser.set_defaults(func=cmd_search)
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='查看项目状态')
    status_parser.add_argument('project', nargs='?', type=str, help='项目名称（可选）')
    status_parser.set_defaults(func=cmd_status)
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有项目')
    list_parser.set_defaults(func=cmd_list)
    
    # step 命令
    step_parser = subparsers.add_parser('step', help='执行指定步骤')
    step_parser.add_argument('project', type=str, help='项目名称')
    step_parser.add_argument('step_num', type=int, help='步骤号 (1-6)')
    step_parser.set_defaults(func=cmd_step)
    
    # collect 命令
    collect_parser = subparsers.add_parser('collect', help='收集总结')
    collect_parser.add_argument('project', type=str, help='项目名称')
    collect_parser.set_defaults(func=cmd_collect)
    
    # report 命令
    report_parser = subparsers.add_parser('report', help='生成HTML报告')
    report_parser.add_argument('project', type=str, help='项目名称')
    report_parser.set_defaults(func=cmd_report)
    
    # test 命令
    test_parser = subparsers.add_parser('test', help='测试基础架构')
    test_parser.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())

