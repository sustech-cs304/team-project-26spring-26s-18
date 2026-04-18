import requests
from bs4 import BeautifulSoup

url = "https://ncesnext.com/"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"状态码: {resp.status_code}")
    print(f"内容长度: {len(resp.text)}")
    # 打印前500字符看看是否是正常页面
    print(resp.text[:500])
except Exception as e:
    print(f"请求失败: {e}")