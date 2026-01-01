"""
文件管理模块
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from .config import Config
from .logger import Logger


class FileManager:
    def __init__(self, config: Config, logger: Optional[Logger] = None):
        self.config = config
        self.logger = logger or Logger("file_manager")
        self.output_dir = config.get('basic', 'output_dir', './projects')
        self.cache_dir = config.get('basic', 'cache_dir', './cache')
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        for directory in [self.output_dir, self.cache_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                self.logger.info(f"创建目录: {directory}")
    
    def create_project_directory(self, project_name: str) -> str:
        """创建项目目录"""
        # 生成安全的项目名称
        safe_name = self._sanitize_filename(project_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir_name = f"{timestamp}_{safe_name}"
        
        project_path = os.path.join(self.output_dir, project_dir_name)
        
        # 创建项目主目录
        if not os.path.exists(project_path):
            os.makedirs(project_path)
            self.logger.info(f"创建项目目录: {project_path}")
        
        # 创建各个步骤的子目录
        step_dirs = [
            'step1_search',
            'step2_details',
            'step3_figures',
            'step4_prompts',
            'step5_overview',
            'step6_report',
            'FinalOutput'
        ]
        
        for step_dir in step_dirs:
            step_path = os.path.join(project_path, step_dir)
            if not os.path.exists(step_path):
                os.makedirs(step_path)
        
        # 创建图片子目录
        figures_path = os.path.join(project_path, 'step3_figures', 'images')
        if not os.path.exists(figures_path):
            os.makedirs(figures_path)
        
        # 创建PDF子目录
        pdfs_path = os.path.join(project_path, 'step2_details', 'pdfs')
        if not os.path.exists(pdfs_path):
            os.makedirs(pdfs_path)
        
        return project_path
    
    def get_step_directory(self, project_path: str, step_name: str) -> str:
        """获取步骤目录路径"""
        step_dir = os.path.join(project_path, step_name)
        if not os.path.exists(step_dir):
            os.makedirs(step_dir)
        return step_dir
    
    def save_json(self, file_path: str, data: Dict) -> str:
        """保存JSON文件"""
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.file_created(file_path)
        return file_path
    
    def load_json(self, file_path: str) -> Dict:
        """加载JSON文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_step_info(self, project_path: str, step_name: str, info: Dict) -> str:
        """保存步骤信息到JSON文件"""
        step_dir = self.get_step_directory(project_path, step_name)
        info_file = os.path.join(step_dir, f"{step_name}_info.json")
        
        # 添加时间戳
        info['timestamp'] = datetime.now().isoformat()
        info['step_name'] = step_name
        
        return self.save_json(info_file, info)
    
    def load_step_info(self, project_path: str, step_name: str) -> Optional[Dict]:
        """加载步骤信息"""
        step_dir = self.get_step_directory(project_path, step_name)
        info_file = os.path.join(step_dir, f"{step_name}_info.json")
        
        if not os.path.exists(info_file):
            return None
        
        return self.load_json(info_file)
    
    def save_step_log(self, project_path: str, step_name: str, log_content: str) -> str:
        """保存步骤日志"""
        step_dir = self.get_step_directory(project_path, step_name)
        log_file = os.path.join(step_dir, f"{step_name}_log.txt")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {log_content}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        return log_file
    
    def get_project_summary(self, project_path: str) -> Dict:
        """获取项目总结信息"""
        summary_file = os.path.join(project_path, 'project_summary.json')
        
        if os.path.exists(summary_file):
            return self.load_json(summary_file)
        
        return {}
    
    def update_project_summary(self, project_path: str, summary: Dict) -> str:
        """更新项目总结信息"""
        summary_file = os.path.join(project_path, 'project_summary.json')
        
        # 添加更新时间
        summary['last_updated'] = datetime.now().isoformat()
        
        return self.save_json(summary_file, summary)
    
    def list_projects(self) -> List[Dict]:
        """列出所有项目"""
        projects = []
        
        if not os.path.exists(self.output_dir):
            return projects
        
        for item in os.listdir(self.output_dir):
            item_path = os.path.join(self.output_dir, item)
            if os.path.isdir(item_path):
                # 检查是否是有效的项目目录（包含project_summary.json或step1_search）
                summary_file = os.path.join(item_path, 'project_summary.json')
                step1_dir = os.path.join(item_path, 'step1_search')
                
                if not os.path.exists(summary_file) and not os.path.exists(step1_dir):
                    continue  # 跳过非项目目录
                
                project_info = {
                    'name': item,
                    'path': item_path,
                    'created_time': datetime.fromtimestamp(
                        os.path.getctime(item_path)
                    ).isoformat(),
                    'modified_time': datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).isoformat(),
                    'summary': {}
                }
                
                # 尝试读取项目总结
                summary = self.get_project_summary(item_path)
                if summary:
                    project_info['summary'] = summary
                
                projects.append(project_info)
        
        # 按修改时间排序
        projects.sort(key=lambda x: x['modified_time'], reverse=True)
        return projects
    
    def get_step_files(self, project_path: str, step_name: str) -> List[Dict]:
        """获取步骤的所有文件"""
        step_dir = self.get_step_directory(project_path, step_name)
        files = []
        
        for item in os.listdir(step_dir):
            item_path = os.path.join(step_dir, item)
            if os.path.isfile(item_path):
                file_info = {
                    'name': item,
                    'path': item_path,
                    'size': os.path.getsize(item_path),
                    'modified_time': datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).isoformat(),
                    'extension': os.path.splitext(item)[1].lower()
                }
                files.append(file_info)
            elif os.path.isdir(item_path):
                # 处理子目录
                subfiles = []
                for subitem in os.listdir(item_path):
                    subitem_path = os.path.join(item_path, subitem)
                    if os.path.isfile(subitem_path):
                        subfile_info = {
                            'name': subitem,
                            'path': subitem_path,
                            'size': os.path.getsize(subitem_path),
                            'modified_time': datetime.fromtimestamp(
                                os.path.getmtime(subitem_path)
                            ).isoformat(),
                            'extension': os.path.splitext(subitem)[1].lower()
                        }
                        subfiles.append(subfile_info)
                
                if subfiles:
                    dir_info = {
                        'name': item,
                        'path': item_path,
                        'is_directory': True,
                        'files': subfiles,
                        'file_count': len(subfiles)
                    }
                    files.append(dir_info)
        
        return files
    
    def _sanitize_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        # 移除或替换不安全的字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 50:
            filename = filename[:50]
        
        # 移除前后空格和点
        filename = filename.strip(' .')
        
        # 确保不为空
        if not filename:
            filename = "untitled"
        
        return filename
    
    def get_file_content(self, file_path: str) -> str:
        """读取文件内容"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def save_text_file(self, file_path: str, content: str) -> str:
        """保存文本文件"""
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.file_created(file_path)
        return file_path

