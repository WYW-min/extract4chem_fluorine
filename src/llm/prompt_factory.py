from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from collections.abc import MutableMapping

from langchain_core.prompts import ChatPromptTemplate


class PromptFactory(MutableMapping[str, ChatPromptTemplate]):
    """提示词工厂，单例模式，实现标准字典接口。"""

    _instance: Optional["PromptFactory"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self, prompt_dir: Path | str | None = None, suffixs: list[str] = ["txt", "md"]
    ) -> None:
        if self._initialized:
            return

        self._initialized = True
        self._suffixs = suffixs
        self._prompt_dir = self._resolve_prompt_dir(prompt_dir)
        self._paths: Dict[str, Path] = {}
        self._templates: Dict[str, ChatPromptTemplate] = {}
        self._discover_prompts()

    def _resolve_prompt_dir(self, prompt_dir: Path | str | None) -> Path:
        """解析提示词目录路径。"""
        if prompt_dir is None:
            return Path(__file__).resolve().parents[4] / "configs" / "prompts"
        return Path(prompt_dir)

    def _discover_prompts(self) -> None:
        """扫描提示词目录并建立索引。"""
        if not self._prompt_dir.exists():
            raise FileNotFoundError(f"提示词目录不存在: {self._prompt_dir}")

        for suffix in self._suffixs:
            self._paths.update(
                {p.stem: p for p in self._prompt_dir.glob(f"*.{suffix}")}
            )

    @staticmethod
    def _normalize_id(prompt_id: str) -> str:
        """规范化提示词标识，去除后缀。"""
        return Path(prompt_id).stem if "." in prompt_id else prompt_id

    def _load_text(self, key: str) -> str:
        """加载原始文本内容。"""
        if key not in self._paths:
            available = ", ".join(sorted(self._paths.keys()))
            raise KeyError(
                f"提示词 '{key}' 未定义。\n"
                f"可用提示词: {available}\n"
                f"提示词目录: {self._prompt_dir}"
            )
        return self._paths[key].read_text(encoding="utf-8")

    def _build_template(self, prompt_text: str) -> ChatPromptTemplate:
        """根据提示词文本构建 ChatPromptTemplate。"""
        blocks = self._parse_blocks(prompt_text)
        return (
            ChatPromptTemplate.from_messages(blocks)
            if blocks
            else ChatPromptTemplate.from_template(prompt_text)
        )

    @staticmethod
    def _parse_blocks(prompt_text: str) -> List[Tuple[str, str]]:
        """解析 <system>/<user>/<assistant> 块。"""
        pattern = re.compile(
            r"<(system|user|assistant)>\s*(.*?)\s*</\1>", re.IGNORECASE | re.DOTALL
        )
        matches = pattern.findall(prompt_text)
        return [(role.lower(), content.strip()) for role, content in matches]

    # ==================== MutableMapping 必需接口 ====================

    def __getitem__(self, prompt_id: str) -> ChatPromptTemplate:
        """通过标识获取 ChatPromptTemplate（懒加载）。"""
        key = self._normalize_id(prompt_id)
        if key not in self._templates:
            self._templates[key] = self._build_template(self._load_text(key))
        return self._templates[key]

    def __setitem__(self, prompt_id: str, template: ChatPromptTemplate) -> None:
        """设置提示词模板（支持动态注册）。"""
        key = self._normalize_id(prompt_id)
        self._templates[key] = template

    def __delitem__(self, prompt_id: str) -> None:
        """删除缓存的模板。"""
        key = self._normalize_id(prompt_id)
        if key in self._templates:
            del self._templates[key]
        else:
            raise KeyError(f"提示词 '{prompt_id}' 未加载")

    def __iter__(self) -> Iterator[str]:
        """迭代所有可用的提示词标识。"""
        return iter(self._paths)

    def __len__(self) -> int:
        """返回可用提示词的数量。"""
        return len(self._paths)

    def __contains__(self, prompt_id: object) -> bool:
        """检查提示词是否存在。"""
        if not isinstance(prompt_id, str):
            return False
        key = self._normalize_id(prompt_id)
        return key in self._paths

    def __repr__(self) -> str:
        """返回工厂的字符串表示。"""
        loaded_count = len(self._templates)
        total_count = len(self._paths)
        return (
            f"PromptFactory(total={total_count}, loaded={loaded_count}, "
            f"dir='{self._prompt_dir}')"
        )

    # ==================== 额外便捷方法 ====================

    def get(
        self, prompt_id: str, default: Optional[ChatPromptTemplate] = None
    ) -> Optional[ChatPromptTemplate]:
        """安全获取 ChatPromptTemplate。"""
        try:
            return self[prompt_id]
        except KeyError:
            return default

    def keys(self) -> List[str]:
        """返回所有可用提示词标识列表。"""
        return sorted(self._paths.keys())

    def values(self) -> List[ChatPromptTemplate]:
        """返回所有已加载的模板实例列表。"""
        return [self[key] for key in self._paths.keys()]

    def items(self) -> List[Tuple[str, ChatPromptTemplate]]:
        """返回所有提示词标识和模板的元组列表。"""
        return [(key, self[key]) for key in self._paths.keys()]

    def reload(self) -> None:
        """重新扫描提示词目录并清空缓存。"""
        self._paths.clear()
        self._templates.clear()
        self._discover_prompts()


# 全局单例
prompt_manager: Optional[PromptFactory] = None


def get_prompt_manager(
    prompt_dir: Path | str | None = None, suffixs: List[str] = ["txt", "md"]
) -> PromptFactory:
    """获取提示词工厂单例。"""
    global prompt_manager
    if prompt_manager is None:
        prompt_manager = PromptFactory(prompt_dir=prompt_dir, suffixs=suffixs)
    return prompt_manager


def get_prompt(prompt_id: str) -> ChatPromptTemplate:
    """快捷方式：获取 ChatPromptTemplate。"""
    return get_prompt_manager()[prompt_id]
