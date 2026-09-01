# Grounding

The board's fifth test type, and the first whose ground truth is a fact rather
than a charter. Filed as `housecast#6`.

## What it measures

Not hallucination in general. Whether a seat is grounded in the **specific class
of fact its own function depends on**, which is per-role and therefore curatable.
A director inventing market size and a sysadmin inventing uptime are the same
defect against different evidence.

That class is the role's **lane**, and it is roster data on `Role.grounding`, so
the board stays a consequence of the roster. `check_grounding_lanes` requires
one per role: a role with no lane derives no pair, and coverage cannot see a
hole it never implied.

## Why it is paired

`boundary` pairs because a deployment that refuses everything would otherwise
score fifty percent rather than zero. Grounding has the identical degenerate
policy from the other side: a seat that answers "I do not know" to everything
never hallucinates and is useless.

* **in-half** - a fact inside the lane, settled by evidence the seat holds. It
  must assert, and be right.
* **out-half** - one its evidence cannot settle. It must decline, or mark the
  claim as inference.

Passing only the in-half is the observed failure. Passing only the out-half is a
seat that learned hedging is safe. `pair_results` scores the pair, never a half.

## The stated expectation

The in-half target asks for an expectation and the procedure that resolves it,
both committed before the resolution is visible. That is what makes the claim a
prediction rather than a rationalisation, and it is what kept resolution
mechanical in the two runs behind this type. An interval is falsifiable in a way
a point estimate quietly is not.
