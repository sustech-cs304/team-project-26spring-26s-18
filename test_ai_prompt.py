from file_helper.course_config import load_courses, _call_bailian_ai

courses = load_courses()
for c in courses:
    print(f"{c['code']} - {c['name']}")

print("\n--- 测试 AI 对 navicat 的回答 ---")
result = _call_bailian_ai("navicat_tutorial.docx", "")
print(result)
