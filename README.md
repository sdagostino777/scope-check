# scope-check

Ask HackerOne the only question that matters before you read a line of code: **is this asset
active and payable today?**

HackerOne's GraphQL mixes active and archived scopes unless you pass `archived: false`. That one
detail has cost two wrong decisions here, in opposite directions:

- an asset treated as "in scope" had been **archived six months earlier**;
- another was written off as "no victim" when the asset itself had been **archived a year before** —
  the real blocker was never the victim.

This prints the active, payable assets and, right under them, the archived ones that still look
tempting.

```
$ python3 scope_check.py example_program
Example Corp (example_program) · submission_state=open · offers_bounties=True

ACTIVE (archived:false) — 3
  URL          app.example.com                  sev=critical  PAYABLE
  URL          api.example.com                  sev=critical  PAYABLE
  WILDCARD     *.example.dev                    sev=none      not payable

ARCHIVED but still looks in scope — do not hunt here (2)
  SMART_CONTRACT https://github.com/example-org/contracts-runtime   archived 2025-01-15
  WILDCARD     *.example-legacy.app            archived 2025-06-25

OK — 2 payable asset(s)
```

## Use

```
python3 scope_check.py <handle>            # table + verdict
python3 scope_check.py <handle> --json     # machine-readable
python3 scope_check.py <handle> --grep api # filter
python3 scope_check.py <handle> --quiet    # verdict only, for scripts
```

Exit codes are the point: `0` = at least one payable asset, `1` = none, `2` = API/input error. So:

```bash
python3 scope_check.py some_program || echo "skip this programme"
```

## Notes

- No dependencies, no credentials: the queries are public.
- `eligible_for_bounty` and `eligible_for_submission` are reported separately — an asset can be
  listed and still pay nothing.
- Programs change scope silently. Run this the day you start, not the day you found the bug.

MIT.
