"""测试Step 1: PubMed搜索"""
import sys
sys.path.insert(0, '.')

from src.core.steps.step1_search_pubmed import PubMedSearcher
from src.utils.config import Config
from src.utils.logger import Logger

def test_search():
    config = Config()
    logger = Logger('test')
    
    searcher = PubMedSearcher(config, logger)
    result = searcher.search('cancer immunotherapy', 5)
    
    print("\n" + "=" * 50)
    print(f"搜索成功: {result['success']}")
    print(f"论文数量: {result.get('returned_count', 0)}")
    print("=" * 50)
    
    if result['success'] and result.get('papers'):
        print("\n论文列表:")
        for i, paper in enumerate(result['papers'], 1):
            print(f"\n{i}. PMID: {paper['pmid']}")
            print(f"   标题: {paper['title'][:80]}...")
            print(f"   期刊: {paper['journal']}")
            print(f"   日期: {paper['pub_date']}")
            print(f"   作者: {', '.join(paper['authors'][:3])}...")

if __name__ == '__main__':
    test_search()

