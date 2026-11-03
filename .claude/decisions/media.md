# Media: file storage

## Each media bucket gets a port shaped by what the flow needs from it
- `PrivateStoragePort` (signed upload, head, read) and `PublicStoragePort` (put) both extend
  `BaseObjectStoragePort` (delete). One `S3ObjectStorage` implements all of them; the component binds two
  instances to their buckets and registers them under the two role ports. Services receive
  `private_storage` / `public_storage`.
- Why: which bucket a service may touch is fixed by its types, not by discipline — an upload service cannot sign a
  link into the public bucket, which guards the invariant that nothing with EXIF/GPS lands there. The base port
  keeps the shared operations declared once; implementation and test fake stay single classes.
- Rejected: one `ObjectStoragePort` with an instance per bucket behind a `MediaStorage(staging, public)` registry
  holder (until 2026-10-30) — the holder is wiring that leaks into the port module, and any service handed the
  port can address whatever bucket it was given without its type saying which role it plays.
- Rejected: one instance with the bucket passed per call as an enum — any service can address any bucket.
- Rejected: `PrivateS3ObjectStorage` / `PublicS3ObjectStorage` implementation subclasses — the S3 requests are
  identical; the split belongs in the contract, not in the adapter. The public URL is not a storage concern: a
  separate URL builder owns it, so a Cloudflare Worker can later replace it.
- Revisit when: a second bucket with the same role appears — then one role port has two instances again.
- Source: plan media-storage-adapter (#27), 2026-10-30

## The local S3 emulator is RustFS
- The dev and e2e stacks and the integration tests run against RustFS; production runs on Cloudflare R2.
- Why: with root keys from the environment it enforces the presigned PUT signature out of the box — signed
  Content-Type, Content-Length and `If-None-Match` — and supports a bucket policy for anonymous read and bucket
  CORS. Checked by a probe on the live image.
- Rejected: Floci — verifies signatures only with a key issued by its own IAM plus an enforce flag (a foreign key
  passes with a broken signature, so tests go green on a lie), and did not enforce the signed size limit. Both
  from experience in ai-recap, not re-measured here.
- Rejected: MinIO — the community edition is archived and `minio/minio` is gone from Docker Hub.
- Rejected: Garage — needs a cluster layout initialised by hand before the first bucket.
- Revisit when: an image bump stops RustFS enforcing one of those checks, or #31 finds it diverging from R2.
- Source: plan media-storage-adapter (#27), 2026-10-30

## Emulator bucket setup lives in `backend/devtools/`, outside the `app` package
- `devtools.storage_bootstrap` creates the buckets, the staging CORS rule and anonymous read on the public bucket;
  the dev and e2e compose one-shots and the integration-test fixture run the same function. Production R2 is
  configured by hand (#31), with this module as the description of what the buckets must look like.
- Why: one implementation for every emulator environment, and code that never runs in production stays out of the
  wheel and the `final` image by construction — both carry only `app`.
- Rejected: a module in `app/media/infra/` — ships code into the production image that never runs there.
- Rejected: a shell script with aws-cli in `ops/` — the integration tests would need a second, Python copy of the
  setup and would check a setup compose does not run.
- Rejected: running the bootstrap against R2 — needs admin credentials on a server where the app only needs object
  read and write, and R2 serves public reads through a custom domain, not a bucket policy.
- Revisit when: production buckets get declarative configuration (OpenTofu/Terraform).
- Source: plan media-storage-adapter (#27), 2026-10-30

## A missing object is any 404, for HEAD and GET alike
- `head_object` answers `None` and `get_object` raises `ObjectNotFoundError` on a 404, whatever its error code.
- Why: a HEAD response has no body, so a missing bucket and a missing object look the same there; GET follows the
  same rule so that "no object" means one thing across the port. A missing bucket is a configuration fault, not a
  case a use case branches on. Nothing catches it yet: the bootstrap runs only against emulators and the app never
  checks its buckets; the HEAD that confirms an upload meets it before any GET does.
- Rejected: telling `NoSuchBucket` from `NoSuchKey` on GET (until 2026-11-02) — protects nothing while HEAD answers
  `None` to a missing bucket.
- Source: external failure classification (#33), 2026-11-02

## The S3 adapter is unit-tested through `AioStubber`, its storage semantics against RustFS
- Unit tests drive the real aiobotocore client with `aiobotocore.stub.AioStubber` in place of the transport;
  integration tests cover what only a real store shows (signature enforcement, 412 on overwrite, anonymous read).
- Why: the coverage gate counts unit and api tests only. The stubber validates parameters and responses against
  the S3 model, so a test cannot pass on a request S3 would reject, and it reaches error branches (403, 5xx) an
  emulator cannot produce.
- Rejected: integration tests only, with the adapter omitted from coverage — error branches stay untested, and it
  opens the first coverage exemption for code that is not an entrypoint.
- Rejected: a hand-written fake client — describes S3 as we imagine it and drifts from the real API.
- Rejected: `moto` — a second emulator beside RustFS, with divergences of its own.
- Source: plan media-storage-adapter (#27), 2026-10-30
