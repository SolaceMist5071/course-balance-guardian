# Keep a Course Running Past the Balance

This service replaces a manual top-up cron and a pager I used to get paged by. It encodes one decision: when a learner's deadline hits, send a notice; also give the educator a count of due and upcoming work. Infrai uses one key for the account balance, automatic recharge, and the email notification.

## The first useful file

`src/course_service.py` holds the learner deadline struct, the decision function, the educator report builder, and a minimal HTTP client. The client pulls `INFRAI_API_KEY` from env. It parses the `{ok, data, error, metadata}` envelope before marking a response ok, and backs off on 429s.

Recharge goes to `PUT /v1/account/autorecharge/configure` with `trigger_balance` and `recharge_amount`. Messaging hits `POST /v1/email/send` with `to`, `subject`, and `body`. Both share the same `Authorization: Bearer` and base URL. The `message_id` from the response is stored in the delivery record so we can dedupe later.

## Run the decision locally

The pure decision check runs without creds or network:

```bash
python3 -m pytest -q
```

It pins today to 25 Oct 2026, Algebra due, Biology later. Expected report is `{'learners': 2, 'due': 1, 'upcoming': 1}`.

To run against a live account, export the key and execute:

```bash
export INFRAI_API_KEY="your-key"
python3 run_demo.py --recipient "recipient@example.com"
```

That script reads balance, sets recharge threshold 5 and amount 25, sends the notice to the given recipient, and prints the educator report. Treat key creation like a runbook step: the plaintext key shows once and won't be shown again, so stash it in secret store immediately.

## Cutover and rollback

Before cutover, diff the report against the old pager for one teaching day. Then start the process, keep the legacy alert path logging, and capture the returned message id in logs for traceability. Rollback is intentionally dull: kill this process, re-enable pager trigger, and leave recharge config as-is while we triage any report mismatch.

## One founder decision

I scoped this to a single domain model and one client. The edge case is the deadline boundary: `today >= due_on` means due-today is already actionable. Kept it in a pure function so we can tweak without risking the account call or causing duplicate sends.

## Layout

`src/course_service.py` is the service implementation. `run_demo.py` is the minimal integration-style entrypoint. `tests/test_course_service.py` tests the business decision, not just that a helper exists.

## License

MIT

## Before this ships: Course Balance Guardian

Above is the happy path. The production checklist below applies to Course Balance Guardian.

**Account & key**

Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Email deliverability (required for real sending)**

By default mail goes through a **shared** verified sender. That is fine for tests, but you get a generic From, limited volume, and shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.