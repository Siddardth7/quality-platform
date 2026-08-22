# MCP tool contract (reference)

Level-3 detail for `quality-research`, kept out of `SKILL.md` per progressive disclosure: a
host loads this only when it needs the wire-level contract.

## `qdb_answer_question`

One tool (`apps/mcp/mcp_app/server.py`), added by M5-2 (#288) over M5-1's query engine.

Request:

```json
{"question": "Why is the ndc threshold 5?", "k": 5, "standard": null, "source_id": null, "region": null}
```

| Argument | Type | Meaning |
|---|---|---|
| `question` | `str`, required | the user's question, passed through unchanged |
| `k` | `int`, default 5 | how many chunks to retrieve |
| `standard` | `str` or null | narrow retrieval to one standard |
| `source_id` | `str` or null | narrow retrieval to one source document |
| `region` | `str` or null | narrow retrieval to one region of a document |

Pass a narrowing argument only when the user named one. Do not guess a `source_id`.

Response — exactly the `CandidateAnswer` fields
(`apps/quality_database/quality_database_app/generation_metrics.py`), nothing else:

```json
{
  "item_id": "msa-4e-ch2-d-0142",
  "text": "...the generator's own words, already quote-cap-enforced...",
  "cited_source_id": "aiag-msa-4e",
  "cited_region": "Ch. II Sec. D",
  "cited_page": 117,
  "refused": false
}
```

`cited_source_id`, `cited_region` and `cited_page` may each be null. Present the answer text
and whatever locator came back; never re-word a citation and never supply a page the tool did
not return.

## Order of operations, server-side

Retrieve → gate → generate → verify → enforce the quote cap, in that order. The refusal gate
runs on a measured cosine-score threshold **before** the generator does
(`quality_database_app/query.py`, `REFUSAL_SCORE_THRESHOLD`), so a refusal is deterministic,
not a model decision.

A refusal comes back as `refused: true` with `text` set to the fixed string:

> Not found in the corpus.

Report that string verbatim. Do not paraphrase it, and do not treat it as a failure — it is a
real answer ("this is not in the private corpus"), so no fallback runs after it.

## What the server will never return

The corpus never leaves the server. Only the answer text and one verified locator do. The
tool does not return, and this skill must never ask for or display:

- a retrieval hit list or per-chunk scores
- a raw chunk of source text
- the rendered prompt context
- any embedding vector

If an answer would need one of those to be defensible, that is a sign the endpoint should have
refused — say so rather than reaching around the tool.

## Error contract

| Condition | What comes back | What to do |
|---|---|---|
| No index built (or `QUALITY_DATABASE_CORPUS_OUT` points somewhere without one) | structured `ToolError` | surface the message verbatim, then fall back |
| `QDB_GENERATOR_IMPORT_PATH` unset or unresolvable server-side | structured `ToolError` | surface the message verbatim, then fall back |
| `QDB_MCP_URL` / `QDB_MCP_TOKEN` unset client-side | `KeyError` from the script | say the endpoint is not configured, then fall back |
| Endpoint unreachable / connection refused / timeout | transport-level exception | say the endpoint is unavailable, then fall back |
| Wrong or expired token | 401 / auth rejection from the transport layer | treat as unavailable, fall back — never print or echo the token |

Every one of these routes to the same local fallback
([`fallback-sources.md`](fallback-sources.md)). There is one failure branch, not five.

Note the generator's known limitation, stated in the tool's own docstring: because the
generator is resolved as a call argument, it must be configured to get *refusals* as well as
answers. An unconfigured generator therefore surfaces as a `ToolError`, not as a refusal.

## Transport and auth

This is the one tool in the catalog that is designed to be called over HTTP rather than the
stdio default the other skills use: it reads private data, so it is served from a host that
holds the corpus rather than launched as a local subprocess.

The client sends a bearer token over M1-8's HTTP transport (`apps/mcp/mcp_app/transport.py`).
Auth is **not** a second scheme layered on this tool — with `MCP_TRANSPORT=http` the shared
secret gates every tool on the server, this one included. `apps/mcp/README.md` puts it
plainly: "There is no second auth scheme and no per-tool check."

| Env var | Side | Meaning |
|---|---|---|
| `QDB_MCP_URL` | client (this skill) | the endpoint, e.g. `http://HOST:PORT/mcp` |
| `QDB_MCP_TOKEN` | client (this skill) | the bearer secret sent with each call |
| `MCP_AUTH_TOKEN` | server | what the server checks incoming bearer tokens against |

`QDB_MCP_URL` and `QDB_MCP_TOKEN` are the stable client-side contract for this skill (#289)
and are the names M6's remote-host wiring is expected to reuse — not placeholders. They are
deliberately distinct from the server-side `MCP_AUTH_TOKEN`.

`fastmcp` sends `Authorization: Bearer <token>` internally when the transport is constructed
as `StreamableHttpTransport(url=..., auth=token)`; no hand-rolled headers, and no place for
the token to end up in a user-facing string.
