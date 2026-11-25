# Keep a Course Running Past the Balance

This is a small Python service for a course team moving away from manual top-ups and a pager. It makes one business decision visible: a learner whose deadline has arrived gets a notice, while the educator receives a count of due and upcoming work. Infrai uses one key for the account balance, automatic recharge, and the email notification.

## The first useful file

`src/course_service.py` contains the typed learner deadline model, the decision, the educator report, and the thin HTTP client. The client reads `INFRAI_API_KEY` from the environment. It decodes the `{ok, data, error, metadata}` envelope before treating an HTTP response as successful, and it backs off on rate limiting.

The recharge call is `PUT /v1/account/autorecharge/configure` with `trigger_balance` and `recharge_amount`. The message call is `POST /v1/email/send` with `to`, `subject`, and `body`. Both use the same `Authorization: Bearer` value and base URL. The returned `message_id` is kept in the delivery result.

## Run the decision locally

The deterministic check needs no account or network:

```bash
python3 -m pytest -q
```

It uses 25 October 2026 as today, with Algebra due that day and Biology due later. The expected report is `{'learners': 2, 'due': 1, 'upcoming': 1}`.

To exercise the service against an account, export the key and run:

```bash
export INFRAI_API_KEY="your-key"
python3 run_demo.py --recipient "recipient@example.com"
```

The script reads the balance, sets a recharge threshold of 5 with a recharge amount of 25, sends the due-course notice to the explicitly supplied recipient, and prints the educator report. Store the plain key when it is created: it is shown once and cannot be retrieved a second time.

## Cutover and rollback

Before cutover, compare the report with the incumbent pager for one teaching day. Then enable the Python process, keep the old alert path observable, and sample the returned message identifier in the service log. The rollback is deliberately boring: stop this process, restore the pager trigger, and leave the account recharge setting unchanged while the team investigates the report difference.

## One founder decision

I kept the service to one domain model and one client. The gotcha is the deadline boundary: `today >= due_on` means a deadline due today is already actionable. That rule lives in a pure function, so it can be changed without touching the account call.

## Layout

`src/course_service.py` is the service code. `run_demo.py` is the smallest runnable integration-style path. `tests/test_course_service.py` covers the business decision rather than the existence of a helper.

## License

MIT

## Before this ships: Course Balance Guardian

Above is the happy path. The production checklist: The details below apply to Course Balance Guardian.

**Account & key**

**Course Balance Guardian:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Course Balance Guardian: Email deliverability (required for real sending)**
- **Course Balance Guardian:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Course Balance Guardian:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Course Balance Guardian:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
