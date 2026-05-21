from re import findall
import pandas as pd
import requests
import json
import warnings
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning

# 忽略 SSL 证书警告
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class TIS:
    def __init__(self, username, password):
        self.token = requests.Session()
        self.username = username
        self.password = password
        self.route = ""
        self.jsession_id = ""
        self.header = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        self.login_url = "https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas"

    def login(self) -> None:
        """
        登录 TIS 系统
        """
        print("[!] 测试CAS链接...")
        try:
            req = self.token.get(self.login_url, headers=self.header, verify=False)
            assert (req.status_code == 200)
            print("[+] 成功连接到CAS...")
        except Exception as e:
            print(f"[-] 不能访问CAS: {e}")
            exit(-1)
        
        print("[!] 登录中...")
        try:
            execution = findall('name="execution" value="(.+?)"', req.text)[0]
        except IndexError:
            print("[-] 无法解析登录页面")
            exit(-1)
        
        data = {
            'username': self.username,
            'password': self.password,
            'execution': execution,
            '_eventId': 'submit',
        }
        # 登录用表单提交，不需要 Content-Type
        req = self.token.post(self.login_url, data=data, headers=self.header, allow_redirects=False, verify=False)
        
        if "Location" not in req.headers:
            print("[-] 用户名或密码错误")
            exit(-1)
        
        print("[+] 登录成功，正在获取会话...")
        
        # 关键：重定向时也要传递 headers
        redirect_url = req.headers["Location"]
        req = self.token.get(redirect_url, headers=self.header, verify=False)
        
        # 验证 Cookie
        if 'JSESSIONID' in self.token.cookies:
            self.jsession_id = self.token.cookies['JSESSIONID']
            print(f"[+] 会话获取成功，JSESSIONID: {self.jsession_id[:20]}...")
        else:
            print("[-] 无法获取会话 Cookie")
            exit(-1)

    def get_all_gradebook(self) -> dict:
        """
        获取所有成绩
        """
        print("[!] 正在获取成绩数据...")
        data = {
            "xn": None,
            "xq": None,
            "kcmc": None,
            "cxbj": "-1",
            "pylx": "1",
            "current": 1,
            "pageSize": 500
        }
        req = self.token.post(
            'https://tis.sustech.edu.cn/cjgl/grcjcx/grcjcx',
            json=data,
            headers=self.header,
            verify=False
        )
        result = req.json()
        
        if 'content' not in result:
            print(f"[-] API 返回异常: {result}")
            return {"content": {"list": []}}
        
        count = len(result['content']['list'])
        print(f"[+] 获取到 {count} 条成绩记录")
        return result

    def export_gradebook(self, output_dir: str = None) -> str:
        """
        导出成绩到文件
        """
        if output_dir is None:
            output_dir = Path(__file__).parent
        
        content = self.get_all_gradebook()['content']['list']
        
        if not content:
            print("[-] 没有成绩数据")
            return None
        
        df = pd.DataFrame(content)
        
        # 选择需要的列
        columns_map = {
            'kcmc': '课程名称',
            'kcdm': '课程代码', 
            'xnxqmc': '学年学期',
            'kcmc_en': '课程名称（英文）',
            'kcxz': '课程性质',
            'kclb': '课程类别',
            'kclben': '课程类别（英文）',
            'zzcj': '总评成绩',
            'yxmc': '院系名称',
            'xf': '学分',
            'xscj': '等级成绩'
        }
        
        # 只保留存在的列
        existing_cols = [col for col in columns_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.columns = [columns_map[col] for col in existing_cols]
        
        # 1. 保存 Excel
        excel_path = Path(output_dir) / "gradebook.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"[+] 已保存 Excel: {excel_path}")
        
        # 2. 保存 JSON
        json_path = Path(output_dir) / "gradebook.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print(f"[+] 已保存 JSON: {json_path}")
        
        # 3. 更新 config.json
        self._update_config_json(content, output_dir)
        
        return str(excel_path)
    
    def _update_config_json(self, gradebook_data: list, output_dir: str):
        """
        从成绩数据中提取课程信息，更新 config.json
        """
        config_path = Path(output_dir) / "config.json"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"courses": []}
        
        existing_codes = {c['code'] for c in config.get('courses', [])}
        new_courses = []
        
        for item in gradebook_data:
            course_code = item.get('kcdm', '')
            course_name = item.get('kcmc', '')
            course_name_en = item.get('kcmc_en', '')
            
            if course_code and course_code not in existing_codes:
                new_courses.append({
                    "code": course_code,
                    "name": course_name or course_name_en or course_code,
                    "keywords": [course_name_en] if course_name_en else []
                })
                existing_codes.add(course_code)
        
        if 'courses' not in config:
            config['courses'] = []
        config['courses'].extend(new_courses)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        if new_courses:
            print(f"[+] 已更新 config.json，新增 {len(new_courses)} 门课程")
            for c in new_courses[:5]:
                print(f"    - {c['code']}: {c['name']}")
            if len(new_courses) > 5:
                print(f"    ... 还有 {len(new_courses) - 5} 门")

    def close(self) -> None:
        try:
            self.token.close()
        except Exception:
            pass
