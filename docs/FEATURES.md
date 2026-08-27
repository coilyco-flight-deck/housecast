# Features

Coarse inventory of the major capabilities housecast ships. Bugfixes,
refactors, and internal plumbing never earn an entry here.

## Shipped

Nothing. This repository carries the catalog scaffold and no product code:
a license, the trifecta, the validator suite, a justfile, a CI gate, and an
empty package that imports and reports its version.

That is the honest state, and it stays written this way until a capability
actually lands. An aspirational inventory would be wrong on the day it was
written.

## Coming

`agent-compose#337` is the parent slice, and it moves the compositor and
`evalkit` into this repository along with the packaging that publishes them.
`agent-compose#329` is the design those pieces serve. Neither is unblocked by
the scaffold commit, so neither belongs in the list above yet.

## See also

* [`../README.md`](../README.md) - what housecast is and how it pairs with acompose.
* [`../AGENTS.md`](../AGENTS.md) - agent-facing operating context for this repository.
* [`../.ward/ward.yaml`](../.ward/ward.yaml) - catalog metadata for the cross-repo graph.
