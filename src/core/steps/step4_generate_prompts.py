"""
步骤4：生成单篇论文的Prompt
整合论文信息、摘要和图片，生成用于LLM的Prompt
"""
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class PromptGenerator:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        
        # 加载模板
        template_path = config.get('prompt', 'single_template', 'config/templates/prompt_single.txt')
        self.template = self._load_template(template_path)
    
    def _load_template(self, template_path: str) -> str:
        """加载Prompt模板"""
        # 尝试多个路径
        paths_to_try = [
            template_path,
            os.path.join(os.path.dirname(__file__), '../../..', template_path),
            os.path.join(os.path.dirname(__file__), '../../../config/templates/prompt_single.txt'),
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        # 使用默认模板
        self.logger.warning("未找到模板文件，使用默认模板")
        return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """默认Prompt模板"""
        return """# 单篇论文总结 Prompt

你是一位专业的医学科研文献分析专家。请根据以下论文信息生成中英双语的论文小结。

## 论文信息
- **标题**: {title}
- **作者**: {authors}
- **期刊**: {journal}
- **发表日期**: {pub_date}
- **PMID**: {pmid}
- **DOI**: {doi}

## 论文内容
{content_note}

{content}

## 图片信息
{figure_info}

## 输出要求

请生成以下内容：

### 1. 中文小结（约200字）
- 简明扼要地概述研究背景、方法、主要发现和意义
- 使用专业但易懂的语言
- 突出研究的创新点和临床/科研价值

### 2. 英文小结（约150词）
- 与中文小结内容对应
- 使用学术英语，风格与原文摘要一致
- 保持专业术语的准确性

### 3. 图片说明（如有图片）
- 对每张图片进行简要说明
- 标注图片类型：[原图] 表示来自论文原文，[不可获取] 表示无法获取原图

请按以下JSON格式输出：
```json
{{"summary_cn": "中文小结内容", "summary_en": "English summary content", "figure_notes": "图片说明内容（如无图片则为空字符串）"}}
```
"""
    
    def generate_prompts(self, project_path: str) -> Dict:
        """
        为所有论文生成Prompt
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 生成结果
        """
        self.logger.info("开始生成单篇论文Prompt")
        
        try:
            file_manager = FileManager(self.config, self.logger)
            
            # 加载论文详情
            step2_dir = file_manager.get_step_directory(project_path, 'step2_details')
            details_file = os.path.join(step2_dir, 'papers_details.json')
            details_data = file_manager.load_json(details_file)
            papers = details_data.get('papers', [])
            
            # 加载图片信息
            step3_dir = file_manager.get_step_directory(project_path, 'step3_figures')
            figures_file = os.path.join(step3_dir, 'figures_info.json')
            figures_data = {}
            if os.path.exists(figures_file):
                figures_data = file_manager.load_json(figures_file)
            
            # 构建PMID到图片的映射
            figures_map = {}
            for paper_fig in figures_data.get('papers', []):
                pmid = paper_fig.get('pmid')
                if pmid:
                    figures_map[pmid] = paper_fig.get('figures', [])
            
            # 获取输出目录
            step4_dir = file_manager.get_step_directory(project_path, 'step4_prompts')
            
            # 为每篇论文生成Prompt
            prompts = []
            for i, paper in enumerate(papers):
                pmid = paper['pmid']
                self.logger.progress(i + 1, len(papers), f"生成Prompt: {pmid}")
                
                # 获取该论文的图片
                paper_figures = figures_map.get(pmid, [])
                
                # 生成Prompt
                prompt = self._generate_single_prompt(paper, paper_figures, project_path)
                
                prompt_info = {
                    'pmid': pmid,
                    'title': paper.get('title', ''),
                    'prompt': prompt,
                    'has_figures': len(paper_figures) > 0,
                    'figure_count': len(paper_figures)
                }
                prompts.append(prompt_info)
                
                # 保存单独的Prompt文件
                prompt_file = os.path.join(step4_dir, f'prompt_{pmid}.txt')
                with open(prompt_file, 'w', encoding='utf-8') as f:
                    f.write(prompt)
            
            print()  # 换行
            
            result = {
                'success': True,
                'generate_time': datetime.now().isoformat(),
                'prompts': prompts,
                'stats': {
                    'total_prompts': len(prompts),
                    'prompts_with_figures': sum(1 for p in prompts if p['has_figures'])
                }
            }
            
            self.logger.success(f"Prompt生成完成: 共 {len(prompts)} 个")
            
            return result
            
        except Exception as e:
            self.logger.error(f"生成Prompt失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'generate_time': datetime.now().isoformat()
            }
    
    def _get_paper_content(self, paper: Dict, project_path: str) -> Dict:
        """
        获取论文内容（优先全文，降级到摘要）
        
        Args:
            paper: 论文信息
            project_path: 项目路径
            
        Returns:
            Dict: {'source': 'fulltext'/'abstract', 'text': '...', 'note': '...'}
        """
        fulltext_status = paper.get('fulltext_status', '')
        fulltext_path = paper.get('fulltext_path')
        
        # 尝试读取全文
        if fulltext_status == 'success' and fulltext_path:
            full_path = os.path.join(project_path, 'step2_details', fulltext_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        fulltext = f.read()
                    word_count = paper.get('fulltext_word_count', len(fulltext.split()))
                    return {
                        'source': 'fulltext',
                        'text': fulltext,
                        'note': f'[全文内容 - 约{word_count}词]'
                    }
                except Exception:
                    pass
        
        # 降级到摘要
        abstract = paper.get('abstract', '摘要不可用')
        
        # 根据状态设置提示信息
        status_notes = {
            'no_pmcid': '[无法获取PDF：非开放获取论文，以下为摘要]',
            'download_failed': '[PDF下载失败，以下为摘要]',
            'extract_failed': '[PDF文本提取失败，以下为摘要]',
            '': '[以下为摘要]'
        }
        note = status_notes.get(fulltext_status, '[以下为摘要]')
        
        return {
            'source': 'abstract',
            'text': abstract,
            'note': note
        }
    
    def _generate_single_prompt(self, paper: Dict, figures: List[Dict], project_path: str) -> str:
        """
        生成单篇论文的Prompt
        
        Args:
            paper: 论文信息
            figures: 图片信息列表
            project_path: 项目路径
            
        Returns:
            str: 生成的Prompt
        """
        # 格式化作者列表
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:5])
            if len(authors) > 5:
                authors_str += f' 等（共{len(authors)}位作者）'
        else:
            authors_str = str(authors)
        
        # 格式化图片信息
        figure_info = self._format_figure_info(figures, project_path)
        
        # 获取论文内容（全文或摘要）
        content_data = self._get_paper_content(paper, project_path)
        
        # 填充模板
        prompt = self.template.format(
            title=paper.get('title', '未知标题'),
            authors=authors_str,
            journal=paper.get('journal', '未知期刊'),
            pub_date=paper.get('pub_date', '未知日期'),
            pmid=paper.get('pmid', ''),
            doi=paper.get('doi', '无'),
            content=content_data['text'],
            content_note=content_data['note'],
            figure_info=figure_info
        )
        
        return prompt
    
    def _format_figure_info(self, figures: List[Dict], project_path: str) -> str:
        """
        格式化图片信息
        
        Args:
            figures: 图片信息列表
            project_path: 项目路径
            
        Returns:
            str: 格式化后的图片信息
        """
        if not figures:
            return "该论文无可获取的图片（非开放获取或无图片）"
        
        info_parts = []
        for i, fig in enumerate(figures, 1):
            fig_id = fig.get('figure_id', f'图{i}')
            caption = fig.get('caption', '无说明')
            local_path = fig.get('local_path')
            is_original = fig.get('is_original', True)
            
            # 状态标记
            if local_path:
                status = "[原图已下载]"
                # 构建完整路径供参考
                full_path = os.path.join(project_path, 'step3_figures', local_path)
            else:
                status = "[原图URL]"
            
            info_parts.append(f"""
### 图片 {i}: {fig_id} {status}
- **说明**: {caption[:300]}{'...' if len(caption) > 300 else ''}
- **类型**: {'论文原图' if is_original else '示意图'}
""")
        
        return "\n".join(info_parts)


def main(project_path: str) -> bool:
    """
    步骤4主函数 - 可独立运行
    
    Args:
        project_path: 项目路径
    """
    try:
        config = Config()
        logger = Logger("step4_prompts")
        file_manager = FileManager(config, logger)
        
        logger.step_start(4, "生成单篇论文Prompt")
        
        generator = PromptGenerator(config, logger)
        result = generator.generate_prompts(project_path)
        
        if result['success']:
            # 保存结果
            step4_dir = file_manager.get_step_directory(project_path, 'step4_prompts')
            output_file = os.path.join(step4_dir, 'prompts_info.json')
            file_manager.save_json(output_file, result)
            
            logger.step_complete(4, "生成单篇论文Prompt")
            return True
        else:
            logger.error(f"生成Prompt失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger = Logger("step4_prompts")
        logger.error(f"步骤4执行异常: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python step4_generate_prompts.py <项目路径>")
        sys.exit(1)
    
    success = main(sys.argv[1])
    sys.exit(0 if success else 1)

