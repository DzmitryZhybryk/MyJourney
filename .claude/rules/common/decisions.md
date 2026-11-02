# Decision records

Settled design decisions live in `.claude/decisions/`, one file per area. Before changing how an
area below behaves, or proposing an alternative to how it works, read its file: the alternative
may already have been rejected. Writing or changing an entry: skill `decision-records`.

| File | Questions it answers |
|---|---|
| `accounts.md` | which domain stores email, username and the profile; what a valid token without an account gets; how registration spans auth and users; where user preferences live |
| `domains.md` | whether tables of different domains may reference each other; where an HTTP status is decided |
| `geo.md` | how a city differs from a place and why they are separate; what a journey stores about a city and where names come from; how gazetteer names are stored per language; where gazetteer data comes from and what a provider must allow |
| `journeys.md` | what one journey record represents; what date a journey carries |
| `media.md` | how many storage ports the media buckets get and how code reaches each bucket; which S3 emulator the dev stack and tests use; where emulator bucket setup lives and how production buckets are configured; how the S3 adapter is tested |
| `frontend.md` | where icons come from |
| `backend.md` | how the process reads its settings; whether anything but the settings module may build `Settings`; where the backend version comes from; which changes to `openapi.json` count as a contract change for the backend version; whether the `openapi.json` snapshot carries the backend version; what the exception tree branches on; where a broken own assumption goes; how the log lines of one request are joined; how a handled error reaches the request log line; whether the edge accepts an incoming trace context |
