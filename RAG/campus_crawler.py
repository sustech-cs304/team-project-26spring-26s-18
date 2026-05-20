"""
校园信息爬虫 - 为RAG系统准备数据
目标网站：
1. 牛蛙评教 https://ncesnext.com
2. 南科大教工部 https://tao.sustech.edu.cn
3. 南科大官网 https://www.sustech.edu.cn
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import re
from urllib.robotparser import RobotFileParser
from typing import List, Dict, Set
from urllib.parse import urljoin

class RespectfulCrawler:
    """遵守robots.txt的爬虫"""
    
    def __init__(self, output_dir: str = "./campus_docs"):
        self.output_dir = output_dir
        self.visited_urls: Set[str] = set()
        os.makedirs(output_dir, exist_ok=True)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 存储每个域名的robots解析器
        self.robot_parsers: Dict[str, RobotFileParser] = {}
    
    def get_robot_parser(self, domain: str) -> RobotFileParser:
        """获取或创建域名的robots解析器"""
        if domain not in self.robot_parsers:
            rp = RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            try:
                rp.read()
                print(f"  已加载 {domain} 的 robots.txt")
            except:
                print(f"  ⚠️ 无法加载 {domain} 的 robots.txt，采用默认允许")
            self.robot_parsers[domain] = rp
        return self.robot_parsers[domain]
    
    def can_fetch(self, url: str) -> bool:
        """检查是否允许抓取该URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path or "/"
        
        rp = self.get_robot_parser(domain)
        try:
            return rp.can_fetch("*", path)
        except:
            return True  # 无法判断时默认允许
    
    def crawl_page(self, url: str, max_depth: int = 1, current_depth: int = 0):
        """爬取单个页面"""
        if current_depth > max_depth:
            return
        if url in self.visited_urls:
            return
        
        # 检查robots.txt
        if not self.can_fetch(url):
            print(f"  ⚠️ robots.txt 禁止: {url}")
            return
        
        print(f"  正在爬取 [{current_depth}]: {url}")
        self.visited_urls.add(url)
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content = self.extract_content(soup, url)
            self.save_content(url, content)
            
            # 继续爬取链接
            if current_depth < max_depth:
                links = self.extract_links(soup, url)
                for link in links[:10]:
                    time.sleep(0.5)
                    self.crawl_page(link, max_depth, current_depth + 1)
                    
        except Exception as e:
            print(f"  爬取失败: {e}")
    
    def extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """提取页面主要内容"""
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        title = soup.title.string if soup.title else "无标题"
        
        # 提取正文
        main_content = (
            soup.find('article') or 
            soup.find('main') or 
            soup.find('div', class_=re.compile(r'content|main|article|news|info')) or
            soup.find('div', id=re.compile(r'content|main|article'))
        )
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines[:300])  # 限制长度
        
        return f"# {title}\n\n来源: {url}\n\n{content}\n"
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取页面中的链接"""
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            full_url = urljoin(base_url, href)
            links.add(full_url)
        return list(links)
    
    def save_content(self, url: str, content: str):
        """保存内容到文件"""
        filename = re.sub(r'[<>:"/\\|?*]', '_', url.replace('https://', '').replace('http://', ''))
        if len(filename) > 100:
            filename = filename[:100]
        
        filepath = os.path.join(self.output_dir, f"{filename}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    已保存: {filename[:50]}...")


# ============================================================
# 配置要爬取的网站
# ============================================================

def crawl_all():
    crawler = RespectfulCrawler(output_dir="./campus_docs")

    # 3. 南科大官网
    print("\n🏫 [3/3] 爬取南科大官网...")
    sustech_urls = [
        "https://www.sustech.edu.cn/zh/about/overview.html",      # 学校概况
        "https://www.sustech.edu.cn/zh/admission/undergraduate.html",  # 本科招生
        "https://www.sustech.edu.cn/zh/academics/programs.html",   # 专业设置
        "https://www.sustech.edu.cn/zh/campus-life/",              # 校园生活
    ]
    for url in sustech_urls:
        crawler.crawl_page(url, max_depth=1)
        time.sleep(1)
    
    print(f"\n✅ 爬取完成！共爬取 {len(crawler.visited_urls)} 个页面")
    print(f"   文件保存在: ./campus_docs")


if __name__ == "__main__":
    print("=" * 50)
    print("校园信息爬虫 - 为RAG系统准备数据")
    print("=" * 50)
    crawl_all()