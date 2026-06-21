# Filter Language

A small query language that turns human-written filter expressions into safe,
executable queries over a product catalog — the take-home described in the Metis
Labs backend assignment. It takes raw text such as:

```
price > 100 AND color = "white"
```

and runs it through a lexer (text → tokens), a hand-rolled parser (tokens → AST),
a schema-aware validator (reject invalid expressions before evaluation), and either
an in-memory evaluator (AST + record → boolean) or an ORM compiler (AST → Django
`Q` object), exposed through a Django endpoint.

## Setup

Requires Python 3.11+.

```bash
# from the project root
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate            # create the database tables
python manage.py seed               # load the sample products
python manage.py runserver
```

`python manage.py seed` populates a small set of sample products (it clears and
re-seeds, so it is safe to re-run).

## Running the tests

```bash
pytest                              # runs the whole suite (pytest-django is configured in pytest.ini)
```

The suite covers the lexer, parser, validator, evaluator, and the HTTP endpoint.

## Example request

```bash
curl -X POST http://127.0.0.1:8000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"expression": "price >= 100 AND (color = \"white\" OR color = \"black\")"}'
```

Response:

```json
{
  "results": [
    {"id": 1, "name": "single wall cup", "price": 120.0, "color": "white", "category": "cups", "qty_available": 600, "tier": 1, "discontinued": false},
    {"id": 4, "name": "dome lid", "price": 200.0, "color": "black", "category": "lids", "qty_available": 150, "tier": 1, "discontinued": false}
  ],
  "count": 2
}
```

A malformed expression returns a 400 with a message, not a 500:

```bash
curl -X POST http://127.0.0.1:8000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"expression": "colour = \"white\""}'
# → 400  {"error": "Unknown field 'colour'"}
```

## Architecture

The pipeline is a sequence of stages. The language engine (lexer → parser →
validator → evaluator / ORM compiler) lives in `product_filter/engine/` and has no
Django dependency, so it can be tested in isolation. The Django layer (the view,
model, and URLs) sits at the app root and wires the engine to HTTP and the database.

```
text → lexer → tokens → parser → AST → validator ─┬─> evaluator (in-memory)  → matches
                                       (schema)    └─> ORM compiler (Q object) → matches
```

- **`engine/lexer.py`** — turns raw text into tokens, tracking each token's position
  for error reporting.
- **`engine/parser.py`** — recursive-descent / precedence-layered parser; builds the
  AST and rejects malformed input with located errors. Single entry point `parse()`.
- **`engine/operators.py`** — a registry of comparison operators (the equality and
  ordering operators), read by both the evaluator and the validator.
- **`engine/validator.py`** — a separate pass that walks the AST and checks it
  against the schema (unknown fields, type mismatches) before evaluation.
- **`engine/evaluator.py`** — walks the AST against a record (a dict) and returns a
  boolean; over a dataset, returns the matches (the in-memory path).
- **`engine/orm_compiler.py`** — walks the AST and builds a Django `Q` object, so the
  database does the filtering (the ORM path).
- **`views.py`** — the Django endpoint wiring the stages together.

The endpoint uses the ORM path so the database does the filtering. The in-memory
evaluator is kept as the reference implementation and is exercised directly by the
unit tests.

## Project layout

```
filter-language/
├── config/                     # Django project settings, root urls
├── product_filter/
│   ├── engine/                 # the language — pure Python, no Django
│   │   ├── lexer.py
│   │   ├── parser.py
│   │   ├── operators.py
│   │   ├── validator.py
│   │   ├── evaluator.py
│   │   └── orm_compiler.py
│   ├── management/commands/
│   │   └── seed.py             # `python manage.py seed`
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── tests/                      # test suite (logic + endpoint)
├── docs/
│   ├── GRAMMAR.md              # full grammar (EBNF), precedence, desugaring
│   ├── DESIGN.md               # decisions, assumptions, types, errors, extension, cuts
│   └── AI_USAGE.md             # how AI tools were used
├── requirements.txt
└── manage.py
```

## Testing approach

Tests are organized around the kinds of failure considered most likely, at every
layer: basic mechanism checks, regression tests for bugs found during development,
error paths that must fail cleanly, and tests that lock in the design decisions
(precedence, missing-field semantics, the BETWEEN collision). Several tests guard
specific bugs found while building — for example, that field names with underscores
lex correctly, that `100` matches a stored `100.0`, and that malformed input such as
trailing tokens or an unterminated string raises a clear error rather than being
silently ignored.

## Further reading

- [Grammar](docs/GRAMMAR.md) — the full grammar, precedence, and the BETWEEN collision.
- [Design](docs/DESIGN.md) — decisions and rejected alternatives, assumptions, type
  behaviour, error reporting, the two execution paths, safety, and what was cut.
- [AI usage](docs/AI_USAGE.md) — where AI tools were used and where the thinking was
  my own.