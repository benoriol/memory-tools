## Long-term memory (`memory-recall` MCP)

This project has the `memory-recall` MCP server configured. Five
tools are available — see their docstrings for full mechanics. This
section is operating guidance, not duplicate documentation.

### When to capture

You decide. There's no policy. The cost is low and the value is
asymmetric — one un-captured finding can cost an hour to
rediscover. Capture freely. Good candidates:

- Bug root causes, especially non-obvious ones
- Architectural facts not visible from any single file
- Contracts with external systems (APIs, file formats, env vars)
- Decisions and their rationale — especially ones that closed off
  alternatives
- Benchmark / experiment results
- Things a teammate told you that aren't written down anywhere

### What to put in a memory body

Be generous with detail. A sub-agent generates the title, summary,
keywords, and paraphrases at capture time, so the body itself is
free to be long and concrete. Useful things to include:

- Bottom-line answer up front
- Pointers: file paths with line numbers, function names, test
  cases, related commit SHAs
- Error codes and exception messages (verbatim — they're how
  future-you will search for the same problem)
- Quantitative results: numbers, measurements, before/after
- Code snippets that illustrate the point
- Counter-examples — things that *don't* work
- Why this matters / what it unblocks

The summary is what future sessions see first via
`memory_retrieve_candidates`; the body is what they get when they
call `memory_get`. Detail in the body is never wasted — it isn't
sent unless explicitly requested.

### How to retrieve (two-step)

When about to spend non-trivial effort on something the project
might already know about, try `memory_retrieve_candidates(query)`
first.

1. Send an open-ended query — a question, a task description, a
   bug report, an error message, a half-formed thought. You get
   back candidate summaries (no bodies). Cost is small even at
   k=20.
2. Read the summaries. For the 0–2 that actually look relevant,
   call `memory_get(ids=[...])` once with all of them in a single
   batched call. Most queries don't need step 2 at all.

Don't burn step 2 on weak candidates — the summary alone is enough
to disqualify.
