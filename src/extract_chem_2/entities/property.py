from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_text_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = _normalize_text(item)
        if not text:
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            items.append(text)
    return items


def _normalize_recursive(value: Any) -> Any:
    if isinstance(value, str):
        return _normalize_text(value)
    if isinstance(value, list):
        return [_normalize_recursive(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_recursive(item) for key, item in value.items()}
    return value


class ScalarValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    单值: float | int | str | None = Field(
        default=None,
        description="单值结果。允许 number / string / null。",
    )
    最小: float | int | str | None = Field(
        default=None,
        description="最小值。允许 number / string / null。",
    )
    最大: float | int | str | None = Field(
        default=None,
        description="最大值。允许 number / string / null。",
    )
    单位: str | None = Field(
        default=None,
        description="单位文本。",
    )
    误差: float | int | str | None = Field(
        default=None,
        description="误差，如 ±1.03、5%。",
    )
    说明: str | None = Field(
        default=None,
        description="定性描述或无法稳定量化时的说明。",
    )

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_scalars(cls, value):
        if isinstance(value, str):
            return _normalize_text(value)
        return value


class PropertyTestConditions(BaseModel):
    model_config = ConfigDict(extra="allow")

    样品: str | None = Field(default=None, description="测试对象样品名。")
    样品尺寸: str | None = Field(default=None, description="样品尺寸、厚度、间距等。")
    方法: str | None = Field(
        default=None,
        description=(
            "测试方法。若步骤、温度程序或参数复杂且难以标准化，优先保留完整原文。"
        ),
    )
    仪器: str | None = Field(default=None, description="测试仪器、型号。")
    样品预处理: str | None = Field(default=None, description="样品预处理。")
    表面处理: str | None = Field(default=None, description="表面处理或前处理。")
    气氛: str | None = Field(default=None, description="测试气氛或环境气体。")
    测量参数: str | None = Field(default=None, description="难以拆分的综合测试参数。")
    工作距离: str | None = Field(default=None, description="工作距离等实验几何参数。")
    工作时间: str | None = Field(default=None, description="测试时长或暴露时长。")
    工作温度: str | None = Field(default=None, description="工作温度、室温等描述。")
    测试温度: ScalarValue | None = Field(default=None, description="单一测试温度。")
    测试温度范围: ScalarValue | None = Field(default=None, description="测试温度范围。")
    升温速率: ScalarValue | None = Field(default=None, description="升温速率。")
    降温速率: ScalarValue | None = Field(default=None, description="降温速率。")
    温度扫描范围: ScalarValue | None = Field(default=None, description="温度扫描范围。")
    温度扫描速率: ScalarValue | None = Field(default=None, description="温度扫描速率。")

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, value):
        if isinstance(value, dict):
            return _normalize_recursive(value)
        return value

    @field_validator(
        "样品",
        "样品尺寸",
        "方法",
        "仪器",
        "样品预处理",
        "表面处理",
        "气氛",
        "测量参数",
        "工作距离",
        "工作时间",
        "工作温度",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value):
        return _normalize_text(value)


class PropertyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    类别: str = Field(
        ...,
        min_length=1,
        description="性质类别。当前无固定词表，允许中文或英文。",
    )
    名称: str = Field(
        ...,
        min_length=1,
        description="性质指标名称。",
    )
    缩写: str | None = Field(
        default=None,
        description="指标缩写。无稳定缩写时为 null。",
    )
    值: ScalarValue = Field(
        ...,
        description="性质值对象。至少应表达数值范围、单值或定性说明之一。",
    )
    测试条件: PropertyTestConditions = Field(
        ...,
        description=(
            "测试条件与方法。结构化字段优先；复杂步骤、温度变化和程序设定优先保留在“方法”中。"
        ),
    )

    @field_validator("类别", "名称", "缩写", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value):
        return _normalize_text(value)


class PropertyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    性质: List[PropertyEntry] = Field(
        default_factory=list,
        description="目标聚合物的性质条目数组。与表征、工艺流程独立。",
    )
    why: str | None = Field(
        default=None,
        description="可选的顶层依据说明。正式落盘时可由后处理移除。",
    )

    @field_validator("why", mode="before")
    @classmethod
    def _normalize_why(cls, value):
        return _normalize_text(value)


def to_json_schema() -> dict:
    return PropertyResult.model_json_schema()


ScalarValue.model_rebuild()
PropertyTestConditions.model_rebuild()
PropertyEntry.model_rebuild()
PropertyResult.model_rebuild()
