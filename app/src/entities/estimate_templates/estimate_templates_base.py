import ast
from typing import Optional, List, Any
from typing_extensions import Literal
from pydantic import BaseModel, Field, field_validator


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']

# The kind of input an estimator captures for a field on site.
FieldDataType = Literal['number', 'dimension', 'select', 'boolean', 'text']


# =====================================================
# TEMPLATE DEFINITION MODELS (stored as JSONB on the template)
# =====================================================

class FieldOption(BaseModel):
    """One choice for a `select` field. `rate` is the numeric value exposed to the
    formula as `<field_key>_rate` when this option is chosen (e.g. fabric price)."""
    label: str = Field(..., min_length=1, max_length=255, description="Human label, e.g. 'Velvet'")
    value: str = Field(..., min_length=1, max_length=255, description="Stored value, e.g. 'velvet'")
    rate: Optional[float] = Field(None, description="Numeric rate exposed to the formula as <key>_rate")


class FieldDef(BaseModel):
    """A single input the estimator fills in for a line item."""
    key: str = Field(..., min_length=1, max_length=100, description="Formula variable name, e.g. 'height'. Use snake_case.")
    label: str = Field(..., min_length=1, max_length=255, description="Label shown in the UI, e.g. 'Window height'")
    data_type: FieldDataType = Field(..., description="number | dimension | select | boolean | text")
    unit: Optional[str] = Field(None, max_length=50, description="Unit hint for the UI, e.g. 'm', 'cm', 'hr'")
    required: bool = Field(default=False, description="Whether the estimator must supply a value")
    default: Optional[Any] = Field(None, description="Default value if none supplied")
    options: Optional[List[FieldOption]] = Field(None, description="Choices for a `select` field")

    @field_validator("key")
    @classmethod
    def _key_is_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"Field key '{v}' must be a valid identifier (letters, digits, underscore; no leading digit)")
        return v


class LineItemDef(BaseModel):
    """A kind of thing that can be added to an estimate (a 'Window', a 'Door',
    'Labour'). Holds the fields to capture and the formula that prices one unit."""
    key: str = Field(..., min_length=1, max_length=100, description="Unique key within the template, e.g. 'window'")
    name: str = Field(..., min_length=1, max_length=255, description="Display name, e.g. 'Window'")
    description: Optional[str] = Field(None, max_length=1000)
    unit: Optional[str] = Field(None, max_length=50, description="Output unit label, e.g. 'window', 'sqm'")
    fields: List[FieldDef] = Field(default_factory=list, description="Inputs captured for this line item")
    formula: str = Field(..., min_length=1, description="Arithmetic over field keys, e.g. 'height * width * fabric_rate + labor'")

    @field_validator("formula")
    @classmethod
    def _formula_is_safe(cls, v: str) -> str:
        # Validate the formula parses against a permissive numeric context so a
        # broken template is rejected at creation time, not when an estimate runs.
        try:
            # Parse only to catch syntax errors at creation time; unknown-name
            # errors are acceptable here (fields are validated separately).
            ast.parse(v, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Invalid formula syntax: {exc.msg}")
        return v

    @field_validator("fields")
    @classmethod
    def _unique_field_keys(cls, v: List[FieldDef]) -> List[FieldDef]:
        keys = [f.key for f in v]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            raise ValueError(f"Duplicate field keys in line item: {', '.join(sorted(dupes))}")
        return v


class TemplateModifiers(BaseModel):
    """Template-level adjustments applied to the estimate totals."""
    markup_percent: float = Field(default=0.0, ge=0, description="Added on top of the line-items subtotal")
    discount_percent: float = Field(default=0.0, ge=0, le=100, description="Discount applied after markup")
    tax_percent: float = Field(default=0.0, ge=0, description="Tax applied to the discounted total")
    min_charge: float = Field(default=0.0, ge=0, description="Floor for the grand total")
    valid_days: int = Field(default=30, ge=0, description="Days an estimate stays valid by default")
    currency: Optional[str] = Field(None, max_length=10, description="Currency code, e.g. 'GHS'")


# =====================================================
# ESTIMATE TEMPLATE BASE DTO
# =====================================================

class EstimateTemplateBase(BaseModel):
    """Base DTO for an estimate template (the per-domain blueprint)."""
    name: str = Field(..., min_length=1, max_length=255, description="Template name, e.g. 'Curtain Job'")
    domain: Optional[str] = Field(None, max_length=100, description="Free-text domain label, e.g. 'Curtains', 'Plumbing'")
    description: Optional[str] = Field(None, max_length=1000, description="What this template estimates")
    line_item_defs: List[LineItemDef] = Field(default_factory=list, description="The kinds of line items and their pricing")
    modifiers: TemplateModifiers = Field(default_factory=TemplateModifiers, description="Template-level totals adjustments")

    @field_validator("line_item_defs")
    @classmethod
    def _unique_line_keys(cls, v: List[LineItemDef]) -> List[LineItemDef]:
        keys = [li.key for li in v]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            raise ValueError(f"Duplicate line item keys: {', '.join(sorted(dupes))}")
        return v
