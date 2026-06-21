from product_filter.engine.lexer import gen_token
from product_filter.engine.parser import Parser
from product_filter.engine.validator import validate
from product_filter.engine.operators import COMPARISON_OPERATORS, values_equal
                
def compare(original, operation, value):
    if original is None:
        return False
    op = COMPARISON_OPERATORS.get(operation)
    if op is None:
        raise ValueError(f"Unknown operation {operation}")
    if op["needs_number"]:
        try:
            return op["fn"](float(original), float(value))
        except (ValueError, TypeError):
            return False
    return op["fn"](original, value)

def evaluation(expression,record):
    expr_type=expression[0]
    if expr_type=='comparison':
        field_name=expression[1]
        operation=expression[2]
        value=expression[3]

        original=record.get(field_name)
        return compare(original,operation,value)
    elif expr_type=='and':
        return evaluation(expression[1],record) and evaluation(expression[2],record)
    elif expr_type=='or':
        return evaluation(expression[1],record) or evaluation(expression[2],record)
    elif expr_type=='not':
        return not evaluation(expression[1],record)
    elif expr_type == 'in':
        field_name=expression[1]
        items=expression[2]
        original=record.get(field_name)
        if original is None:
            return False
        return any(values_equal(original, item) for item in items)
    elif expr_type=="contains":
        field_name=expression[1]
        substring=expression[2]
        original=record.get(field_name)
        if original is None:
            return False
        return substring.lower() in str(original).lower()
    else:
        raise ValueError(f"Unknown expression type: {expr_type}")

if __name__=="__main__":
    pass
    # tokens=gen_token('tier in [1,2,4]')
    # ast=Parser(tokens).parse()
    # validate(ast)
    # sample_produc={"name":"wood product","price":150,"colour":"white","tier":4.0,"discontinued":"true","qty":5}
    # print(evaluation(ast,sample_produc))

    # product2 = {"name":"good product","price": 50, "color": "white","tier":1,"qty":3}
    # print(evaluation(ast, product2))