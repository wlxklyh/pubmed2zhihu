"""
步骤6：生成HTML报告
整合LLM分析结果，生成最终的HTML报告页面（主页+详情页）
"""
import os
import sys
import re
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
    
    def _load_llm_response(self, project_path: str) -> Optional[Dict]:
        """
        加载LLM返回的JSON结果
        
        Args:
            project_path: 项目路径
            
        Returns:
            Optional[Dict]: LLM响应数据，如果不存在则返回None
        """
        llm_response_file = os.path.join(project_path, 'step5_overview', 'llm_response.json')
        
        if os.path.exists(llm_response_file):
            try:
                file_manager = FileManager(self.config, self.logger)
                data = file_manager.load_json(llm_response_file)
                self.logger.info(f"已加载LLM响应: {llm_response_file}")
                return data
            except Exception as e:
                self.logger.warning(f"加载LLM响应失败: {str(e)}")
                return None
        else:
            self.logger.warning(f"未找到LLM响应文件: {llm_response_file}")
            self.logger.info("请先将LLM输出的JSON保存到 step5_overview/llm_response.json")
            return None
    
    def _load_all_data(self, project_path: str, file_manager: FileManager) -> Dict:
        """加载所有步骤的数据"""
        data = {}
        
        step1_file = os.path.join(project_path, 'step1_search', 'search_results.json')
        if os.path.exists(step1_file):
            data['search'] = file_manager.load_json(step1_file)
        
        step2_file = os.path.join(project_path, 'step2_details', 'papers_details.json')
        if os.path.exists(step2_file):
            data['details'] = file_manager.load_json(step2_file)
            data['papers'] = data['details'].get('papers', [])
        
        step3_file = os.path.join(project_path, 'step3_figures', 'figures_info.json')
        if os.path.exists(step3_file):
            data['figures'] = file_manager.load_json(step3_file)
            data['figures_map'] = {}
            for paper_fig in data['figures'].get('papers', []):
                pmid = paper_fig.get('pmid')
                if pmid:
                    data['figures_map'][pmid] = paper_fig.get('figures', [])
        
        return data
    
    def _generate_slug(self, title: str) -> str:
        """生成URL友好的文件名slug"""
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug[:50]
    
    def generate_report(self, project_path: str) -> Dict:
        """
        生成HTML报告（主页+详情页）
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 生成结果
        """
        self.logger.info("开始生成HTML报告")
        
        try:
            file_manager = FileManager(self.config, self.logger)
            
            data = self._load_all_data(project_path, file_manager)
            llm_response = self._load_llm_response(project_path)
            
            final_output_dir = os.path.join(project_path, 'FinalOutput')
            os.makedirs(final_output_dir, exist_ok=True)
            
            papers = data.get('papers', [])
            figures_map = data.get('figures_map', {})
            
            generated_files = []
            
            if llm_response:
                papers_analysis = llm_response.get('papers', {})
                for i, paper in enumerate(papers, 1):
                    pmid = paper.get('pmid', '')
                    paper_analysis = papers_analysis.get(pmid, {})
                    paper_figures = figures_map.get(pmid, [])
                    
                    self.logger.progress(i, len(papers), f"生成详情页: {pmid}")
                    
                    detail_html = self._generate_paper_detail_html(
                        paper, paper_analysis, paper_figures, project_path
                    )
                    
                    slug = self._generate_slug(paper.get('title', pmid))
                    detail_file = os.path.join(final_output_dir, f'{pmid}_{slug}.html')
                    with open(detail_file, 'w', encoding='utf-8') as f:
                        f.write(detail_html)
                    
                    generated_files.append(f'{pmid}_{slug}.html')
                
                print()
            
            overview_html = self._generate_overview_html(data, llm_response, project_path, generated_files)
            overview_file = os.path.join(final_output_dir, 'overview_report.html')
            with open(overview_file, 'w', encoding='utf-8') as f:
                f.write(overview_html)
            
            result = {
                'success': True,
                'generate_time': datetime.now().isoformat(),
                'overview_file': overview_file,
                'detail_files': generated_files,
                'paper_count': len(papers),
                'has_llm_response': llm_response is not None
            }
            
            self.logger.success(f"HTML报告生成完成")
            self.logger.info(f"主报告: {overview_file}")
            self.logger.info(f"详情页: {len(generated_files)} 个")
            
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
    
    def _generate_overview_html(self, data: Dict, llm_response: Optional[Dict], 
                                 project_path: str, detail_files: List[str]) -> str:
        """生成主报告HTML"""
        search_query = data.get('search', {}).get('query', '未知主题')
        papers = data.get('papers', [])
        
        overview = llm_response.get('overview', {}) if llm_response else {}
        papers_analysis = llm_response.get('papers', {}) if llm_response else {}
        
        overview_cn = overview.get('overview_cn', '等待LLM生成...')
        overview_en = overview.get('overview_en', 'Waiting for LLM generation...')
        research_trends = overview.get('research_trends', '')
        key_themes = overview.get('key_themes', [])
        evidence = overview.get('evidence', {})
        hypotheses = overview.get('hypotheses', '')
        open_questions = overview.get('open_questions', [])
        
        themes_html = self._generate_themes_html(key_themes)
        evidence_html = self._generate_evidence_html(evidence)
        questions_html = self._generate_questions_html(open_questions)
        papers_list_html = self._generate_papers_list_html(papers, papers_analysis, detail_files)
        
        fulltext_count = sum(1 for p in papers if p.get('fulltext_status') == 'success')
        abstract_count = len(papers) - fulltext_count
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{search_query} - 文献综述</title>
    <style>
        {self._get_overview_css_styles()}
    </style>
