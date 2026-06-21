from django.db.models import Q

OPERATION_LOOKUPS={
    "=":"exact",
    "!=":"exact",
    ">":"gt",
    "<":"lt",
    ">=":"gte",
    "<=":"lte",
}

NEGATION={"!="}

def convert_value(value):
    if isinstance(value,str):
        low=value.lower()
        if low=="true":
            return True
        if low=="false":
            return False
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value
def convert_to_q(expression):
    opr_type=expression[0]
    if opr_type =="comparison":
        field,operator,value=expression[1],expression[2],expression[3]
        value=convert_value(value)
        lookup=OPERATION_LOOKUPS[operator]
        q=Q(**{f"{field}__{lookup}":value})
        if operator in NEGATION:
            return ~q
        return q
    elif opr_type == "and":
        return convert_to_q(expression[1]) & convert_to_q(expression[2])
    elif opr_type == "or":
        return convert_to_q(expression[1]) | convert_to_q(expression[2])
    elif opr_type == "not":
        return ~convert_to_q(expression[1])
    elif opr_type == "in":
        field,items=expression[1],expression[2]
        items=[convert_value(item) for item in items]
        return Q(**{f"{field}__in":items})
    elif opr_type == "contains":
        field,substring=expression[1],expression[2]
        return Q(**{f"{field}__icontains":substring})
    else:
        raise ValueError(f"Cannot create Q expression for operation type : {opr_type}")
       

    