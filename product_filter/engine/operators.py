def values_equal(original, value):
    try:
        return float(original) == float(value)
    except (ValueError, TypeError):
        return str(original).lower() == str(value).lower()


COMPARISON_OPERATORS = {
    "=":  {"fn": lambda a, b: values_equal(a, b),     "needs_number": False},
    "!=": {"fn": lambda a, b: not values_equal(a, b), "needs_number": False},
    ">":  {"fn": lambda a, b: float(a) > float(b),    "needs_number": True},
    "<":  {"fn": lambda a, b: float(a) < float(b),    "needs_number": True},
    ">=": {"fn": lambda a, b: float(a) >= float(b),   "needs_number": True},
    "<=": {"fn": lambda a, b: float(a) <= float(b),   "needs_number": True},
}