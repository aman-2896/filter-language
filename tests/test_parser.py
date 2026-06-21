import pytest
from product_filter.engine.lexer import gen_token
from product_filter.engine.parser import Parser


def parse(text):
    # small helper so tests read cleanly
    return Parser(gen_token(text)).parse()


# --- simplest: a single comparison ---

def test_single_comparison():
    # why: the atom — field/op/value becomes one comparison node
    assert parse("price > 100") == ("comparison", "price", ">", "100")


# --- AND / OR build the right node ---

def test_and_node():
    # why: AND joins two comparisons into an 'and' node
    assert parse('price > 100 AND color = "white"') == (
        "and",
        ("comparison", "price", ">", "100"),
        ("comparison", "color", "=", "white"),
    )


# --- precedence: AND binds tighter than OR (THE key parser property) ---

def test_and_binds_tighter_than_or():
    # why: "a AND b OR c" must group as "(a AND b) OR c" — precedence via grammar layering.
    #      this is the single most important parser test.
    tree = parse('price > 1 AND price > 2 OR price > 3')
    # top node must be OR, with the AND as its LEFT child
    assert tree[0] == "or"
    assert tree[1][0] == "and"
    assert tree[2] == ("comparison", "price", ">", "3")


# --- parentheses override precedence ---

def test_parentheses_override_grouping():
    # why: parens force OR to group first — different tree, different meaning
    tree = parse('price > 1 AND (price > 2 OR price > 3)')
    # top node must now be AND, with the OR as its RIGHT child
    assert tree[0] == "and"
    assert tree[2][0] == "or"


# --- NOT binds to one primary ---

def test_not_node():
    # why: NOT wraps a single primary
    assert parse("NOT discontinued") == ("not", ("comparison", "discontinued", "=", "true"))

def test_double_not():
    # why: stacked NOT works via right-recursion — decision A
    assert parse("NOT NOT discontinued") == (
        "not", ("not", ("comparison", "discontinued", "=", "true"))
    )


# --- bare boolean field desugars ---

def test_bare_field_desugars_to_equals_true():
    # why: a bare field becomes (field = true) at parse time, so the evaluator needs no special case
    assert parse("discontinued") == ("comparison", "discontinued", "=", "true")


# --- error cases: malformed input raises, never a silent/garbage tree ---

def test_missing_value_raises():
    # why: "price >" with no value must raise (becomes a 400)
    with pytest.raises(ValueError):
        parse("price >")

def test_double_operator_raises():
    # why: "price > > 100" is legal tokens in an illegal arrangement — parser must reject
    with pytest.raises(ValueError):
        parse("price > > 100")

def test_unclosed_paren_raises():
    # why: "(price > 100" with no closing paren must raise a clear error
    with pytest.raises(ValueError):
        parse("(price > 100")


# --- BETWEEN: the desugaring + collision (the crown jewel) ---

def test_between_desugars():
    # why: BETWEEN is pure sugar — it must become (field >= low) AND (field <= high),
    #      with NO 'between' node anywhere, so the evaluator never sees BETWEEN.
    assert parse("price BETWEEN 10 AND 50") == (
        "and",
        ("comparison", "price", ">=", "10"),
        ("comparison", "price", "<=", "50"),
    )

def test_between_and_collision():
    # why: THE key test — two ANDs, different jobs. BETWEEN's inner AND is consumed as
    #      part of its shape; the SECOND AND is the logical one joining the desugared
    #      BETWEEN-clump to color = "white". This proves the collision is resolved.
    assert parse('price BETWEEN 10 AND 50 AND color = "white"') == (
        "and",
        (
            "and",
            ("comparison", "price", ">=", "10"),
            ("comparison", "price", "<=", "50"),
        ),
        ("comparison", "color", "=", "white"),
    )


# --- IN: builds an 'in' node carrying the list ---

def test_in_node():
    # why: IN produces its own node type (not desugared) with the list of values
    assert parse("tier IN [1, 2, 3]") == ("in", "tier", ["1", "2", "3"])

def test_empty_list():
    # why: decision #7 edge — IN [] is valid, yields an empty list (matches nothing at eval)
    assert parse("tier IN []") == ("in", "tier", [])


# --- nested parens: loop-back-to-top recursion ---

def test_nested_parens():
    # why: ((price > 100)) must parse without error — each "(" re-enters at the top,
    #      proving the parenthesis recursion handles arbitrary nesting depth
    assert parse("((price > 100))") == ("comparison", "price", ">", "100")


# --- AND's right operand goes through the FULL chain ---

def test_and_with_not_on_right():
    # why: "a AND NOT b" — the right side of AND must pass through parse_not, not skip
    #      to parse_comparison. (This exact case would have caught the Phase 1 bug where
    #      parse_and's loop called parse_comparison directly and broke on NOT/parens.)
    assert parse("price > 100 AND NOT discontinued") == (
        "and",
        ("comparison", "price", ">", "100"),
        ("not", ("comparison", "discontinued", "=", "true")),
    )

def test_trailing_tokens_raise():
    # why: malformed input with leftover tokens must raise, not silently ignore the junk
    with pytest.raises(ValueError):
        Parser(gen_token("price >= 100 garbage")).parse()

def test_unterminated_string_raises():
    # why: a string with no closing quote must raise a clear error, not silently tokenize
    with pytest.raises(ValueError):
        gen_token('name = "white')