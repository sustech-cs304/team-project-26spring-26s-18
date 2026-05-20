"""
URL ???????
??????????????????????????
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import urllib.parse


def get_platform_search_url(title: str, platform: str, course_slug: str = "") -> Dict[str, Any]:
    """
    ???????????
    ???? API??????????????
    
    Args:
        title: ????
        platform: ????
        course_slug: ??????????
        
    Returns:
        {"success": bool, "url": str, "title": str, "platform": str, "is_direct": bool}
    """
    platform_lower = platform.lower()
    
    # ???????????
    search_keywords = course_slug if course_slug else title
    # URL ??
    encoded_query = urllib.parse.quote(search_keywords)
    
    # ??????? URL ??
    search_templates = {
        "coursera": {
            "search": f"https://www.coursera.org/search?query={encoded_query}",
            "course_direct": f"https://www.coursera.org/learn/{course_slug}" if course_slug else None,
        },
        "edx": {
            "search": f"https://www.edx.org/search?q={encoded_query}",
            "course_direct": f"https://www.edx.org/course/{course_slug}" if course_slug else None,
        },
        "bilibili": {
            "search": f"https://search.bilibili.com/all?keyword={encoded_query}",
        },
        "github": {
            "search": f"https://github.com/search?q={encoded_query}&type=repositories",
        },
        "youtube": {
            "search": f"https://www.youtube.com/results?search_query={encoded_query}",
        },
        "mdn": {
            "search": f"https://developer.mozilla.org/en-US/search?q={encoded_query}",
        },
        "w3schools": {
            "search": f"https://www.w3schools.com/search/search.php?q={encoded_query}",
        },
        "stackoverflow": {
            "search": f"https://stackoverflow.com/search?q={encoded_query}",
        },
        "zhihu": {
            "search": f"https://www.zhihu.com/search?type=content&q={encoded_query}",
        },
        "csdn": {
            "search": f"https://so.csdn.net/so/search?q={encoded_query}",
        },
        "juejin": {
            "search": f"https://juejin.cn/search?query={encoded_query}",
        },
        "leetcode": {
            "search": f"https://leetcode.com/search/?q={encoded_query}",
        },
        "khanacademy": {
            "search": f"https://www.khanacademy.org/search?search={encoded_query}",
        },
    }
    
    # ???????
    matched_platform = None
    for key in search_templates.keys():
        if key in platform_lower:
            matched_platform = key
            break
    
    if matched_platform:
        template = search_templates[matched_platform]
        # ????????????? course_slug?????
        if template.get("course_direct"):
            url = template["course_direct"]
            is_direct = True
        else:
            url = template["search"]
            is_direct = False
            
        return {
            "success": True,
            "url": url,
            "title": title,
            "platform": platform,
            "is_direct": is_direct,
            "source": "platform-search"
        }
    
    # ????????? Bing ??
    bing_query = urllib.parse.quote(f"{title} {platform}")
    return {
        "success": True,
        "url": f"https://www.bing.com/search?q={bing_query}",
        "title": title,
        "platform": platform,
        "is_direct": False,
        "source": "bing-fallback"
    }


def verify_and_get_urls(resources: List[Dict[str, Any]], max_verify: int = 5) -> List[Dict[str, Any]]:
    """
    ??????????????
    
    Args:
        resources: AI ???????
        max_verify: ???????
        
    Returns:
        ??????????????? URL
    """
    verified_resources = []
    
    for i, resource in enumerate(resources[:max_verify]):
        title = resource.get("title", "")
        platform = resource.get("platform", "")
        course_slug = resource.get("course_slug", "")
        original_url = resource.get("url", "")
        
        if title and platform:
            result = get_platform_search_url(title, platform, course_slug)
            
            if result["success"]:
                # ?????? URL
                resource["url"] = result["url"]
                resource["url_verified"] = True
                resource["is_direct_link"] = result["is_direct"]
                resource["original_url"] = original_url
                resource["search_method"] = result["source"]
                print(f"[verify_and_get_urls] {title} -> {result['url'][:60]}...")
            else:
                resource["url_verified"] = False
                
        verified_resources.append(resource)
    
    # ??????????
    verified_resources.extend(resources[max_verify:])
    
    return verified_resources


# ?????????????
def build_course_url(platform: str, course_slug: str) -> Optional[str]:
    """
    ???????????????
    """
    if not course_slug:
        return None
        
    platform_lower = platform.lower()
    
    if "coursera" in platform_lower:
        return f"https://www.coursera.org/learn/{course_slug}"
    elif "edx" in platform_lower:
        return f"https://www.edx.org/course/{course_slug}"
    elif "udemy" in platform_lower:
        return f"https://www.udemy.com/course/{course_slug}"
    elif "khanacademy" in platform_lower:
        return f"https://www.khanacademy.org/{course_slug}"
    
    return None
