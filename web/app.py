"""
PubMed2Zhihu Web应用
提供交互式界面用于文献搜索、总结和报告生成
"""
import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory

# 添加项目根路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager
from src.core.processor import PubMedProcessor

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 全局配置
config = Config()
logger = Logger("web")

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_output_dir():
    """获取输出目录的绝对路径"""
    output_dir = config.get('basic', 'output_dir', './projects')
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(PROJECT_ROOT, output_dir)
    return output_dir

def get_project_path(project_name):
    """获取项目路径"""
    return os.path.join(get_output_dir(), project_name)


@app.route('/')
def index():
    """首页 - 项目列表"""
    file_manager = FileManager(config, logger)
    projects = file_manager.list_projects()
    return render_template('index.html', projects=projects)


@app.route('/new', methods=['GET', 'POST'])
def new_project():
    """创建新项目"""
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            return render_template('new.html', error="请输入搜索关键词")
        
        # 创建项目并执行步骤1-3
        processor = PubMedProcessor()
        result = processor.execute_steps_1_to_3(query)
        
        if result['success']:
            project_path = result['project_path']
            project_name = os.path.basename(project_path)
            return redirect(url_for('project_detail', project_name=project_name))
        else:
            return render_template('new.html', error=f"创建失败: {result.get('error', '未知错误')}")
    
    return render_template('new.html')


@app.route('/project/<project_name>')
def project_detail(project_name):
    """项目详情页"""
    file_manager = FileManager(config, logger)
    project_path = get_project_path(project_name)
    
    if not os.path.exists(project_path):
        return render_template('error.html', message="项目不存在"), 404
    
    # 加载项目数据
    project_data = load_project_data(project_path)
    
    return render_template('project.html', 
                         project_name=project_name,
                         project_path=project_path,
                         data=project_data)


@app.route('/project/<project_name>/step/<int:step_num>', methods=['POST'])
def execute_step(project_name, step_num):
    """执行指定步骤"""
    project_path = get_project_path(project_name)
    
    if not os.path.exists(project_path):
        return jsonify({'success': False, 'error': '项目不存在'})
    
    processor = PubMedProcessor()
    result = processor.execute_step(project_path, step_num)
    
    return jsonify(result)


@app.route('/project/<project_name>/steps456', methods=['POST'])
def execute_steps_456(project_name):
    """执行步骤4-6"""
    project_path = get_project_path(project_name)
    
    if not os.path.exists(project_path):
        return jsonify({'success': False, 'error': '项目不存在'})
    
    processor = PubMedProcessor()
    result = processor.execute_steps_4_to_6(project_path)
    
    return jsonify(result)


@app.route('/project/<project_name>/report')
@app.route('/project/<project_name>/report/')
@app.route('/project/<project_name>/report/<path:filename>')
def view_report(project_name, filename=None):
    """
    查看HTML报告
    
    支持访问：
    - /project/<name>/report -> 主报告 overview_report.html
    - /project/<name>/report/overview_report.html -> 主报告
    - /project/<name>/report/<pmid>_xxx.html -> 论文详情页
    """
    project_path = get_project_path(project_name)
    report_dir = os.path.join(project_path, 'FinalOutput')
    
    # 如果没有指定文件名，默认显示overview_report.html
    if filename is None:
        filename = 'overview_report.html'
    
    report_file = os.path.join(report_dir, filename)
    
    # 调试日志
    logger.info(f"访问报告: {filename}")
    logger.info(f"报告目录: {report_dir}")
    logger.info(f"完整路径: {report_file}")
    logger.info(f"文件存在: {os.path.exists(report_file)}")
    
    if os.path.exists(report_file):
        return send_from_directory(report_dir, filename)
    else:
        # 检查是否是报告未生成的情况
        if filename == 'overview_report.html':
            error_msg = "报告尚未生成，请先在项目详情页点击「生成报告」或运行步骤4-6"
        else:
            error_msg = f"文件不存在: {filename}"
        
        logger.warning(f"报告访问失败: {error_msg} | 路径: {report_file}")
        return render_template('error.html', message=error_msg), 404


