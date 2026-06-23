import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from product_filter.engine.lexer import gen_token
from product_filter.engine.parser import Parser
from product_filter.engine.evaluator import evaluation
from product_filter.engine.validator import validate
from product_filter.engine.orm_compiler import convert_to_q
from product_filter.models import Product
from product_filter.signals import health_checked

MAX_EXPRESSION_LENGTH=1000
@csrf_exempt
def filter_products(request):
    if request.method!="POST":
        return JsonResponse({"error":"Please use POST method"},status=405)
    
    try:
        body=json.loads(request.body)
        expression=body["expression"]
    except (json.JSONDecodeError,KeyError):
        return JsonResponse({"error":"Send json with 'expression' field."}, status=400)
    
    try:
        if len(expression)>MAX_EXPRESSION_LENGTH:
            return JsonResponse(
                {"error":f"Expression too long (max {MAX_EXPRESSION_LENGTH} characters)"},
            status=400
            )
        tokens=gen_token(expression)
        ast=Parser(tokens).parse()
        validate(ast)
    except ValueError as e:
        return JsonResponse({"error":str(e)},status=400)
    # products = Product.objects.all().values()
    # results=[p for p in products if evaluation(ast,p)] evaluator based

    #q based
    q = convert_to_q(ast)
    results=list(Product.objects.filter(q).values())
    return JsonResponse({"results":results,"count":len(results)})

def health_check(request):
    health_checked.send(sender="health_check")   # fire our custom signal
    return JsonResponse({"status": "ok"})
