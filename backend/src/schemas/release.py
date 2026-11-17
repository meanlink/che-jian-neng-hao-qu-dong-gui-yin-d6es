import math
from datetime import date
from pydantic import BaseModel, Field, field_validator
class SealInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    job_id: int
    note: str = Field(default='', max_length=500)
class RatioInput(BaseModel):
    ratio: int = Field(ge=0, le=100)
class PublishInput(BaseModel):
    ratio: int = Field(default=10, ge=1, le=100)
class PredictItem(BaseModel):
    day: str = Field(min_length=4, max_length=10)
    units: float
    run_hours: float
    temp_c: float
    idle_hours: float
    @field_validator('day')
    @classmethod
    def day_must_be_iso(cls, v):
        try:
            date.fromisoformat(v.strip())
        except ValueError:
            raise ValueError('日期须为ISO格式，如 2026-11-20') from None
        return v.strip()
    @field_validator('units', 'run_hours', 'temp_c', 'idle_hours')
    @classmethod
    def must_be_finite(cls, v):
        if not math.isfinite(v):
            raise ValueError('数值不能为NaN或无穷')
        return v
class PredictInput(BaseModel):
    order_no: str = Field(min_length=2, max_length=64)
    items: list[PredictItem] = Field(min_length=1, max_length=500)
    @field_validator('order_no')
    @classmethod
    def order_no_charset(cls, v):
        v = v.strip()
        if not all(ch.isalnum() or ch in '-_/' for ch in v):
            raise ValueError('排产单号仅允许字母、数字及 - _ /')
        return v
