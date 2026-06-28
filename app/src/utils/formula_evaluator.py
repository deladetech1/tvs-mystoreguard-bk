"""
Safe expression evaluator for the estimator.

Estimate templates carry free-text formulas (per computation), e.g.
    "height * width * fabric_rate"
    "ifelse(num_windows >= 5, material_cost * 0.9, material_cost)"
This module evaluates such expressions against a context of field/computation
values WITHOUT ever using Python's built-in eval()/exec(). It parses the
expression into an AST and walks a strict whitelist of node types, operators and
helper functions, so a malicious or malformed template can never execute
arbitrary code.

Supported:
  - numeric literals and text literals ('velvet')
  - variable names (resolved from the supplied context dict)
  - arithmetic:   + - * / // % ** and unary +/-
  - comparisons:  > >= < <= == !=   (== / != also work on text; chained allowed)
  - logic:        and  or  not
  - conditional:  ifelse(condition, value_if_true, value_if_false)
                  (and the native `a if cond else b`)
  - functions:    min max round abs ceil floor sqrt area perimeter

Comparisons/logic evaluate to 1.0 (true) or 0.0 (false) so they compose with
arithmetic. Anything outside the whitelist (attribute access, comprehensions,
lambdas, unknown names/functions) raises FormulaError.
"""
import ast
import math
import operator
from typing import Any, Dict, List


class FormulaError(ValueError):
    """Raised when a formula is invalid or cannot be evaluated safely."""
    pass


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
        result *= _num(d)
    return result


def _perimeter(height: float, width: float) -> float:
    """Perimeter of a rectangle: 2 * (height + width)."""
    return 2.0 * (_num(height) + _num(width))


_FUNCTIONS = {
    "min": lambda *a: min(_num(x) for x in a),
    "max": lambda *a: max(_num(x) for x in a),
    "round": lambda x, *r: round(_num(x), int(_num(r[0])) if r else 0),
    "abs": lambda x: abs(_num(x)),
    "ceil": lambda x: float(math.ceil(_num(x))),
    "floor": lambda x: float(math.floor(_num(x))),
    "sqrt": lambda x: math.sqrt(_num(x)),
    "area": _area,
    "perimeter": _perimeter,
}


def _num(v: Any) -> float:
    """Coerce a value to float for arithmetic/ordering, or raise FormulaError."""
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            raise FormulaError(f"Value '{v}' is not a number")
    raise FormulaError("Non-numeric value used in a calculation")


def _is_numeric(v: Any) -> bool:
    try:
        _num(v)
        return True
    except FormulaError:
        return False


def _truthy(v: Any) -> bool:
    """True/false test used by ifelse, and, or, not."""
    if isinstance(v, str):
        return v.strip() != ""
    return _num(v) != 0.0


def _equal(a: Any, b: Any) -> bool:
    """Equality that works for numbers and text. Numeric when both look numeric,
    otherwise compared as text (so fabric == 'velvet' works)."""
    if _is_numeric(a) and _is_numeric(b):
        return _num(a) == _num(b)
    return str(a) == str(b)


