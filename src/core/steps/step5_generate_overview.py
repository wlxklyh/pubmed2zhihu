"""
步骤5：生成综合总结Prompt
整合所有论文信息，生成总体概述的Prompt
"""
import os
import sys
from datetime import datetime
from typing import Dict, List

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class OverviewPromptGenerator:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        
        # 加载模板
        template_path = config.get('prompt', 'overview_template', 'config/templates/prompt_overview.txt')
        self.template = self._load_template(template_path)
        self.word_count = config.get_int('prompt', 'overview_word_count', 500)
    
    def _load_template(self, template_path: str) -> str:
        """加载Prompt模板"""
        paths_to_try = [
            template_path,
            os.path.join(os.path.dirname(__file__), '../../..', template_path),
            os.path.join(os.path.dirname(__file__), '../../../config/templates/prompt_overview.txt'),
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        self.logger.warning("未找到模板文件，使用默认模板")
        return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """默认Prompt模板"""
        return """# 论文综述总结 Prompt

你是一位专业的医学科研文献综述专家。请根据以下{paper_count}篇论文的信息，生成一篇中英双语的综合小结。

## 检索主题
{search_query}

## 论文列表概览

{papers_overview}

## 输出要求

请生成以下内容：

### 1. 中文综合小结（约500字）

要求：
- 概述该领域的研究现状和主要进展
- 归纳总结这{paper_count}篇论文的共同主题和研究方向
- 指出主要的研究发现和趋势
- 提出该领域可能的发展方向或研究空白
- 使用专业但易懂的语言，适合科研人员阅读

### 2. 英文综合小结（约400词）

要求：
- 与中文综合小结内容对应
- 使用学术英语，保持专业性
- 结构清晰，逻辑严谨

请按以下JSON格式输出：
```json
{{{{"overview_cn": "中文综合小结内容", "overview_en": "English overview content", "key_themes": ["主题1", "主题2", "主题3"], "research_trends": "研究趋势简述"}}}}
```
"""
    
    def generate_overview_prompt(self, project_path: str) -> Dict:
        """
        生成综合总结Prompt
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 生成结果
        """
        self.logger.info("开始生成综合总结Prompt")
        
        try:
            file_manager = FileManager(self.config, self.logger)
            
            # 加载搜索结果获取查询关键词
            step1_dir = file_manager.get_step_directory(project_path, 'step1_search')
            search_file = os.path.join(step1_dir, 'search_results.json')
            search_data = file_manager.load_json(search_file)
            search_query = search_data.get('query', '未知主题')
            
            # 加载论文详情
            step2_dir = file_manager.get_step_directory(project_path, 'step2_details')
            details_file = os.path.join(step2_dir, 'papers_details.json')
            details_data = file_manager.load_json(details_file)
            papers = details_data.get('papers', [])
            
            # 生成论文概览
            papers_overview = self._generate_papers_overview(papers)
            
            # 填充模板
            prompt = self.template.format(
                paper_count=len(papers),
                search_query=search_query,
                papers_overview=papers_overview
            )
            
            # 获取输出目录
            step5_dir = file_manager.get_step_directory(project_path, 'step5_overview')
            
            # 保存Prompt
            prompt_file = os.path.join(step5_dir, 'overview_prompt.txt')
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            result = {
                'success': True,
                'generate_time': datetime.now().isoformat(),
                'search_query': search_query,
                'paper_count': len(papers),
                'prompt_file': prompt_file,
                'prompt_preview': prompt[:500] + '...' if len(prompt) > 500 else prompt
            }
            
            self.logger.success(f"综合Prompt生成完成")
            self.logger.info(f"保存至: {prompt_file}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"生成综合Prompt失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'generate_time': datetime.now().isoformat()
            }
    
    def _generate_papers_overview(self, papers: List[Dict]) -> str:
        """
        生成论文列表概览
        
        Args:
            papers: 论文列表
            
        Returns:
            str: 格式化的论文概览
        """
        overview_parts = []
        
        for i, paper in enumerate(papers, 1):
            title = paper.get('title', '未知标题')
            authors = paper.get('authors', [])
            journal = paper.get('journal', '未知期刊')
            pub_date = paper.get('pub_date', '未知日期')
            abstract = paper.get('abstract', '')
            
            # 格式化作者
            if isinstance(authors, list):
                first_author = authors[0] if authors else '未知'
                author_str = f"{first_author} 等" if len(authors) > 1 else first_author
            else:
                author_str = str(authors)
            
            # 截取摘要前200字
            abstract_preview = abstract[:200] + '...' if len(abstract) > 200 else abstract
            
            overview_parts.append(f"""
### 论文 {i}
- **标题**: {title}
- **作者**: {author_str}
- **期刊**: {journal} ({pub_date})
- **摘要概要**: {abstract_preview}
""")
        
        return "\n".join(overview_parts)


def main(project_path: str) -> bool:
    """
    步骤5主函数 - 可独立运行
    
    Args:
        project_path: 项目路径
    """
    try:
        config = Config()
        logger = Logger("step5_overview")
        file_manager = FileManager(config, logger)
        
        logger.step_start(5, "生成综合总结Prompt")
        
        generator = OverviewPromptGenerator(config, logger)
        result = generator.generate_overview_prompt(project_path)
        
        if result['success']:
            # 保存结果
            step5_dir = file_manager.get_step_directory(project_path, 'step5_overview')
            output_file = os.path.join(step5_dir, 'overview_info.json')
            file_manager.save_json(output_file, result)
            
            logger.step_complete(5, "生成综合总结Prompt")
            return True
        else:
            logger.error(f"生成综合Prompt失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger = Logger("step5_overview")
        logger.error(f"步骤5执行异常: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python step5_generate_overview.py <项目路径>")
        sys.exit(1)
    
    success = main(sys.argv[1])
    sys.exit(0 if success else 1)

