# Design

This document explains the reasoning behind the filter language: the key
decisions and the alternatives rejected, the assumptions made where the brief was
silent, how types and errors behave, and what was deliberately left out.

---

## Key decisions

Each decision lists what was chosen, why, and the alternative that was rejected.

### 1. Schema-aware language

**Chosen:** the language knows the catalog's fields and their types up front (a
field→type map).
**Why:** this enables rejecting unknown fields and type mismatches at parse time,
before any data is touched — which means fail-fast behaviour and genuinely helpful
errors like "unknown field 'colour'". It also makes ORM compilation possible.
**Cost accepted:** the language is coupled to the catalog's shape; the schema is a
second source of truth that can drift from the database. In production this would
be derived from the Django model's field definitions (`Product._meta`) rather than
hand-maintained.
**Rejected:** a schema-unaware language — more decoupled and reusable across any
dataset, but it can only detect these errors at evaluation time and gives weaker
messages.

### 2. Include BETWEEN

**Chosen:** support `BETWEEN`, desugared into `>= AND <=`.
**Why:** it is more ergonomic for users (a range reads naturally), and it
demonstrates handling the collision between `BETWEEN`'s internal `AND` and the
logical `AND`. Desugaring keeps the evaluator free of a `BETWEEN` special case.
**Rejected:** cutting it as redundant with `>= AND <=` — defensible on simplicity
grounds, but the ergonomics plus the collision-handling were judged worth the
small grammar cost.

### 3. CONTAINS is case-insensitive

**Chosen:** `CONTAINS` matches regardless of case.
**Why:** a user filtering a catalog expects "wall" to match "Single Wall Cup";
case-sensitive matching would return nothing and look like a bug.
**Cost named:** the in-memory evaluator always folds case, but a database only
folds case if its collation does — so the same expression could return different
results in-memory versus through the ORM. The mitigation is to emit the explicitly
case-insensitive ORM lookup so both paths agree.
**Rejected:** case-sensitive matching.

### 4. Cut LIKE

**Chosen:** support `CONTAINS`, not `LIKE`.
**Why:** `LIKE` is strictly more powerful than `CONTAINS` (wildcard patterns:
starts-with, ends-with), but that power requires parsing and escaping wildcard
syntax, which is complexity the catalog use case does not justify. `CONTAINS`
covers the common substring case. `LIKE` is the natural extension point if richer
matching is needed.
**Rejected:** including `LIKE`.

### 5. Two kinds of type mismatch

Type problems split into two cases handled at different stages:

- **Type-incoherent expression** (e.g. `price > "white"`): wrong regardless of
  data, so caught at parse time and returned as a 400. This is only possible
  because the language is schema-aware (decision 1).
- **Missing field at evaluation time:** the expression is valid but a particular
  record lacks the field; handled per-record at evaluation, never a 400.

The governing principle: **wrong-regardless-of-data is a parse-time 400;
wrong-only-for-a-record is an evaluation-time non-match.**

### 6. Missing field → non-matching

**Chosen:** when a record lacks a field the filter references, that condition is
false (the record is a non-match). Two-valued logic.
**Why:** predictable and simple for a catalog — every condition resolves to a clean
true/false.
**Cost accepted:** `NOT (missing field)` evaluates to true, since the inner
condition is false and `NOT` flips it.
**Rejected:** SQL-style three-valued (true/false/unknown) NULL logic — arguably
more correct about missing data, but more complex and more surprising to users.
**Never:** crashing on a missing field.

### 7. List literals must match the field type

**Chosen:** every item in an `IN` list must match the field's type. An empty list
(`tier IN []`) is valid and matches nothing.
**Why:** `IN` compares the field against each item, so an item of a different type
is the same incoherence as `price > "white"`. Because the language is
schema-aware, requiring each item to match the field type also gives homogeneity
for free.
**Rejected:** mixed-type lists.

### 8. Single `=` for equality

**Chosen:** equality is a single `=`; `==` is rejected with a clear error.
**Why:** the language has no assignment, so unlike a programming language there is
no second meaning for `=` to be confused with — comparison is the only thing it
can mean. The two-symbol convention that exists to disambiguate assignment from
comparison simply does not apply. It is also friendlier for the hand-writing user.
**Rejected:** requiring `==`.

