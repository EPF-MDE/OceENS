# The candidate seam: `llm_client.py`

If this application is ever going to need a second implementation of something,
the first place to look is `oceens.services.llm_client`, behind the summaries
daemon. This file records that candidate and the facts around it. It is a note,
not a change: nothing here is implemented, no interface is introduced, no
wrapper is added and no call site is touched.

## What the seam holds

**How soon a closed survey's summaries are ready** — the delay between a
program manager pressing *Générer les résumés* on a closed survey and the last `Summary`
row of that survey leaving the pending state.

That delay is the property worth being able to change without rewriting the
application, and `llm_client` is where it is decided: every remote call the
daemon makes goes through this module, and the module owns the HTTP cache the
daemon runs on.

No target is stated here. Deriving one is the job of whoever proposes a change;
what this file gives them is the facts to derive it from.

## The facts

### Where *generate* queues its jobs

`POST /api/surveys/{survey_id}/generate-summaries`
(`oceens.routers.summaries.generate_summaries`) does not call a model. It
requires the survey to be closed (`status == 0`), sets `Survey.status = 2` to
lock it, and inserts one `Summary` row per distinct (question, module, teacher)
combination that has open-ended answers, each with `http_status = 0`. Then it
returns. The number of rows is therefore a property of the survey's data, not of
the request.

The `summaries` table *is* the queue. `http_status` carries both queue state and
result: `0` pending, `200` done, anything else a failure kept for diagnosis.

### How the daemon picks them up

`oceens.summaries_generator_daemon` is a separate process, started by hand. Its
loop takes the *first* row still at `http_status = 0`, processes it to
completion, and starts again; when no row is pending it sleeps
`POLL_INTERVAL_SECONDS` before looking again. So the work is strictly serial:
one provider call at a time, for the whole installation, and a survey's total
time is the sum of its rows' times plus up to one poll interval before the first
one is noticed.

Per row, the daemon resolves the prompt's provider (falling back to
`DEFAULT_PROVIDER_NAME`), checks the model is available, loads the verbatims,
and calls `ask_model` with `REQUEST_TIMEOUT_SECONDS` as the ceiling on that one
call. The model-availability check is memoised per `(provider, model)` for the
life of the process, so it costs one request, not one per row. Every exit path
goes through `finish_summary`, which writes a status other than `0` — a row
never stays in the queue.

### What the client caches

`build_cache_session` returns a `requests_cache.CachedSession` backed by
`cache_llm.db` on disk, and the daemon uses it for every call. Three properties
of it matter here:

- `allowable_methods=["GET", "POST"]` — generations are cached, not just model
  listings;
- `expire_after=NEVER_EXPIRE` — an entry is never invalidated by age;
- `match_headers=True` — the authorisation headers are part of the cache key, so
  two providers sharing a base URL do not collide.

The consequence: an identical prompt sent to the same provider with the same
headers is served from that file instead of being generated again, in the time a
SQLite read takes. This is why `_MIN_DURATION_FOR_RATE` exists — below that
threshold the measured duration is a cache hit, not a generation, and the
tokens/s figure it would produce is meaningless. Regenerating a survey whose
verbatims have not changed is therefore not a measurement of the model, and
deleting `cache_llm.db` is what makes it one again.

## Where it sits

`llm_client` is a public module of the `services` package, reachable as
`oceens.services.llm_client` — see `../README.md` for what that guarantees. Its
two callers are the daemon and the provider administration screens
(`oceens.routers.llm.providers`).
