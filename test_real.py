from file_helper.course_config import identify_course_for_file
import os

docs_dir = "campus_docs"
files = os.listdir(docs_dir)[:15]

for f in files:
    result = identify_course_for_file(os.path.join(docs_dir, f))
    print(f.split(".")[0][:50], "->", result[0], result[1])