### 9. Stretch goals

All three of the stretch goals from the Metis Labs brief are implemented:

- **Extensibility** — comparison operators live in a single registry
  (`engine/operators.py`) read by both the evaluator and the validator, so adding a
  comparison operator is a localized change. See "Extending the language" below.
- **ORM compilation** — the AST can be compiled to a Django `Q` object so the
  database does the filtering, alongside the in-memory evaluator. See "The two
  execution paths" below.
- **Safety** — input-length and nesting-depth limits, plus an injection note. See
  "Safety" below.

---

## Assumptions (where the brief was silent)

- **Product schema:** the brief does not define one, so a single flat `Product`
  table is assumed, with `price`, `color`, `category`, `qty_available`, `name`,
  `tier`, `discontinued` as direct columns. A single table is used because the
  language filters fields on one record and has no joins; a normalized multi-table
  schema would not be queryable by this language. Field names match the brief's
  example expressions exactly (`color`, `qty_available`) so the reviewer's own test
  queries work without translation.
- **Field names:** follow standard identifier rules — a letter or underscore
  followed by letters, digits, or underscores. (This was confirmed by a bug:
  `qty_available` must lex as one token.)
- **Strings:** double-quoted only; single quotes are not supported. An unterminated
  string (no closing quote) raises a clear error. Escaped quote characters inside
  strings are not supported (a documented limitation).
- **Numbers:** integer and decimal literals are valid; negatives are allowed at the
  literal level. Whether a specific field accepts decimals or negatives is a
  schema/type concern, not a lexer concern.
- **Booleans:** bare `true`/`false`, case-insensitive; `"true"` in quotes is a
  string, not a boolean.
- **Keywords:** case-insensitive (`AND` and `and` both work); field names match the
  schema exactly.
- **Endpoint:** a successful filter returns 200 with a JSON list of matching
  products and a count; an expression that matches nothing returns 200 with an
  empty list (not an error).

---

## Type coercion and mismatch behaviour

Validation runs after parsing and before evaluation, against the schema. It checks:

| Case | Stage | Result |
|---|---|---|
| Unknown field (`colour = "white"`) | parse-time (validation) | 400 |
| Type mismatch (`price > "white"`) | parse-time (validation) | 400 |
| Ordering operator on a non-number field (`name > 5`) | parse-time | 400 |
| Wrong/mixed-type list (`tier IN ["a"]`) | parse-time | 400 |
| CONTAINS on a non-string field | parse-time | 400 |
| Malformed syntax (`price > > 100`) | parse-time (parser) | 400 |
| Illegal character (`price > @`) | parse-time (lexer) | 400 |
| Record missing the field at evaluation | evaluation-time | non-match, no error |

At evaluation, equality is type-aware: it compares numerically when both sides are
numeric (so `100` matches a stored `100.0`) and falls back to case-insensitive
string comparison otherwise. `IN` reuses the same equality logic, so membership is
consistent with `=`. Ordering operators (`<`, `>`, `<=`, `>=`) coerce both sides to
numbers and treat a non-numeric operand as a non-match.

A note on a non-obvious result of this design: there is no dedicated "bare boolean
field" validation rule. `NOT price` (where `price` is a number) is desugared to
`price = true`, and type-matching then rejects it because a number field cannot be
compared to a boolean value. The desugaring and the type-matching together handle a
case that would otherwise need its own check.

---

## Error reporting — what the user sees

Errors are raised as exceptions carrying a human-readable message, and the endpoint
turns any of them into an HTTP 400 with that message in the response body — never a
500 or a stack trace. Because the lexer tracks the position of every token, lexer
and parser errors can point at the offending location. Examples of what a user
receives:

- `colour = "white"` → 400, "Unknown field 'colour'"
- `price > "white"` → 400, type-mismatch message
- `price > @` → 400, "Unexpected character '@' at position ..."
- `price == 100` → 400, message indicating single `=` should be used
- `price >= 100 garbage` → 400, "Unexpected token 'garbage' at position ..." — after
  parsing the full expression, any leftover tokens are reported rather than silently
  ignored (`parse()` checks that all tokens were consumed).
