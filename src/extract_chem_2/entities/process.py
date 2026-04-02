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
    raw_items = value if isinstance(value, list) else [value]

    items: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = _normalize_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
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


class ProcessValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    单值: float | int | str | None = Field(default=None, description="单值结果。")
    单位: str | None = Field(default=None, description="单位。")

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_scalars(cls, value):
        if isinstance(value, str):
            return _normalize_text(value)
        return value


class ProcessMaterial(BaseModel):
    model_config = ConfigDict(extra="allow")

    原料名称: str = Field(..., min_length=1, description="原料名称或文中使用的物质名称。")
    原料类别: str | None = Field(
        default=None,
        description="如单体/聚合物/溶剂/添加剂/催化剂/引发剂/交联剂/酸/碱/试剂，或自行总结。",
    )
    原料类型: str | None = Field(
        default=None,
        description="原料类型或角色，如二胺、聚酰亚胺前驱体溶液。需与原料类别区分。",
    )
    IUPAC名称: str | None = Field(default=None, description="原文未给出则省略。")
    缩写: str | None = Field(default=None, description="原文中的稳定简称。")
    分子式: str | None = Field(default=None, description="原文未给出则省略。")
    SMILES: str | None = Field(default=None, description="原文未给出则省略。")
    CAS号: str | None = Field(default=None, description="原文未给出则省略。")
    InChI: str | None = Field(default=None, description="原文未给出则省略。")
    投料方式: str | None = Field(
        default=None,
        description="投料、加入或分散方式。复杂时保留原文最小片段。",
    )
    型号: str | None = Field(default=None, description="规格、粒径、型号等。")
    来源: str | None = Field(default=None, description="供应商、来源。")
    质量: ProcessValue | None = Field(default=None, description="质量。")
    体积: ProcessValue | None = Field(default=None, description="体积。")
    摩尔量: ProcessValue | None = Field(default=None, description="摩尔量。")
    当量比: ProcessValue | None = Field(default=None, description="当量比。")
    纯度: ProcessValue | None = Field(default=None, description="纯度。")

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "原料类型" not in data and "单体类型" in data:
            data["原料类型"] = data.get("单体类型")
        data.pop("单体类型", None)
        if "SMILES" not in data and "smiles" in data:
            data["SMILES"] = data.get("smiles")
        data.pop("smiles", None)
        if "InChI" not in data and "inchi" in data:
            data["InChI"] = data.get("inchi")
        data.pop("inchi", None)
        return _normalize_recursive(data)

    @field_validator(
        "原料名称",
        "原料类别",
        "原料类型",
        "IUPAC名称",
        "缩写",
        "分子式",
        "SMILES",
        "CAS号",
        "InChI",
        "投料方式",
        "型号",
        "来源",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value):
        return _normalize_text(value)


class ReactionCondition(BaseModel):
    model_config = ConfigDict(extra="allow")

    反应装置: str | None = Field(default=None, description="装置、设备或反应平台。")
    反应气氛: str | None = Field(default=None, description="反应气氛。")
    反应温度: ProcessValue | None = Field(default=None, description="反应温度。")
    溶剂: str | None = Field(default=None, description="溶剂名称。")
    溶剂量: ProcessValue | None = Field(default=None, description="溶剂量。")
    反应时间: ProcessValue | None = Field(default=None, description="反应时间。")
    制备过程: str | None = Field(
        default=None,
        description="制备过程。复杂时优先保留完整原文。",
    )
    反应条件: str | None = Field(
        default=None,
        description="反应条件。复杂时优先保留完整原文。",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, value):
        if isinstance(value, dict):
            return _normalize_recursive(value)
        return value

    @field_validator(
        "反应装置",
        "反应气氛",
        "溶剂",
        "制备过程",
        "反应条件",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value):
        return _normalize_text(value)


class LocationIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str | None = Field(default=None, description="块级定位。")
    md_range: str | None = Field(default=None, description="Markdown 范围定位。")
    原文: str | None = Field(default=None, description="关键原文摘录。")

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value):
        return _normalize_text(value)


class ProcessStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    产物名称: str = Field(..., min_length=1, description="当前产物节点名称。")
    产物质量: float |  None = Field(default=None, description="产物质量。")
    产物单位: str | None = Field(default=None, description="产物质量单位。")
    产物收率百分比: float | None = Field(
        default=None,
        description="产物收率百分比。",
    )
    原料: List[ProcessMaterial] = Field(
        default_factory=list,
        description="当前产物节点对应的原料列表。",
    )
    反应条件: List[ReactionCondition] = Field(
        default_factory=list,
        description="当前产物节点的反应条件列表。复杂时保留原文。",
    )
    后处理步骤: str | list[str] | None = Field(
        default=None,
        description="后处理步骤，可以是字符串，也可以是数组。",
    )
    位置索引: LocationIndex | None = Field(
        default=None,
        description="位置索引与关键原文。",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_step_input(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("原料") is None:
            data["原料"] = []
        if data.get("反应条件") is None:
            data["反应条件"] = []
        return _normalize_recursive(data)

    @field_validator("产物名称", "产物单位", mode="before")
    @classmethod
    def _normalize_product_text(cls, value):
        return _normalize_text(value)

    @field_validator("后处理步骤", mode="before")
    @classmethod
    def _normalize_postprocess(cls, value):
        if isinstance(value, list):
            normalized = _normalize_text_list(value)
            return normalized or None
        return _normalize_text(value)


class ProcessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    工艺流程: List[ProcessStep] = Field(
        default_factory=list,
        description="按产物节点切分的工艺流程数组。",
    )
    why: str | None = Field(
        default=None,
        description="可选顶层依据说明。正式落盘时可由后处理移除。",
    )

    @field_validator("why", mode="before")
    @classmethod
    def _normalize_why(cls, value):
        return _normalize_text(value)


def to_json_schema() -> dict:
    return ProcessResult.model_json_schema()


ProcessValue.model_rebuild()
ProcessMaterial.model_rebuild()
ReactionCondition.model_rebuild()
LocationIndex.model_rebuild()
ProcessStep.model_rebuild()
ProcessResult.model_rebuild()
