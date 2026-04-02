from typing import TypeVar, Generic, Optional, Type, AsyncIterator, Iterator
from pydantic import BaseModel, Field
from langchain_core.output_parsers import BaseOutputParser
from json_repair import repair_json
import json


# 定义泛型类型
T = TypeVar("T", bound=BaseModel)


class ParseResult(BaseModel, Generic[T]):
    """解析结果模型"""

    parse: Optional[T] = Field(None, description="解析成功的结果")
    raw_text: str = Field(..., description="原始LLM输出文本")
    error: Optional[str] = Field(None, description="解析错误信息(如果有)")


class RobustJSONParser(BaseOutputParser[ParseResult[T]], Generic[T]):
    """
    自定义JSON解析器 - 完整版

    支持:
    - 同步/异步解析
    - 流式/非流式输出
    - 使用json_repair自动修复损坏的JSON
    - 与LangChain完全兼容
    """

    pydantic_model: Type[T]

    def __init__(self, pydantic_model: Type[T]):
        """
        初始化解析器

        参数:
            pydantic_model: 目标Pydantic模型类
        """
        super().__init__(pydantic_model=pydantic_model)

    # ==========================================
    # 非流式解析 - 同步
    # ==========================================
    def parse(self, text: str) -> ParseResult[T]:
        """
        解析LLM输出文本 (同步版本)

        参数:
            text: LLM输出的原始文本

        返回:
            ParseResult: 包含解析结果和原始文本
        """
        try:
            # 使用json_repair修复并提取JSON内容
            json_str = repair_json(text)

            if not json_str:
                return ParseResult(
                    parse=None, raw_text=text, error="未找到有效的JSON内容"
                )

            # 解析JSON
            json_obj = json.loads(json_str)

            # 转换为Pydantic模型
            parsed_obj = self.pydantic_model(**json_obj)

            return ParseResult(parse=parsed_obj, raw_text=text, error=None)

        except json.JSONDecodeError as e:
            return ParseResult(
                parse=None, raw_text=text, error=f"JSON解析错误: {str(e)}"
            )
        except Exception as e:
            return ParseResult(
                parse=None, raw_text=text, error=f"模型验证错误: {str(e)}"
            )

    # ==========================================
    # 非流式解析 - 异步
    # ==========================================
    async def aparse(self, text: str) -> ParseResult[T]:
        """
        解析LLM输出文本 (异步版本)

        参数:
            text: LLM输出的原始文本

        返回:
            ParseResult: 包含解析结果和原始文本
        """
        # 对于JSON解析,异步版本直接调用同步版本
        # 因为JSON解析是CPU密集型,不涉及I/O操作
        return self.parse(text)

    # ==========================================
    # 流式解析 - 同步
    # ==========================================
    def parse_stream(self, stream: Iterator[str]) -> Iterator[ParseResult[T]]:
        """
        解析流式输出 (同步版本)

        参数:
            stream: 文本流迭代器

        返回:
            Iterator[ParseResult]: 解析结果流

        使用示例:
            for result in parser.parse_stream(stream):
                if result.parse:
                    print(f"解析成功: {result.parse}")
        """
        accumulated_text = ""
        last_successful_parse = None

        for chunk in stream:
            accumulated_text += chunk.content

            # 尝试解析当前累积的文本
            result = self._try_parse_partial(accumulated_text)

            # 如果成功解析且与上次不同,则yield
            if result and result.parse:
                # 避免重复yield相同的结果
                if (
                    last_successful_parse is None
                    or result.parse != last_successful_parse
                ):
                    last_successful_parse = result.parse
                    yield result

        # 流结束后,确保返回最终结果
        final_result = self.parse(accumulated_text)
        if not last_successful_parse or (
            final_result.parse and final_result.parse != last_successful_parse
        ):
            yield final_result

    def transform(
        self, input: Iterator[str], config: Optional[dict] = None, **kwargs
    ) -> Iterator[ParseResult[T]]:
        """
        LangChain的transform接口 (同步流式)

        这是LangChain标准的流式处理接口
        """
        return self.parse_stream(input)

    # ==========================================
    # 流式解析 - 异步
    # ==========================================
    async def aparse_stream(
        self, stream: AsyncIterator[str]
    ) -> AsyncIterator[ParseResult[T]]:
        """
        解析流式输出 (异步版本)

        参数:
            stream: 异步文本流迭代器

        返回:
            AsyncIterator[ParseResult]: 解析结果流

        使用示例:
            async for result in parser.aparse_stream(stream):
                if result.parse:
                    print(f"解析成功: {result.parse}")
        """
        accumulated_text = ""
        last_successful_parse = None

        async for chunk in stream:
            accumulated_text += chunk.content

            # 尝试解析当前累积的文本
            result = self._try_parse_partial(accumulated_text)

            # 如果成功解析且与上次不同,则yield
            if result and result.parse:
                if (
                    last_successful_parse is None
                    or result.parse != last_successful_parse
                ):
                    last_successful_parse = result.parse
                    yield result

        # 流结束后,确保返回最终结果
        final_result = await self.aparse(accumulated_text)
        if not last_successful_parse or (
            final_result.parse and final_result.parse != last_successful_parse
        ):
            yield final_result

    async def atransform(
        self, input: AsyncIterator[str], config: Optional[dict] = None, **kwargs
    ) -> AsyncIterator[ParseResult[T]]:
        """
        LangChain的异步transform接口

        这是LangChain标准的异步流式处理接口
        """
        async for result in self.aparse_stream(input):
            yield result

    # ==========================================
    # 辅助方法
    # ==========================================
    def _try_parse_partial(self, text: str) -> Optional[ParseResult[T]]:
        """
        尝试解析部分文本
        只在JSON可能完整时才返回结果
        """
        # 检查是否可能包含完整的JSON
        if not self._looks_complete(text):
            return None

        # 尝试解析
        try:
            json_str = repair_json(text)
            if json_str:
                json_obj = json.loads(json_str)
                parsed_obj = self.pydantic_model(**json_obj)
                return ParseResult(parse=parsed_obj, raw_text=text, error=None)
        except:
            # 解析失败,继续累积
            pass

        return None

    def _looks_complete(self, text: str) -> bool:
        """
        检查文本是否看起来包含完整的JSON
        (简单的启发式检查)
        """
        text = text.strip()

        # 检查是否有JSON的开始和结束
        has_object = "{" in text and "}" in text
        has_array = "[" in text and "]" in text

        if not (has_object or has_array):
            return False

        # 检查括号是否基本平衡
        if has_object:
            open_count = text.count("{")
            close_count = text.count("}")
            if close_count > 0 and close_count >= open_count:
                return True

        if has_array:
            open_count = text.count("[")
            close_count = text.count("]")
            if close_count > 0 and close_count >= open_count:
                return True

        return False

    def get_format_instructions(self) -> str:
        """
        返回格式说明,用于提示LLM如何输出
        """
        schema = self.pydantic_model.model_json_schema()
        return f"""严格按照以下schema输出**合法json**，除此之外绝不得输出任何其他文字:
<SCHEMA>
{json.dumps(schema, indent=2, ensure_ascii=False)}
</SCHEMA>
"""
