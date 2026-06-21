import pytest
from product_filter.engine.lexer import gen_token
from product_filter.engine.parser import Parser
from product_filter.engine.validator import validate


def check(text):
    # parse then validate — the helper mirrors the real pipeline order
    tree = Parser(gen_token(text)).parse()
    validate(tree)
    return tree


# --- valid expressions pass silently (no exception) ---

def test_valid_comparison_passes():
    # why: a well-formed expression against known fields must NOT raise
    check('color = "white"')          # no assertion needed — passing = not raising

def test_valid_complex_expression_passes():
    # why: nested valid expression validates fully (recursion reaches every leaf)
    check('price > 100 AND (color = "white" OR tier IN [1, 2, 3])')


# --- validation-boundary table, row by row (each must RAISE) ---

def test_unknown_field_rejected():
    # why: row 1 — field not in schema → 400
    with pytest.raises(ValueError):
        check('colour = "white"')      # British spelling, not in schema

def test_type_mismatch_rejected():
    # why: row 2 — number field compared to a string literal → 400
    with pytest.raises(ValueError):
        check('price > "white"')

def test_ordering_on_string_field_rejected():
    # why: ordering operator on a non-number field is incoherent → 400
    with pytest.raises(ValueError):
        check('name > 5')

def test_wrong_type_list_rejected():
    # why: row 4 — list item type doesn't match the numeric field → 400
    with pytest.raises(ValueError):
        check('tier IN ["a", "b"]')

def test_contains_on_number_field_rejected():
    # why: CONTAINS needs a string field; using it on a number is invalid
    with pytest.raises(ValueError):
        check('price CONTAINS "1"')


# --- the desugaring-meets-validation case (your sharp insight) ---

def test_not_on_number_field_rejected():
    # why: "NOT price" desugars to (price = true); validation then rejects it because
    #      price is a number, not boolean. No dedicated bare-boolean check needed —
    #      desugaring + type-matching catch it together.
    with pytest.raises(ValueError):
        check("NOT price")

def test_not_on_boolean_field_passes():
    # why: "NOT discontinued" desugars to (discontinued = true); discontinued IS boolean,
    #      so this must PASS — proving the same machinery accepts the valid case
    check("NOT discontinued")

# --- valid expressions using the brief's own fields ---

def test_category_equality_passes():
    # why: a valid string-field equality from the brief's examples — proves schema matches the brief
    check('category = "cups"')

def test_qty_available_passes():
    # why: the brief's exact underscore field — proves it VALIDATES (in schema), not just lexes
    check("qty_available >= 500")


# --- recursion: error buried inside a nested expression ---

def test_nested_unknown_field_rejected():
    # why: the error (misspelled "colour") is a CHILD of the AND node. validation must
    #      recurse to find it — a validator that only checked the top 'and' node would miss it.
    #      this directly proves the recursion property.
    with pytest.raises(ValueError):
        check('price > 100 AND colour = "white"')


# --- type-matching edge cases ---

def test_string_field_vs_number_rejected():
    # why: decision — a string field compared to a numeric-looking value is flagged as a
    #      likely mistake. verifies the string branch of type_matches rejects numbers.
    with pytest.raises(ValueError):
        check("name = 100")

def test_boolean_field_vs_number_rejected():
    # why: discontinued is boolean; comparing it to 5 is a type mismatch → must raise
    with pytest.raises(ValueError):
        check("discontinued = 5")


# --- empty list still validates (decision #7) ---

def test_empty_list_passes_validation():
    # why: IN [] is valid (matches nothing at eval); the validator must not choke on
    #      zero items — the per-item loop simply runs zero times
    check("tier IN []")