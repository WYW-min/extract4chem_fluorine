from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class CharacterizationMethodBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    仪器: str | None = Field(
        default=None,
        description="与该表征方法直接相关的仪器名称或型号。",
    )
    说明: str | None = Field(
        default=None,
        description="该表征方法无法稳定拆分到结构化字段时的结果说明。",
    )

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_scalars(cls, value):
        if isinstance(value, str):
            return _normalize_text(value)
        return value


class FTIRCharacterization(CharacterizationMethodBase):
    峰位_cm_1: List[str] = Field(
        default_factory=list,
        description="FTIR 特征峰位列表，建议保留峰位及峰归属，如 1776 (C=O)。",
    )
    特征峰位: List[str] = Field(
        default_factory=list,
        description="与 峰位_cm_1 同义的兼容字段。",
    )

    @field_validator("峰位_cm_1", "特征峰位", mode="before")
    @classmethod
    def _normalize_peaks(cls, value):
        return _normalize_text_list(value)


class UVVisCharacterization(CharacterizationMethodBase):
    吸收峰_nm: List[str] = Field(
        default_factory=list,
        description="UV-Vis 吸收峰或特征波长，建议保留单位或峰归属。",
    )
    λmax_nm: List[str] = Field(
        default_factory=list,
        description="最大吸收波长列表。兼容单值或多值。",
    )

    @field_validator("吸收峰_nm", "λmax_nm", mode="before")
    @classmethod
    def _normalize_uv_peaks(cls, value):
        return _normalize_text_list(value)


class GPCSECCharacterization(CharacterizationMethodBase):
    流动相: str | None = Field(default=None, description="GPC/SEC 流动相。")
    温度: str | None = Field(default=None, description="测试温度，保留原文最小表达。")
    校准: str | None = Field(default=None, description="校准标准或校准方式。")
    Mn_kDa: float | int | str | None = Field(default=None, description="数均分子量。")
    Mw_kDa: float | int | str | None = Field(default=None, description="重均分子量。")
    PDI: float | int | str | None = Field(default=None, description="分散系数。")


class NMRCharacterization(CharacterizationMethodBase):
    溶剂: str | None = Field(default=None, description="NMR 溶剂。")
    频率_MHz: float | int | str | None = Field(default=None, description="NMR 频率。")
    H1_NMR: str | None = Field(default=None, description="1H NMR 结果摘要。")
    C13_NMR: str | None = Field(default=None, description="13C NMR 结果摘要。")


class XRDWAXSCharacterization(CharacterizationMethodBase):
    峰位_2theta: List[str] = Field(
        default_factory=list,
        description="XRD/WAXS 特征峰位，建议保留 2theta 表达及峰说明。",
    )

    @field_validator("峰位_2theta", mode="before")
    @classmethod
    def _normalize_xrd_peaks(cls, value):
        return _normalize_text_list(value)


class MassSpecCharacterization(CharacterizationMethodBase):
    模式: str | None = Field(default=None, description="质谱模式，如 MS+, MS-, ESI 等。")
    特征峰_m_z: List[str] = Field(
        default_factory=list,
        description="LC-MS 或质谱特征峰，建议保留 m/z 及峰说明。",
    )

    @field_validator("特征峰_m_z", mode="before")
    @classmethod
    def _normalize_mass_peaks(cls, value):
        return _normalize_text_list(value)


class RamanCharacterization(CharacterizationMethodBase):
    峰位_cm_1: List[str] = Field(
        default_factory=list,
        description="Raman 特征峰位列表，建议保留峰位及峰归属。",
    )

    @field_validator("峰位_cm_1", mode="before")
    @classmethod
    def _normalize_raman_peaks(cls, value):
        return _normalize_text_list(value)


class XPSCharacterization(CharacterizationMethodBase):
    峰位_eV: List[str] = Field(
        default_factory=list,
        description="XPS 特征峰位列表，建议保留 eV 和峰归属。",
    )
    元素与价态: List[str] = Field(
        default_factory=list,
        description="XPS 解析得到的元素、化学态或价态信息。",
    )

    @field_validator("峰位_eV", "元素与价态", mode="before")
    @classmethod
    def _normalize_xps_items(cls, value):
        return _normalize_text_list(value)


