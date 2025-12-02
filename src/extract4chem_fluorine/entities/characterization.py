from typing import List
from pydantic import BaseModel, Field, model_validator

# ---------- Characterization ----------

class CrystalSize(BaseModel):
    """晶体尺寸（nm）。可为空；取值>=0。"""
    a_axis_nm: float | None = Field(None, description="a 轴尺寸（nm）")
    b_axis_nm: float | None = Field(None, description="b 轴尺寸（nm）")
    c_axis_nm: float | None = Field(None, description="c 轴尺寸（nm）")
    average_nm: float | None = Field(None, description="平均晶体尺寸（nm）")

    @model_validator(mode="after")
    def _nonneg(self):
        for k in ["a_axis_nm","b_axis_nm","c_axis_nm","average_nm"]:
            v = getattr(self, k)
            if v is not None and v < 0:
                raise ValueError(f"{k} must be >= 0")
        return self

class Porosity(BaseModel):
    """孔结构参数。单位固定：BET→m2/g；孔容积→cm3/g；取值>=0。"""
    bet_m2_g: float | None = Field(None, description="比表面积（m2/g）")
    v_total_cm3_g: float | None = Field(None, description="总孔容积（cm3/g）")
    v_micro_cm3_g: float | None = Field(None, description="微孔容积（cm3/g）")
    v_meso_cm3_g: float | None = Field(None, description="介孔容积（cm3/g）")

    @model_validator(mode="after")
    def _nonneg(self):
        for k in ["bet_m2_g","v_total_cm3_g","v_micro_cm3_g","v_meso_cm3_g"]:
            v = getattr(self, k)
            if v is not None and v < 0:
                raise ValueError(f"{k} must be >= 0")
        return self

class Acidity(BaseModel):
    """酸性参数。单位：mmol/g；l_b_ratio=Lewis/Brønsted。"""
    bronsted_acid_amount_mmol_g: float | None = Field(None, description="Brønsted 酸含量（mmol/g）")
    lewis_acid_amount_mmol_g: float | None = Field(None, description="Lewis 酸含量（mmol/g）")
    l_b_ratio: float | None = Field(None, description="Lewis/Brønsted 比值（>=0）")

    @model_validator(mode="after")
    def _check(self):
        if self.l_b_ratio is not None and self.l_b_ratio < 0:
            raise ValueError("l_b_ratio must be >= 0")
        return self

class Characterization(BaseModel):
    """
    物化性质结果（与特定 material_id 直接相关的“数值/定性结果”）。
    - 优先来自 Results & Discussion、表格、图注；方法性描述若无数值则置 null
    """
    morphology: str | None = Field(None, description='形貌：如 "sheet"|"flower-like"|"spherical"|"cubic" 等')
    crystal_size: CrystalSize | None = Field(None, description="晶体尺寸（nm）")
    si_al_ratio_actual: float | None = Field(None, description="实际硅铝比（>0）")
    porosity: Porosity | None = Field(None, description="孔结构参数")
    acidity: Acidity | None = Field(None, description="酸性参数")

    @model_validator(mode="after")
    def _positive(self):
        if self.si_al_ratio_actual is not None and self.si_al_ratio_actual <= 0:
            raise ValueError("si_al_ratio_actual must be > 0")
        return self

class CharacterizationResult(BaseModel):
    """
    单个样品（material_id）的物化性质抽取结果。
    """
    characterization: Characterization = Field(default_factory=Characterization, description="物化性质对象")
    why: str | None = Field(
        default=None,
        description=(
            "说明 提取到或无法抽取各信息的直接论据"
        )
    )
