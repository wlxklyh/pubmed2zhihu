"""测试Step 3并保存结果"""
import sys
sys.path.insert(0, '.')

from src.core.steps.step3_fetch_figures import PMCFigureFetcher
from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager
import os

def test_and_save():
    config = Config()
    logger = Logger('test')
    file_manager = FileManager(config, logger)
    
    project_path = './projects/20251231_224737_breast_cancer_treatment'
    
    fetcher = PMCFigureFetcher(config, logger)
    result = fetcher.fetch_figures(project_path)
    
    # 保存结果
    step3_dir = file_manager.get_step_directory(project_path, 'step3_figures')
    output_file = os.path.join(step3_dir, 'figures_info.json')
    file_manager.save_json(output_file, result)
    
    print("\n" + "=" * 50)
    print(f"结果已保存到: {output_file}")
    print(f"统计: {result.get('stats', {})}")
    print("=" * 50)
    
    # 显示有图片URL的论文
    for paper in result.get('papers', []):
        if paper.get('figures'):
            print(f"\nPMID: {paper['pmid']}")
            for fig in paper['figures']:
                print(f"  - {fig['figure_id']}: {fig.get('original_url', 'N/A')[:80]}...")

if __name__ == '__main__':
    test_and_save()


