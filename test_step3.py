"""测试Step 3: 图片获取"""
import sys
sys.path.insert(0, '.')

from src.core.steps.step3_fetch_figures import PMCFigureFetcher
from src.utils.config import Config
from src.utils.logger import Logger

def test_figure_fetch():
    config = Config()
    logger = Logger('test')
    
    # 测试已有的项目
    project_path = './projects/20251231_224737_breast_cancer_treatment'
    
    fetcher = PMCFigureFetcher(config, logger)
    result = fetcher.fetch_figures(project_path)
    
    print("\n" + "=" * 50)
    print(f"获取成功: {result['success']}")
    print(f"统计信息: {result.get('stats', {})}")
    print("=" * 50)
    
    if result['success']:
        for paper in result.get('papers', []):
            print(f"\nPMID: {paper['pmid']}, PMCID: {paper.get('pmcid', 'N/A')}")
            print(f"  图片数: {paper['figure_count']}")
            for fig in paper.get('figures', []):
                print(f"    - {fig['figure_id']}: {fig['local_path']}")

if __name__ == '__main__':
    test_figure_fetch()


