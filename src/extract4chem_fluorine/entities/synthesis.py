from typing import List, Optional
import re
from pydantic import BaseModel, Field, model_validator, field_validator


# ------------------------------
# 模型定义（含详细字段解释）
# ------------------------------

class Crystallization(BaseModel):
    """
    晶化条件：沸石晶体生长阶段的核心参数。
    - 温度单位固定为 °C（数值）
    - 时间单位固定为 day（数值）
    - 搅拌速度单位固定为 rpm（数值）
    """
    temp_c: float | None = Field(
        default=None,
        description=(
            "晶化生长的温度（°C，数值）"
        ),
    )
    time_d: float | None = Field(
        default=None,
        description=(
            "晶化过程持续的总时间（day，数值）"
        ),
    )
    agitation_rpm: float | None = Field(
        default=None,
        description=(
            "晶化搅拌转速（rpm，数值）；若静置/未说明，填 null。"
        ),
    )

    @model_validator(mode="after")
    def _nonneg(self):
        for k in ("temp_c", "time_d", "agitation_rpm"):
            v = getattr(self, k)
            if v is not None and v < 0:
                raise ValueError(f"{k} must be >= 0")
        return self


class Synthesis(BaseModel):
    """
    合成信息（仅限与指定 material_id 直接相关的制备内容；表征/性能不在此处）。
    统一口径：
    - 温度：°C（数值）
    - 时间：结晶用 day；后处理用 hour；不确定则 null
    - 负载：wt%（数值放在 token 文本中亦可）
    """
    zeolite_type: str | None = Field(
        default=None,
        description="样品内部的结构类型(IZA 三大写字母框架代码)"
    )
    gel_composition: str | None = Field(
        default=None,
        description=(
            "合成配方（氧化物/前驱体形式）在反应前的计量比字符串；"
            "示例：\"30Na2O:1Al2O3:100SiO2:10C22-6-6Br2:18H2SO4:4000H2O\" 或 \"100TEOS:1Al2O3\"。"
            "若仅给出原料用量（g/mL 等），用 \"原料: 数值单位\" 列表字符串按顺序记录（如 \"TEOS: 10 g; H2O: 40 mL\"），不做摩尔比换算。"
            "若给出 Si/Al 比且需要换算 SiO2/Al2O3，使用 SiO2/Al2O3 = (Si/Al) * 0.5。未知则为 null。"
        ),
    )
    
    template: str | None = Field(
        default=None,
        description=(
            "模板剂（SDA）短名或化学式，在合成过程中用于引导沸石骨架结构形成的有机分子；示例：\"TPAOH\", \"C22-6-6Br2\"。未知则 null。"
        ),
    )
    silica_source: str | None = Field(
        default=None,
        description=(
            "硅源，合成凝胶中提供硅原子 (Si) 的化合物；示例：\"sodium silicate solution\", \"TEOS\"。未知则 null。"
        ),
    )
    aluminium_source: str | None = Field(
        default=None,
        description=(
            "铝源，合成凝胶中提供铝原子 (Al) 的化合物；示例：\"Al2(SO4)3·18H2O\", \"Al(O-i-Pr)3\"。未知则 null。"
        ),
    )
    crystallization: Crystallization | None = Field(
        default=None,
        description=(
            "晶化条件对象"
        ),
    )
    post_treatment_steps: List[str] = Field(
        default_factory=list,
        description=(
            "晶化后处理步骤的短 token 列表（按出现顺序）。允许形态：\n"
            "  - \"filtered\"（过滤）\n"
            "  - \"washed_<溶剂>\"            例：\"washed_deionized-water\"\n"
            "  - \"dried_<温度>c\" 或加时间    例：\"dried_120c\"、\"dried_120c_2h\"\n"
            "  - \"calcination_<温度>c\" 可加时间/气氛\n"
            "        例：\"calcination_550c_4h_air\"（气氛枚举：air/N2/O2/vacuum/unknown）\n"
            "  - \"ion-exchange_<离子源>_<温度>c(_<次数>times)?\"\n"
            "        例：\"ion-exchange_NH4NO3_80c_3times\"\n"
            "  - \"incipient-wetness-impregnation_<金属>_<负载>\"\n"
            "        例：\"incipient-wetness-impregnation_Zn_2 wt%\"\n"
            
        ),
    )


class SynthesisResult(BaseModel):
    """
    单个样品（material_id）的合成抽取结果。
    """
    material_id: str = Field(
        ...,
        description="目标样品在文献中的命名（原样）。示例：\"Zn/ZSM-5 (10 nm)\"。",
    )
    synthesis: Synthesis = Field(
        default_factory=Synthesis,
        description="与该样品直接相关的合成信息对象。字段定义与约束见 Synthesis。"
    )
    why: str | None = Field(
        default=None,
        description=(
            "说明 提取到或无法抽取各合成信息的直接论据"
        )
    )



# ------------------------------
# 生成“模式提示词/Schema片段”的小工具
# ------------------------------

def to_json_schema() -> dict:
    """
    导出 JSON Schema（供前端/LLM 校验、或写入提示的 <SCHEMA_SNIPPET>）。
    """
    return SynthesisResult.model_json_schema()

def render_prompt_schema() -> str:
    """
    生成“人类可读的输出模式定义”（带注释的伪JSON）。
    可直接粘贴到 System/开发者提示里，指导 LLM 严格输出。
    """
    return (
        '{\n'
        '  "material_id": "<样品原样命名，如 \\"Zn/ZSM-5 (10 nm)\\">",\n'
        '  "synthesis": {\n'
        '    "zeolite_type": "MFI" | null,  // IZA 三字母（仅回填，不得推断）\n'
        '    "gel_composition": "30Na2O:1Al2O3:100SiO2:10C22-6-6Br2:18H2SO4:4000H2O" | "100TEOS:1Al2O3" | "TEOS: 10 g; H2O: 40 mL" | null,\n'
        '    "template": "C22-6-6Br2" | "TPAOH" | null,\n'
        '    "silica_source": "sodium silicate solution" | "TEOS" | null,\n'
        '    "aluminium_source": "Al2(SO4)3·18H2O" | "Al(O-i-Pr)3" | null,\n'
        '    "crystallization": {\n'
        '      "temp_c": 150 | null,     // °C 数值\n'
        '      "time_d": 5 | null,       // day 数值\n'
        '      "agitation_rpm": 60 | null// rpm 数值\n'
        '    },\n'
        '    "post_treatment_steps": [   // 依出现顺序列出短token，允许：\n'
        '      "filtered",\n'
        '      "washed_deionized-water",\n'
        '      "dried_120c" | "dried_120c_2h",\n'
        '      "calcination_550c" | "calcination_550c_4h_air",\n'
        '      "ion-exchange_NH4NO3_80c_3times",\n'
        '      "incipient-wetness-impregnation_Zn_2 wt%"\n'
        '    ]\n'
        '  },\n'
        '  "why_null": null | "<当 synthesis 为空时≥30字原因，否则必须为 null>"\n'
        '}\n'
    )
