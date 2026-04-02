from __future__ import annotations

import re
from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator


class PolymerMainInfo(BaseModel):
    名称: str = Field(
        ...,
        min_length=1,
        description="聚合物对象的主名称。优先使用文中最明确、最适合作为样本主名的写法。",
    )
    别名: List[str] = Field(
        default_factory=list,
        description="同一聚合物对象在文本中的其他明确写法。去重，不得与“名称”重复。",
    )
    聚合物分类名称: str | None = Field(
        default=None,
        description="对象的规范类别名称，如 Polyimide、Polyamic Acid、Polyamic Acid Ammonium Salt、PI/CNC Composite Aerogel。",
    )
    聚合物分类编码: str | None = Field(
        default=None,
        description="对象的简短类别编码，如 PI、PAA、PAAS、PI/CNC、CNC。",
    )
    样本形态: str | None = Field(
        default=None,
        description="对象的物理或制样形态，如 film、membrane、aerogel、fiber、powder、ink、gel、solution、precursor。",
    )
    结构特征_L1: str | None = Field(
        default=None,
        description=(
            "一级结构特征标签。当前阶段为单值字符串；文本无法稳定支持时为 null。"
        ),
    )
    结构特征_L2: str | None = Field(
        default=None,
        description=(
            "二级结构特征标签。当前阶段为单值字符串；文本无法稳定支持时为 null。"
        ),
    )

    @field_validator("别名", mode="before")
    @classmethod
    def _dedup_aliases(cls, value):
        if not value:
            return []
        uniq = []
        seen = set()
        for item in value:
            text = (item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(text)
        return uniq

    @field_validator("结构特征_L1", "结构特征_L2", mode="before")
    @classmethod
    def _normalize_feature_tag(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @model_validator(mode="after")
    def _remove_name_from_aliases(self):
        name_key = self.名称.strip().lower()
        self.别名 = [alias for alias in self.别名 if alias.strip().lower() != name_key]
        return self


class LiteratureInfo(BaseModel):
    唯一文献标识: str | None = Field(
        default=None,
        description="文献唯一标识。优先为 DOI；若文本中无明确 DOI，则为 null。",
    )
    论文标题: str | None = Field(
        default=None,
        description="文献正式标题。优先使用标题页中的标题。",
    )
    作者列表: List[str] = Field(
        default_factory=list,
        description="按出现顺序抽取的作者姓名列表。",
    )
    期刊名称: str | None = Field(
        default=None,
        description="文献所属期刊名称。",
    )
    年份: int | str | None = Field(
        default=None,
        description="文献年份。若只能稳定抽取字符串形式，也允许字符串。",
    )
    卷号: int | str | None = Field(
        default=None,
        description="卷号。允许整数或字符串。",
    )
    页码: str | None = Field(
        default=None,
        description="页码、文章号或电子定位码。",
    )
    文档类型: str | None = Field(
        default=None,
        description="文本明确给出的文档类型，如 Article、Review、Patent、研究论文、综述。",
    )
    语言: str | None = Field(
        default=None,
        description="文献语言，如 English、中文。无法稳定判断则为 null。",
    )
    关键词: List[str] = Field(
        default_factory=list,
        description="从 Keywords / 关键词 行提取的关键词列表。即使原文为单个分号分隔字符串，也应拆分为数组。",
    )

    @field_validator("作者列表", "关键词", mode="before")
    @classmethod
    def _dedup_text_list(cls, value):
        if not value:
            return []
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if ";" in text or "；" in text:
                value = re.split(r"[;；]", text)
            else:
                value = [text]
        uniq = []
        seen = set()
        for item in value:
            text = (item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(text)
        return uniq


class MainSignalResult(BaseModel):
    文献信息: LiteratureInfo = Field(
        ...,
        description="文献级基础信息。",
    )
    聚合物: List[PolymerMainInfo] = Field(
        default_factory=list,
        description=(
            "独立聚合物对象列表。注意：同一篇文献中，即使“名称”完全相同，只要形态、配比、工艺阶段不同，"
            "仍应视为不同对象，不应在模型层按名称强行去重。"
        ),
    )
    why: str = Field(
        ...,
        min_length=1,
        description="总结本次文献信息与聚合物对象识别的依据。当前阶段仅保留顶层 why。",
    )

    @model_validator(mode="after")
    def _drop_exact_duplicate_polymers(self):
        uniq = []
        seen = set()
        for polymer in self.聚合物:
            key = (
                polymer.名称.strip().lower(),
                (polymer.聚合物分类编码 or "").strip().lower(),
                (polymer.样本形态 or "").strip().lower(),
                (polymer.结构特征_L1 or "").strip().lower(),
                (polymer.结构特征_L2 or "").strip().lower(),
            )
            if key not in seen:
                seen.add(key)
                uniq.append(polymer)
        self.聚合物 = uniq
        return self


def to_json_schema() -> dict:
    return MainSignalResult.model_json_schema()
