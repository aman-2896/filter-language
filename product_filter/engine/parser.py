from product_filter.engine.lexer import gen_token


class Parser:
    def __init__(self,tokens):
        self.tokens=tokens
        self.position=0
        self.depth=0
        self.max_depth=100
    def parse(self):
        result = self.parse_or()
        if self.current_tok() is not None:
            token = self.current_tok()
            raise ValueError(f"Unexpected token '{token[1]}' at position {token[2]}")
        return result
    def current_tok(self):
        token_length=len(self.tokens)
        if self.position < token_length:
            return self.tokens[self.position]
        return None
    def parse_list(self):
        self.analyse_tok("lsqbracket")               # consume "["
        values = []
        # empty list: IN []
        if self.current_tok() is not None and self.current_tok()[0] == 'rsqbracket':
            self.position += 1
            return values
        while True:
            value = self.current_tok()
            if value is None or value[0] not in ('number', 'string', 'boolean'):
                raise ValueError("List items must be number, string, or boolean")
            values.append(value[1])
            self.position += 1
            nxt = self.current_tok()
            if nxt is not None and nxt[0] == 'comma':
                self.position += 1                   # consume comma, continue
                continue
            break
        self.analyse_tok("rsqbracket")               # consume "]"
        return values
    def analyse_tok(self,tok_type):
        token=self.current_tok()
        if token is None:
            raise ValueError(f"the {tok_type} token not identified")
        if token[0] !=tok_type:
            raise ValueError(f"Expected {tok_type} but got '{token[0]}' at location {token[2]} ")
        self.position+=1
        return token
    
    def parse_comparison(self):
        field = self.analyse_tok("field")
        token = self.current_tok()
        if token is None:
            return ('comparison', field[1], '=', 'true')

        kind = token[0]
        if kind == 'in':
            self.position += 1                       # consume IN
            values = self.parse_list()
            return ('in', field[1], values)

        if kind == 'contains':
            self.position += 1                       # consume CONTAINS
            value = self.current_tok()
            if value is None or value[0] != 'string':
                raise ValueError("CONTAINS expects a string value")
            self.position += 1
            return ('contains', field[1], value[1])

        if kind == 'between':
            self.position += 1                       # consume BETWEEN
            low = self.current_tok()
            if low is None or low[0] not in ('number', 'string'):
                raise ValueError("BETWEEN expects a value")
            self.position += 1
            self.analyse_tok("and")                  # the inner AND, part of BETWEEN's shape
            high = self.current_tok()
            if high is None or high[0] not in ('number', 'string'):
                raise ValueError("BETWEEN expects a value after AND")
            self.position += 1
            return ('and',
                    ('comparison', field[1], '>=', low[1]),
                    ('comparison', field[1], '<=', high[1]))
        if kind == 'operation':
            operation = self.analyse_tok("operation")
            value = self.current_tok()
            if value is None or value[0] not in ('number', 'string', 'boolean'):
                raise ValueError("Invalid value type, expected (string, number, boolean) after operator.")
            self.position += 1
            return ('comparison', field[1], operation[1], value[1])

        
        return ('comparison', field[1], '=', 'true')
    
    def parse_and(self):
        expression=self.parse_not()
        while self.current_tok() is not None and self.current_tok()[0]=='and':
            self.position+=1
            right=self.parse_not()
            expression=('and',expression,right)
        return expression
    def parse_or(self):
        expression=self.parse_and()
        while self.current_tok() is not None and self.current_tok()[0]=='or':
            self.position+=1
            right=self.parse_and()
            expression=('or',expression,right)
        return expression

    def parse_not(self):
        if self.current_tok() is not None and self.current_tok()[0]=='not':
            self.position+=1
            next=self.parse_not()
            return ('not',next)
        return self.parse_primary()
    
    def parse_primary(self):
        token = self.current_tok()
        if token is None:
            raise ValueError("Expression ended unexpectedly")
        if token[0]=='lparen':
            self.depth+=1
            if self.depth > self.max_depth:
                raise ValueError(f"Expression nested too deeply (max {self.max_depth})")
            self.position+=1
            inner = self.parse_or() # whle expression to top
            if self.current_tok() is None or self.current_tok()[0]!='rparen':
                raise ValueError("Missing closing ')'")
            self.position+=1
            self.depth-=1
            return inner
        if token[0]=='field':
            return self.parse_comparison()
        raise ValueError(f"Expected a field or '(' but got '{token[0]}' at position {token[2]}")
    
if __name__=="__main__":
    tokens=gen_token('price BETWEEN 10 AND 50')
    result = Parser(tokens).parse()
    print(result)
    # pass