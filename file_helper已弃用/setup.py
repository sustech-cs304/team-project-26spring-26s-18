from setuptools import setup, find_packages

setup(
    name="file-helper",
    version="0.1.0",
    description="自然语言文件管理助手",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "dashscope>=1.0.0",
    ],
)
