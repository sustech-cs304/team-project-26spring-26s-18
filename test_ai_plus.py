import json
import urllib.request
from file_helper.course_config import load_courses
from file_helper.config import BAILIAN_API_KEY

courses = load_courses()
course_lines = []
for c in courses:
    kw = ", ".join(c.get("keywords",[])) if c.get("keywords") else ""
    if kw:
        course_lines.append(f"{c['code']} - {c['name']} ({kw})")
    else:
        course_lines.append(f"{c['code']} - {c['name']}")
course_list = "\n".join(course_lines)

test_cases = [
    "navicat_tutorial.docx",
    "xv6_Lab3.pdf",
    "CS303_Lab1.pdf",
    "database_project.sql",
    "MATH205_quiz.pdf",
    "discrete_math.pdf",
    "Principles_of_Database_Systems.pdf",
    "SoftwareEngineering_Lab.pdf",
]

for filename in test_cases:
    prompt = f"""文件名: {filename}
内容: 无

课程列表:
{course_list}

请根据文件名判断属于哪门课程，直接返回JSON：
{{"course_code": "课程代码", "course_name": "课程名称"}}
无法判断返回: {{"course_code": "Unknown", "course_name": "Unknown"}}
"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    try:
        req = urllib.request.Request(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            print(f"{filename}: {content}")
    except Exception as e:
        print(f"{filename}: ERROR - {e}")
