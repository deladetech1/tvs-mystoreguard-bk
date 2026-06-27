"""
Safe arithmetic formula evaluator for the estimator.

Estimate templates carry a free-text `formula` per line-item, e.g.
    "height * width * fabric_rate + labor"
This module evaluates such a formula against a context of field values WITHOUT
ever using Python's built-in eval()/exec(). It parses the expression into an AST
and walks a strict whitelist of node types, operators and helper functions, so a
malicious or malformed template can never execute arbitrary code.

Allowed:
  - numeric literals
  - variable names (resolved from the supplied context dict)
  - + - * / // % ** and unary +/-
  - parentheses
  - helper functions: min, max, round, abs, ceil, floor, sqrt, area, perimeter

Anything else (attribute access, comprehensions, lambdas, names not in context,
unknown functions) raises FormulaError.
"""
import ast
import math
import operator
from typing import Any, Dict


class FormulaError(ValueError):
    """Raised when a formula is invalid or cannot be evaluated safely."""
    pass


# Binary operators we allow, mapped to their implementation.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _area(*dims: float) -> float:
    """Multiply all dimensions together (height * width [* depth ...])."""
    result = 1.0
    for d in dims:
        result *= float(d)
    return result


def _perimeter(height: float, width: float) -> float:
    """Perimeter of a rectangle: 2 * (height + width)."""
    return 2.0 * (float(height) + float(width))


# Whitelisted helper functions usable inside a formula.
_FUNCTIONS = {
    "min": min,
    "max": max,
    "round": round,
    "abs": abs,
    "ceil": lambda x: math.ceil(float(x)),
    "floor": lambda x: math.floor(float(x)),
    "sqrt": lambda x: math.sqrt(float(x)),
    "area": _area,
    "perimeter": _perimeter,
}


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def visit(self, node):  # noqa: D401 - dispatch
        method = "visit_" + type(node).__name__
        visitor = getattr(self, method, None)
        if visitor is None:
            raise FormulaError(
                f"Unsupported expression element: {type(node).__name__}"
            )
        return visitor(node)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            return 1.0 if node.value else 0.0
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError("Only numeric literals are allowed in formulas")

    def visit_Name(self, node):
        if node.id in self.context:
            value = self.context[node.id]
            try:
                return float(value)
            except (TypeError, ValueError):
                raise FormulaError(f"Field '{node.id}' is not numeric")
        raise FormulaError(f"Unknown field or variable: '{node.id}'")

    def visit_BinOp(self, node):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise FormulaError(f"Operator not allowed: {type(node.op).__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            return op(left, right)
        except ZeroDivisionError:
            raise FormulaError("Division by zero in formula")

    def visit_UnaryOp(self, node):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise FormulaError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op(self.visit(node.operand))

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise FormulaError("Only direct function calls are allowed")
        func = _FUNCTIONS.get(node.func.id)
        if func is None:
            raise FormulaError(f"Unknown function: '{node.func.id}'")
        if node.keywords:
            raise FormulaError("Keyword arguments are not allowed in formulas")
        args = [self.visit(arg) for arg in node.args]
        return float(func(*args))


def evaluate_formula(formula: str, context: Dict[str, Any]) -> float:
    """Safely evaluate `formula` against `context` and return a float.

    Raises FormulaError on any invalid/unsafe expression so callers can return a
    clean validation error instead of a 500.
    """
    if formula is None or str(formula).strip() == "":
        raise FormulaError("Formula is empty")
    try:
        tree = ast.parse(str(formula), mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Invalid formula syntax: {exc.msg}")
    result = _SafeEvaluator(context).visit(tree)
    return float(result)


def build_context(field_values: Dict[str, Any], field_defs: list) -> Dict[str, Any]:
    """Turn a line-item's raw field_values into a formula context.

    For each field definition we expose variables the formula can reference:
      - number / dimension  -> the numeric value under its key
      - boolean             -> 1.0 / 0.0 under its key
      - select              -> the chosen value under its key, AND the chosen
                               option's `rate` under `<key>_rate` (0 if none)
      - text                -> ignored (not numeric)

    Missing values fall back to the field's `default` (or 0 for numerics).
    """
    context: Dict[str, Any] = {}
    defs_by_key = {d.get("key"): d for d in (field_defs or []) if d.get("key")}

    for key, fdef in defs_by_key.items():
        data_type = fdef.get("data_type")
        raw = field_values.get(key, fdef.get("default"))

        if data_type in ("number", "dimension"):
            context[key] = float(raw) if raw not in (None, "") else 0.0
        elif data_type == "boolean":
            context[key] = 1.0 if raw in (True, 1, "true", "True", "1") else 0.0
        elif data_type == "select":
            context[key] = raw
            # Resolve the rate carried by the chosen option, if any.
            rate = 0.0
            for opt in fdef.get("options") or []:
                if str(opt.get("value")) == str(raw):
                    try:
                        rate = float(opt.get("rate") or 0.0)
                    except (TypeError, ValueError):
                        rate = 0.0
                    break
            context[f"{key}_rate"] = rate
        # text fields are intentionally not added to the numeric context

    # Also expose any extra numeric values the caller passed that weren't defined
    # as fields (e.g. an ad-hoc `quantity`), so simple formulas still work.
    for key, value in (field_values or {}).items():
        if key not in context:
            try:
                context[key] = float(value)
            except (TypeError, ValueError):
                pass

    return context
