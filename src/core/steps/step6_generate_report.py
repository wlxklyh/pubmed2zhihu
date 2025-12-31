"""
步骤6：生成HTML报告
整合所有信息生成最终的HTML报告页面
"""
import os
import sys
import base64
from datetime import datetime
from typing import Dict, List, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class ReportGenerator:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.image_width = config.get_int('html', 'image_width', 600)
    
    def generate_report(self, project_path: str, summaries: Optional[Dict] = None) -> Dict:
        """
        生成HTML报告
        
        Args:
            project_path: 项目路径
            summaries: 可选的总结数据（从LLM获取后传入）
            
        Returns:
            Dict: 生成结果
        """
        self.logger.info("开始生成HTML报告")
        
        try:
            file_manager = FileManager(self.config, self.logger)
            
            # 加载所有数据
            data = self._load_all_data(project_path, file_manager)
            
            # 生成HTML
            html_content = self._generate_html(data, project_path, summaries)
            
            # 保存报告
            step6_dir = file_manager.get_step_directory(project_path, 'step6_report')
            report_file = os.path.join(step6_dir, 'report.html')
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            result = {
                'success': True,
                'generate_time': datetime.now().isoformat(),
                'report_file': report_file,
                'paper_count': len(data.get('papers', []))
            }
            
            self.logger.success(f"HTML报告生成完成")
            self.logger.info(f"保存至: {report_file}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'generate_time': datetime.now().isoformat()
            }
    
    def _load_all_data(self, project_path: str, file_manager: FileManager) -> Dict:
        """加载所有步骤的数据"""
        data = {}
        
        # 搜索结果
        step1_file = os.path.join(project_path, 'step1_search', 'search_results.json')
        if os.path.exists(step1_file):
            data['search'] = file_manager.load_json(step1_file)
        
        # 论文详情
        step2_file = os.path.join(project_path, 'step2_details', 'papers_details.json')
        if os.path.exists(step2_file):
            data['details'] = file_manager.load_json(step2_file)
            data['papers'] = data['details'].get('papers', [])
        
        # 图片信息
        step3_file = os.path.join(project_path, 'step3_figures', 'figures_info.json')
        if os.path.exists(step3_file):
            data['figures'] = file_manager.load_json(step3_file)
            # 构建PMID到图片的映射
            data['figures_map'] = {}
            for paper_fig in data['figures'].get('papers', []):
                pmid = paper_fig.get('pmid')
                if pmid:
                    data['figures_map'][pmid] = paper_fig.get('figures', [])
        
        return data
    
    def _generate_html(self, data: Dict, project_path: str, summaries: Optional[Dict] = None) -> str:
        """生成HTML内容"""
        search_query = data.get('search', {}).get('query', '未知主题')
        papers = data.get('papers', [])
        figures_map = data.get('figures_map', {})
        
        # 生成论文卡片HTML
        papers_html = []
        for i, paper in enumerate(papers, 1):
            pmid = paper.get('pmid', '')
            figures = figures_map.get(pmid, [])
            
            # 获取该论文的总结（如果有）
            paper_summary = None
            if summaries and summaries.get('papers'):
                paper_summary = summaries['papers'].get(pmid)
            
            card_html = self._generate_paper_card(paper, figures, project_path, i, paper_summary)
            papers_html.append(card_html)
        
        # 获取综合总结（如果有）
        overview_html = ""
        if summaries and summaries.get('overview'):
            overview = summaries['overview']
            overview_html = f"""
            <section class="overview-section">
                <h2>综合总结 Overview</h2>
                <div class="overview-content">
                    <div class="summary-cn">
                        <h3>中文总结</h3>
                        <p>{overview.get('overview_cn', '等待生成...')}</p>
                    </div>
                    <div class="summary-en">
                        <h3>English Summary</h3>
                        <p>{overview.get('overview_en', 'Waiting for generation...')}</p>
                    </div>
                </div>
            </section>
            """
        
        # 完整HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PubMed文献综述 - {search_query}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <header class="main-header">
        <div class="container">
            <h1>PubMed 文献综述</h1>
            <p class="search-query">检索主题: <strong>{search_query}</strong></p>
            <p class="meta-info">共 {len(papers)} 篇论文 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </header>
    
    <main class="container">
        {overview_html}
        
        <section class="papers-section">
            <h2>论文详情 Papers</h2>
            <div class="papers-grid">
                {''.join(papers_html)}
            </div>
        </section>
        
        <section class="prompts-section">
            <h2>Prompt 文件位置</h2>
            <div class="prompt-info">
                <p>单篇论文Prompt: <code>{project_path}/step4_prompts/</code></p>
                <p>综合总结Prompt: <code>{project_path}/step5_overview/overview_prompt.txt</code></p>
                <p class="hint">将Prompt内容复制到LLM（如Cursor/ChatGPT）获取总结，然后将结果填入summaries.json</p>
            </div>
        </section>
    </main>
    
    <footer class="main-footer">
        <div class="container">
            <p>Generated by PubMed2Zhihu | {datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
    </footer>
</body>
</html>
"""
        return html
    
    def _generate_paper_card(self, paper: Dict, figures: List[Dict], 
                             project_path: str, index: int, 
                             summary: Optional[Dict] = None) -> str:
        """生成单篇论文的HTML卡片"""
        pmid = paper.get('pmid', '')
        title = paper.get('title', '未知标题')
        authors = paper.get('authors', [])
        journal = paper.get('journal', '未知期刊')
        pub_date = paper.get('pub_date', '')
        abstract = paper.get('abstract', '摘要不可用')
        doi = paper.get('doi', '')
        pmcid = paper.get('pmcid', '')
        
        # 格式化作者
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:3])
            if len(authors) > 3:
                authors_str += f' 等'
        else:
            authors_str = str(authors)
        
        # 生成图片HTML
        figures_html = self._generate_figures_html(figures, project_path)
        
        # 生成总结HTML（如果有）
        summary_html = ""
        if summary:
            summary_html = f"""
            <div class="paper-summary">
                <div class="summary-cn">
                    <h4>中文小结</h4>
                    <p>{summary.get('summary_cn', '')}</p>
                </div>
                <div class="summary-en">
                    <h4>English Summary</h4>
                    <p>{summary.get('summary_en', '')}</p>
                </div>
            </div>
            """
        
        # 链接
        pubmed_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        doi_link = f"https://doi.org/{doi}" if doi else ""
        pmc_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
        
        return f"""
        <article class="paper-card" id="paper-{pmid}">
            <div class="paper-header">
                <span class="paper-index">#{index}</span>
                <h3 class="paper-title">{title}</h3>
            </div>
            
            <div class="paper-meta">
                <span class="authors">{authors_str}</span>
                <span class="journal">{journal}</span>
                <span class="date">{pub_date}</span>
            </div>
            
            <div class="paper-links">
                <a href="{pubmed_link}" target="_blank" class="link-btn pubmed">PubMed</a>
                {f'<a href="{doi_link}" target="_blank" class="link-btn doi">DOI</a>' if doi_link else ''}
                {f'<a href="{pmc_link}" target="_blank" class="link-btn pmc">PMC全文</a>' if pmc_link else ''}
            </div>
            
            <div class="paper-abstract">
                <h4>摘要 Abstract</h4>
                <p>{abstract}</p>
            </div>
            
            {summary_html}
            
            {figures_html}
        </article>
        """
    
    def _generate_figures_html(self, figures: List[Dict], project_path: str) -> str:
        """生成图片展示HTML"""
        if not figures:
            return '<div class="no-figures"><p>该论文无可获取的图片</p></div>'
        
        figures_items = []
        for fig in figures:
            fig_id = fig.get('figure_id', '')
            caption = fig.get('caption', '')
            local_path = fig.get('local_path')
            original_url = fig.get('original_url', '')
            is_original = fig.get('is_original', True)
            
            # 图片来源标记
            source_tag = '<span class="source-tag original">原图</span>' if is_original else '<span class="source-tag generated">示意图</span>'
            
            if local_path:
                # 本地图片 - 使用相对路径
                img_path = f"../step3_figures/{local_path}"
                img_html = f'<img src="{img_path}" alt="{fig_id}" style="max-width: {self.image_width}px;">'
            elif original_url:
                # 使用原始URL
                img_html = f'<img src="{original_url}" alt="{fig_id}" style="max-width: {self.image_width}px;" onerror="this.style.display=\'none\'">'
            else:
                img_html = '<p class="no-image">图片不可用</p>'
            
            figures_items.append(f"""
            <div class="figure-item">
                <div class="figure-header">
                    <span class="figure-id">{fig_id}</span>
                    {source_tag}
                </div>
                <div class="figure-image">
                    {img_html}
                </div>
                <div class="figure-caption">
                    <p>{caption}</p>
                </div>
            </div>
            """)
        
        return f"""
        <div class="paper-figures">
            <h4>图片 Figures ({len(figures)}张)</h4>
            <div class="figures-grid">
                {''.join(figures_items)}
            </div>
        </div>
        """
    
    def _get_css_styles(self) -> str:
        """获取CSS样式"""
        return """
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --accent-color: #0891b2;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-color: #1e293b;
            --text-light: #64748b;
            --border-color: #e2e8f0;
            --success-color: #10b981;
            --warning-color: #f59e0b;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        /* Header */
        .main-header {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
            padding: 40px 0;
            margin-bottom: 40px;
        }
        
        .main-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .search-query {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .meta-info {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: 10px;
        }
        
        /* Sections */
        section {
            margin-bottom: 40px;
        }
        
        section h2 {
            font-size: 1.5rem;
            color: var(--primary-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
        }
        
        /* Overview */
        .overview-section {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        
        .overview-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .overview-content h3 {
            color: var(--primary-color);
            margin-bottom: 15px;
        }
        
        /* Papers Grid */
        .papers-grid {
            display: flex;
            flex-direction: column;
            gap: 30px;
        }
        
        /* Paper Card */
        .paper-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .paper-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        }
        
        .paper-header {
            display: flex;
            align-items: flex-start;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .paper-index {
            background: var(--primary-color);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        
        .paper-title {
            font-size: 1.2rem;
            color: var(--text-color);
            line-height: 1.4;
        }
        
        .paper-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 15px;
            font-size: 0.9rem;
            color: var(--text-light);
        }
        
        .paper-meta .journal {
            color: var(--accent-color);
            font-weight: 500;
        }
        
        .paper-links {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .link-btn {
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            text-decoration: none;
            font-weight: 500;
            transition: background-color 0.2s;
        }
        
        .link-btn.pubmed {
            background: #e0f2fe;
            color: #0369a1;
        }
        
        .link-btn.pubmed:hover {
            background: #bae6fd;
        }
        
        .link-btn.doi {
            background: #fef3c7;
            color: #b45309;
        }
        
        .link-btn.doi:hover {
            background: #fde68a;
        }
        
        .link-btn.pmc {
            background: #d1fae5;
            color: #047857;
        }
        
        .link-btn.pmc:hover {
            background: #a7f3d0;
        }
        
        .paper-abstract {
            margin-bottom: 20px;
        }
        
        .paper-abstract h4 {
            color: var(--secondary-color);
            margin-bottom: 10px;
            font-size: 0.95rem;
        }
        
        .paper-abstract p {
            color: var(--text-light);
            font-size: 0.95rem;
            line-height: 1.7;
        }
        
        /* Summary */
        .paper-summary {
            background: #f0f9ff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .paper-summary h4 {
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 0.95rem;
        }
        
        .summary-cn, .summary-en {
            margin-bottom: 15px;
        }
        
        .summary-cn:last-child, .summary-en:last-child {
            margin-bottom: 0;
        }
        
        /* Figures */
        .paper-figures {
            border-top: 1px solid var(--border-color);
            padding-top: 20px;
        }
        
        .paper-figures h4 {
            color: var(--secondary-color);
            margin-bottom: 15px;
        }
        
        .figures-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .figure-item {
            background: #fafafa;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }
        
        .figure-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background: #f1f5f9;
        }
        
        .figure-id {
            font-weight: 600;
            color: var(--text-color);
        }
        
        .source-tag {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .source-tag.original {
            background: #dcfce7;
            color: #166534;
        }
        
        .source-tag.generated {
            background: #fef3c7;
            color: #92400e;
        }
        
        .figure-image {
            padding: 15px;
            text-align: center;
            background: white;
        }
        
        .figure-image img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }
        
        .figure-caption {
            padding: 15px;
            font-size: 0.9rem;
            color: var(--text-light);
            border-top: 1px solid var(--border-color);
        }
        
        .no-figures {
            text-align: center;
            padding: 20px;
            color: var(--text-light);
            background: #f8fafc;
            border-radius: 8px;
        }
        
        /* Prompts Section */
        .prompts-section {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 30px;
        }
        
        .prompt-info code {
            background: #f1f5f9;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        .prompt-info .hint {
            margin-top: 15px;
            padding: 15px;
            background: #fef3c7;
            border-radius: 8px;
            color: #92400e;
            font-size: 0.9rem;
        }
        
        /* Footer */
        .main-footer {
            background: #1e293b;
            color: #94a3b8;
            padding: 20px 0;
            text-align: center;
            margin-top: 60px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .main-header h1 {
                font-size: 1.8rem;
            }
            
            .overview-content {
                grid-template-columns: 1fr;
            }
            
            .paper-header {
                flex-direction: column;
            }
            
            .figures-grid {
                grid-template-columns: 1fr;
            }
        }
        """


def main(project_path: str) -> bool:
    """
    步骤6主函数 - 可独立运行
    
    Args:
        project_path: 项目路径
    """
    try:
        config = Config()
        logger = Logger("step6_report")
        file_manager = FileManager(config, logger)
        
        logger.step_start(6, "生成HTML报告")
        
        generator = ReportGenerator(config, logger)
        result = generator.generate_report(project_path)
        
        if result['success']:
            # 保存结果
            step6_dir = file_manager.get_step_directory(project_path, 'step6_report')
            output_file = os.path.join(step6_dir, 'report_info.json')
            file_manager.save_json(output_file, result)
            
            logger.step_complete(6, "生成HTML报告")
            return True
        else:
            logger.error(f"生成报告失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger = Logger("step6_report")
        logger.error(f"步骤6执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python step6_generate_report.py <项目路径>")
        sys.exit(1)
    
    success = main(sys.argv[1])
    sys.exit(0 if success else 1)

