"""端到端测试: Step 1-3"""
import sys
sys.path.insert(0, '.')

from src.core.processor import PubMedProcessor

def test_e2e():
    print("=" * 60)
    print("端到端测试: PubMed搜索 -> 详情获取 -> 图片下载")
    print("=" * 60)
    
    # 使用较小的测试集（5篇论文）
    processor = PubMedProcessor()
    
    # 临时修改配置为5篇
    processor.config.config.set('basic', 'max_results', '5')
    
    # 执行搜索
    result = processor.execute_steps_1_to_3("breast cancer treatment")
    
    print("\n" + "=" * 60)
    if result['success']:
        print("测试成功!")
        print(f"项目路径: {result['project_path']}")
    else:
        print(f"测试失败: {result.get('error')}")
    print("=" * 60)
    
    return result['success']

if __name__ == '__main__':
    success = test_e2e()
    sys.exit(0 if success else 1)

