from file_helper.course_config import load_courses
courses = load_courses()
lines = []
for c in courses:
    kw = ", ".join(c.get("keywords",[])) if c.get("keywords") else ""
    if kw:
        lines.append(f"{c['code']} - {c['name']} ({kw})")
    else:
        lines.append(f"{c['code']} - {c['name']}")
total = len("\n".join(lines))
print(f"课程数量: {len(courses)}, 字符数: {total}")
