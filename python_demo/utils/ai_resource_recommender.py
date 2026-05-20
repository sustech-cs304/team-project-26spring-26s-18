"""
AI Resource Recommender Module

This module provides AI-powered resource recommendation functionality using OpenAI/DashScope API.
It generates educational resource recommendations (MOOCs, tutorials, documentation) based on user queries.
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Initialize OpenAI client with DashScope API key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


async def generate_resource_recommendations(
    query: str,
    local_resources_found: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate AI-powered resource recommendations based on user query.

    Args:
        query: The user's search query or question
        local_resources_found: List of resources already found in local database

    Returns:
        List of AI-generated resource recommendations in JSON format
    """
    if not DASHSCOPE_API_KEY:
        return []

    # Prepare context about local resources
    local_context = ""
    if local_resources_found:
        local_context = "\n\nAlready found local resources:\n"
        for idx, resource in enumerate(local_resources_found[:5], 1):
            title = resource.get("title", "Unknown")
            resource_type = resource.get("type", "unknown")
            local_context += f"{idx}. {title} ({resource_type})\n"

    # Build prompt for AI
    # Note: Use {{ and }} to escape curly braces in f-string
    prompt = f"""Based on the user's query: "{query}", please recommend relevant educational resources including MOOCs, tutorials, documentation, or learning materials.

Requirements:
1. Recommend 3-5 high-quality, SPECIFIC resources that DIRECTLY address the user's query
2. For each resource, provide:
   - title: Specific course/resource name (e.g., "CS50's Introduction to Computer Science", "PyTorch??????")
   - type: Resource type (mooc|tutorial|documentation|video|article|practice)
   - platform: Platform name (Coursera, Bilibili, GitHub, MDN, etc.)
   - description: DETAILED 2-3 sentences explaining what this resource covers
   - difficulty: beginner|intermediate|advanced
   - url: Provide the MOST SPECIFIC URL you know for this resource. Guidelines:
     * For Coursera: https://www.coursera.org/learn/[course-name] (e.g., https://www.coursera.org/learn/cs50)
     * For edX: https://www.edx.org/course/[course-name]
     * For Bilibili: https://www.bilibili.com/video/BV[xxxxx] if known
     * For GitHub: https://github.com/[owner]/[repo] (e.g., https://github.com/microsoft/Web-Dev-For-Beginners)
     * For docs: specific tutorial page URL
     * If unsure exact URL, use: https://www.bing.com/search?q=[platform]+[course+name]
   - course_slug: The course identifier if applicable (e.g., "cs50", "machine-learning")
3. ONLY recommend well-known, verifiable resources (famous MOOCs, popular repos 10k+ stars, official docs)
4. Do NOT invent fake course URLs - use real ones you know or search links
5. Make recommendations specific to the query
{local_context}

Please return ONLY a JSON array with this exact structure:
[
    {{
        "title": "Specific Resource Name",
        "type": "mooc|tutorial|documentation|video|article|practice",
        "platform": "Platform Name",
        "description": "Detailed 2-3 sentence description",
        "difficulty": "beginner|intermediate|advanced",
        "course_slug": "course-identifier",
        "url": "https://specific-url-or-search-link",
        "source": "AI-generated"
    }}
]

Return valid JSON only, no additional text."""

    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are an expert educational resource recommender. Your task is to suggest high-quality learning resources based on user queries. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        content = response.choices[0].message.content.strip()

        # Try to extract JSON from the response
        try:
            # Direct JSON parsing
            ai_resources = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx + 1]
                ai_resources = json.loads(json_str)
            else:
                return []

        # Validate and clean up resources
        validated_resources = []
        for resource in ai_resources:
            if isinstance(resource, dict) and "title" in resource:
                validated_resource = {
                    "title": resource.get("title", ""),
                    "type": resource.get("type", "resource"),
                    "platform": resource.get("platform", ""),
                    "description": resource.get("description", ""),
                    "difficulty": resource.get("difficulty", "intermediate"),
                    "course_slug": resource.get("course_slug", ""),
                    "url": resource.get("url", ""),
                    "source": "AI-generated"
                }
                validated_resources.append(validated_resource)

        return validated_resources

    except Exception as e:
        print(f"Error generating AI resource recommendations: {e}")
        return []


async def smart_recommend_v2(
    query: str,
    session_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Smart resource recommendation that integrates local resources and AI-generated resources.

    This function combines local database resources with AI-generated recommendations
    to provide a comprehensive list of learning resources. No external search APIs are used.

    Args:
        query: The user's search query
        session_context: Optional session context containing user history, preferences, etc.

    Returns:
        Dictionary containing local resources and AI-generated recommendations
    """
    # Initialize session context if not provided
    if session_context is None:
        session_context = {}

    # Get local resources from session context (previously found by other methods)
    local_resources = session_context.get("local_resources", [])

    # Generate AI recommendations based on query and local resources
    ai_recommendations = await generate_resource_recommendations(query, local_resources)

    # Combine and deduplicate resources by title
    seen_titles = set()
    combined_resources = []

    # Add local resources first (prioritize real resources)
    for resource in local_resources:
        title = resource.get("title", "").lower().strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            combined_resources.append(resource)

    # Add AI-generated resources
    for resource in ai_recommendations:
        title = resource.get("title", "").lower().strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            combined_resources.append(resource)

    return {
        "query": query,
        "local_resources": local_resources,
        "ai_recommendations": ai_recommendations,
        "combined_resources": combined_resources,
        "total_count": len(combined_resources),
        "local_count": len(local_resources),
        "ai_count": len(ai_recommendations)
    }
