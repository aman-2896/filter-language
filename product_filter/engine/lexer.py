KEYWORDS={
    "AND":"and",
    "OR":"or",
    "NOT":"not",
    "IN":"in",
    "CONTAINS":"contains",
    "BETWEEN":"between"
}
def gen_token(inp_str:str):
    tokens=[]
    position=0
    str_length=len(inp_str)
    while position<str_length:
        char =inp_str[position]
        # if it is a space, we don't need to parseit
        if char==' ': 
            position+=1
            continue
        elif char.isalpha() or char == "_":
            begin = position
            while position < str_length and (inp_str[position].isalpha() or inp_str[position].isdigit() or inp_str[position] == "_"):
                position += 1
            word = inp_str[begin:position]
            upper_word=word.upper()
            if upper_word in KEYWORDS:
                kind=KEYWORDS[upper_word]
            elif upper_word in ("TRUE","FALSE"):
                kind="boolean"
            else:
                kind="field"
            tokens.append((kind, word, begin))
            continue
        elif char.isdigit():
            begin=position
            while position < str_length and inp_str[position].isdigit():
                position+=1
            tokens.append(("number",inp_str[begin:position],begin))
            continue
        elif char=='"':
            begin=position
            position+=1
            while position < str_length and inp_str[position]!='"':
                position+=1
            if position >= str_length:                   
                raise ValueError(f"Unterminated string starting at position {begin}")
            word=inp_str[begin+1:position]
            position+=1
            tokens.append(("string",word,begin))
            continue
        elif char=="[":
            tokens.append(("lsqbracket",char,position))
            position+=1
            continue
        elif char=="]":
            tokens.append(("rsqbracket",char,position))
            position+=1
            continue
        elif char==",":
            tokens.append(("comma",char,position))
            position+=1
            continue
        elif char in "<>=!":
            begin=position
            next_char=inp_str[position+1] if position+1 < len(inp_str) else None
            if char == "!":
                if next_char=="=":
                    tokens.append(("operation","!=",begin))
                    position+=2
                else:
                    raise ValueError(f"Unexpected '!' at position {position}; did you mean '!='? e.g. price != 100")
            elif char=="=":
                if next_char=="=":
                    raise ValueError(f"Unexpected '==' at position {position}; use single '=' for equal check")
                tokens.append(("operation","=",begin))
                position+=1
            elif char in "<>":
                if next_char=="=":
                    tokens.append(("operation",char+"=",begin))
                    position+=2
                else:
                    tokens.append(("operation",char,begin))
                    position+=1
            continue
        elif char == "(":
            tokens.append(("lparen", char, position))
            position += 1
            continue
        elif char == ")":
            tokens.append(("rparen", char, position))
            position += 1
            continue
        else:
            raise ValueError(f"Unexpected value {char} encountered")
    return tokens


if __name__=="__main__":
    # inp_str="price == 100"
    # tokens=gen_token(inp_str)
    # print(tokens)
    pass