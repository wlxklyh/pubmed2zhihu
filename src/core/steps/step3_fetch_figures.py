"""
步骤3：PMC图片提取模块
从PubMed Central获取开放获取论文的图片
使用浏览器截图方式绕过403限制
"""
import os
import sys
import ssl
import time
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

# 处理SSL证书验证问题
ssl._create_default_https_context = ssl._create_unverified_context

from Bio import Entrez

# 浏览器自动化
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.utils.config import Config
from src.utils.logger import Logger
from src.utils.file_manager import FileManager


class PMCFigureFetcher:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        
        # Entrez设置
        Entrez.email = config.get('pubmed', 'email', 'user@example.com')
        api_key = config.get('pubmed', 'api_key', '')
        if api_key:
            Entrez.api_key = api_key
        
        self.timeout = config.get_int('pmc', 'figure_download_timeout', 30)
        self.max_figures = config.get_int('pmc', 'max_figures_per_paper', 5)
        self.retry_attempts = config.get_int('pubmed', 'retry_attempts', 3)
        
        # 请求头 - 模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.ncbi.nlm.nih.gov/',
        }
        
        # 浏览器实例（延迟初始化）
        self._playwright = None
        self._browser = None
    
    def _init_browser(self):
        """初始化浏览器（延迟加载）"""
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning("Playwright未安装，无法使用浏览器截图功能")
            return False
        
        if self._browser is None:
            try:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(headless=True)
                self.logger.info("浏览器初始化成功")
                return True
            except Exception as e:
                self.logger.error(f"浏览器初始化失败: {str(e)}")
                return False
        return True
    
    def _close_browser(self):
        """关闭浏览器"""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def fetch_figures(self, project_path: str) -> Dict:
        """
        获取论文图片（使用浏览器截图方式）
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict: 图片获取结果
        """
        self.logger.info("开始获取PMC论文图片（浏览器截图模式）")
        
        try:
            # 加载Step 2的详情结果
            file_manager = FileManager(self.config, self.logger)
            step2_dir = file_manager.get_step_directory(project_path, 'step2_details')
            details_file = os.path.join(step2_dir, 'papers_details.json')
            
            if not os.path.exists(details_file):
                raise FileNotFoundError(f"未找到论文详情文件: {details_file}")
            
            details_data = file_manager.load_json(details_file)
            papers = details_data.get('papers', [])
            
            # 获取图片输出目录
            step3_dir = file_manager.get_step_directory(project_path, 'step3_figures')
            images_dir = os.path.join(step3_dir, 'images')
            os.makedirs(images_dir, exist_ok=True)
            
            # 筛选有PMCID的论文
            papers_with_pmc = [p for p in papers if p.get('pmcid')]
            
            self.logger.info(f"共 {len(papers)} 篇论文, 其中 {len(papers_with_pmc)} 篇有PMC全文")
            
            # 初始化浏览器
            browser_available = self._init_browser()
            if not browser_available:
                self.logger.warning("浏览器不可用，将只保存图片URL信息")
            
            # 获取每篇论文的图片
            papers_figures = []
            total_figures = 0
            
            try:
                for i, paper in enumerate(papers):
                    pmid = paper['pmid']
                    pmcid = paper.get('pmcid')
                    
                    self.logger.progress(i + 1, len(papers), f"处理: {pmid}")
                    
                    paper_result = {
                        'pmid': pmid,
                        'pmcid': pmcid,
                        'figures': [],
                        'figure_count': 0
                    }
                    
                    if pmcid:
                        # 使用浏览器截图获取图片
                        if browser_available:
                            figures = self._fetch_figures_via_browser(pmcid, images_dir)
                        else:
                            figures = []
                        
                        # 如果浏览器截图失败，保存图片URL信息
                        if not figures:
                            url_info = self._get_figure_urls_from_page(pmcid)
                            if url_info:
                                paper_result['figures'] = url_info
                                paper_result['figure_count'] = len(url_info)
                                paper_result['note'] = '图片URL已获取（可在浏览器中查看）'
                            else:
                                paper_result['note'] = '无法获取图片信息'
                        else:
                            paper_result['figures'] = figures
                            paper_result['figure_count'] = len(figures)
                            total_figures += len(figures)
                    else:
                        paper_result['note'] = '原图不可获取（非开放获取）'
                    
                    papers_figures.append(paper_result)
                
            finally:
                # 关闭浏览器
                self._close_browser()
            
            print()  # 换行
            
            # 统计
            papers_with_figures = sum(1 for p in papers_figures if p['figure_count'] > 0)
            
            result = {
                'success': True,
                'fetch_time': datetime.now().isoformat(),
                'papers': papers_figures,
                'stats': {
                    'total_papers': len(papers),
                    'papers_with_pmc': len(papers_with_pmc),
                    'papers_with_figures': papers_with_figures,
                    'papers_without_figures': len(papers) - papers_with_figures,
                    'total_figures_downloaded': total_figures
                }
            }
            
            self.logger.success(f"图片获取完成: 共截图 {total_figures} 张图片")
            self.logger.info(f"有图片: {papers_with_figures} 篇, 无图片: {len(papers) - papers_with_figures} 篇")
            
            return result
            
        except Exception as e:
            self._close_browser()
            self.logger.error(f"获取图片失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'fetch_time': datetime.now().isoformat()
            }
    
    def _fetch_figures_via_browser(self, pmcid: str, output_dir: str) -> List[Dict]:
        """
        使用浏览器截图获取论文图片
        
        Args:
            pmcid: PMC ID (如 PMC1234567)
            output_dir: 图片输出目录
            
        Returns:
            List[Dict]: 图片信息列表
        """
        if not self._browser:
            return []
        
        figures = []
        pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
        
        try:
            # 创建新页面
            page = self._browser.new_page()
            page.set_viewport_size({"width": 1200, "height": 800})
            
            # 访问PMC文章页面
            page.goto(pmc_url, timeout=self.timeout * 1000)
            
            # 等待页面加载完成
            page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
            
            # 查找所有figure元素
            figure_elements = page.query_selector_all('figure.fig, div.fig')
            
            if not figure_elements:
                # 尝试其他选择器
                figure_elements = page.query_selector_all('[id^="fig"], [id^="F"], .figure')
            
            self.logger.info(f"{pmcid}: 找到 {len(figure_elements)} 个图片元素")
            
            for i, fig_elem in enumerate(figure_elements[:self.max_figures]):
                try:
                    # 获取figure ID
                    fig_id = fig_elem.get_attribute('id') or f"fig{i+1}"
                    
                    # 获取caption
                    caption = ""
                    caption_elem = fig_elem.query_selector('figcaption, .caption, .fig-caption')
                    if caption_elem:
                        caption = caption_elem.inner_text()[:500]
                    
                    # 滚动到元素位置
                    fig_elem.scroll_into_view_if_needed()
                    time.sleep(0.5)  # 等待图片加载
                    
                    # 截图保存
                    screenshot_filename = f"{pmcid}_{fig_id}.png"
                    screenshot_path = os.path.join(output_dir, screenshot_filename)
                    
                    # 截取figure元素
                    fig_elem.screenshot(path=screenshot_path)
                    
                    # 检查截图文件是否有效
                    if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 1000:
                        figures.append({
                            'figure_id': fig_id,
                            'caption': caption,
                            'local_path': f"images/{screenshot_filename}",
                            'original_url': f"{pmc_url}#{fig_id}",
                            'is_original': True,
                            'method': 'browser_screenshot'
                        })
                    else:
                        # 截图失败，删除无效文件
                        if os.path.exists(screenshot_path):
                            os.remove(screenshot_path)
                            
                except Exception as e:
                    self.logger.warning(f"截图失败 {pmcid}/{fig_id}: {str(e)}")
                    continue
            
            page.close()
            
        except PlaywrightTimeout:
            self.logger.warning(f"页面加载超时: {pmcid}")
        except Exception as e:
            self.logger.warning(f"浏览器获取 {pmcid} 图片失败: {str(e)}")
        
        return figures
    
    def _get_figure_urls_from_page(self, pmcid: str) -> List[Dict]:
        """
        从PMC页面获取图片URL和caption信息（不下载）
        
        Args:
            pmcid: PMC ID
            
        Returns:
            List[Dict]: 图片信息列表
        """
        figures = []
        pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
        
        try:
            # 尝试获取页面HTML
            response = requests.get(pmc_url, headers=self.headers, timeout=self.timeout, verify=False)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找figure元素
            figure_elements = soup.select('figure.fig, div.fig, [id^="fig"], [id^="F"]')
            
            for i, fig_elem in enumerate(figure_elements[:self.max_figures]):
                fig_id = fig_elem.get('id', f'fig{i+1}')
                
                # 获取图片URL
                img_elem = fig_elem.select_one('img')
                img_url = ""
                if img_elem:
                    img_url = img_elem.get('src', '') or img_elem.get('data-src', '')
                    if img_url and not img_url.startswith('http'):
                        img_url = f"https://www.ncbi.nlm.nih.gov{img_url}"
                
                # 获取caption
                caption = ""
                caption_elem = fig_elem.select_one('figcaption, .caption, .fig-caption')
                if caption_elem:
                    caption = caption_elem.get_text(strip=True)[:500]
                
                if img_url or caption:
                    figures.append({
                        'figure_id': fig_id,
                        'caption': caption,
                        'local_path': None,
                        'original_url': img_url or f"{pmc_url}#{fig_id}",
                        'is_original': True,
                        'download_failed': True
                    })
                    
        except Exception as e:
            self.logger.warning(f"获取 {pmcid} 页面信息失败: {str(e)}")
        
        return figures
    


def main(project_path: str) -> bool:
    """
    步骤3主函数 - 可独立运行
    
    Args:
        project_path: 项目路径
    """
    try:
        config = Config()
        logger = Logger("step3_figures")
        file_manager = FileManager(config, logger)
        
        logger.step_start(3, "获取PMC图片")
        
        fetcher = PMCFigureFetcher(config, logger)
        result = fetcher.fetch_figures(project_path)
        
        if result['success']:
            # 保存结果
            step3_dir = file_manager.get_step_directory(project_path, 'step3_figures')
            output_file = os.path.join(step3_dir, 'figures_info.json')
            file_manager.save_json(output_file, result)
            
            logger.step_complete(3, "获取PMC图片")
            return True
        else:
            logger.error(f"获取图片失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        logger = Logger("step3_figures")
        logger.error(f"步骤3执行异常: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python step3_fetch_figures.py <项目路径>")
        sys.exit(1)
    
    success = main(sys.argv[1])
    sys.exit(0 if success else 1)
