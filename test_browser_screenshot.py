"""
测试浏览器截图功能
"""
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from src.utils.config import Config
from src.utils.logger import Logger


def test_single_paper():
    """测试单篇论文的图片截图"""
    config = Config()
    logger = Logger("test_browser")
    
    # 测试的PMCID
    pmcid = "PMC9222657"
    output_dir = "./test_screenshots"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        from playwright.sync_api import sync_playwright
        
        logger.info("启动浏览器...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1200, "height": 800})
            
            # 访问PMC页面
            pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
            logger.info(f"访问: {pmc_url}")
            page.goto(pmc_url, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            
            # 查找figure元素
            figure_elements = page.query_selector_all('figure.fig, div.fig')
            
            if not figure_elements:
                figure_elements = page.query_selector_all('[id^="fig"], [id^="F"], .figure')
            
            logger.info(f"找到 {len(figure_elements)} 个图片元素")
            
            # 截图每个figure
            for i, fig_elem in enumerate(figure_elements[:3]):  # 只测试前3个
                try:
                    fig_id = fig_elem.get_attribute('id') or f"fig{i+1}"
                    
                    # 获取caption
                    caption = ""
                    caption_elem = fig_elem.query_selector('figcaption, .caption, .fig-caption')
                    if caption_elem:
                        caption = caption_elem.inner_text()[:200]
                    
                    # 滚动到元素
                    fig_elem.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    
                    # 截图
                    screenshot_path = os.path.join(output_dir, f"{pmcid}_{fig_id}.png")
                    fig_elem.screenshot(path=screenshot_path)
                    
                    logger.success(f"截图成功: {fig_id}")
                    logger.info(f"  路径: {screenshot_path}")
                    logger.info(f"  Caption: {caption[:100]}...")
                    
                except Exception as e:
                    logger.warning(f"截图失败 {i}: {str(e)}")
            
            browser.close()
            
        logger.success("测试完成!")
        logger.info(f"截图保存在: {output_dir}")
        
    except ImportError:
        logger.error("Playwright未安装，请运行: py -m pip install playwright")
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_single_paper()


