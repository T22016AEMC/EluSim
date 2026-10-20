# V1 data boundary

Anonymous projects are stored only in the visitor's browser and exported on demand. The backend serves a public generic column/model catalog; it has no shared project-list/read endpoint. No SQLite file is used as a fictitious multi-user production database.

Future authenticated persistence should use an owner-scoped repository layer and SQLite in development / PostgreSQL in production. Enforce owner_id on every project read/write and migrations before enabling server project storage. Non-small-molecule representations and parameter provenance remain in the versioned API schema today.
