import requests
import json
import re
import os
import sys
import warnings
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning

# 忽略不安全的请求警告（针对学校可能存在的证书问题）
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

class SUSTechTIS:
    def __init__(self):
        self.session = requests.Session()
        self.head = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        self.login_url = "https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas"
        self.score_url = "https://tis.sustech.edu.cn/cjgl/grcjcx/grcjcx"

    def login(self, username, password):
        """执行 CAS 登录并获取 Session"""
        print(f"[*] 尝试连接 CAS 认证系统...")
        try:
            # 1. 获取登录页面的 execution ID [cite: 1]
            resp = self.session.get(self.login_url, headers=self.head, verify=False)
            execution = re.findall('name="execution" value="(.+?)"', resp.text)[0]
            
            # 2. 提交登录凭证
            data = {
                'username': username,
                'password': password,
                'execution': execution,
                '_eventId': 'submit',
            }
            resp = self.session.post(self.login_url, data=data, headers=self.head, allow_redirects=False, verify=False)
            
            if "Location" in resp.headers:
                # 3. 跟随重定向以激活 TIS 会话
                # 这一步至关重要，它会从服务器获取并设置 TIS 的会话 cookie (JSESSIONID, route)
                # 必须传递 headers，因为服务器可能在重定向时也需要它们
                self.session.get(resp.headers["Location"], headers=self.head, verify=False)
                
                # 验证 TIS 会话是否真的建立成功 (检查 JSESSIONID 是否已在 cookie 中)
                if 'JSESSIONID' in self.session.cookies:
                    print("[+] 登录成功！")
                    return True
                else:
                    print("[x] CAS 认证成功，但建立 TIS 会话失败。可能是 TIS 系统暂时无响应或重定向逻辑变更。")
                    return False
            else:
                print("[x] 登录失败，请检查学号或密码。")
                return False
        except Exception as e:
            print(f"[x] 登录过程出现异常: {e}")
            return False

    def fetch_grades(self, page_size=500):
        """获取个人成绩查询的所有信息"""
        print(f"[*] 正在从 TIS 获取成绩数据...")
        
        # 构造你抓到的 Payload 结构 
        payload = {
            "pageIndex": 1,
            "pageSize": page_size,
            "xnxq": ""  # 留空查询所有学期
        }

        try:
            # 成绩接口通常接收 JSON 格式的 POST 请求
            resp = self.session.post(self.score_url, json=payload, headers=self.head, verify=False)
            res_json = resp.json()

            if res_json.get('code') == 200:
                raw_list = res_json['content']['list']
                print(f"[+] 成功获取 {len(raw_list)} 门课程的原始记录。")
                
                # 提取并清洗你需要的 7 个字段
                cleaned_data = []
                for item in raw_list:
                    score_value = item.get("zpcj")
                    try:
                        # 尝试将成绩转换为数字，如果失败则默认为0
                        score_value = float(score_value)
                        if score_value == int(score_value): # 如果是整数，显示为整数
                            score_value = int(score_value)
                    except (ValueError, TypeError):
                        score_value = 0 # 不是有效数字则设为0

                    course = {
                        "semester": item.get("xnxqmc"),     # 学年学期 
                        "code": item.get("kcdm"),         # 课程代码 
                        "name": item.get("kcmc"),         # 课程名称 
                        "department": item.get("yxmc"),   # 开课院系 
                        "hours": item.get("xs"),           # 学时 
                        "credits": item.get("xf"),         # 学分 
                        "score": score_value               # 总评成绩 (已处理为数字或0)
                    }
                    cleaned_data.append(course)
                return cleaned_data
            else:
                print(f"[x] API 返回错误: {res_json.get('msg')}")
                return None
        except Exception as e:
            print(f"[x] 获取成绩时发生异常: {e}")
            return None



def main():
    # 建议通过环境变量或输入获取，不要在代码里写死密码
    username = input("请输入学号: ")
    password = input("请输入密码: ")

    tis = SUSTechTIS()
    if tis.login(username, password):
        grades = tis.fetch_grades()
        if grades:
            print("\n" + "="*80)
            print(f"{'学期':<10} | {'课程代码':<8} | {'课程名称':<25} | {'学分':<4} | {'成绩':<5}")
            print("-" * 80)
            for g in grades:
                # 简单的对齐处理
                name = (g['name'][:22] + '..') if len(g['name']) > 22 else g['name']
                print(f"{g['semester']:<10} | {g['code']:<8} | {name:<25} | {g['credits']:<4} | {g['score']:<5}")
            print("="*80 + "\n")

        # 获取课程信息并保存到 config.json
        course_info = tis.fetch_grades()
        if course_info:
            print(f"\n[+] 成功获取到 {len(course_info)} 门课程信息。")
            config_path = Path(__file__).parent / "config.json"
            student_info = {}
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    student_info = json.load(f)
            
            student_info["courses"] = course_info # 更新或设置课程列表
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(student_info, f, ensure_ascii=False, indent=2)
            print(f"[+] 课程信息已保存到 {config_path}")
            
            # 这里你可以将 grades 变量通过 JSON 传给你的 Spring Boot 后端
            # 例如: requests.post("http://localhost:8075/api/save_grades", json=grades)

if __name__ == "__main__":
    main()