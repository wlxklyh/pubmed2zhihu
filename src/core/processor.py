"""
主处理器 - 协调各个步骤的执行
"""
import os
import sys
from datetime import datetime
from typing import Dict, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager
from src.core.steps.step1_search_pubmed import PubMedSearcher
from src.core.steps.step2_fetch_details import PaperDetailsFetcher
from src.core.steps.step3_fetch_figures import PMCFigureFetcher
from src.core.steps.step4_generate_prompts import PromptGenerator
from src.core.steps.step5_generate_overview import MergedPromptGenerator
from src.core.steps.step6_generate_report import ReportGenerator


class PubMedProcessor:
    def __init__(self, config_path: str = "config/config.ini"):
        self.config = Config(config_path)
        self.logger = Logger("processor")
        self.file_manager = FileManager(self.config, self.logger)
    
    def create_project(self, query: str) -> str:
        """
        创建新项目
        
        Args:
            query: 搜索关键词
            
        Returns:
            str: 项目路径
        """
        # 使用搜索关键词作为项目名
        project_name = query.replace(' ', '_')[:30]
        project_path = self.file_manager.create_project_directory(project_name)
        
        # 保存项目信息
        project_info = {
            'search_query': query,
            'created_time': datetime.now().isoformat(),
            'status': 'created',
            'current_step': 0
        }
        self.file_manager.update_project_summary(project_path, project_info)
        
        self.logger.info(f"项目创建成功: {project_path}")
        return project_path
    
    def execute_step(self, project_path: str, step_num: int) -> Dict:
        """
        执行指定步骤
        
        Args:
            project_path: 项目路径
            step_num: 步骤号 (1-6)
            
        Returns:
            Dict: 执行结果
        """
        step_handlers = {
            1: self._execute_step1,
            2: self._execute_step2,
            3: self._execute_step3,
            4: self._execute_step4,
            5: self._execute_step5,
            6: self._execute_step6
        }
        
        handler = step_handlers.get(step_num)
        if not handler:
            return {
                'success': False,
                'error': f'无效的步骤号: {step_num}'
            }
        
        result = handler(project_path)
        
        # 执行成功后更新状态
        if result.get('success'):
            self._update_status(project_path, step_num, f'step{step_num}_completed')
        
        return result
    
    def execute_steps_1_to_3(self, query: str) -> Dict:
        """
        执行步骤1-3：搜索、获取详情、下载图片
        
        Args:
            query: 搜索关键词
            
        Returns:
            Dict: 执行结果
        """
        self.logger.info("=" * 60)
        self.logger.info(f"开始处理: {query}")
        self.logger.info("=" * 60)
        
        # 创建项目
        project_path = self.create_project(query)
        
        try:
            # 步骤1: 搜索
            result = self._execute_step1(project_path, query)
            if not result['success']:
                return result
            
            # 更新状态
            self._update_status(project_path, 1, 'step1_completed')
            
            # 步骤2: 获取详情
            result = self._execute_step2(project_path)
            if not result['success']:
                return result
            
            # 更新状态
            self._update_status(project_path, 2, 'step2_completed')
            
            # 步骤3: 下载图片
            result = self._execute_step3(project_path)
            if not result['success']:
                return result
            
            # 更新状态
            self._update_status(project_path, 3, 'step3_completed')
            
            self.logger.success("步骤1-3全部完成!")
            self.logger.info(f"项目路径: {project_path}")
            
            return {
                'success': True,
                'project_path': project_path,
                'message': '步骤1-3执行完成'
            }
            
        except Exception as e:
            self.logger.error(f"处理失败: {str(e)}")
            self._update_status(project_path, -1, f'error: {str(e)}')
            return {
                'success': False,
                'error': str(e),
                'project_path': project_path
            }
    
    def execute_steps_4_to_6(self, project_path: str) -> Dict:
        """
        执行步骤4-6：生成Prompt和报告
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 执行结果
        """
        self.logger.info("=" * 60)
        self.logger.info(f"继续处理项目: {project_path}")
        self.logger.info("=" * 60)
        
        try:
            # 步骤4: 生成单篇论文Prompt
            result = self._execute_step4(project_path)
            if not result['success']:
                return result
            
            self._update_status(project_path, 4, 'step4_completed')
            
            # 步骤5: 生成综合总结Prompt
            result = self._execute_step5(project_path)
            if not result['success']:
                return result
            
            self._update_status(project_path, 5, 'step5_completed')
            
            # 步骤6: 生成HTML报告
            result = self._execute_step6(project_path)
            if not result['success']:
                return result
            
            self._update_status(project_path, 6, 'step6_completed')
            
            self.logger.success("步骤4-6全部完成!")
            self.logger.info(f"HTML报告: {project_path}/step6_report/report.html")
            
            return {
                'success': True,
                'project_path': project_path,
                'message': '步骤4-6执行完成'
            }
            
        except Exception as e:
            self.logger.error(f"处理失败: {str(e)}")
            self._update_status(project_path, -1, f'error: {str(e)}')
            return {
                'success': False,
                'error': str(e),
                'project_path': project_path
            }
    
    def execute_all_steps(self, query: str) -> Dict:
        """
        执行所有步骤（1-6）
        
        Args:
            query: 搜索关键词
            
        Returns:
            Dict: 执行结果
        """
        # 先执行步骤1-3
        result = self.execute_steps_1_to_3(query)
        if not result['success']:
            return result
        
        project_path = result['project_path']
        
        # 继续执行步骤4-6
        return self.execute_steps_4_to_6(project_path)
    
    def _execute_step1(self, project_path: str, query: str = None) -> Dict:
        """执行步骤1: PubMed搜索"""
        self.logger.step_start(1, "PubMed搜索")
        
        # 如果没有提供query，从项目信息读取
        if query is None:
            project_info = self.file_manager.get_project_summary(project_path)
            query = project_info.get('search_query')
            if not query:
                return {'success': False, 'error': '未找到搜索关键词'}
        
        searcher = PubMedSearcher(self.config, self.logger)
        result = searcher.search(query)
        
        if result['success']:
            # 保存结果
            step1_dir = self.file_manager.get_step_directory(project_path, 'step1_search')
            output_file = os.path.join(step1_dir, 'search_results.json')
            self.file_manager.save_json(output_file, result)
            
            self.logger.step_complete(1, "PubMed搜索")
            return {'success': True, 'data': result}
        else:
            return {'success': False, 'error': result.get('error', '搜索失败')}
    
    def _execute_step2(self, project_path: str) -> Dict:
        """执行步骤2: 获取论文详情"""
        self.logger.step_start(2, "获取论文详情")
        
        fetcher = PaperDetailsFetcher(self.config, self.logger)
        result = fetcher.fetch_details(project_path)
        
        if result['success']:
            # 保存结果
            step2_dir = self.file_manager.get_step_directory(project_path, 'step2_details')
            output_file = os.path.join(step2_dir, 'papers_details.json')
            self.file_manager.save_json(output_file, result)
            
            self.logger.step_complete(2, "获取论文详情")
            return {'success': True, 'data': result}
        else:
            return {'success': False, 'error': result.get('error', '获取详情失败')}
    
    def _execute_step3(self, project_path: str) -> Dict:
        """执行步骤3: 下载PMC图片"""
        self.logger.step_start(3, "下载PMC图片")
        
        fetcher = PMCFigureFetcher(self.config, self.logger)
        result = fetcher.fetch_figures(project_path)
        
        if result['success']:
            # 保存结果
            step3_dir = self.file_manager.get_step_directory(project_path, 'step3_figures')
            output_file = os.path.join(step3_dir, 'figures_info.json')
            self.file_manager.save_json(output_file, result)
            
            self.logger.step_complete(3, "下载PMC图片")
            return {'success': True, 'data': result}
        else:
            return {'success': False, 'error': result.get('error', '下载图片失败')}
    
    def _execute_step4(self, project_path: str) -> Dict:
        """执行步骤4: 生成单篇论文Prompt"""
        self.logger.step_start(4, "生成单篇论文Prompt")
        
        generator = PromptGenerator(self.config, self.logger)
        result = generator.generate_prompts(project_path)
        
        if result['success']:
            # 保存结果
            step4_dir = self.file_manager.get_step_directory(project_path, 'step4_prompts')
            output_file = os.path.join(step4_dir, 'prompts_info.json')
            self.file_manager.save_json(output_file, result)
            
            self.logger.step_complete(4, "生成单篇论文Prompt")
            return {'success': True, 'data': result}
        else:
            return {'success': False, 'error': result.get('error', '生成Prompt失败')}
    
    def _execute_step5(self, project_path: str) -> Dict:
        """执行步骤5: 生成综合总结Prompt"""
        self.logger.step_start(5, "生成综合总结Prompt")
        
        generator = MergedPromptGenerator(self.config, self.logger)
        result = generator.generate_merged_prompt(project_path)
        
        if result['success']:
            # 保存结果
            step5_dir = self.file_manager.get_step_directory(project_path, 'step5_overview')
            output_file = os.path.join(step5_dir, 'overview_info.json')
            self.file_manager.save_json(output_file, result)
            
            self.logger.step_complete(5, "生成综合总结Prompt")
            return {'success': True, 'data': result}
        else:
            return {'success': False, 'error': result.get('error', '生成综合Prompt失败')}
    
    def _execute_step6(self, project_path: str) -> Dict:
        """执行步骤6: 生成HTML报告"""
        self.logger.step_start(6, "生成HTML报告")
        
        generator = ReportGenerator(self.config, self.logger)
        result = generator.generate_report(project_path)
        
        if result['success']:
            # 保存结果
            step6_dir = self.file_manager.get_step_directory(project_path, 'step6_report')
            output_file = os.path.join(step6_dir, 'report_info.json')
            self.file_manager.save_json(output_file, result)
            
            self.logger.step_complete(6, "生成HTML报告")
            return {'success': True, 'data': result}
        else:
            return {'success': False, 'error': result.get('error', '生成报告失败')}
    
    def _update_status(self, project_path: str, step: int, status: str):
        """更新项目状态"""
        summary = self.file_manager.get_project_summary(project_path)
        summary['current_step'] = step
        summary['status'] = status
        summary['last_updated'] = datetime.now().isoformat()
        self.file_manager.update_project_summary(project_path, summary)
    
    def get_project_status(self, project_path: str) -> Dict:
        """获取项目状态"""
        if not os.path.exists(project_path):
            return {'success': False, 'error': '项目不存在'}
        
        summary = self.file_manager.get_project_summary(project_path)
        return {
            'success': True,
            'project_path': project_path,
            'summary': summary
        }

