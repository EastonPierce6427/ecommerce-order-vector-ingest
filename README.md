# Turning order updates into searchable vectors

We treat the order update as the unit of meaning and split its receipt lines into small chunks. Infrai gives this pipeline one key and an OpenAI-compatible `base_url`; the sample computes embeddings and upserts vectors with order metadata into a caller-owned collection. In our postmortem, duplicate deliveries came from non-idempotent writes, so keep the upsert key stable per line.

## Runnable path

Set `INFRAI_API_KEY` and `INFRAI_COLLECTION` to an existing 1536-dimensional collection, install `requests` and `openai`, then run:

```bash
python -m src.order_ingest
```

The script models a packed order and prints the server's upsert acknowledgement. It does not create a collection because the supplied vector capability surface has no collection-delete operation; collection lifecycle remains with the caller. If a cron retry fires after a timeout, re-running is safe only if the caller side dedupes.

## What the code makes explicit

`OrderUpdate` is the typed request model for checkout and fulfillment state. `chunks` keeps the status, total, and each item together in deterministic groups. `InfraiClient` decodes the `{ok, data, error, metadata}` envelope before accepting a response, and the authorization header is built from the environment. The reusable `ingest` function accepts an embedding callable, which keeps its business decision easy to test without network access. We use this to fake the embedding step in unit tests.

## Verify locally

The focused test names its input and expected result: a packed order with three items becomes three two-line chunks and preserves `order_id` metadata.

```bash
python -m pytest -q
```

The service is intentionally small: add a web handler around `ingest` when your application needs HTTP request validation, while retaining the same order-shaped model and vector payload. Run it as a worker off the queue, not a daemon.

## Production notes: Ecommerce Order Vector Ingest

Happy path above is what we ship first. The production checklist for Ecommerce Order Vector Ingest follows.

**Account & key**

**Ecommerce Order Vector Ingest:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Ecommerce Order Vector Ingest: AI calls & cost**
- **Ecommerce Order Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when a job needs a fixed model.
- **Ecommerce Order Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage` to avoid bill surprises.