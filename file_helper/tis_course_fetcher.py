"""
tis_course_fetcher.py — 从 TIS 选课系统爬取学生已选课程

接口来源：Network 抓包
  URL:   https://tis.sustech.edu.cn/Xsxk/queryYxkc
  Method: POST (Form Data)
  Response: { yxkcList: [...] }

使用方式：
  from file_helper.tis_course_fetcher import TISCourseFetcher

  fetcher = TISCourseFetcher("你的学号", "你的密码")
  fetcher.login()

  # 方式1：获取所有学期
  courses = fetcher.get_selected_courses()

  # 方式2：指定学期（格式：学年-学期，xq=1/2/3）
  courses = fetcher.get_selected_courses(semester='2025-2026-1')

  # 导出到 file_helper/user_config.json
  fetcher.update_config(courses)

  fetcher.close()
"""

from re import findall
import json
import warnings
from pathlib import Path
import sys

import requests
import urllib3.exceptions

# 忽略 SSL 证书警告
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# TIS 选课接口 URL
TIS_QUERY_YXKC_URL = "https://tis.sustech.edu.cn/Xsxk/queryYxkc"
TIS_CAS_LOGIN_URL = "https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas"


class TISCourseFetcher:
    """从 TIS 选课系统获取已选课程"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.jsession_id = ""

        self.header = {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/99.0.0.0 Safari/537.36"
            ),
            "x-requested-with": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

    # ── 登录 ────────────────────────────────────────────────

    def login(self) -> bool:
        """
        CAS 单点登录 TIS
        成功返回 True，失败抛异常
        """
        print("[!] 测试 CAS 链接...")
        try:
            req = self.session.get(TIS_CAS_LOGIN_URL, headers=self.header, verify=False)
            assert req.status_code == 200
            print("[+] CAS 连接成功")
        except Exception as e:
            print(f"[-] 无法访问 CAS: {e}")
            raise ConnectionError("CAS 不可达")

        print("[!] 登录中...")
        try:
            execution = findall(
                r'name="execution" value="(.+?)"', req.text
            )[0]
        except IndexError:
            print("[-] 无法解析登录页面")
            raise ConnectionError("无法解析 CAS 登录页")

        data = {
            'username': self.username,
            'password': self.password,
            'execution': execution,
            '_eventId': 'submit',
        }
        req = self.session.post(
            TIS_CAS_LOGIN_URL,
            data=data,
            headers=self.header,
            allow_redirects=False,
            verify=False,
        )

        if "Location" not in req.headers:
            raise ValueError("用户名或密码错误")

        print("[+] 登录成功，正在获取会话...")

        redirect_url = req.headers["Location"]
        req = self.session.get(redirect_url, headers=self.header, verify=False)

        if 'JSESSIONID' in self.session.cookies:
            self.jsession_id = self.session.cookies['JSESSIONID']
            print(f"[+] 会话获取成功，JSESSIONID: {self.jsession_id[:20]}...")
        else:
            raise ConnectionError("无法获取会话 Cookie")

        return True

    # ── 选课数据获取 ────────────────────────────────────────

    def get_selected_courses(self, semester: str = None) -> list:
        """
        获取学生已选课程

        semester=None         → 遍历所有学期（从 2010 秋季到当前）
        semester="2025-2026-1" → 指定某学期（xq=1 秋 / 2 春 / 3 夏短学期）

        返回 yxkcList 中的课程字典列表
        """
        if semester:
            return self._fetch_single_semester(semester)

        return self._fetch_all_semesters()

    def _fetch_single_semester(self, semester: str) -> list:
        """查询单个学期"""
        xn, xq = semester.rsplit('-', 1)
        xnxq = f'{xn}{xq}'

        req = self.session.post(
            TIS_QUERY_YXKC_URL,
            data=self._make_payload(xn, xq, xnxq, xn, xq, xnxq),
            headers=self.header,
            verify=False,
        )

        if req.status_code != 200:
            print(f"[-] 请求失败: HTTP {req.status_code}")
            return []

        courses = req.json().get('yxkcList', [])
        print(f"[+] {xn} 第{xq}学期：{len(courses)} 门课程")
        return courses

    def _fetch_all_semesters(self) -> list:
        """遍历所有学期"""
        all_courses = []

        semesters = []
        for year_start in range(2010, 2027):
            for xq in ['1', '2', '3']:
                xn = f'{year_start}-{year_start + 1}'
                semesters.append((xn, xq, f'{xn}{xq}'))

        print(f"[!] 开始遍历 {len(semesters)} 个学期...")

        for xn, xq, xnxq in semesters:
            data = self._make_payload(xn, xq, xnxq, xn, xq, xnxq)
            req = self.session.post(
                TIS_QUERY_YXKC_URL,
                data=data,
                headers=self.header,
                verify=False,
            )
            if req.status_code != 200:
                continue

            courses = req.json().get('yxkcList', [])
            if courses:
                print(f"    [+] {xn} 第{xq}学期：{len(courses)} 门")
                all_courses.extend(courses)

        # 按 (课程代码, 学年, 学期) 去重
        seen = set()
        unique = []
        for c in all_courses:
            key = (c.get('kcdm', ''), c.get('xn', ''), c.get('xq', ''))
            if key not in seen:
                seen.add(key)
                unique.append(c)

        print(f"[+] 共 {len(unique)} 门不重复课程")
        return unique

    def _make_payload(
        self,
        xn: str,
        xq: str,
        xnxq: str,
        dqxn: str,
        dqxq: str,
        dqxnxq: str,
    ) -> dict:
        """
        构造选课查询的 Form Data
        参数从浏览器 Network 抓包获取（见文件头部注释）
        """
        return {
            # 固定参数
            'cxsfmt': '0',
            'p_pylx': '1',
            'mxpylx': '1',
            'p_sfgldjr': '0',
            'p_sfredis': '0',
            'p_sfsyxkgwc': '0',
            'p_xkfsdm': 'yixuan',    # 已选模式
            'p_sfxsgwckb': '1',
            # 空字段（保留，服务器可能检查存在性）
            'p_xktjz': '',
            'p_chaxunxh': '',
            'p_gjz': '',
            'p_skjs': '',
            'p_kkyx': '',
            'p_kclb': '',
            'p_xkxs': '',
            'p_dyc': '',
            'p_kkxnxq': '',
            'p_id': '',
            'p_skyy': '',
            'p_sfmxzj': '',
            'p_chaxunxkfsdm': '',
            # 学期参数
            'p_xn': xn,
            'p_xq': xq,
            'p_xnxq': xnxq,
            'p_dqxn': dqxn,
            'p_dqxq': dqxq,
            'p_dqxnxq': dqxnxq,
        }

    # ── 导出 / 更新 config ──────────────────────────────────

    def update_config(self, courses: list, config_path: str = None) -> None:
        """
        把课程列表增量写入 file_helper/user_config.json

        对每个课程：
          - code: 课程代码 (kcdm)
          - name: 课程中文名 (kcmc)
          - keywords: 课程英文名 (kcmc_en)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "user_config.json"

        config_path = Path(config_path)

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"courses": []}

        all_courses = []
        seen_codes = set()
        for item in courses:
            code = item.get('kcdm', '')
            name = item.get('kcmc', '')
            name_en = item.get('kcmc_en', '')

            if code and code not in seen_codes:
                seen_codes.add(code)
                all_courses.append({
                    "code": code,
                    "name": name or name_en or code,
                    "keywords": [name_en] if name_en else [],
                })

        config['courses'] = all_courses

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"[+] config.json 更新完成，共 {len(all_courses)} 门课程")

    # ── 清理 ────────────────────────────────────────────────

    def close(self) -> None:
        """关闭会话"""
        try:
            self.session.close()
        except Exception:
            pass


# ── 命令行入口 ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python tis_course_fetcher.py <学号> <密码>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]

    fetcher = TISCourseFetcher(username, password)
    try:
        fetcher.login()
        courses = fetcher.get_selected_courses()           # 获取全部学期
        # courses = fetcher.get_selected_courses('2025-2026-1')  # 指定学期
        fetcher.update_config(courses)
    finally:
        fetcher.close()
