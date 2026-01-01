"""
报告访问测试工具
用于验证报告文件的路径和可访问性
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置UTF-8输出
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# 颜色输出
class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Color.GREEN}[OK] {msg}{Color.END}")

def print_warning(msg):
    print(f"{Color.YELLOW}[WARN] {msg}{Color.END}")

def print_error(msg):
    print(f"{Color.RED}[ERROR] {msg}{Color.END}")

def print_info(msg):
    print(f"{Color.BLUE}[INFO] {msg}{Color.END}")

def test_project_paths(project_name):
    """测试项目路径"""
    print(f"\n{Color.BOLD}测试项目: {project_name}{Color.END}\n")
    
    project_path = os.path.join('projects', project_name)
    
    if not os.path.exists(project_path):
        print_error(f"项目目录不存在: {project_path}")
        return False
    
    print_success(f"项目目录: {project_path}")
    
    # 检查各步骤目录
    steps = {
        'step1_search': 'search_results.json',
        'step2_details': 'papers_details.json',
        'step3_figures': 'figures_info.json',
        'step4_prompts': 'prompts_info.json',
        'step5_overview': 'overview_info.json',
    }
    
    for step_dir, info_file in steps.items():
        step_path = os.path.join(project_path, step_dir)
        info_path = os.path.join(step_path, info_file)
        
        if os.path.exists(info_path):
            print_success(f"{step_dir}: {info_file} 存在")
        else:
            print_warning(f"{step_dir}: {info_file} 不存在")
    
    # 检查LLM响应文件
    llm_response = os.path.join(project_path, 'step5_overview', 'llm_response.json')
    if os.path.exists(llm_response):
        print_success(f"LLM响应文件存在")
        try:
            with open(llm_response, 'r', encoding='utf-8') as f:
                data = json.load(f)
                has_overview = 'overview' in data
                has_papers = 'papers' in data
                paper_count = len(data.get('papers', {}))
                
                if has_overview:
                    print_success(f"  - 包含 overview 数据")
                else:
                    print_error(f"  - 缺少 overview 数据")
                
                if has_papers:
                    print_success(f"  - 包含 {paper_count} 篇论文解读")
                else:
                    print_error(f"  - 缺少 papers 数据")
        except Exception as e:
            print_error(f"  - JSON解析失败: {str(e)}")
    else:
        print_error(f"LLM响应文件不存在: {llm_response}")
    
    # 检查FinalOutput目录
    final_output = os.path.join(project_path, 'FinalOutput')
    if os.path.exists(final_output):
        print_success(f"FinalOutput 目录存在")
        
        # 检查report_info.json
        report_info = os.path.join(final_output, 'report_info.json')
        if os.path.exists(report_info):
            print_success(f"  - report_info.json 存在")
            try:
                with open(report_info, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    print_info(f"    生成时间: {info.get('generate_time', 'N/A')}")
                    print_info(f"    论文数量: {info.get('paper_count', 0)}")
                    print_info(f"    详情页数: {len(info.get('detail_files', []))}")
                    print_info(f"    有LLM数据: {info.get('has_llm_response', False)}")
            except Exception as e:
                print_error(f"    JSON解析失败: {str(e)}")
        else:
            print_error(f"  - report_info.json 不存在")
        
        # 检查overview_report.html
        overview_html = os.path.join(final_output, 'overview_report.html')
        if os.path.exists(overview_html):
            size = os.path.getsize(overview_html)
            print_success(f"  - overview_report.html 存在 ({size:,} 字节)")
        else:
            print_error(f"  - overview_report.html 不存在")
        
        # 统计详情页HTML文件
        html_files = list(Path(final_output).glob('*.html'))
        detail_pages = [f for f in html_files if f.name != 'overview_report.html']
        print_success(f"  - 论文详情页: {len(detail_pages)} 个")
        
    else:
        print_error(f"FinalOutput 目录不存在")
    
    # 生成访问URL
    print(f"\n{Color.BOLD}访问地址:{Color.END}")
    print_info(f"主报告: http://127.0.0.1:5001/project/{project_name}/report")
    print_info(f"或: http://127.0.0.1:5001/project/{project_name}/report/overview_report.html")
    
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
    else:
        # 自动查找最新项目
        projects_dir = 'projects'
        if os.path.exists(projects_dir):
            projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
            if projects:
                project_name = sorted(projects)[-1]  # 最新的项目
                print_info(f"自动选择最新项目: {project_name}")
            else:
                print_error("未找到任何项目")
                sys.exit(1)
        else:
            print_error("projects 目录不存在")
            sys.exit(1)
    
    test_project_paths(project_name)

