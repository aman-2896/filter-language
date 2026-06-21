from product_filter.engine.operators import COMPARISON_OPERATORS
SCHEMA = {
    "price": "number",
    "color": "string",
    "category": "string",
    "qty_available": "number",
    "name": "string",
    "tier": "number",
    "discontinued": "boolean",
}


def validate(expression, schema=SCHEMA):
    expr_type = expression[0]

    if expr_type == 'comparison':
        field_name = expression[1]
        operation = expression[2]
        value = expression[3]

        if field_name not in schema:
            raise ValueError(f"Unknown field '{field_name}'")

        field_type = schema[field_name]
        op = COMPARISON_OPERATORS.get(operation)
        if op and op["needs_number"] and field_type != 'number':
            raise ValueError(f"Operator '{operation}' needs a number field, but '{field_name}' is {field_type}")

        # type mismatch between field and value
        if not type_matches(field_type, value):
            raise ValueError(f"Field '{field_name}' is {field_type}, cannot compare to '{value}'")

    elif expr_type == 'in':
        field_name = expression[1]
        items = expression[2]
        if field_name not in schema:
            raise ValueError(f"Unknown field '{field_name}'")
        field_type = schema[field_name]
        for item in items:
            if not type_matches(field_type, item):
                raise ValueError(f"List item '{item}' does not match {field_type} field '{field_name}'")

    elif expr_type == 'contains':
        field_name = expression[1]
        if field_name not in schema:
            raise ValueError(f"Unknown field '{field_name}'")
        if schema[field_name] != 'string':
            raise ValueError(f"CONTAINS needs a string field, but '{field_name}' is {schema[field_name]}")

    elif expr_type in ('and', 'or'):
        validate(expression[1], schema)
        validate(expression[2], schema)

    elif expr_type == 'not':
        validate(expression[1], schema)

    else:
        raise ValueError(f"Unknown expression type: {expr_type}")


def type_matches(field_type, value):
    text = str(value).lower()
    if field_type == 'number':
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    if field_type == 'boolean':
        return text in ('true', 'false')
    if field_type == 'string':
        if text in ('true', 'false'):
            return False
        try:
            float(value)
            return False
        except (ValueError, TypeError):
            return True
    return False