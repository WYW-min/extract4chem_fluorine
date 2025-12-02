from typing import List
from pydantic import BaseModel, Field, model_validator

class ScalarWithUnit(BaseModel):
    """带单位的标量：value（数值）+ unit（字符串）；任一缺失则另一项可为 null。"""
    value: float | None = Field(None, description="数值；未知则 null")
    unit: str | None = Field(None, description='单位文本，保持语义紧凑，如 "%_light_olefins", "g_MeOH/g_catalyst", "h_t50"')

class Regeneration(BaseModel):
    """再生信息：温度 °C 与恢复比例 %。"""
    temp_c: float | None = Field(None, description="再生温度（°C）")
    yield_percent: float | None = Field(None, description="再生后性能恢复比例（0–100）")

    @model_validator(mode="after")
    def _bounds(self):
        if self.temp_c is not None and self.temp_c < 0:
            raise ValueError("temp_c must be >= 0")
        if self.yield_percent is not None and not (0 <= self.yield_percent <= 100):
            raise ValueError("yield_percent must be within [0, 100]")
        return self

class Application(BaseModel):
    """
    应用/性能结果（与特定 material_id 直接相关）。
    - 数值/读数优先来自 Results & Discussion、表格、图注；测试条件可参考 Experimental
    """
    scenario: str | None = Field(
        None,
        description='应用场景："catalysis"|"adsorption_separation"|"ion_exchange" 等'
    )
    target_species: str | None = Field(None, description="反应底物/被分离客体，如 methanol、CO2 等")
    capacity: ScalarWithUnit | None = Field(None, description='转化/吸附能力，如 {"value":157.6,"unit":"g_MeOH/g_catalyst"}')
    selectivity: ScalarWithUnit | None = Field(None, description='轻烯烃选择性，如 {"value":2.52,"unit":"%_light_olefins"}')
    breakthrough: ScalarWithUnit | None = Field(None, description='转化率从 100 % 掉到 50 % 所经历时间(t₅₀)，如 {"value":197,"unit":"h_t50"}')
    regeneration: Regeneration | None = Field(None, description="再生温度与性能恢复比例")

class ApplicationResult(BaseModel):
    """
    单个样品的应用抽取结果。
    """
    
    application: Application = Field(default_factory=Application, description="应用对象")
    why: str | None = Field(
        default=None,
        description=(
            "说明 提取到或无法抽取各信息的直接论据"
        )
    )