- `name = "white` → 400, "Unterminated string ..." — a string with no closing quote
  is rejected rather than silently tokenized.
- a request with no `expression` field → 400, "Send JSON with an 'expression' field"

---

## Extending the language

Comparison operators (`=`, `!=`, `<`, `<=`, `>`, `>=`) are defined in a single
registry in `engine/operators.py`, where each entry holds how the operator is
evaluated and whether it requires a number field. Both the evaluator and the
validator read from this registry rather than from their own hardcoded lists.

As a result, **adding a comparison operator is one registry entry plus teaching the
lexer its token** — the parser, evaluator, and validator need no changes, because
the parser accepts any operator token and the other two read the registry. (For
example, adding a `<>` alias for `!=` is one registry line and one lexer branch.)

Operators with a different *shape* — `IN` (a list), `CONTAINS` (substring),
`BETWEEN` (desugared) — are not part of this registry, because they are not simple
`field op value` comparisons. Adding one of those is a localized change across the
stages (lexer keyword, a parser branch, an evaluator/compiler node), in the same
way `CONTAINS` was added. The registry is applied where the pattern fits and not
forced where it does not.

A new **value type** is added to the lexer's literal recognition, the validator's
type vocabulary, and the equality/comparison logic.

---

## The two execution paths

The same AST can be run two ways, both walking the tree with the same node dispatch:

- **In-memory** (`engine/evaluator.py`) — loads records and returns a boolean per
  record. Simple, and it can express anything Python can, but it loads all rows and
  filters in Python, which does not scale.
- **ORM** (`engine/orm_compiler.py`) — compiles the AST to a Django `Q` object so
  the database filters and returns only matches. This scales, and it is what the
  endpoint uses.

Per the Metis Labs brief's request to "be honest about what your language can and
cannot express once it has to become SQL," the two paths can diverge:

- **Type strictness.** The in-memory path coerces loosely in Python (a string
  `"true"` compares fine against a boolean). The ORM path must convert literals to
  their proper Python types first, because the database columns are strictly typed —
  `discontinued = true` only works once `"true"` becomes the boolean `True`. The
  compiler infers the type from the literal, not from the schema; a schema-driven
  conversion would be more correct and is the natural next step.
- **Case folding.** In-memory `CONTAINS` folds case in Python; the ORM path uses the
  database's case-insensitive lookup, which depends on the database's collation. The
  same expression can therefore return different results on the two paths.

These divergences are a property of compiling to SQL, not a bug — naming where the
two paths disagree is the honest version of the stretch goal.

---

## Safety

The language runs user-supplied input, so two limits guard it, both returning a 400:

- **Input length** — expressions longer than a fixed cap are rejected before lexing,
  to prevent a very large input from exhausting memory.
- **Nesting depth** — the parser is recursive descent, so deeply nested parentheses
  (`((((...))))`) would otherwise consume the call stack and crash with a
  `RecursionError`. A depth counter rejects expressions nested past a sane limit
  before the recursion can overflow the stack. The limit is far beyond any
  hand-written filter and well under Python's recursion limit, so it is invisible to
  real users and blocks the abuse.

**Injection** is closed by construction rather than by sanitizing: user input never
becomes executable code. It becomes typed data in an AST, and on the ORM path values
reach the database only as parameters of a `Q` object (Django parameterizes them),
never concatenated into a SQL string. A value such as `"'; DROP TABLE products; --"`
is only ever matched as a literal string, never executed.

---

## What was cut, and what's next

- **LIKE** — cut as discussed; `CONTAINS` covers the common case.
- **Joins / cross-table filtering** — the language filters fields on a single
  record; querying across related tables would be a significant language extension.
- **Escaped quotes inside strings** — not supported; would be added to the lexer's
  string handling.
- **Three-valued NULL logic** — chose two-valued for predictability; would revisit
  if the data needed to distinguish "missing" from "false".
- **Schema from the model** — the schema is currently a hand-maintained map; the
  next step is deriving it from `Product._meta` to remove the drift risk.
- **Schema-driven type conversion in the ORM path** — the compiler currently infers
  a literal's type from the literal itself; driving it from the field's declared
  type would remove the divergence noted under "The two execution paths".