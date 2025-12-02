
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class MaterialID(BaseModel):
    id: str = Field(..., min_length=1, description="材料/样品命名（可含字母、数字、符号），保留论文原样")
    aliases: List[str] = Field(default_factory=list, description="同义/简称，不允许重复，不允许和id相同")
    framework_code: str | None = Field(default=None, description="IZA 的三字母骨架代码")
    why:str = Field(description="取值理由说明，≤120字")
    
    @field_validator("aliases", mode="before")
    @classmethod
    def _dedup_aliases(cls, v):
        if not v:
            return []
        uniq, seen = [], set()
        for s in v:
            k = (s or "").strip()
            if not k:
                continue
            key = k.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(k)
        return uniq



class Er4MaterialId(BaseModel):
    material_ids: List[MaterialID] = Field(default_factory=list)
    paper_frameworks:List[str] = Field(default_factory=list,description="论文级出现但无法绑定到具体样品的IZA 三字母骨架代码列表")
    why: str = Field(description="取值理由说明，≤300字")
    @model_validator(mode="after")
    def _dedup_ids(self):
        seen, uniq = set(), []
        for m in self.material_ids:
            key = m.id.strip().lower()
            if key not in seen:
                seen.add(key)
                uniq.append(m)
        self.material_ids = uniq
        return self
    
