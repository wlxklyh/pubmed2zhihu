"""
步骤1：PubMed搜索模块
根据关键词搜索PubMed，获取相关论文的PMID和基本信息
"""
import os
import sys
import ssl
import time
from datetime import datetime
from typing import Dict, List, Optional

# 处理SSL证书验证问题
ssl._create_default_https_context = ssl._create_unverified_context

# Biopython Entrez模块
from Bio import Entrez

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class PubMedSearcher:
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
    
    def search(self, query: str, max_results: int = None) -> Dict:
        """
        执行PubMed搜索
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数，默认从配置读取
            
        Returns:
            Dict: 搜索结果
        """
        if max_results is None:
            max_results = self.config.get_int('basic', 'max_results', 20)
        
        self.logger.info(f"开始PubMed搜索: {query}")
        self.logger.info(f"最大结果数: {max_results}")
        
        try:
            # 步骤1: 搜索获取PMID列表
            pmids = self._fetch_pmids(query, max_results)
            
            if not pmids:
                self.logger.warning("未找到匹配的论文")
                return {
                    'success': True,
                    'query': query,
                    'search_time': datetime.now().isoformat(),
                    'total_found': 0,
                    'returned_count': 0,
                    'papers': []
                }
            
            self.logger.info(f"找到 {len(pmids)} 篇论文，正在获取基本信息...")
            
            # 步骤2: 获取论文基本信息
            papers = self._fetch_basic_info(pmids)
            
            result = {
                'success': True,
                'query': query,
                'search_time': datetime.now().isoformat(),
                'total_found': len(pmids),
                'returned_count': len(papers),
                'papers': papers
            }
            
            self.logger.success(f"搜索完成，获取了 {len(papers)} 篇论文的基本信息")
            return result
            
        except Exception as e:
            self.logger.error(f"PubMed搜索失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_time': datetime.now().isoformat()
            }
    
    def _fetch_pmids(self, query: str, max_results: int) -> List[str]:
        """
        搜索PubMed获取PMID列表
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            List[str]: PMID列表
        """
        for attempt in range(self.retry_attempts):
            try:
                # 使用esearch搜索
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=max_results,
                    sort="relevance"  # 按相关性排序
                )
                record = Entrez.read(handle)
                handle.close()
                
                pmids = record.get("IdList", [])
                total_count = int(record.get("Count", 0))
                
                self.logger.info(f"PubMed总共找到 {total_count} 篇相关论文")
                
                return pmids
                
            except Exception as e:
                self.logger.warning(f"搜索尝试 {attempt + 1}/{self.retry_attempts} 失败: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
        
        return []
    
    def _fetch_basic_info(self, pmids: List[str]) -> List[Dict]:
        """
        获取论文基本信息
        
        Args:
            pmids: PMID列表
            
        Returns:
            List[Dict]: 论文信息列表
        """
        papers = []
        
        for attempt in range(self.retry_attempts):
            try:
                # 使用efetch获取详细信息
                handle = Entrez.efetch(
                    db="pubmed",
                    id=pmids,
                    rettype="xml",
                    retmode="xml"
                )
                records = Entrez.read(handle)
                handle.close()
                
                # 解析每篇论文
                for i, article in enumerate(records.get('PubmedArticle', [])):
                    try:
                        paper = self._parse_article(article)
                        papers.append(paper)
                        self.logger.progress(i + 1, len(pmids), f"解析论文: {paper['pmid']}")
                    except Exception as e:
                        self.logger.warning(f"解析论文失败: {str(e)}")
                        continue
                
                print()  # 换行
                return papers
                
            except Exception as e:
                self.logger.warning(f"获取信息尝试 {attempt + 1}/{self.retry_attempts} 失败: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
        
        return papers
    
    def _parse_article(self, article: Dict) -> Dict:
        """
        解析单篇论文信息
        
        Args:
            article: PubMed文章数据
            
        Returns:
            Dict: 解析后的论文信息
        """
        medline = article.get('MedlineCitation', {})
        article_data = medline.get('Article', {})
        
        # PMID
        pmid = str(medline.get('PMID', ''))
        
        # 标题
        title = article_data.get('ArticleTitle', '')
        if isinstance(title, list):
            title = ' '.join(str(t) for t in title)
        
        # 摘要
        abstract_data = article_data.get('Abstract', {})
        abstract_texts = abstract_data.get('AbstractText', [])
        if isinstance(abstract_texts, list):
            abstract_parts = []
            for text in abstract_texts:
                if hasattr(text, 'attributes') and 'Label' in text.attributes:
                    label = text.attributes['Label']
                    abstract_parts.append(f"{label}: {str(text)}")
                else:
                    abstract_parts.append(str(text))
            abstract = ' '.join(abstract_parts)
        else:
            abstract = str(abstract_texts) if abstract_texts else ''
        
        # 作者
        author_list = article_data.get('AuthorList', [])
        authors = []
        for author in author_list:
            if isinstance(author, dict):
                last_name = author.get('LastName', '')
                fore_name = author.get('ForeName', '')
                if last_name:
                    authors.append(f"{last_name} {fore_name}".strip())
        
        # 期刊
        journal_info = article_data.get('Journal', {})
        journal = journal_info.get('Title', '')
        if not journal:
            journal = journal_info.get('ISOAbbreviation', '')
        
        # 发表日期
        pub_date_data = article_data.get('ArticleDate', [])
        if pub_date_data:
            date_info = pub_date_data[0] if isinstance(pub_date_data, list) else pub_date_data
            year = date_info.get('Year', '')
            month = date_info.get('Month', '')
            pub_date = f"{year}-{month}" if month else year
        else:
            # 尝试从Journal获取日期
            journal_issue = journal_info.get('JournalIssue', {})
            pub_date_info = journal_issue.get('PubDate', {})
            year = pub_date_info.get('Year', '')
            month = pub_date_info.get('Month', '')
            pub_date = f"{year}-{month}" if month else year
        
        return {
            'pmid': pmid,
            'title': title,
            'abstract': abstract,
            'authors': authors,
            'journal': journal,
            'pub_date': pub_date
        }


def main(query: str, output_dir: str = None) -> bool:
    """
    步骤1主函数 - 可独立运行
    
    Args:
        query: 搜索关键词
        output_dir: 输出目录（可选）
    """
    try:
        config = Config()
        logger = Logger("step1_search")
        
        logger.step_start(1, "PubMed搜索")
        
        searcher = PubMedSearcher(config, logger)
        result = searcher.search(query)
        
        if result['success']:
            # 如果指定了输出目录，保存结果
            if output_dir:
                file_manager = FileManager(config, logger)
                output_file = os.path.join(output_dir, 'search_results.json')
                file_manager.save_json(output_file, result)
            
            logger.step_complete(1, "PubMed搜索")
            
            # 打印摘要
            logger.info(f"搜索关键词: {query}")
            logger.info(f"找到论文数: {result['returned_count']}")
            
            return True
        else:
            logger.error(f"搜索失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger = Logger("step1_search")
        logger.error(f"步骤1执行异常: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python step1_search_pubmed.py <搜索关键词> [输出目录]")
        sys.exit(1)
    
    query = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = main(query, output_dir)
    sys.exit(0 if success else 1)

