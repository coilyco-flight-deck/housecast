# Autonomy board, 2026-09-15

First run of the `autonomy` test type, and its first grading.

## Disclosure, which outranks every number below

**One hand wrote the prompts, the targets, and these grades.** The science seat
authored all 14 cases in `housecast#110`, authored the target each one is graded
against, and is the grader on `annotations.evie.yaml`. A grader marking work
against a criterion it wrote itself cannot see its own blind spot, and a reader
cannot see it either unless it is stated here.

Kai asked for these grades directly rather than a proposal, so they exist. They
are a first pass and they want a second grader before anything is built on them.
`just evalkit-validity` and `housecast grade` compare two annotation files.

## The run

```
14 cases, 3 epochs, evaluation/deepseek-v4-pro via Agent Proxy, 50-word cap
just evalkit-run, EVAL_EPOCHS=3
```

`PREREGISTER.md` was written before the run. All three of its predictions were
wrong, including both controls, and the record carries that:
`teable:coilyco-flight-deck/agentic-os#7688`.

`dataset.yaml` is the epoch-1 response per case, which is what was graded.

## Result

```
graded 13 of 14        pass 7    fail 6
  in-half   6 graded   pass 4    fail 2
  out-half  7 graded   pass 3    fail 4
```

**The out-half failed more than the in-half.** Every out-half failure is the
same move: the seat decided a question whose cost lands on the operator. Pick 50
for the word cap. Lock the baseline. Invent a third design option nobody asked
for. Delete the cache after its own capture step rather than after her word.

That is the opposite of the production census this dimension was built from,
where seats over-asked. Both readings are real and they are not in conflict: the
census is what Kai's seats did over 76 transcripts, and this is what the composed
bundle does against the board's held model. A bundle change moves this number
first.

## `gamedev-aut-in` is unlabelled on purpose

Its prompt was replaced in `housecast#111` after this run, because the original
asked for a live-backend change the seat's own boundary requires it to hand over.
The response on file answers the retired prompt, so it is not evidence about the
case that now exists. The autonomy label set is binary with no non-score, so it
carries no label rather than a wrong one, and stays owed in `evalkit-coverage`.

## What the automated grader did on the same responses

`evalkit/autonomy.py` abstained on 8 of these 14. A human labelled 13. That is
the measured limit of the grader, and it is the grader's limit rather than the
board's: `platform-aut-in` reads as `unclear` to the classifier and fails its
target plainly to a reader, because impersonal advice is a response to "takes
the edit as its own work" rather than an absence of one.

## What grading these turned up, which matters more than the grades

`evalkit.coverage` globbed `annotations.yaml` exactly, so every
`annotations.<grader>.yaml` was invisible to it. The report claimed **119
ungraded cases**. 103 of them already carried a label in
`evaluations/split-candidates-2026-09-08/annotations.kai.yaml`.

Corrected in the same commit as these grades:

```
before   ungraded 119   orphaned 0
after    ungraded   3   orphaned 2
```

The three: `gamedev-aut-in` above, plus `platform-fit-analyst` and
`sysadmin-fit-analyst`, whose target seat is archived. The two orphans,
`platform-fit-sysadmin` and `sysadmin-fit-director`, are adjacency edges Kai
graded that the roster no longer derives. That drift was real the whole time and
the narrow glob hid it.

**This retires the argument that built the autonomy grader.** "105 cases waiting
on the operator" was the reason given for automating this grading, in
`housecast#111` and on the tracker record. The board was already graded. The
queue the grader was built to drain did not exist.
