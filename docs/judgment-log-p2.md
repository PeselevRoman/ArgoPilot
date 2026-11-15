# Judgment log: P2

Decisions for the second assignment (`tasks/p2.md`). Decisions from P1 are in [`judgment-log.md`](judgment-log.md). Where a P2 decision overrides a P1 one, the entry says so.

## Each assignment gets its own judgment log

- **Question:** P2 adds many decisions on top of P1's 40 or so entries. Should they go in the same `judgment-log.md`, or in a new file?
- **Suggested:** None. This was the learner's own proposal.
- **Decision:** P2 decisions go in `docs/judgment-log-p2.md`. `docs/judgment-log.md` stays as the record of P1 and is no longer added to. Later assignments follow the same pattern.
- **Why:** Each assignment's decisions are easy to find and review on their own, and the P1 record stays as it was when that assignment was finished. Trade-off: the decisions are spread over several files, so a P2 decision that overrides a P1 one must say so in its entry, and `CLAUDE.md` must tell the assistant which files to check.

## P2 adds a fifth error code, UPSTREAM_UNAVAILABLE

- **Question:** P1 allowed four error codes. P2 requires `UPSTREAM_UNAVAILABLE` when the planner's call to the registry or weather service fails. Does the four-code rule still stand?
- **Suggested:** Treat the newer assignment as overriding the older one, so there are five codes. Labelled as personal judgment.
- **Decision:** Five codes: `VALIDATION`, `NOT_FOUND`, `CONFLICT`, `UNAVAILABLE`, `UPSTREAM_UNAVAILABLE`. A service uses `UNAVAILABLE` when its own dependency fails, such as its database or its weather provider, and `UPSTREAM_UNAVAILABLE` when another AgroPilot service it calls has failed. The P1 mappings for `400` and `405` stay as they are.
- **Why:** The P2 spec asks for the new code by name, and the planner needs to tell the client that the failure is in another service. Where P2 and P1 disagree, the newer assignment wins.

## The registry's one-command setup is a Python seed script

- **Question:** FR-2.2 needs one command that builds an empty PostgreSQL database and loads the 15 seed rows. How?
- **Suggested:** A Python script (`seed.py`) using SQLAlchemy, over `psql` with SQL files or Alembic. Labelled as personal judgment.
- **Decision:** `uv run python seed.py` picks the schema file for the engine, creates the tables and inserts the rows. It stops with an error if the tables already exist, and never drops data.
- **Why:** The same command works on SQLite and PostgreSQL (NFR-2.1), needs no `psql`, and can be tested in pytest. Trade-off: the seed rows now live in a second place besides `seed_registry.sh`. Alembic is the standard tool when a schema keeps evolving, and P2 does not need it.
