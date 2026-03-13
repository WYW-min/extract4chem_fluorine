import os
from langchain.chat_models import init_chat_model
from typing import Dict, Optional

class LLMManager:
    """LLM管理器，单例模式，用于管理和获取不同的语言模型"""
    
    _instance: Optional['LLMManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._models: Dict = {}
        self._configs = {
            "doubao": {
                "model": "doubao-seed-1-6-flash",
                "model_provider": "openai",
                "temperature": 0,
                "base_url": os.getenv("DOUBAO_BASEURL"),
                "api_key": os.getenv("DOUBAO_APIKEY_FS"),
                "max_completion_tokens": 64000
            },
            "gpt": {
                "model": "gpt-5.2",
                "model_provider": "openai",
                "temperature": 0,
                "base_url": os.getenv("BASEURL_FS"),
                "api_key": os.getenv("OPENAI_APIKEY_FS"),
                "reasoning_effort": "high"
            },
            "gpt_medium": {
                "model": "gpt-5.2",
                "model_provider": "openai",
                "temperature": 0,
                "base_url": os.getenv("BASEURL_FS"),
                "api_key": os.getenv("OPENAI_APIKEY_FS"),
                "reasoning_effort": "medium"
            },
            "gpt_low": {
                "model": "gpt-5.2",
                "model_provider": "openai",
                "temperature": 0,
                "base_url": os.getenv("BASEURL_FS"),
                "api_key": os.getenv("OPENAI_APIKEY_FS"),
                "reasoning_effort": "low"
            },
            "qwen_stream": {
                "model": "qwen3-max-preview",
                "model_provider": "openai",
                "temperature": 0,
                "base_url": os.getenv("QWEN_BASEURL"),
                "api_key": os.getenv("QWEN_APIKEY_FS"),
                "extra_body": {"enable_thinking": True},
                "stream": True,
            },
            "qwen": {
                "model": "qwen3-max",
                "model_provider": "openai",
                "temperature": 0,
                "base_url": os.getenv("QWEN_BASEURL"),
                "api_key": os.getenv("QWEN_APIKEY_FS"),
                "response_format": {
                    "type": "json_object"
                },
            }
        }
    
    def __getitem__(self, model_name: str):
        """通过模型名获取对应的模型实例"""
        if model_name not in self._models:
            if model_name not in self._configs:
                raise KeyError(f"Model '{model_name}' not found in configurations")
            self._models[model_name] = init_chat_model(**self._configs[model_name])
        return self._models[model_name]
    
    def get_config(self, model_name: str) -> dict:
        """获取模型配置"""
        return self._configs.get(model_name, {})


# 创建单例实例
llm_manager = LLMManager()