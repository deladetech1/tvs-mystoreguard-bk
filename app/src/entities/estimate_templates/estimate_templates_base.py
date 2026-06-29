import ast
from typing import Optional, List, Any
from typing_extensions import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# =====================================================
# ENUMS AND LITERALS
# =====================================================

DeleteStatusType = Literal['PENDING', 'DELETED', 'NOT_DELETED']

# The kind of input an estimator captures for a field on site.
FieldDataType = Literal['number', 'dimension', 'select', 'boolean', 'text']

# What a computed value represents:
#   money    -> adds to the line price (and the estimate's money total)
#   quantity -> rolled up into its own total by key (e.g. total yards), never money
#   display  -> just shown on the line, not totalled anywhere
ComputationKind = Literal['money', 'quantity', 'display']


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


def _parses(expr: str) -> str:
    """Reject a formula with a syntax error at template-create time."""
    try:
        ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula syntax: {exc.msg}")
    return expr


class Computation(BaseModel):
    """One named, computed value on a line item. Computations run in order and
    each can reference the fields AND any computation defined above it."""
    key: str = Field(..., min_length=1, max_length=100, description="Variable name, e.g. 'yards', 'material_cost'. Reusable by later computations.")
    label: str = Field(..., min_length=1, max_length=255, description="Label shown on the estimate, e.g. 'Material cost'")
    formula: str = Field(..., min_length=1, description="Expression over field keys + earlier computation keys. Supports + - * /, ifelse, comparisons, and/or/not.")
    unit: Optional[str] = Field(None, max_length=50, description="Unit shown next to the value, e.g. 'yd', 'GHS'")
    kind: ComputationKind = Field(default='money', description="money (adds to price) | quantity (own rolled-up total) | display (shown only)")

    @field_validator("key")
    @classmethod
    def _key_is_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"Computation key '{v}' must be a valid identifier (letters, digits, underscore; no leading digit)")
        return v

    @field_validator("formula")
    @classmethod
    def _formula_is_safe(cls, v: str) -> str:
        return _parses(v)


class LineItemDef(BaseModel):
    """A kind of thing that can be added to an estimate (a 'Window', a 'Door',
    'Labour'). Holds the fields to capture and the computations that price it.

    Provide EITHER a single `formula` (simple: becomes one money computation) OR a
    list of `computations` (advanced: multiple named, chained values)."""
    key: str = Field(..., min_length=1, max_length=100, description="Unique key within the template, e.g. 'window'")
    name: str = Field(..., min_length=1, max_length=255, description="Display name, e.g. 'Window'")
    description: Optional[str] = Field(None, max_length=1000)
    unit: Optional[str] = Field(None, max_length=50, description="Output unit label, e.g. 'window', 'sqm'")
    fields: List[FieldDef] = Field(default_factory=list, description="Inputs captured for this line item")
    formula: Optional[str] = Field(None, description="Shortcut: a single money formula (auto-wrapped into one computation)")
    computations: List[Computation] = Field(default_factory=list, description="Named, ordered computed values (yards, material cost, ...)")

    @field_validator("formula")
    @classmethod
    def _formula_is_safe(cls, v: Optional[str]) -> Optional[str]:
        return _parses(v) if v else v

    @field_validator("fields")
    @classmethod
    def _unique_field_keys(cls, v: List[FieldDef]) -> List[FieldDef]:
        keys = [f.key for f in v]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            raise ValueError(f"Duplicate field keys in line item: {', '.join(sorted(dupes))}")
        return v

    @model_validator(mode="after")
    def _normalise_computations(self):
        # Allow the simple `formula` shortcut: wrap it as one money computation.
        if not self.computations:
            if self.formula:
                self.computations = [Computation(key="amount", label="Amount", formula=self.formula, kind="money")]
            else:
                raise ValueError(f"Line item '{self.key}' needs either a formula or at least one computation")

        comp_keys = [c.key for c in self.computations]
        dupes = {k for k in comp_keys if comp_keys.count(k) > 1}
        if dupes:
            raise ValueError(f"Duplicate computation keys in line item '{self.key}': {', '.join(sorted(dupes))}")

        # A computation key must not collide with a field key (would be ambiguous).
        field_keys = {f.key for f in self.fields}
        clash = field_keys.intersection(comp_keys)
        if clash:
            raise ValueError(f"Computation key(s) clash with field key(s) in '{self.key}': {', '.join(sorted(clash))}")

        # At least one money computation, so the line has a price.
        if not any(c.kind == "money" for c in self.computations):
            raise ValueError(f"Line item '{self.key}' needs at least one 'money' computation to have a price")
        return self


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
