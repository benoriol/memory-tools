# Task: remember

The main agent has dumped a (potentially long) free-form description of
what just happened in the session. Your job is to convert it into one or
more memory notes at appropriate abstraction levels and connect them into
the graph.

## Workflow

1. **Reflect.** What was the goal? What was tried? What worked / failed?
   What was decided, and why? What surprised the main agent?

2. **Generate candidates.** Look for:
   - `capture`: raw observations, one fact each
   - `lesson`: patterns extracted from observations
   - `principle`: reusable decision rules
   - `decision`: ADR-style records with reason
   - `experiment`: what was tried (set `outcome` in body if failed)
   - `incident`: surprising failures
   - `archaeology`: explanations for current code shape (use `anchors`)
   - `transition`: "project used to be X" records
   - `next_step`: open follow-up implied by today's work

   A typical dump yields 0–3 captures, 0–2 lessons, maybe 1 principle,
   maybe 1 decision, 0–3 next_steps.

3. **Connect.** For each candidate, call `search` for nearby existing
   notes and `neighbors` on the closest ones. Decide per candidate:
   - **NEW**: write it, propose edges (generalizes / derived_from /
     coupled_with / applies_to / related)
   - **UPDATE**: skip writing; the existing note already covers this
   - **CONFLICT**: write the new note AND call `supersede(old, new, reason)`

4. **Write.** Use `capture_batch` so cross-references resolve in one
   commit. Use "@1", "@2" placeholder ids inside the batch.

5. **Respond.** Return a short structured summary:
   - `written`: list of {id, kind, title}
   - `superseded`: list of {old_id, new_id, reason}
   - `clarifications_needed`: list of free-text questions (empty if none)
   - `notes`: short prose summary

Do not narrate your tool calls. The main agent only sees your final
response, so put what matters there.
