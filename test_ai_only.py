from file_helper.course_config import identify_course_for_file

tests = [
    'campus_docs/CS303_Lab1_Processes.pdf',
    'campus_docs/navicat_tutorial.docx',
    'campus_docs/MATH205_lecture1.pdf',
    'campus_docs/OS_Assignment3_xv6.pdf',
    'campus_docs/database_project_mysql.sql',
    'campus_docs/xv6_user Programs.pdf',
    'campus_docs/discrete_math_quiz.pdf',
]
for f in tests:
    result = identify_course_for_file(f)
    print(f.split("/")[-1], "->", result)
