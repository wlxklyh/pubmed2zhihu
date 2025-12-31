"""
步骤2：论文详情获取模块
获取论文的完整元数据，包括DOI、PMCID等
支持PDF下载和全文提取
"""
import os
import sys
import ssl
import time
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional

# 处理SSL证书验证问题
ssl._create_default_https_context = ssl._create_unverified_context

# 禁用系统代理（环境变量级别）
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from Bio import Entrez

# PDF处理
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class PaperDetailsFetcher:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        
        # 设置Entrez参数
        Entrez.email = config.get('pubmed', 'email', 'user@example.com')
        api_key = config.get('pubmed', 'api_key', '')
        if api_key:
            Entrez.api_key = api_key
        Entrez.tool = config.get('pubmed', 'tool_name', 'pubmed2zhihu')
        
        self.retry_attempts = config.get_int('pubmed', 'retry_attempts', 3)
        self.retry_delay = config.get_int('pubmed', 'retry_delay', 2)
        
        # PDF下载配置
        self.pdf_enabled = config.get_boolean('pmc', 'pdf_download_enabled', True)
        self.pdf_timeout = config.get_int('pmc', 'pdf_download_timeout', 60)
        self.fulltext_max_words = config.get_int('pmc', 'fulltext_max_words', 8000)
        
        # HTTP请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def fetch_details(self, project_path: str) -> Dict:
        """
        获取论文详细信息
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 详情获取结果
        """
        self.logger.info("开始获取论文详细信息")
        
        try:
            # 加载Step 1的搜索结果
            file_manager = FileManager(self.config, self.logger)
            step1_dir = file_manager.get_step_directory(project_path, 'step1_search')
            search_results_file = os.path.join(step1_dir, 'search_results.json')
            
            if not os.path.exists(search_results_file):
                raise FileNotFoundError(f"未找到搜索结果文件: {search_results_file}")
            
            search_results = file_manager.load_json(search_results_file)
            papers = search_results.get('papers', [])
            
            if not papers:
                self.logger.warning("搜索结果中没有论文")
                return {
                    'success': True,
                    'fetch_time': datetime.now().isoformat(),
                    'papers': [],
                    'message': '没有论文需要获取详情'
                }
            
            self.logger.info(f"需要获取 {len(papers)} 篇论文的详细信息")
            
            # PDF输出目录
            pdfs_dir = os.path.join(project_path, 'step2_details', 'pdfs')
            os.makedirs(pdfs_dir, exist_ok=True)
            
            # 获取每篇论文的详细信息
            detailed_papers = []
            pmids = [p['pmid'] for p in papers]
            
            # 批量获取链接信息（包含PMCID）
            link_info = self._fetch_pmc_links(pmids)
            
            # PDF统计
            papers_with_fulltext = 0
            papers_pdf_failed = 0
            
            for i, paper in enumerate(papers):
                pmid = paper['pmid']
                self.logger.progress(i + 1, len(papers), f"处理: {pmid}")
                
                # 合并基本信息和链接信息
                detailed_paper = paper.copy()
                
                # 添加PMCID信息
                pmc_info = link_info.get(pmid, {})
                pmcid = pmc_info.get('pmcid')
                detailed_paper['pmcid'] = pmcid
                detailed_paper['has_free_fulltext'] = pmcid is not None
                
                # 生成作者简写
                authors = paper.get('authors', [])
                if len(authors) > 3:
                    detailed_paper['authors_short'] = f"{authors[0]} et al."
                elif authors:
                    detailed_paper['authors_short'] = ', '.join(authors)
                else:
                    detailed_paper['authors_short'] = 'Unknown'
                
                # 尝试获取DOI
                doi = self._fetch_doi(pmid)
                detailed_paper['doi'] = doi
                
                # PDF下载和全文提取
                if self.pdf_enabled:
                    if pmcid:
                        self.logger.info(f"下载PDF: {pmcid}")
                        pdf_result = self._download_and_extract_pdf(pmcid, pdfs_dir)
                        detailed_paper['pdf_path'] = pdf_result.get('pdf_path')
                        detailed_paper['fulltext_path'] = pdf_result.get('fulltext_path')
                        detailed_paper['fulltext_status'] = pdf_result.get('status')
                        detailed_paper['fulltext_word_count'] = pdf_result.get('word_count', 0)
                        
                        if pdf_result.get('status') == 'success':
                            papers_with_fulltext += 1
                        elif pdf_result.get('status') in ['download_failed', 'extract_failed']:
                            papers_pdf_failed += 1
                    else:
                        detailed_paper['pdf_path'] = None
                        detailed_paper['fulltext_path'] = None
                        detailed_paper['fulltext_status'] = 'no_pmcid'
                        detailed_paper['fulltext_word_count'] = 0
                
                detailed_papers.append(detailed_paper)
            
            print()  # 换行
            
            # 统计
            papers_with_pmc = sum(1 for p in detailed_papers if p.get('pmcid'))
            
            result = {
                'success': True,
                'fetch_time': datetime.now().isoformat(),
                'query': search_results.get('query', ''),
                'papers': detailed_papers,
                'stats': {
                    'total_papers': len(detailed_papers),
                    'papers_with_pmc': papers_with_pmc,
                    'papers_without_pmc': len(detailed_papers) - papers_with_pmc,
                    'papers_with_fulltext': papers_with_fulltext,
                    'papers_pdf_failed': papers_pdf_failed
                }
            }
            
            self.logger.success(f"详情获取完成: {len(detailed_papers)} 篇论文")
            self.logger.info(f"有PMC全文: {papers_with_pmc} 篇, 无PMC全文: {len(detailed_papers) - papers_with_pmc} 篇")
            if self.pdf_enabled:
                self.logger.info(f"PDF全文提取成功: {papers_with_fulltext} 篇, 失败: {papers_pdf_failed} 篇")
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取论文详情失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fetch_time': datetime.now().isoformat()
            }
    
    def _fetch_pmc_links(self, pmids: List[str]) -> Dict[str, Dict]:
        """
        批量获取PMCID信息
        
        Args:
            pmids: PMID列表
            
        Returns:
            Dict: {pmid: {'pmcid': 'PMCxxxxxxx'}}
        """
        link_info = {}
        
        for attempt in range(self.retry_attempts):
            try:
                # 使用elink获取PMC链接
                handle = Entrez.elink(
                    dbfrom="pubmed",
                    db="pmc",
                    id=pmids,
                    linkname="pubmed_pmc"
                )
                records = Entrez.read(handle)
                handle.close()
                
                # 解析链接结果
                for record in records:
                    pmid = record.get('IdList', [''])[0]
                    linksets = record.get('LinkSetDb', [])
                    
                    pmcid = None
                    for linkset in linksets:
                        if linkset.get('LinkName') == 'pubmed_pmc':
                            links = linkset.get('Link', [])
                            if links:
                                pmc_id = links[0].get('Id', '')
                                pmcid = f"PMC{pmc_id}" if pmc_id else None
                                break
                    
                    link_info[pmid] = {'pmcid': pmcid}
                
                return link_info
                
            except Exception as e:
                self.logger.warning(f"获取PMC链接尝试 {attempt + 1}/{self.retry_attempts} 失败: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    # 失败时返回空信息
                    return {pmid: {'pmcid': None} for pmid in pmids}
        
        return link_info
    
    def _fetch_doi(self, pmid: str) -> Optional[str]:
        """
        获取论文DOI
        
        Args:
            pmid: PubMed ID
            
        Returns:
            str: DOI或None
        """
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=pmid,
                rettype="xml",
                retmode="xml"
            )
            records = Entrez.read(handle)
            handle.close()
            
            for article in records.get('PubmedArticle', []):
                article_ids = article.get('PubmedData', {}).get('ArticleIdList', [])
                for article_id in article_ids:
                    if hasattr(article_id, 'attributes'):
                        if article_id.attributes.get('IdType') == 'doi':
                            return str(article_id)
            
            return None
            
        except Exception:
            return None
    
    def _download_pdf(self, pmcid: str, output_dir: str) -> Optional[str]:
        """
        从PMC下载PDF文件（优先使用Europe PMC）
        
        Args:
            pmcid: PMC ID (如 PMC7847674)
            output_dir: 输出目录
            
        Returns:
            str: PDF文件路径，失败返回None
        """
        if not pmcid:
            return None
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_filename = f"{pmcid}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
            self.logger.info(f"PDF已存在，跳过下载: {pmcid}")
            return pdf_path
        
        # 禁用系统代理
        no_proxy = {'http': None, 'https': None}
        
        # PDF下载源列表（按优先级排序）
        pdf_urls = [
            # Europe PMC - 通常更容易访问
            f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
            # PMC 直接链接
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
            # PMC 备用链接
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/main.pdf",
        ]
        
        for pdf_url in pdf_urls:
            for attempt in range(self.retry_attempts):
                try:
                    response = requests.get(
                        pdf_url,
                        headers=self.headers,
                        timeout=self.pdf_timeout,
                        allow_redirects=True,
                        verify=False,
                        proxies=no_proxy
                    )
                    
                    # 检查是否是PDF
                    content_type = response.headers.get('Content-Type', '')
                    is_pdf = (response.status_code == 200 and 
                              (response.content[:4] == b'%PDF' or 'pdf' in content_type.lower()))
                    
                    if is_pdf and len(response.content) > 1000:
                        with open(pdf_path, 'wb') as f:
                            f.write(response.content)
                        
                        # 验证文件
                        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                            self.logger.info(f"PDF下载成功: {pmcid} (来源: {pdf_url[:30]}...)")
                            return pdf_path
                        else:
                            if os.path.exists(pdf_path):
                                os.remove(pdf_path)
                    
                    # 如果不是PDF，尝试下一个URL
                    break
                        
                except Exception as e:
                    self.logger.warning(f"PDF下载尝试失败 ({pmcid}): {str(e)}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay)
        
        self.logger.warning(f"PDF下载失败: {pmcid} (已尝试所有来源)")
        return None
    
    def _extract_text_from_pdf(self, pdf_path: str, output_path: str) -> Optional[Dict]:
        """
        从PDF提取文本
        
        Args:
            pdf_path: PDF文件路径
            output_path: 文本输出路径
            
        Returns:
            Dict: {'text': str, 'word_count': int} 或 None
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF未安装，无法提取PDF文本")
            return None
        
        if not os.path.exists(pdf_path):
            return None
        
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page in doc:
                full_text += page.get_text()
            
            doc.close()
            
            # 清理文本
            full_text = self._clean_text(full_text)
            word_count = len(full_text.split())
            
            # 如果超过最大词数，提取关键章节
            if word_count > self.fulltext_max_words:
                full_text = self._extract_key_sections(full_text)
                word_count = len(full_text.split())
            
            # 保存文本文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return {
                'text': full_text,
                'word_count': word_count
            }
            
        except Exception as e:
            self.logger.warning(f"PDF文本提取失败: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """
        清理提取的文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # 修复常见的PDF提取问题
        text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)  # 修复断字
        return text.strip()
    
    def _extract_key_sections(self, text: str) -> str:
        """
        从全文中提取关键章节
        
        Args:
            text: 全文文本
            
        Returns:
            str: 提取的关键章节
        """
        # 定义关键章节标题的正则模式
        section_patterns = [
            (r'(?i)\b(abstract)\b', 'Abstract'),
            (r'(?i)\b(introduction)\b', 'Introduction'),
            (r'(?i)\b(methods?|materials?\s+and\s+methods?)\b', 'Methods'),
            (r'(?i)\b(results?)\b', 'Results'),
            (r'(?i)\b(discussion)\b', 'Discussion'),
            (r'(?i)\b(conclusion|conclusions)\b', 'Conclusion'),
        ]
        
        extracted_sections = []
        
        for pattern, section_name in section_patterns:
            match = re.search(pattern, text)
            if match:
                start = match.start()
                # 找到下一个章节的开始位置
                end = len(text)
                for next_pattern, _ in section_patterns:
                    next_match = re.search(next_pattern, text[start + len(match.group()):])
                    if next_match:
                        potential_end = start + len(match.group()) + next_match.start()
                        if potential_end < end:
                            end = potential_end
                
                section_text = text[start:end].strip()
                # 限制每个章节的长度
                words = section_text.split()
                if len(words) > 2000:
                    section_text = ' '.join(words[:2000]) + '...'
                
                extracted_sections.append(f"## {section_name}\n{section_text}")
        
        if extracted_sections:
            result = '\n\n'.join(extracted_sections)
            # 确保不超过最大词数
            words = result.split()
            if len(words) > self.fulltext_max_words:
                result = ' '.join(words[:self.fulltext_max_words]) + '...'
            return result
        
        # 如果无法识别章节，返回前max_words个词
        words = text.split()
        return ' '.join(words[:self.fulltext_max_words]) + ('...' if len(words) > self.fulltext_max_words else '')
    
    def _download_and_extract_pdf(self, pmcid: str, output_dir: str) -> Dict:
        """
        下载PDF并提取全文
        
        Args:
            pmcid: PMC ID
            output_dir: 输出目录
            
        Returns:
            Dict: 包含 pdf_path, fulltext_path, status, word_count
        """
        result = {
            'pdf_path': None,
            'fulltext_path': None,
            'status': 'no_pmcid',
            'word_count': 0
        }
        
        if not pmcid:
            return result
        
        # 下载PDF
        pdf_path = self._download_pdf(pmcid, output_dir)
        
        if not pdf_path:
            result['status'] = 'download_failed'
            return result
        
        result['pdf_path'] = f"pdfs/{pmcid}.pdf"
        
        # 提取文本
        txt_filename = f"{pmcid}.txt"
        txt_path = os.path.join(output_dir, txt_filename)
        
        extract_result = self._extract_text_from_pdf(pdf_path, txt_path)
        
        if extract_result:
            result['fulltext_path'] = f"pdfs/{txt_filename}"
            result['status'] = 'success'
            result['word_count'] = extract_result['word_count']
        else:
            result['status'] = 'extract_failed'
        
        return result


def main(project_path: str) -> bool:
    """
    步骤2主函数 - 可独立运行
    
    Args:
        project_path: 项目路径
    """
    try:
        config = Config()
        logger = Logger("step2_details")
        file_manager = FileManager(config, logger)
        
        logger.step_start(2, "获取论文详情")
        
        fetcher = PaperDetailsFetcher(config, logger)
        result = fetcher.fetch_details(project_path)
        
        if result['success']:
            # 保存结果
            step2_dir = file_manager.get_step_directory(project_path, 'step2_details')
            output_file = os.path.join(step2_dir, 'papers_details.json')
            file_manager.save_json(output_file, result)
            
            logger.step_complete(2, "获取论文详情")
            return True
        else:
            logger.error(f"获取详情失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger = Logger("step2_details")
        logger.error(f"步骤2执行异常: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python step2_fetch_details.py <项目路径>")
        sys.exit(1)
    
    success = main(sys.argv[1])
    sys.exit(0 if success else 1)

