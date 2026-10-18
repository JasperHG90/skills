---
name: httpx-for-http
description: Make HTTP calls with httpx2 rather than urllib or requests, on a reused client with an explicit timeout and jittered retries. Read before writing code that talks to an HTTP API.
applyTo: "**/*.py"
---

<constraint name="one-client-explicit-timeout">
HTTP calls go through `httpx2`, not `urllib.request`, `http.client`, or
`requests`. Create one `Client` (or `AsyncClient`), reuse it as a context
manager, and set the timeout explicitly rather than inheriting the default.
</constraint>

`httpx2` is Pydantic's maintained continuation of `httpx`, forked from
`httpx` 0.28.1. The only public API change is the package name: `import httpx2`,
`httpx2.Client`, `httpx2.Timeout`, the `httpx2` CLI. Upstream `httpx` last
shipped a stable release in December 2024 and its `master` branch has moved
only sporadically since; `httpx2` is where fixes and security updates land. It
requires Python 3.10+.

`urllib` and `http.client` leave you owning JSON encoding, headers,
query-string building, and error classification. `requests` covers those but is
sync-only, so an async fan-out becomes a rewrite; `httpx2` is one API for both,
and its `MockTransport` mocks it offline (see the python-testing rule).
Module-level `httpx2.get` builds and tears down a client per call, losing the
connection pool along with your shared headers and base URL.

<example name="client">
```python
import httpx2

with httpx2.Client(base_url=API, headers=auth, timeout=10.0) as client:
    response = client.get("/releases")
    response.raise_for_status()
```
</example>

The default timeout is 5 seconds on connect, read, write, and pool alike — too
tight for a slow report, too loose for a health check. A bare float sets all
four. To vary them, pass a default alongside the override —
`httpx2.Timeout(30.0, connect=5.0)`. A partial set such as
`httpx2.Timeout(connect=5.0, read=30.0)` raises `ValueError`, because it leaves
the other two phases undefined.

Retry with `tenacity`, not `HTTPTransport(retries=...)`, which retries only
connection failures and returns a 500 on the first try. Retry idempotent
requests on explicit 429 and 5xx, never a blind `except`, and use
`wait_exponential_jitter` so a fleet of clients does not resynchronize its
retries. A 429 usually carries `Retry-After`; tenacity has no built-in for it,
so honor it with a custom `wait`.

Parse the body into a Pydantic model (see the pydantic-boundaries rule). For
many concurrent calls, see the async-python rule.