</head>
<body>
    <header>
        <div class="container header-content">
            <span class="doc-type">Literature Review</span>
            <h1>{search_query}</h1>
            <div class="meta-info">
                <span class="meta-item">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                    </svg>
                    共 {len(papers)} 篇论文
                </span>
                <span class="meta-item">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    生成时间: {datetime.now().strftime('%Y-%m-%d')}
                </span>
                <span class="meta-item">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    {fulltext_count}篇全文 / {abstract_count}篇摘要
                </span>
            </div>
        </div>
    </header>
    
    <main>
        <div class="container">
            <!-- 综合综述 -->
            <section class="section">
                <h2 class="section-title">综合综述 Overview</h2>
                
                <div class="overview-card">
                    <h3><span class="lang-tag">ZH</span> 中文综述</h3>
                    <div class="overview-content">{self._format_paragraphs(overview_cn)}</div>
                </div>
                
                <div class="overview-card en-version">
                    <h3><span class="lang-tag">EN</span> English Summary</h3>
                    <div class="overview-content">{self._format_paragraphs(overview_en)}</div>
                </div>
            </section>
            
            <!-- 研究趋势 -->
            {f'''<section class="section">
                <h2 class="section-title">研究趋势 Research Trends</h2>
                <div class="trends-box">
                    <div class="trends-content">{self._format_paragraphs(research_trends)}</div>
                </div>
            </section>''' if research_trends else ''}
            
            <!-- 核心主题 -->
            {f'''<section class="section">
                <h2 class="section-title">核心研究主题 Key Themes</h2>
                {themes_html}
            </section>''' if key_themes else ''}
            
            <!-- 研究证据 -->
            {f'''<section class="section">
                <h2 class="section-title">研究证据 Research Evidence</h2>
                {evidence_html}
            </section>''' if evidence else ''}
            
            <!-- 推测性假说 -->
            {f'''<section class="section">
                <h2 class="section-title">推测性假说 Hypotheses</h2>
                <div class="hypotheses-box">
                    <div class="hypotheses-content">{self._format_paragraphs(hypotheses)}</div>
                </div>
            </section>''' if hypotheses else ''}
            
            <!-- 未解决问题 -->
            {f'''<section class="section">
                <h2 class="section-title">未解决问题与实验策略 Open Questions</h2>
                {questions_html}
            </section>''' if open_questions else ''}
            
            <!-- 论文列表 -->
            <section class="section">
                <h2 class="section-title">纳入文献 Included Studies</h2>
                <div class="papers-summary">
                    {papers_list_html}
                </div>
            </section>
        </div>
    </main>
    
    <footer>
        <div class="container">
            <p>Generated by PubMed2Zhihu | 文献综述报告</p>
            <p>数据来源: NCBI PubMed / PubMed Central | {datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
    </footer>
</body>
</html>
"""
        return html
    
    def _generate_paper_detail_html(self, paper: Dict, paper_analysis: Dict,
                                     figures: List[Dict], project_path: str) -> str:
        """生成单篇论文详情页HTML"""
        pmid = paper.get('pmid', '')
        title = paper.get('title', '未知标题')
        authors = paper.get('authors', [])
        journal = paper.get('journal', '未知期刊')
        pub_date = paper.get('pub_date', '')
        abstract = paper.get('abstract', '摘要不可用')
        doi = paper.get('doi', '')
        pmcid = paper.get('pmcid', '')
        
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:5])
            if len(authors) > 5:
                authors_str += f' 等（共{len(authors)}位作者）'
        else:
            authors_str = str(authors)
        
        research_content = paper_analysis.get('research_content', '')
        future_directions = paper_analysis.get('future_directions', '')
        paper_themes = paper_analysis.get('paper_themes', [])
        
        themes_tags = ''.join([f'<span class="theme-tag">{t}</span>' for t in paper_themes])
        figures_html = self._generate_figures_html(figures, project_path)
        
        pubmed_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        doi_link = f"https://doi.org/{doi}" if doi else ""
        pmc_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title[:80]} - 论文详情</title>
    <style>
        {self._get_detail_css_styles()}
    </style>
</head>
<body>
    <nav class="top-nav">
        <div class="container">
            <a href="overview_report.html" class="back-link">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
                返回综述
            </a>
        </div>
    </nav>
    
    <header>
        <div class="container header-content">
            <span class="paper-type">Research Article</span>
            <h1>{title}</h1>
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
        </div>
    </header>
    
    <main>
        <div class="container">
            <!-- 关键主题 -->
            {f'''<section class="section themes-section">
                <h2 class="section-title">关键主题 Key Themes</h2>
                <div class="themes-container">
                    {themes_tags}
                </div>
            </section>''' if paper_themes else ''}
            
            <!-- 研究内容 -->
            {f'''<section class="section">
                <h2 class="section-title">研究内容 Research Content</h2>
                <div class="content-card">
                    {self._format_paragraphs(research_content)}
                </div>
            </section>''' if research_content else ''}
            
            <!-- 潜在研究方向 -->
            {f'''<section class="section">
                <h2 class="section-title">潜在研究方向 Future Directions</h2>
                <div class="directions-card">
                    {self._format_paragraphs(future_directions)}
                </div>
            </section>''' if future_directions else ''}
            
            <!-- 原文摘要 -->
            <section class="section">
                <h2 class="section-title">原文摘要 Abstract</h2>
                <div class="abstract-card">
                    <p>{abstract}</p>
                </div>
            </section>
            
            <!-- 图片 -->
            {figures_html}
        </div>
    </main>
    
    <footer>
        <div class="container">
            <p>PMID: {pmid} | Generated by PubMed2Zhihu</p>
        </div>
    </footer>
</body>
</html>
"""
        return html
    
    def _format_paragraphs(self, text: str) -> str:
        """将文本格式化为HTML段落"""
        if not text:
            return '<p>内容待生成...</p>'
        
        paragraphs = text.split('\n\n')
        if len(paragraphs) == 1:
            paragraphs = text.split('。')
            if len(paragraphs) > 3:
                chunks = []
                current = []
                for p in paragraphs:
                    current.append(p)
                    if len(current) >= 3:
                        chunks.append('。'.join(current) + '。')
                        current = []
                if current:
                    chunks.append('。'.join(current))
                paragraphs = chunks
            else:
                paragraphs = [text]
        
        return ''.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])
    
    def _generate_themes_html(self, themes: List[Dict]) -> str:
        """生成主题卡片HTML"""
        if not themes:
            return ''
        
        cards = []
        for theme in themes:
            title_cn = theme.get('title_cn', theme.get('title', ''))
            title_en = theme.get('title_en', '')
            description = theme.get('description', '')
            
            cards.append(f'''
            <div class="theme-card">
                <h4>{title_cn}</h4>
                {f'<span class="theme-en">{title_en}</span>' if title_en else ''}
                <p>{description}</p>
            </div>
            ''')
        
        return f'<div class="themes-grid">{" ".join(cards)}</div>'
    
    def _generate_evidence_html(self, evidence: Dict) -> str:
        """生成研究证据HTML"""
        if not evidence:
            return ''
        
        basic = evidence.get('basic_research', '')
        clinical = evidence.get('clinical_research', '')
        
        return f'''
        <div class="evidence-grid">
            <div class="evidence-card basic">
                <h4>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"></path>
                    </svg>
                    基础研究证据
                </h4>
                <div class="evidence-content">{self._format_paragraphs(basic)}</div>
            </div>
            <div class="evidence-card clinical">
                <h4>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                        <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                    </svg>
                    临床研究证据
                </h4>
                <div class="evidence-content">{self._format_paragraphs(clinical)}</div>
            </div>
        </div>
        '''
    
    def _generate_questions_html(self, questions: List[Dict]) -> str:
        """生成未解决问题HTML"""
        if not questions:
            return ''
        
        items = []
        for i, q in enumerate(questions, 1):
            question = q.get('question', '')
            strategy = q.get('strategy', '')
            
            items.append(f'''
            <div class="question-item">
                <div class="question-num">{i}</div>
                <div class="question-content">
                    <h4>{question}</h4>
                    <div class="strategy">
                        <span class="strategy-label">实验策略:</span>
                        <p>{strategy}</p>
                    </div>
                </div>
            </div>
            ''')
        
        return f'<div class="questions-list">{" ".join(items)}</div>'
    
    def _generate_papers_list_html(self, papers: List[Dict], papers_analysis: Dict, 
                                    detail_files: List[str]) -> str:
        """生成论文列表HTML"""
        items = []
        
        file_map = {}
        for f in detail_files:
            pmid = f.split('_')[0]
            file_map[pmid] = f
        
        for i, paper in enumerate(papers, 1):
            pmid = paper.get('pmid', '')
            title = paper.get('title', '未知标题')
            authors = paper.get('authors', [])
            journal = paper.get('journal', '未知期刊')
            pub_date = paper.get('pub_date', '')
            
            if isinstance(authors, list):
                first_author = authors[0] if authors else '未知'
            else:
                first_author = str(authors)
            
            analysis = papers_analysis.get(pmid, {})
            paper_themes = analysis.get('paper_themes', [])
            themes_html = ''.join([f'<span class="mini-tag">{t}</span>' for t in paper_themes[:3]])
            
            detail_file = file_map.get(pmid, '')
            
            if detail_file:
                items.append(f'''
                <a href="{detail_file}" class="paper-item">
                    <span class="paper-num">{i}</span>
                    <div class="paper-info">
                        <div class="paper-title">{title}</div>
                        <div class="paper-meta">{first_author} 等 | {journal} | {pub_date}</div>
                        {f'<div class="paper-themes">{themes_html}</div>' if themes_html else ''}
                    </div>
                    <svg class="arrow-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                </a>
                ''')
            else:
                items.append(f'''
                <div class="paper-item no-link">
                    <span class="paper-num">{i}</span>
                    <div class="paper-info">
                        <div class="paper-title">{title}</div>
                        <div class="paper-meta">{first_author} 等 | {journal} | {pub_date}</div>
                    </div>
                </div>
                ''')
        
        return f'<div class="papers-list">{" ".join(items)}</div>'
    
    def _generate_figures_html(self, figures: List[Dict], project_path: str) -> str:
        """生成图片展示HTML"""
        if not figures:
            return ''
        
        figures_items = []
        for fig in figures:
            fig_id = fig.get('figure_id', '')
            caption = fig.get('caption', '')
            local_path = fig.get('local_path')
            original_url = fig.get('original_url', '')
            
            if local_path:
                # 使用相对路径，使HTML文件可以直接在文件系统中打开
                # FinalOutput目录下的HTML需要访问 ../step3_figures/images/
                img_path = f"../step3_figures/{local_path}"
                # 添加点击放大功能
                img_html = f'<a href="{img_path}" target="_blank" class="figure-link"><img src="{img_path}" alt="{fig_id}" style="max-width: {self.image_width}px; cursor: pointer;" title="点击查看大图"></a>'
            elif original_url:
                img_html = f'<img src="{original_url}" alt="{fig_id}" style="max-width: {self.image_width}px;" onerror="this.style.display=\'none\'">'
            else:
                img_html = '<p class="no-image">图片不可用</p>'
            
            figures_items.append(f'''
            <div class="figure-item">
                <div class="figure-header">{fig_id}</div>
                <div class="figure-image">{img_html}</div>
                <div class="figure-caption">{caption}</div>
            </div>
            ''')
        
        return f'''
        <section class="section">
            <h2 class="section-title">图片 Figures ({len(figures)})</h2>
            <div class="figures-grid">{" ".join(figures_items)}</div>
        </section>
        '''
    
    def _get_overview_css_styles(self) -> str:
        """获取主报告CSS样式"""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Serif+Pro:wght@400;600&family=Noto+Serif+SC:wght@400;600;700&display=swap');
        
        :root {
            --primary: #1a365d;
            --primary-light: #2c5282;
            --primary-dark: #0d1b2a;
            --accent: #ed8936;
            --accent-light: #fbd38d;
            --bg-main: #f7fafc;
            --bg-card: #ffffff;
            --text-dark: #1a202c;
            --text-muted: #4a5568;
            --border-color: #e2e8f0;
            --success: #38a169;
            --info: #3182ce;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Source Serif Pro', 'Noto Serif SC', Georgia, serif;
            line-height: 1.8;
            color: var(--text-dark);
            background: var(--bg-main);
        }
        
        .container { max-width: 1000px; margin: 0 auto; padding: 0 24px; }
        
        /* Header */
        header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: #fff;
            padding: 60px 0 50px;
            position: relative;
        }
        
        header::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--accent-light), transparent);
        }
        
        .doc-type {
            display: inline-block;
            background: var(--accent);
            color: var(--primary-dark);
            font-size: 11px;
            font-weight: 600;
            padding: 5px 16px;
            border-radius: 20px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 20px;
        }
        
        header h1 {
            font-family: 'Playfair Display', 'Noto Serif SC', serif;
            font-size: 28px;
            font-weight: 600;
            line-height: 1.4;
            margin-bottom: 20px;
        }
        
        .meta-info {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 14px;
            opacity: 0.9;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }
        
        .meta-item { display: flex; align-items: center; gap: 8px; }
        .meta-item svg { width: 16px; height: 16px; opacity: 0.8; }
        
        /* Main */
        main { padding: 50px 0 80px; }
        
        .section { margin-bottom: 50px; }
        
        .section-title {
            font-family: 'Playfair Display', 'Noto Serif SC', serif;
            font-size: 22px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--border-color);
            position: relative;
        }
        
        .section-title::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 60px;
            height: 2px;
            background: var(--accent);
        }
        
        /* Overview Cards */
        .overview-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 24px;
            border-left: 4px solid var(--primary);
        }
        
        .overview-card h3 {
            font-size: 18px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .lang-tag {
            font-size: 10px;
            font-weight: 700;
            background: var(--accent-light);
            color: var(--primary-dark);
            padding: 3px 8px;
            border-radius: 4px;
        }
        
        .overview-card.en-version { border-left-color: var(--info); }
        .overview-card.en-version .overview-content { font-style: italic; color: var(--text-muted); }
        
        .overview-content p { margin-bottom: 12px; text-align: justify; }
        .overview-content p:last-child { margin-bottom: 0; }
        
        /* Trends */
        .trends-box {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: #fff;
            border-radius: 12px;
            padding: 32px;
        }
        
        .trends-content p { opacity: 0.95; margin-bottom: 12px; }
        
        /* Themes */
        .themes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .theme-card {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-left: 4px solid var(--accent);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .theme-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.1);
        }
        
        .theme-card h4 {
            font-size: 16px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 8px;
        }
        
        .theme-en {
            display: block;
            font-size: 13px;
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 12px;
        }
        
        .theme-card p { font-size: 14px; color: var(--text-muted); line-height: 1.7; }
        
        /* Evidence */
        .evidence-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
        }
        
        .evidence-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .evidence-card.basic { border-top: 4px solid var(--info); }
        .evidence-card.clinical { border-top: 4px solid var(--success); }
        
        .evidence-card h4 {
            font-size: 16px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .evidence-card h4 svg { width: 20px; height: 20px; }
        .evidence-card.basic h4 svg { color: var(--info); }
        .evidence-card.clinical h4 svg { color: var(--success); }
        
        .evidence-content p { font-size: 14px; color: var(--text-muted); margin-bottom: 10px; }
        
        /* Hypotheses */
        .hypotheses-box {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-left: 4px solid var(--accent);
        }
        
        .hypotheses-content p { margin-bottom: 12px; }
        
        /* Questions */
        .questions-list { display: flex; flex-direction: column; gap: 20px; }
        
        .question-item {
            display: flex;
            gap: 20px;
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .question-num {
            flex-shrink: 0;
            width: 36px;
            height: 36px;
            background: var(--primary);
            color: #fff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
        }
        
        .question-content { flex: 1; }
        .question-content h4 { font-size: 16px; color: var(--primary); margin-bottom: 12px; }
        
        .strategy {
            background: #f0fff4;
            border-radius: 8px;
            padding: 12px 16px;
            margin-top: 12px;
        }
        
        .strategy-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--success);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .strategy p { font-size: 14px; color: var(--text-muted); margin-top: 6px; }
        
        /* Papers List */
        .papers-summary {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .papers-list { display: flex; flex-direction: column; gap: 8px; }
        
        .paper-item {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px;
            background: var(--bg-main);
            border-radius: 10px;
            text-decoration: none;
            color: inherit;
            transition: background 0.2s, transform 0.2s;
        }
        
        .paper-item:hover {
            background: rgba(237, 137, 54, 0.1);
            transform: translateX(4px);
        }
        
        .paper-item.no-link { cursor: default; }
        .paper-item.no-link:hover { transform: none; }
        
        .paper-num {
            flex-shrink: 0;
            width: 32px;
            height: 32px;
            background: var(--primary);
            color: #fff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 600;
        }
        
        .paper-info { flex: 1; min-width: 0; }
        
        .paper-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dark);
            line-height: 1.4;
            margin-bottom: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        
        .paper-meta { font-size: 12px; color: var(--text-muted); }
        
        .paper-themes { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
        
        .mini-tag {
            font-size: 11px;
            background: var(--accent-light);
            color: var(--primary-dark);
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        .arrow-icon {
            flex-shrink: 0;
            width: 20px;
            height: 20px;
            color: var(--text-muted);
            opacity: 0.5;
        }
        
        .paper-item:hover .arrow-icon { opacity: 1; color: var(--accent); }
        
        /* Footer */
        footer {
            background: var(--primary-dark);
            color: rgba(255,255,255,0.7);
            padding: 24px 0;
            text-align: center;
            font-size: 13px;
        }
        
        footer p { margin: 4px 0; }
        
        /* Responsive */
        @media (max-width: 768px) {
            header h1 { font-size: 22px; }
            .evidence-grid { grid-template-columns: 1fr; }
            .themes-grid { grid-template-columns: 1fr; }
            .question-item { flex-direction: column; gap: 12px; }
        }
        """
    
    def _get_detail_css_styles(self) -> str:
        """获取详情页CSS样式"""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Serif+Pro:wght@400;600&family=Noto+Serif+SC:wght@400;600;700&display=swap');
        
        :root {
            --primary: #2d3748;
            --primary-light: #4a5568;
            --accent: #ed8936;
            --accent-light: #fbd38d;
            --bg-main: #f7fafc;
            --bg-card: #ffffff;
            --text-dark: #1a202c;
            --text-muted: #4a5568;
            --border-color: #e2e8f0;
            --success: #38a169;
            --info: #3182ce;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Source Serif Pro', 'Noto Serif SC', Georgia, serif;
            line-height: 1.8;
            color: var(--text-dark);
            background: var(--bg-main);
        }
        
        .container { max-width: 900px; margin: 0 auto; padding: 0 24px; }
        
        /* Top Nav */
        .top-nav {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .back-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: var(--primary);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: color 0.2s;
        }
        
        .back-link:hover { color: var(--accent); }
        .back-link svg { width: 18px; height: 18px; }
        
        /* Header */
        header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: #fff;
            padding: 50px 0 40px;
        }
        
        .paper-type {
            display: inline-block;
            background: var(--accent);
            color: var(--primary);
            font-size: 10px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 16px;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 16px;
        }
        
        header h1 {
            font-family: 'Playfair Display', 'Noto Serif SC', serif;
            font-size: 24px;
            font-weight: 600;
            line-height: 1.4;
            margin-bottom: 16px;
        }
        
        .paper-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            font-size: 13px;
            opacity: 0.9;
            margin-bottom: 16px;
        }
        
        .paper-meta .journal { color: var(--accent-light); }
        
        .paper-links { display: flex; gap: 10px; flex-wrap: wrap; }
        
        .link-btn {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .link-btn:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        
        .link-btn.pubmed { background: #e0f2fe; color: #0369a1; }
        .link-btn.doi { background: #fef3c7; color: #b45309; }
        .link-btn.pmc { background: #d1fae5; color: #047857; }
        
        /* Main */
        main { padding: 40px 0 60px; }
        
        .section { margin-bottom: 40px; }
        
        .section-title {
            font-family: 'Playfair Display', 'Noto Serif SC', serif;
            font-size: 20px;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
        }
        
        /* Themes */
        .themes-container { display: flex; flex-wrap: wrap; gap: 10px; }
        
        .theme-tag {
            display: inline-block;
            background: linear-gradient(135deg, var(--accent), #dd6b20);
            color: #fff;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* Content Cards */
        .content-card, .directions-card, .abstract-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .content-card { border-left: 4px solid var(--info); }
        .directions-card { border-left: 4px solid var(--success); }
        .abstract-card { border-left: 4px solid var(--primary); }
        
        .content-card p, .directions-card p, .abstract-card p {
            margin-bottom: 12px;
            text-align: justify;
        }
        
        /* Figures */
        .figures-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .figure-item {
            background: var(--bg-card);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .figure-header {
            background: var(--primary);
            color: #fff;
            padding: 10px 16px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .figure-image {
            padding: 16px;
            text-align: center;
            background: #fafafa;
        }
        
        .figure-image img { 
            max-width: 100%; 
            height: auto; 
            border-radius: 4px; 
            transition: transform 0.2s ease;
        }
        
        .figure-link {
            display: inline-block;
            text-decoration: none;
        }
        
        .figure-link:hover img {
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .figure-caption {
            padding: 14px 16px;
            font-size: 13px;
            color: var(--text-muted);
            border-top: 1px solid var(--border-color);
        }
        
        /* Footer */
        footer {
            background: var(--primary);
            color: rgba(255,255,255,0.7);
            padding: 20px 0;
            text-align: center;
            font-size: 13px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            header h1 { font-size: 20px; }
            .paper-meta { flex-direction: column; gap: 8px; }
            .figures-grid { grid-template-columns: 1fr; }
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
            final_output_dir = os.path.join(project_path, 'FinalOutput')
            os.makedirs(final_output_dir, exist_ok=True)
            
            # 保存到 FinalOutput（主要位置）
            output_file = os.path.join(final_output_dir, 'report_info.json')
            file_manager.save_json(output_file, result)
            
            # 同时保存到 step6_report（兼容旧版本）
            step6_dir = os.path.join(project_path, 'step6_report')
            os.makedirs(step6_dir, exist_ok=True)
            legacy_output_file = os.path.join(step6_dir, 'report_info.json')
            file_manager.save_json(legacy_output_file, result)
            
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
