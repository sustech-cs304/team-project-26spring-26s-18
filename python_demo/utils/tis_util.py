"""
tis_util.py — 从 TIS 获取课程并存储到 OSS + 数据库
"""

import json
import warnings
from re import findall

import requests
import urllib3.exceptions

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

TIS_QUERY_YXKC_URL = "https://tis.sustech.edu.cn/Xsxk/queryYxkc"
TIS_CAS_LOGIN_URL = "https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas"

HEADER = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/99.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def fetch_courses_from_tis(username: str, password: str) -> list:
    """
    登录 TIS 并获取所有已选课程，返回标准化课程列表。
    失败时抛出异常。
    """
    session = requests.Session()

    # CAS 登录
    req = session.get(TIS_CAS_LOGIN_URL, headers=HEADER, verify=False)
    if req.status_code != 200:
        raise ConnectionError("无法访问 TIS 登录页")

    try:
        execution = findall(r'name="execution" value="(.+?)"', req.text)[0]
    except IndexError:
        raise ConnectionError("无法解析 TIS 登录页")

    req = session.post(
        TIS_CAS_LOGIN_URL,
        data={
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
        },
        headers=HEADER,
        allow_redirects=False,
        verify=False,
    )

    if "Location" not in req.headers:
        raise ValueError("TIS 用户名或密码错误")

    session.get(req.headers["Location"], headers=HEADER, verify=False)

    if "JSESSIONID" not in session.cookies:
        raise ConnectionError("无法获取 TIS 会话")

    # 遍历所有学期
    all_courses = []
    for year_start in range(2018, 2027):
        xn = f"{year_start}-{year_start + 1}"
        for xq in ["1", "2", "3"]:
            xnxq = f"{xn}{xq}"
            payload = {
                "cxsfmt": "0", "p_pylx": "1", "mxpylx": "1",
                "p_sfgldjr": "0", "p_sfredis": "0", "p_sfsyxkgwc": "0",
                "p_xkfsdm": "yixuan", "p_sfxsgwckb": "1",
                "p_xktjz": "", "p_chaxunxh": "", "p_gjz": "",
                "p_skjs": "", "p_kkyx": "", "p_kclb": "", "p_xkxs": "",
                "p_dyc": "", "p_kkxnxq": "", "p_id": "", "p_skyy": "",
                "p_sfmxzj": "", "p_chaxunxkfsdm": "",
                "p_xn": xn, "p_xq": xq, "p_xnxq": xnxq,
                "p_dqxn": xn, "p_dqxq": xq, "p_dqxnxq": xnxq,
            }
            resp = session.post(TIS_QUERY_YXKC_URL, data=payload, headers=HEADER, verify=False)
            if resp.status_code == 200:
                all_courses.extend(resp.json().get("yxkcList", []))

    session.close()

    # 去重 + 标准化格式
    seen, result = set(), []
    for c in all_courses:
        code = c.get("kcdm", "")
        if code and code not in seen:
            seen.add(code)
            name_en = c.get("kcmc_en", "")
            result.append({
                "code": code,
                "name": c.get("kcmc") or name_en or code,
                "keywords": [name_en] if name_en else [],
            })

    return result


def courses_to_oss(user_id: int, courses: list) -> str:
    """
    将课程列表序列化为 JSON 上传到 OSS，返回公网 URL。
    OSS 路径：courses/user_{user_id}.json
    """
    from utils.oss_util import OSSUtil

    json_bytes = json.dumps({"courses": courses}, ensure_ascii=False, indent=2).encode("utf-8")
    oss_key = f"courses/user_{user_id}.json"
    url = OSSUtil.upload(json_bytes, oss_key)
    return url
