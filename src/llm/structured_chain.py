from __future__ import annotations

from loguru import logger

from .robust_json_parser import RobustJSONParser

"""
LLM 链路封装：提示词 + 模型 + 结构化解析。
"""

import asyncio
import re
from typing import Any, Dict, Iterable, List, Set, Tuple, Type

from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel


class StructuredChain:
    """简化版结构化输出链封装。"""

    def __init__(
        self,
        prompt_template: ChatPromptTemplate,
        data_model: Type[BaseModel],
        llm: BaseChatModel,
    ) -> None:
        """初始化 MyChain，仅依赖提示词文本与模型实例。"""
        self._parser = RobustJSONParser(pydantic_model=data_model)

        # 校验 prompt_template 模板
        if "schema_define" not in prompt_template.input_variables:
            raise ValueError(
                f"prompt_template 缺少必需的输入变量 'schema_define', 对应的提示词如下：\n\n[prompt]\n{prompt_template.pretty_repr()}"
            )
        self._required_inputs: Set[str] = set(prompt_template.input_variables) - {
            "schema_define"
        }

        self._prompt_template = prompt_template
        self._llm = llm
        self.chain = (
            self._prompt_template.partial(
                schema_define=self._parser.get_format_instructions()
            )
            | self._llm
            | self._parser
        )

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """同步执行链路，返回最后一次解析结果。"""
        self._validate_input_data(input_data)
        results = list(self.chain.stream(input_data))
        if not results:
            return None
        return results[-1].model_dump(mode="json")

    def batch(self, input_datas: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """同步批量执行，并统一返回字典结构。"""
        results: List[Dict[str, Any]] = [
            self.run(input_data) for input_data in input_datas
        ]
        return results

    async def arun(self, input_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """异步执行链路，返回最后一次解析结果。"""

        self._validate_input_data(input_data)
        results = [item async for item in self.chain.astream(input_data)]
        if not results:
            return None

        return results[-1].model_dump(mode="json")

    async def abatch(
        self, input_datas: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """异步批量执行，使用并发调用聚合结果。"""
        coroutine_list = [self.arun(data) for data in input_datas]
        results = await asyncio.gather(*coroutine_list, return_exceptions=True)
        return results

    def _validate_input_data(self, input_data: Dict[str, Any]) -> None:
        """校验 input_data 的 key 是否与模板要求的输入变量匹配。"""
        provided_keys = set(input_data.keys())

        # 检查缺失的必需变量
        missing_keys = self._required_inputs - provided_keys
        if missing_keys:
            raise ValueError(
                f"input_data 缺少必需的输入变量: {sorted(missing_keys)}. "
                f"模板需要: {sorted(self._required_inputs)}, "
                f"实际提供: {sorted(provided_keys)}"
            )

        # 检查多余的变量（警告但不抛异常）
        extra_keys = provided_keys - self._required_inputs
        if extra_keys:
            logger.warning(
                f"input_data 包含未使用的输入变量: {sorted(extra_keys)}. "
                f"模板仅需要: {sorted(self._required_inputs)}"
            )

    @property
    def required_inputs(self) -> Set[str]:
        """返回模板所需的输入变量集合（只读属性）。"""
        return self._required_inputs.copy()
