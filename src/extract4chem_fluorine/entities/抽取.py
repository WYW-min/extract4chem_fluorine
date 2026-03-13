from __future__ import annotations

try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:  # pragma: no cover
    from pydantic import BaseModel, Field  # type: ignore

    ConfigDict = None  # type: ignore


class BaseSchema(BaseModel):
    """抽取结果的基础模型，统一禁止未声明的额外字段。"""

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(extra="forbid", populate_by_name=True)
    else:  # pragma: no cover
        class Config:
            extra = "forbid"
            allow_population_by_field_name = True


class Crystallization(BaseSchema):
    temp_c: float | None = Field(None, description="晶化温度（℃）")
    time_d: float | None = Field(None, description="晶化时间（天）")
    agitation_rpm: float | None = Field(None, description="搅拌速度（rpm）")


class Synthesis(BaseSchema):
    zeolite_type: str | None = Field(None, description="分子筛结构代码")
    gel_composition: str | None = Field(
        None,
        description="合成凝胶配方；优先摩尔比，若仅有原料用量则记录“原料: 数值单位”",
    )
    template: str | None = Field(None, description="结构导向剂")
    silica_source: str | None = Field(None, description="硅源名称")
    aluminium_source: str | None = Field(None, description="铝源名称")
    crystallization: Crystallization | None = Field(None, description="晶化条件")
    post_treatment_steps: list[str] | None = Field(
        None, description="后处理步骤，按原文顺序排列"
    )


class CrystalSize(BaseSchema):
    a_axis_nm: float | None = Field(None, description="晶体 a 轴尺寸（nm）")
    b_axis_nm: float | None = Field(None, description="晶体 b 轴尺寸（nm）")
    c_axis_nm: float | None = Field(None, description="晶体 c 轴尺寸（nm）")
    average_nm: float | None = Field(None, description="平均晶粒尺寸（nm）")


class Porosity(BaseSchema):
    bet_m2_g: float | None = Field(None, description="BET 比表面积（m²/g）")
    v_total_cm3_g: float | None = Field(None, description="总孔容（cm³/g）")
    v_micro_cm3_g: float | None = Field(None, description="微孔容积（cm³/g）")
    v_meso_cm3_g: float | None = Field(None, description="介孔容积（cm³/g）")


class Acidity(BaseSchema):
    bronsted_acid_amount_mmol_g: float | None = Field(
        None, description="Brønsted 酸含量（mmol/g）"
    )
    lewis_acid_amount_mmol_g: float | None = Field(
        None, description="Lewis 酸含量（mmol/g）"
    )
    b_l_ratio: float | None = Field(None, description="Brønsted/Lewis 酸含量比值")


class Characterization(BaseSchema):
    morphology: str | None = Field(None, description="颗粒形貌关键词")
    crystal_size: CrystalSize | None = Field(None, description="晶粒尺寸信息（nm）")
    si_al_ratio_actual: float | None = Field(None, description="样品的实际硅铝比")
    porosity: Porosity | None = Field(None, description="孔结构数据")
    acidity: Acidity | None = Field(None, description="酸性表征结果")


class Measurement(BaseSchema):
    value: float | None = Field(None, description="测量数值")
    unit: str | None = Field(None, description="测量数值的单位")


class Regeneration(BaseSchema):
    temp_c: float | None = Field(None, description="再生温度（℃）")
    yield_percent: float | None = Field(None, description="再生后性能恢复比例（%）")


class Application(BaseSchema):
    scenario: str | None = Field(None, description="应用场景")
    target_species: str | None = Field(None, description="反应底物或目标物种")
    capacity: Measurement | None = Field(None, description="产能或容量数据")
    selectivity: Measurement | None = Field(None, description="选择性指标")
    breakthrough: Measurement | None = Field(None, description="穿透或稳定性指标")
    regeneration: Regeneration | None = Field(None, description="再生性能")


class ExtractionResult(BaseSchema):
    material_id: str | None = Field(None, description="文献中给出的材料名称")
    doi: str | None = Field(None, description="文献的 DOI")
    synthesis: Synthesis | None = Field(None, description="合成相关信息")
    characterization: Characterization | None = Field(None, description="物化表征数据")
    application: Application | None = Field(None, description="应用表现指标")
    extraction_notes: list[str] | None = Field(
        None,
        alias="_extraction_notes",
        description="抽取过程中的补充说明或存在歧义之处",
    )


class ExtractionResults(BaseSchema):
    doi: str | None = Field(None, description="文献的 DOI")
    results: list[ExtractionResult] | None = Field(None, description="抽取结果列表")
