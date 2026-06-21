import pytest
from product_filter.engine.lexer import gen_token
from product_filter.engine.parser import Parser
from product_filter.engine.validator import validate
from product_filter.engine.evaluator import evaluation


def run(text, record):
    # full logic pipeline: lex -> parse -> validate -> evaluate
    tree = Parser(gen_token(text)).parse()
    validate(tree)
    return evaluation(tree, record)


# --- sample records (dicts, the shape .values() produces) ---

WHITE_CUP = {"name": "single wall cup", "price": 120, "color": "white",
             "category": "cups", "qty_available": 600, "tier": 1, "discontinued": False}

CHEAP_LID = {"name": "flat lid", "price": 40, "color": "white",
             "category": "lids", "qty_available": 900, "tier": 3, "discontinued": True}

FLOAT_PRICE = {"name": "odd", "price": 100.0, "color": "white",
               "category": "cups", "qty_available": 10, "tier": 4, "discontinued": False}


# --- basic operators ---

def test_greater_than_true():
    assert run("price > 100", WHITE_CUP) is True

def test_greater_than_false():
    assert run("price > 100", CHEAP_LID) is False

def test_equality_string():
    assert run('color = "white"', WHITE_CUP) is True

def test_not_equal():
    assert run("tier != 1", WHITE_CUP) is False     # tier IS 1, so != is false


# --- AND / OR / NOT semantics ---

def test_and_both_true():
    assert run('price > 100 AND color = "white"', WHITE_CUP) is True

def test_and_one_false():
    assert run('price > 100 AND color = "black"', WHITE_CUP) is False

def test_or_one_true():
    assert run('price > 1000 OR color = "white"', WHITE_CUP) is True

def test_not_inverts():
    assert run("NOT discontinued", WHITE_CUP) is True       # not discontinued -> true
    assert run("NOT discontinued", CHEAP_LID) is False      # is discontinued -> false


# --- REGRESSION: bugs found during development ---

def test_int_float_equality_matches():
    # why: BUG FOUND — price=100 must match a record storing price as 100.0.
    #      string comparison missed this; values_equal's numeric path fixes it.
    assert run("price = 100", FLOAT_PRICE) is True

def test_in_matches_float_value():
    # why: BUG FOUND — tier IN [1,2,4] must match tier stored as 4.0.
    #      naive string-IN missed this; reusing values_equal fixes it.
    assert run("tier IN [1, 2, 4]", FLOAT_PRICE) is True


# --- decision #6: missing field semantics ---

def test_missing_field_non_match():
    # why: decision #6 — a record missing the field is a non-match, never a crash
    record_without_price = {"name": "x", "color": "white", "category": "cups",
                            "qty_available": 5, "tier": 1, "discontinued": False}
    assert run("price > 100", record_without_price) is False

def test_not_of_missing_field_is_true():
    # why: decision #6 consequence (two-valued logic) — NOT(missing) is true,
    #      because the inner condition is false and NOT flips it
    record_without_disc = {"name": "x", "price": 50, "color": "white",
                           "category": "cups", "qty_available": 5, "tier": 1}
    assert run("NOT discontinued", record_without_disc) is True


# --- CONTAINS case-insensitivity (decision #3) ---

def test_contains_case_insensitive():
    # why: decision #3 — "WALL" matches "single wall cup" regardless of case
    assert run('name CONTAINS "WALL"', WHITE_CUP) is True


# --- BETWEEN evaluates correctly through its desugared form ---

def test_between_inclusive_match():
    # why: BETWEEN desugared to >= AND <=; price 120 is within [50, 150]
    assert run("price BETWEEN 50 AND 150", WHITE_CUP) is True

def test_between_outside_range():
    # why: price 40 is below the range -> false
    assert run("price BETWEEN 50 AND 150", CHEAP_LID) is False

# --- boundary inclusivity ---

def test_gte_boundary_inclusive():
    # why: price is exactly 120; >= must include the boundary (classic off-by-one guard)
    assert run("price >= 120", WHITE_CUP) is True

def test_lte_boundary_inclusive():
    # why: the other inclusive boundary — price 120 <= 120 is true
    assert run("price <= 120", WHITE_CUP) is True


# --- IN non-match ---

def test_in_no_match():
    # why: tier is 1, not in [2, 3] -> false
    assert run("tier IN [2, 3]", WHITE_CUP) is False


# --- empty list evaluation (eval side of decision #7) ---

def test_empty_list_matches_nothing():
    # why: IN [] can match nothing — no item to equal — so always false
    assert run("tier IN []", WHITE_CUP) is False


# --- precedence EVALUATES right, not just parses right ---

def test_precedence_evaluates_correctly():
    # why: "(price>1000 AND color=white) OR tier=1" — left clump is FALSE (price not >1000),
    #      but OR tier=1 is TRUE, so whole thing is TRUE. proves AND-binds-tighter produces
    #      the right ANSWER, not just the right tree.
    assert run('price > 1000 AND color = "white" OR tier = 1', WHITE_CUP) is True


# --- double negation evaluates correctly ---

def test_double_not_evaluates():
    # why: NOT NOT discontinued, on a discontinued record -> True NOT'd twice -> True
    assert run("NOT NOT discontinued", CHEAP_LID) is True