class MorphologyCharacterization(CharacterizationMethodBase):
    SEM: str | None = Field(default=None, description="SEM 形貌描述。")
    TEM: str | None = Field(default=None, description="TEM 形貌描述。")
    AFM: str | None = Field(default=None, description="AFM 形貌描述。")
    显微: str | None = Field(default=None, description="其他显微或形貌描述。")


class BETCharacterization(CharacterizationMethodBase):
    比表面积_m2_g: float | int | str | None = Field(
        default=None,
        description="BET 比表面积。",
    )
    孔径_nm: float | int | str | None = Field(
        default=None,
        description="平均孔径或代表性孔径。",
    )
    孔容_cm3_g: float | int | str | None = Field(
        default=None,
        description="总孔容。",
    )


class ContactAngleCharacterization(CharacterizationMethodBase):
    接触角_deg: List[str] = Field(
        default_factory=list,
        description="接触角结果，建议保留数值和液滴类型。",
    )

    @field_validator("接触角_deg", mode="before")
    @classmethod
    def _normalize_contact_angles(cls, value):
        return _normalize_text_list(value)


class ElementalAnalysisCharacterization(CharacterizationMethodBase):
    元素组成: List[str] = Field(
        default_factory=list,
        description="元素分析、EDS/EDX、ICP 等得到的元素组成或比例信息。",
    )

    @field_validator("元素组成", mode="before")
    @classmethod
    def _normalize_elemental_items(cls, value):
        return _normalize_text_list(value)


class CharacterizationObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    红外_FTIR: FTIRCharacterization | None = Field(
        default=None,
        description="红外表征对象。",
    )
    紫外_UVVis: UVVisCharacterization | None = Field(
        default=None,
        description="紫外/可见吸收表征对象。",
    )
    分子量_GPC_SEC: GPCSECCharacterization | None = Field(
        default=None,
        description="GPC/SEC 分子量表征对象。",
    )
    核磁_NMR: NMRCharacterization | None = Field(
        default=None,
        description="核磁表征对象。",
    )
    XRD_WAXS: XRDWAXSCharacterization | None = Field(
        default=None,
        description="XRD/WAXS 表征对象。",
    )
    质谱_LCMS: MassSpecCharacterization | None = Field(
        default=None,
        description="LC-MS 或其他质谱表征对象。",
    )
    拉曼_Raman: RamanCharacterization | None = Field(
        default=None,
        description="拉曼表征对象。",
    )
    XPS: XPSCharacterization | None = Field(
        default=None,
        description="XPS 表征对象。",
    )
    形貌: MorphologyCharacterization | None = Field(
        default=None,
        description="形貌表征对象。",
    )
    BET比表面积: BETCharacterization | None = Field(
        default=None,
        description="BET 比表面积与孔结构表征对象。",
    )
    接触角: ContactAngleCharacterization | None = Field(
        default=None,
        description="接触角表征对象。",
    )
    元素分析: ElementalAnalysisCharacterization | None = Field(
        default=None,
        description="元素分析、EDS/EDX、ICP 等表征对象。",
    )


class CharacterizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    表征: CharacterizationObject = Field(
        default_factory=CharacterizationObject,
        description="目标聚合物的表征结果。按方法名组织为 object，而不是数组。",
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
    return CharacterizationResult.model_json_schema()


CharacterizationMethodBase.model_rebuild()
FTIRCharacterization.model_rebuild()
UVVisCharacterization.model_rebuild()
GPCSECCharacterization.model_rebuild()
NMRCharacterization.model_rebuild()
XRDWAXSCharacterization.model_rebuild()
MassSpecCharacterization.model_rebuild()
RamanCharacterization.model_rebuild()
XPSCharacterization.model_rebuild()
MorphologyCharacterization.model_rebuild()
BETCharacterization.model_rebuild()
ContactAngleCharacterization.model_rebuild()
ElementalAnalysisCharacterization.model_rebuild()
CharacterizationObject.model_rebuild()
CharacterizationResult.model_rebuild()
