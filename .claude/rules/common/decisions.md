# Decision records

Settled decisions live in `.claude/decisions/`, one file per area. Before changing an area below
or proposing an alternative, read its file: the alternative may already have been rejected.

| File | Questions it answers |
|---|---|
| `accounts.md` | which domain stores email, username and the profile; what a valid token without an account gets; how registration spans auth and users; where user preferences live; how one-time codes are resent, stored and locked out; how access and the first admin work; how other domains see role and plan |
| `permissions.md` | how a route checks a permission; how one is named; what `user` gets; what a missing one answers |
| `admin.md` | where admin routes live; admin schemas and names; whose rows an admin route may read; the SPA admin |
| `backoffice.md` | where a cross-domain operator screen reads; what `backoffice` may call |
| `config.md` | how a domain stores, seeds, edits config |
| `domains.md` | whether tables of different domains may reference each other; where an HTTP status is decided; what PUT and PATCH answer; how others learn of a change; what an event carries |
| `geo.md` | how a city differs from a place; what a journey stores about a city and where names come from; how gazetteer names are stored per language; where gazetteer data comes from and what a provider must allow |
| `journeys.md` | what one journey record represents; what date a journey carries |
| `media.md` | how code reaches each media bucket; which S3 emulator is used; where bucket setup lives; what counts as a missing object; how the S3 adapter is tested; the media config shape |
| `scripts.md` | where scripts live and what they may import |
| `frontend.md` | where icons come from; how a value that can be edited in place is told apart from a read-only one; where dev Vite runs |
| `backend.md` | how the process reads its settings; who may build `Settings`; where the backend version comes from; what in `openapi.json` counts as a contract change, and whether its snapshot carries the version; what the exception tree branches on; where a broken own assumption goes; who classifies an external failure and who retries it; which failures a background task retries; how a task honours a dependency's retry delay; what a server-fault response carries; when a 503 carries `Retry-After`; how the log lines of one request are joined; how a handled error reaches the request log line; whether the edge accepts an incoming trace context; which event loop integration tests run in and how their schema is created; where the one-shot steps before app start live; which tables carry a row version; keyset vs offset paging |
