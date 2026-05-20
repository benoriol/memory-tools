# Task: remember

The main agent has dumped a (potentially long) free-form description of
what just happened in the session. Convert it into one or more memory
notes and connect them into the graph.

## Workflow

1. **Reflect.** What was the goal? What was tried? What worked / failed?
   What was decided, and why? What surprised the main agent? Did the
   user say anything substantive (vision, constraint, preference, plan)?

2. **Decompose.** Slice the dump into discrete pieces of knowledge.
   Don't pad — only write what's worth recalling later.

3. **For each piece, pick a `kind` label.** Use whatever describes it
   best. Common choices:

   - `observation` — something we noticed
   - `experiment` — something we tried (note the outcome in the body)
   - `mistake` — something we got wrong
   - `bug_fix` — a bug we fixed (cause + resolution)
   - `decision` — a choice we made and why
   - `principle` — a reusable rule (rare; only when truly general)
   - `former_state` — the project used to be this way
   - `user_said` — the user stated this directly

   New labels are fine if none of the above fit.

4. **Connect with abstraction edges where appropriate.** When two
   notes in the batch are at different abstraction levels (raw
   observation vs. distilled lesson; concrete experiment vs.
   generalized principle), draw an `abstracts` edge from the **more
   abstract** to the **more concrete** one:

   ```
   capture_batch([
     {note_id: "@1", kind: "experiment", title: "Tried X at lr=0.01", ...},
     {note_id: "@2", kind: "principle", title: "Default lr=0.01 for this family",
      edges: [{to: "@1", type: "abstracts"}]},   # principle @2 abstracts @1
   ])
   ```

   Use `related` for lateral connections (same domain, no abstraction
   claim). Skip edges entirely if there's nothing meaningful to say.

5. **Handle conflicts.** If a new note contradicts an existing one in
   the graph, call `supersede(old_id, new_id, reason)`. Don't silently
   overwrite — the old note stays for history but goes
   `status: superseded`.

6. **Detect "user said" inputs specifically.** If part of the dump
   describes something the user told the agent (a goal, a preference,
   a hard constraint, a vision), capture it as `kind: user_said`.
   These notes deserve more weight at retrieval time and should not be
   superseded by your own observations without an explicit go-ahead.

## Response shape

Return a short structured summary:

- `written`: list of `{id, kind, title}` for each new note
- `superseded`: list of `{old_id, new_id, reason}`
- `clarifications_needed`: list of free-text questions (empty if none)
- `notes`: 1–3 sentence prose summary

Do not narrate your tool calls. The main agent only sees your final
response.
