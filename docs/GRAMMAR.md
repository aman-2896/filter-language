# Grammar

The filter language is defined by the grammar below, written in EBNF. The parser
is a hand-rolled recursive-descent / precedence-layered parser, and each grammar
rule maps directly to one parser function (`parse_or`, `parse_and`, `parse_not`,
`parse_primary`, `parse_comparison`).

## EBNF

```
or_expression   = and_expression { "OR" and_expression }
and_expression  = not_expression { "AND" not_expression }
not_expression  = "NOT" not_expression | primary
primary         = comparison
                | field
                | "(" or_expression ")"
comparison      = field comp_op value
                | field "IN" list
                | field "CONTAINS" string
                | field "BETWEEN" value "AND" value
comp_op         = "=" | "!=" | "<" | "<=" | ">" | ">="
value           = number | string | boolean
list            = "[" [ value { "," value } ] "]"
field           = letter { letter | digit | "_" }
```

Notation: `=` defines a rule, `|` is alternation, `{ }` is zero-or-more,
`[ ]` is optional, and quoted text is a literal token.

## Precedence

Precedence is encoded by the **layering** of the rules, not by a separate
precedence table. From loosest-binding (top) to tightest-binding (bottom):

```
OR   (loosest)
AND
NOT
comparison / primary   (tightest)
```

Because `or_expression` is built from `and_expression`, which is built from
`not_expression`, which is built from `primary`, the tighter operators clump
first and the looser ones join the clumps. For example:

```
price > 1 AND price > 2 OR price > 3
```

parses as `(price > 1 AND price > 2) OR price > 3` — the `AND` binds tighter, so
it groups first, and `OR` joins the result. Parentheses override this grouping by
re-entering the grammar at the top (`"(" or_expression ")"`), which is also what
allows arbitrary nesting depth with a fixed set of rules.

## NOT is right-recursive

The rule `not_expression = "NOT" not_expression | primary` references itself,
which allows stacked negation (`NOT NOT discontinued`). The parser mirrors this:
`parse_not` calls `parse_not` for its operand, so any number of `NOT`s chain
naturally without a special case.

## The BETWEEN / AND collision

`BETWEEN` introduces a deliberate subtlety: its grammar contains an `AND`
(`field BETWEEN value AND value`), and `AND` is also the logical operator. In an
expression like:

```
price BETWEEN 10 AND 50 AND color = "white"
```

there are two `AND`s with different jobs. The first belongs to `BETWEEN`'s fixed
shape and is consumed as part of parsing the `BETWEEN` comparison. The second is
the logical `AND`, handled by the `and_expression` rule, which joins the
(desugared) `BETWEEN` clump to `color = "white"`. Because `BETWEEN`'s rule has
exactly one `AND` slot, any further `AND` can only be the logical one — position
disambiguates them.

## Desugaring

Two constructs are desugared at parse time so the evaluator never sees them as
distinct node types:

- `field BETWEEN low AND high` becomes `(field >= low) AND (field <= high)`.
- A bare boolean field (e.g. `discontinued`) becomes `field = true`.

Desugaring is applied to constructs that are exactly equivalent to existing
nodes, which keeps the AST node set minimal (comparison, logical AND/OR, NOT)
and keeps the evaluator — which runs once per record — as small as possible.
`IN` and `CONTAINS`, by contrast, are genuinely new operations not reducible to
existing nodes, so they keep their own node types.

## AST node types

```
("comparison", field, operator, value)
("and", left, right)
("or", left, right)
("not", child)
("in", field, [values])
("contains", field, substring)
```