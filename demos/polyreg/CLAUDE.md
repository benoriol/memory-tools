# Demo task: polynomial regression hyperparameter sweep

You have a tiny self-contained experimental task. The dataset is
provided by `data.py`. The signal is `sin(2π x) + 0.3·cos(6π x)` for
`x ∈ [0, 1]`, plus Gaussian noise. Your job is to **find the best
polynomial degree for fitting it, and learn how that degree shifts
with noise.**

Use only numpy. Don't install anything.

## Concrete steps

1. **Look at the data.**
   - Load datasets at three noise levels: 0.05, 0.20, 0.50.
   - Record what you observe about each (range, std, anything else).

2. **Sweep polynomial degree** at each noise level.
   - For each `noise ∈ {0.05, 0.20, 0.50}` and each
     `degree ∈ {1, 3, 5, 7, 9, 11, 13, 15}`:
     fit a least-squares polynomial via `np.polyfit` on the training
     split, and compute mean-squared error on the validation split.
   - You may add a 20-second wall-clock budget per fit; in practice
     none of these takes more than a few ms.

3. **Find the best degree for each noise level.**
   - The one with lowest validation MSE.
   - Re-evaluate on the held-out test set (`data.held_out_test(noise=...)`)
     to confirm.

4. **Generalize.**
   - Is there a pattern in how the best degree shifts with noise?
   - State it concisely.

## Memory protocol — please use it generously

This project has the `memory-graph` MCP server wired in. Use it
liberally — the whole point of this run is to build a graph.

**After each step above**, call `memory_remember` with a thorough
dump describing what you did, what numbers you saw, what worked,
what surprised you. Examples of what to capture:

- **Observations**: about each dataset before fitting anything.
- **Experiments**: each `(noise, degree)` fit you ran, with the
  validation MSE you observed.
- **Mistakes / surprises**: anything that didn't behave as expected
  (e.g. very high degree blowing up, an unexpectedly low MSE for a
  low degree, a numerical-stability issue with `np.polyfit`).
- **Lessons**: patterns you notice across experiments (overfitting
  threshold, noise dependence).
- **Principles**: rules you'd carry to a similar task in the future.

When you write a principle that abstracts a lesson, include an
`abstracts` edge from the principle to the lesson (the principle is
the more abstract end; the edge points from principle to lesson).
Same for lessons that abstract specific experiments.

It's fine to call `memory_remember` 4–6 times during this task —
don't try to batch everything into one giant call at the end.

## Output

When you finish, print:
- The best polynomial degree at each noise level (with the test MSE).
- Your one-sentence answer to "how does the best degree shift with
  noise?"
- A short list of the memory ids you wrote (so the operator can find
  them in the viz).

Don't write code files unless you need to (a few `np.polyfit` calls
inline are enough). Stay under ~15 minutes of work.