class _SafeEvaluator(ast.NodeVisitor):
    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def visit(self, node):
        visitor = getattr(self, "visit_" + type(node).__name__, None)
        if visitor is None:
            raise FormulaError(f"Unsupported expression element: {type(node).__name__}")
        return visitor(node)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        v = node.value
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            return v
        raise FormulaError("Only numbers and text are allowed as literals")

    def visit_Name(self, node):
        if node.id in self.context:
            return self.context[node.id]
        raise FormulaError(f"Unknown field or value: '{node.id}'")

    def visit_BinOp(self, node):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise FormulaError(f"Operator not allowed: {type(node.op).__name__}")
        try:
            return op(_num(self.visit(node.left)), _num(self.visit(node.right)))
        except ZeroDivisionError:
            raise FormulaError("Division by zero in formula")

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            return 0.0 if _truthy(self.visit(node.operand)) else 1.0
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise FormulaError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op(_num(self.visit(node.operand)))

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            return 1.0 if all(_truthy(self.visit(v)) for v in node.values) else 0.0
        if isinstance(node.op, ast.Or):
            return 1.0 if any(_truthy(self.visit(v)) for v in node.values) else 0.0
        raise FormulaError("Boolean operator not allowed")

    def visit_Compare(self, node):
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if isinstance(op, ast.Eq):
                ok = _equal(left, right)
            elif isinstance(op, ast.NotEq):
                ok = not _equal(left, right)
            elif isinstance(op, ast.Lt):
                ok = _num(left) < _num(right)
            elif isinstance(op, ast.LtE):
                ok = _num(left) <= _num(right)
            elif isinstance(op, ast.Gt):
                ok = _num(left) > _num(right)
            elif isinstance(op, ast.GtE):
                ok = _num(left) >= _num(right)
            else:
                raise FormulaError(f"Comparison not allowed: {type(op).__name__}")
            if not ok:
                return 0.0
            left = right
        return 1.0

    def visit_IfExp(self, node):
        # native ternary: body if test else orelse
        return self.visit(node.body) if _truthy(self.visit(node.test)) else self.visit(node.orelse)

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise FormulaError("Only direct function calls are allowed")
        if node.keywords:
            raise FormulaError("Keyword arguments are not allowed in formulas")
        name = node.func.id

        # ifelse(condition, value_if_true, value_if_false) — lazy: only the
        # chosen branch is evaluated.
        if name == "ifelse":
            if len(node.args) != 3:
                raise FormulaError("ifelse(condition, value_if_true, value_if_false) needs exactly 3 arguments")
            if _truthy(self.visit(node.args[0])):
                return self.visit(node.args[1])
            return self.visit(node.args[2])

        func = _FUNCTIONS.get(name)
        if func is None:
            raise FormulaError(f"Unknown function: '{name}'")
        args = [self.visit(a) for a in node.args]
        return float(func(*args))


def evaluate_formula(formula: str, context: Dict[str, Any]) -> Any:
    """Safely evaluate `formula` against `context`. Returns a float for numeric
    expressions, or a string when the expression yields text (e.g. a chosen
    select value passed through ifelse). Raises FormulaError on anything unsafe
    or invalid so callers can return a clean validation error."""
    if formula is None or str(formula).strip() == "":
        raise FormulaError("Formula is empty")
    try:
        tree = ast.parse(str(formula), mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Invalid formula syntax: {exc.msg}")
    return _SafeEvaluator(context).visit(tree)


def evaluate_number(formula: str, context: Dict[str, Any]) -> float:
    """Like evaluate_formula but guarantees a numeric result (for money/quantity
    computations). Raises FormulaError if the result isn't a number."""
    return _num(evaluate_formula(formula, context))


def build_context(field_values: Dict[str, Any], field_defs: list) -> Dict[str, Any]:
    """Turn a line-item's raw field_values into a formula context.

    For each field definition we expose variables the formula can reference:
      - number / dimension  -> the numeric value under its key
      - boolean             -> 1.0 / 0.0 under its key
      - select              -> the chosen value (text) under its key, AND the
                               chosen option's `rate` under `<key>_rate` (0 if none)
      - text                -> the raw text under its key (usable in == / != only)

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
            rate = 0.0
            for opt in fdef.get("options") or []:
                if str(opt.get("value")) == str(raw):
                    try:
                        rate = float(opt.get("rate") or 0.0)
                    except (TypeError, ValueError):
                        rate = 0.0
                    break
            context[f"{key}_rate"] = rate
        elif data_type == "text":
            context[key] = raw if raw is not None else ""

    # Also expose any extra values the caller passed that weren't defined as
    # fields (e.g. an ad-hoc value), coercing numbers where possible.
    for key, value in (field_values or {}).items():
        if key not in context:
            try:
                context[key] = float(value)
            except (TypeError, ValueError):
                context[key] = value

    return context
