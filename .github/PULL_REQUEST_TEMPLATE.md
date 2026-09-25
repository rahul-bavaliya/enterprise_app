## What this changes

**Parts catalog and work order line items.** Work orders need billable
materials, so parts are modelled as a reusable catalog rather than duplicated
per work order:

- `part` — unique `part_number`, description, manufacturer, unit of measure,
  `list_price` stored as `Numeric(12,2)` and handled as `Decimal` throughout
- `work_order_part` — line items joining a work order to a part with
  `quantity` and a `unit_price` **snapshot**, so a later catalog price change
  never rewrites the history of work already done

**Unified response contract.** Every non-auth endpoint now returns
`ResponseEnvelope` on both success and failure:

```jsonc
// success
{ "success": true,  "data": { ... }, "message": "..." }
// failure
{ "success": false, "data": null,    "message": "Work order not found" }
```

New central handlers in `app/core/exceptions.py` cover validation, HTTP,
database integrity, SQLAlchemy and unexpected errors. Tracebacks and raw
database text stay server-side; clients only ever see an opaque message.

**Performance.** The work order parts listing issued one query per line item
(1+N); it is now a single `JOIN`. Connection pooling is tuned
(`pool_size`, `max_overflow`, `pool_recycle`, `pool_use_lifo`) and indexes
match the filter and sort paths the list endpoints actually use.

## Breaking changes

> **Clients must be updated before this merges.**

| Before | After |
|---|---|
| `response.json().title` | `response.json().data.title` |
| `response.json().detail` | `response.json().message` |
| items list: `data: [...]` | `data: { data: [...], count }` |

Authentication contracts are unchanged: `login`, `users` and the password
recovery/reset routes keep their existing shapes.

## Migrations

Run in order before serving traffic from this branch:

1. `c4d9e6b3f8a2` — creates `part` and `work_order_part`
2. `d7a1f4c9b2e5` — adds query indexes

## Verification

- 112/112 tests pass (`pytest tests/`)
- `ruff check` and `ruff format --check` clean
- `test_response_envelope.py` walks the generated OpenAPI and fails if any
  non-auth operation declares a non-envelope schema, so the contract cannot
  silently regress
- Verified live in Docker: 200/403/404/422 all return the envelope, and a
  work order with 5 part lines resolves in a constant number of queries

## Notes for reviewers

- Parts are deactivated rather than deleted (`DELETE /parts/{id}` sets
  `is_active = false`); the `RESTRICT` FK backs this so work order history
  can never be orphaned.
- Adding the same part twice increases quantity rather than creating a
  duplicate line.
- Inactive parts and voided work orders reject new line items with 409.
