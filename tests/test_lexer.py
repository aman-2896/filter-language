import pytest
from product_filter.engine.lexer import gen_token


# --- simplest: single tokens ---

def test_single_field():
    # why: the most basic unit — a lone word becomes a field token with position 0
    assert gen_token("price") == [("field", "price", 0)]

def test_single_number():
    # why: digits group into one number token
    assert gen_token("100") == [("number", "100", 0)]

def test_single_string():
    # why: quotes are stripped, inner text becomes the value
    assert gen_token('"white"') == [("string", "white", 0)]


# --- basic comparison ---

def test_simple_comparison():
    # why: the core three-token shape, with correct positions for error reporting
    assert gen_token("price > 100") == [
        ("field", "price", 0), ("operation", ">", 6), ("number", "100", 8)
    ]

def test_whitespace_insensitive():
    # why: no spaces must work — proves we segment on char-type, not on spaces
    assert gen_token("price>100") == [
        ("field", "price", 0), ("operation", ">", 5), ("number", "100", 6)
    ]


# --- multi-character operators (look-ahead) ---

def test_gte_is_one_token():
    # why: >= must be ONE token, not > then = (maximal munch on operators)
    tokens = gen_token("price >= 100")
    assert ("operation", ">=", 6) in tokens

def test_not_equal():
    # why: != is a two-char operator with no single-char fallback
    assert ("operation", "!=", 6) in gen_token("price != 100")


# --- keyword vs field disambiguation (maximal munch on words) ---

def test_and_is_keyword():
    # why: AND alone is the keyword
    assert ("and", "AND", 0) in gen_token("AND")

def test_anderson_is_field_not_and():
    # why: a field starting with "AND" must NOT be read as the keyword (maximal munch)
    tokens = gen_token("Anderson")
    assert tokens == [("field", "Anderson", 0)]

def test_keywords_case_insensitive():
    # why: decision — keywords work in any case (and == AND)
    assert ("and", "and", 0) in gen_token("and")


# --- field names with underscores (a bug we hit) ---

def test_underscore_field():
    # why: qty_available must be ONE field token — underscores are valid in field names.
    #      (this exact input caused an infinite loop before the fix)
    assert gen_token("qty_available") == [("field", "qty_available", 0)]


# --- error cases: each must RAISE, not produce silent garbage ---

def test_illegal_character_raises():
    # why: an unexpected char must raise (becomes a 400), not silently vanish
    with pytest.raises(ValueError):
        gen_token("price > @")

def test_double_equals_rejected():
    # why: decision #8 — == is deliberately rejected (no assignment exists to disambiguate)
    with pytest.raises(ValueError):
        gen_token("price == 100")

def test_lone_bang_rejected():
    # why: ! has no single-char meaning; must raise with a helpful message
    with pytest.raises(ValueError):
        gen_token("price ! 100")

# --- maximal munch on booleans (words that START with true/false are fields) ---

def test_truest_is_field_not_boolean():
    # why: "truest" starts with "true" but isn't the boolean — must be a field
    #      (same maximal-munch rule as Anderson vs AND)
    assert gen_token("truest") == [("field", "truest", 0)]

def test_false_alarm_is_field():
    # why: "false_alarm" starts with "false" but is a field; also exercises the underscore
    assert gen_token("false_alarm") == [("field", "false_alarm", 0)]


# --- string containing an operator: chars inside quotes are literal ---

def test_operator_inside_string_is_literal():
    # why: the ">" inside quotes is part of the string VALUE, not an operator token.
    #      proves the string-gobble reads until the closing quote, ignoring everything inside.
    assert gen_token('name = "a > b"') == [
        ("field", "name", 0),
        ("operation", "=", 5),
        ("string", "a > b", 7),
    ]


# --- list tokens ---

def test_list_tokens():
    # why: brackets and commas become structural tokens so the parser can read a list
    assert gen_token("[1, 2, 3]") == [
        ("lsqbracket", "[", 0),
        ("number", "1", 1),
        ("comma", ",", 2),
        ("number", "2", 4),
        ("comma", ",", 5),
        ("number", "3", 7),
        ("rsqbracket", "]", 8),
    ]


# --- the other two-char operator ---

def test_lte_is_one_token():
    # why: <= must be ONE token, mirror of the >= test
    assert ("operation", "<=", 6) in gen_token("price <= 100")


# --- operator at end of input: the look-ahead end-guard ---

def test_operator_at_end_of_input():
    # why: when ">" is the LAST character, peeking at pos+1 must not crash —
    #      the "pos + 1 < len(text)" guard handles this. ">" should be a lone operator.
    assert gen_token("price >") == [
        ("field", "price", 0),
        ("operation", ">", 6),
    ]