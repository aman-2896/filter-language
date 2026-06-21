# AI Usage

I used AI (Claude) throughout this assignment, mainly as a teacher and a thinking
partner. I had not built a language before — lexers, ASTs, recursive-descent
parsing, and operator precedence were new to me — so I leaned on it to learn these
concepts before and while building.

**Decisions.** The design decisions were mine. I worked through each by
brainstorming with the AI: it laid out trade-offs and pushed back on my reasoning,
and I made the calls. In several cases I questioned its framing until it made sense
to me — for example, choosing to include `BETWEEN` to handle its `AND` collision,
and working through why "OR is made of AND" until I understood the precedence
layering. The decisions in `DESIGN.md`, and the alternatives I rejected, are mine.

**Code.** For the more complex parts, AI wrote the initial implementation and I
worked with it to understand how each part functioned. The clearest examples are
the parser's precedence layering (how `OR`, `AND`, and `NOT` are structured so
precedence falls out of the grammar) and the `BETWEEN` desugaring that resolves the
collision between its internal `AND` and the logical `AND`, along with the lexer's
multi-character operator look-ahead (`>=`, `<=`, `!=`). I focused on understanding
how each piece worked rather than just running it.

**Tests.** I took help from the AI in writing the test cases. The bugs they guard,
though, are ones I ran into during the build and then understood — a missing
negation in the `NOT` evaluator, a parser entry-point bug that dropped top-level
`OR`, a status-code bug returning 200 instead of 400, and an equality bug where
`100` did not match a stored `100.0`.

In short: AI accelerated my learning and helped me write the harder code faster,
while the decisions and the understanding of how it fits together are what I
brought to it.