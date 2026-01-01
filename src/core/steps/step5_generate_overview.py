"""
步骤5：生成合并的综述分析Prompt
整合所有论文信息，生成用于LLM的合并任务Prompt
"""
import os
import sys
from datetime import datetime
from typing import Dict, List

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class MergedPromptGenerator:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        
        template_path = config.get('prompt', 'merged_template', 'config/templates/prompt_merged.txt')
        self.template = self._load_template(template_path)
        self.max_words_per_paper = config.get_int('prompt', 'max_words_per_paper', 8000)
    
    def _load_template(self, template_path: str) -> str:
        """加载Prompt模板"""
        paths_to_try = [
            template_path,
            os.path.join(os.path.dirname(__file__), '../../..', template_path),
            os.path.join(os.path.dirname(__file__), '../../../config/templates/prompt_merged.txt'),
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        self.logger.warning("未找到模板文件，使用默认模板")
        return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """默认Prompt模板"""
        return """# 文献综述深度分析任务

你是一位专业的医学科研文献分析专家。请根据以下{paper_count}篇论文的完整信息，生成一份深度综述报告。

## 检索主题
{search_query}

## 论文详情
{papers_content}

## 输出要求

请按JSON格式输出综述内容和每篇论文的解读。

```json
{{
  "overview": {{
    "overview_cn": "中文综述",
    "overview_en": "English overview",
    "research_trends": "研究趋势",
    "key_themes": [{{"title_cn": "主题", "title_en": "Theme", "description": "描述"}}],
    "evidence": {{"basic_research": "基础研究", "clinical_research": "临床研究"}},
    "hypotheses": "推测性假说",
    "open_questions": [{{"question": "问题", "strategy": "策略"}}]
  }},
  "papers": {{
    "PMID": {{
      "title": "标题",
      "research_content": "研究内容",
      "future_directions": "研究方向",
      "paper_themes": ["主题1", "主题2"]
    }}
  }}
}}
```
"""
    
    def _get_paper_content(self, paper: Dict, project_path: str) -> Dict:
        """
        获取论文内容（优先全文，降级到摘要）
        
        Args:
            paper: 论文信息
            project_path: 项目路径
            
        Returns:
            Dict: {'source': 'fulltext'/'abstract', 'text': '...', 'word_count': int}
        """
        fulltext_status = paper.get('fulltext_status', '')
        fulltext_path = paper.get('fulltext_path')
        
        if fulltext_status == 'success' and fulltext_path:
            full_path = os.path.join(project_path, 'step2_details', fulltext_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        fulltext = f.read()
                    
                    words = fulltext.split()
                    word_count = len(words)
                    
                    if word_count > self.max_words_per_paper:
                        truncated_text = ' '.join(words[:self.max_words_per_paper])
                        return {
                            'source': 'fulltext',
                            'text': truncated_text,
                            'word_count': word_count,
                            'truncated': True
                        }
                    else:
                        return {
                            'source': 'fulltext',
                            'text': fulltext,
                            'word_count': word_count,
                            'truncated': False
                        }
                except Exception:
                    pass
        
        abstract = paper.get('abstract', '摘要不可用')
        return {
            'source': 'abstract',
            'text': abstract,
            'word_count': len(abstract.split()),
            'truncated': False
        }
    
    def _format_figure_info(self, figures: List[Dict]) -> str:
        """格式化图片信息"""
        if not figures:
            return "无可获取的图片"
        
        info_parts = []
        for i, fig in enumerate(figures, 1):
            fig_id = fig.get('figure_id', f'图{i}')
            caption = fig.get('caption', '无说明')
            caption_preview = caption[:200] + '...' if len(caption) > 200 else caption
            info_parts.append(f"- {fig_id}: {caption_preview}")
        
        return "\n".join(info_parts)
    
    def _generate_paper_section(self, paper: Dict, figures: List[Dict], 
                                 index: int, project_path: str) -> str:
        """
        生成单篇论文的内容区块
        
        Args:
            paper: 论文信息
            figures: 图片信息列表
            index: 论文序号
            project_path: 项目路径
            
        Returns:
            str: 格式化的论文区块
        """
        pmid = paper.get('pmid', '')
        title = paper.get('title', '未知标题')
        authors = paper.get('authors', [])
        journal = paper.get('journal', '未知期刊')
        pub_date = paper.get('pub_date', '未知日期')
        doi = paper.get('doi', '')
        
        if isinstance(authors, list):
            first_author = authors[0] if authors else '未知'
            author_str = f"{first_author} 等" if len(authors) > 1 else first_author
        else:
            author_str = str(authors)
        
        content_data = self._get_paper_content(paper, project_path)
        
        if content_data['source'] == 'fulltext':
            source_label = '[全文]'
            if content_data.get('truncated'):
                source_label = f'[全文-已截取前{self.max_words_per_paper}词]'
        else:
            source_label = '[摘要]'
        
        figure_info = self._format_figure_info(figures)
        
        section = f"""
### 论文 {index} (PMID: {pmid})
- **标题**: {title}
- **作者**: {author_str}
- **期刊**: {journal} ({pub_date})
- **DOI**: {doi if doi else '无'}
- **内容来源**: {source_label} (约{content_data['word_count']}词)

**论文内容**:
{content_data['text']}

**图片信息**:
{figure_info}
"""
        return section
    
    def generate_merged_prompt(self, project_path: str) -> Dict:
        """
        生成合并的综述分析Prompt
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 生成结果
        """
        self.logger.info("开始生成合并的综述分析Prompt")
        
        try:
            file_manager = FileManager(self.config, self.logger)
            
            step1_dir = file_manager.get_step_directory(project_path, 'step1_search')
            search_file = os.path.join(step1_dir, 'search_results.json')
            search_data = file_manager.load_json(search_file)
            search_query = search_data.get('query', '未知主题')
            
            step2_dir = file_manager.get_step_directory(project_path, 'step2_details')
            details_file = os.path.join(step2_dir, 'papers_details.json')
            details_data = file_manager.load_json(details_file)
            papers = details_data.get('papers', [])
            
            step3_dir = file_manager.get_step_directory(project_path, 'step3_figures')
            figures_file = os.path.join(step3_dir, 'figures_info.json')
            figures_data = {}
            if os.path.exists(figures_file):
                figures_data = file_manager.load_json(figures_file)
            
            figures_map = {}
            for paper_fig in figures_data.get('papers', []):
                pmid = paper_fig.get('pmid')
                if pmid:
                    figures_map[pmid] = paper_fig.get('figures', [])
            
            paper_sections = []
            papers_list = []
            fulltext_count = 0
            abstract_count = 0
            
            for i, paper in enumerate(papers, 1):
                pmid = paper.get('pmid', '')
                self.logger.progress(i, len(papers), f"处理论文: {pmid}")
                
                paper_figures = figures_map.get(pmid, [])
                section = self._generate_paper_section(paper, paper_figures, i, project_path)
                paper_sections.append(section)
                
                content_data = self._get_paper_content(paper, project_path)
                if content_data['source'] == 'fulltext':
                    fulltext_count += 1
                else:
                    abstract_count += 1
                
                papers_list.append({
                    'pmid': pmid,
                    'title': paper.get('title', ''),
                    'authors': paper.get('authors', []),
                    'journal': paper.get('journal', ''),
                    'pub_date': paper.get('pub_date', ''),
                    'doi': paper.get('doi', ''),
                    'has_fulltext': content_data['source'] == 'fulltext',
                    'figure_count': len(paper_figures)
                })
            
            print()
            
            stats_header = f"**内容统计**: 共{len(papers)}篇论文，其中{fulltext_count}篇有全文，{abstract_count}篇仅有摘要\n"
            papers_content = stats_header + "\n".join(paper_sections)
            
            example_pmid = papers[0].get('pmid', 'PMID') if papers else 'PMID'
            
            prompt = self.template.format(
                paper_count=len(papers),
                search_query=search_query,
                papers_content=papers_content,
                example_pmid=example_pmid
            )
            
            step5_dir = file_manager.get_step_directory(project_path, 'step5_overview')
            
            prompt_file = os.path.join(step5_dir, 'merged_prompt.txt')
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            papers_list_file = os.path.join(step5_dir, 'papers_list.json')
            file_manager.save_json(papers_list_file, {
                'search_query': search_query,
                'paper_count': len(papers),
                'papers': papers_list
            })
            
            result = {
                'success': True,
                'generate_time': datetime.now().isoformat(),
                'search_query': search_query,
                'paper_count': len(papers),
                'fulltext_count': fulltext_count,
                'abstract_count': abstract_count,
                'prompt_file': prompt_file,
                'papers_list_file': papers_list_file,
                'prompt_char_count': len(prompt),
                'next_step': '请将 merged_prompt.txt 的内容复制到LLM，获取JSON结果后保存到 step5_overview/llm_response.json'
            }
            
            self.logger.success(f"合并Prompt生成完成")
            self.logger.info(f"Prompt文件: {prompt_file}")
            self.logger.info(f"字符数: {len(prompt)}")
            self.logger.info(f"下一步: 将prompt复制到LLM，结果保存到 llm_response.json")
            
            return result
            
        except Exception as e:
            self.logger.error(f"生成合并Prompt失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'generate_time': datetime.now().isoformat()
            }


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
        
        logger.step_start(5, "生成合并的综述分析Prompt")
        
        generator = MergedPromptGenerator(config, logger)
        result = generator.generate_merged_prompt(project_path)
        
        if result['success']:
            step5_dir = file_manager.get_step_directory(project_path, 'step5_overview')
            output_file = os.path.join(step5_dir, 'overview_info.json')
            file_manager.save_json(output_file, result)
            
            logger.step_complete(5, "生成合并的综述分析Prompt")
            return True
        else:
            logger.error(f"生成合并Prompt失败: {result.get('error', '未知错误')}")
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
