"""
配置管理模块
从 .env 文件读取 API 配置，初始化 LLM 客户端。
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 加载项目根目录的 .env 文件
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")


def get_config() -> dict:
    """获取 API 配置，如果 .env 不存在则使用默认值"""
    return {
        "base_url": os.getenv("API_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key": os.getenv("API_KEY", "your-api-key-here"),
        "model_name": os.getenv("MODEL_NAME", "deepseek-chat"),
    }


def get_llm_client() -> OpenAI:
    """返回配置好的 OpenAI 兼容客户端"""
    config = get_config()
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )


def get_model_name() -> str:
    """返回配置的模型名称"""
    return get_config()["model_name"]