@app.route('/project/<project_name>/prompts')
def view_prompts(project_name):
    """查看Prompt列表"""
    project_path = get_project_path(project_name)
    
    prompts = []
    prompts_dir = os.path.join(project_path, 'step4_prompts')
    
    if os.path.exists(prompts_dir):
        for f in os.listdir(prompts_dir):
            if f.startswith('prompt_') and f.endswith('.txt'):
                pmid = f.replace('prompt_', '').replace('.txt', '')
                prompt_path = os.path.join(prompts_dir, f)
                with open(prompt_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                prompts.append({
                    'pmid': pmid,
                    'filename': f,
                    'content': content
                })
    
    # 加载综合Prompt
    overview_prompt = ""
    overview_file = os.path.join(project_path, 'step5_overview', 'overview_prompt.txt')
    if os.path.exists(overview_file):
        with open(overview_file, 'r', encoding='utf-8') as f:
            overview_prompt = f.read()
    
    return render_template('prompts.html',
                         project_name=project_name,
                         prompts=prompts,
                         overview_prompt=overview_prompt)


@app.route('/project/<project_name>/images/<path:filename>')
def serve_image(project_name, filename):
    """提供图片访问"""
    project_path = get_project_path(project_name)
    images_dir = os.path.join(project_path, 'step3_figures', 'images')
    return send_from_directory(images_dir, filename)


@app.route('/project/<project_name>/paper/<path:filename>')
def serve_paper_detail(project_name, filename):
    """提供论文详情页访问"""
    project_path = get_project_path(project_name)
    final_output_dir = os.path.join(project_path, 'FinalOutput')
    
    if os.path.exists(os.path.join(final_output_dir, filename)):
        return send_from_directory(final_output_dir, filename)
    else:
        return render_template('error.html', message="详情页不存在"), 404


@app.route('/api/projects')
def api_projects():
    """API: 获取项目列表"""
    file_manager = FileManager(config, logger)
    projects = file_manager.list_projects()
    return jsonify(projects)


@app.route('/api/project/<project_name>')
def api_project_detail(project_name):
    """API: 获取项目详情"""
    project_path = get_project_path(project_name)
    
    if not os.path.exists(project_path):
        return jsonify({'error': '项目不存在'}), 404
    
    project_data = load_project_data(project_path)
    return jsonify(project_data)


def load_project_data(project_path):
    """加载项目所有数据"""
    data = {
        'summary': {},
        'search': {},
        'papers': [],
        'figures': {},
        'prompts_info': {},
        'overview_info': {},
        'report_info': {}
    }
    
    # 项目摘要
    summary_file = os.path.join(project_path, 'project_summary.json')
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            data['summary'] = json.load(f)
    
    # 搜索结果
    search_file = os.path.join(project_path, 'step1_search', 'search_results.json')
    if os.path.exists(search_file):
        with open(search_file, 'r', encoding='utf-8') as f:
            data['search'] = json.load(f)
    
    # 论文详情
    details_file = os.path.join(project_path, 'step2_details', 'papers_details.json')
    if os.path.exists(details_file):
        with open(details_file, 'r', encoding='utf-8') as f:
            details = json.load(f)
            data['papers'] = details.get('papers', [])
    
    # 图片信息
    figures_file = os.path.join(project_path, 'step3_figures', 'figures_info.json')
    if os.path.exists(figures_file):
        with open(figures_file, 'r', encoding='utf-8') as f:
            data['figures'] = json.load(f)
    
    # Prompts信息
    prompts_file = os.path.join(project_path, 'step4_prompts', 'prompts_info.json')
    if os.path.exists(prompts_file):
        with open(prompts_file, 'r', encoding='utf-8') as f:
            data['prompts_info'] = json.load(f)
    
    # 综合概述信息
    overview_file = os.path.join(project_path, 'step5_overview', 'overview_info.json')
    if os.path.exists(overview_file):
        with open(overview_file, 'r', encoding='utf-8') as f:
            data['overview_info'] = json.load(f)
    
    # 报告信息 - 优先从FinalOutput读取，兼容旧路径step6_report
    report_file = os.path.join(project_path, 'FinalOutput', 'report_info.json')
    if not os.path.exists(report_file):
        report_file = os.path.join(project_path, 'step6_report', 'report_info.json')
    
    if os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            data['report_info'] = json.load(f)
    
    return data


if __name__ == '__main__':
    host = config.get('web', 'host', '127.0.0.1')
    port = config.get_int('web', 'port', 5001)
    debug = config.get_boolean('web', 'debug', True)
    
    print(f"Starting PubMed2Zhihu Web at http://{host}:{port}")
    # 禁用 reloader 以避免与 Playwright 冲突
    # Playwright 运行时会修改内部文件，触发 watchdog 重启导致 EPIPE 错误
    app.run(host=host, port=port, debug=debug, use_reloader=False)

