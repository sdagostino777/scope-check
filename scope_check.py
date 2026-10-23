#!/usr/bin/env python3
"""scope_check.py — is this HackerOne asset actually active and payable *today*?

HackerOne's GraphQL mixes active and archived scopes when you do not pass
`archived: false`. That one detail has burned two bug-bounty decisions this
workspace knows of, in opposite directions:

  * an asset reported as "in scope" had been archived six months earlier;
  * another was written off as "no victim" when the asset itself had been
    archived a year before — the real blocker was never the victim.

This tool asks both questions. It prints the active, payable assets and, right
under them, the archived ones that still look tempting.

  python3 scope_check.py yuga_labs
  python3 scope_check.py yuga_labs --json
  python3 scope_check.py yuga_labs --grep borde
  python3 scope_check.py yuga_labs --quiet        # only the verdict, for scripts

Exit codes: 0 = at least one active payable asset; 1 = none (do not hunt);
2 = API or input error.

No dependencies, no credentials: these queries are public.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://hackerone.com/graphql"
UA = "scope-check/0.1 (https://github.com/)"

QUERY = """query { team(handle:"%(handle)s") {
  handle name submission_state offers_bounties
  structured_scopes(first:%(n)d, archived:%(arch)s) {
    edges { node {
      asset_identifier asset_type eligible_for_submission eligible_for_bounty
      max_severity archived_at
    } } } } }"""

FIELDS = ("asset_identifier", "asset_type", "eligible_for_submission",
          "eligible_for_bounty", "max_severity", "archived_at")


def query(handle, archived, n=100):
    body = json.dumps({"query": QUERY % {"handle": handle, "arch": "true" if archived else "false", "n": n}})
    req = urllib.request.Request(ENDPOINT, data=body.encode(),
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          "Accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        payload = json.loads(r.read())
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"])[:300])
    team = (payload.get("data") or {}).get("team")
    if team is None:
        raise RuntimeError(f'programme "{handle}" not found (wrong handle, or the programme is private)')
    edges = ((team.get("structured_scopes") or {}).get("edges") or [])
    return team, [e["node"] for e in edges]


def classify(scopes):
    payable, submission, other = [], [], []
    for s in scopes:
        if s.get("eligible_for_bounty") and s.get("eligible_for_submission"):
            payable.append(s)
        elif s.get("eligible_for_submission"):
            submission.append(s)
        else:
            other.append(s)
    return payable, submission, other


def main(argv):
    ap = argparse.ArgumentParser(add_help=True, description="Is this HackerOne asset active and payable today?")
    ap.add_argument("handle", help="HackerOne programme handle, e.g. yuga_labs")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--grep", default=None, help="only assets whose identifier contains this substring")
    ap.add_argument("--quiet", action="store_true", help="print only the verdict line")
    a = ap.parse_args(argv)

    try:
        team, active = query(a.handle, archived=False)
        _, archived = query(a.handle, archived=True)
    except (urllib.error.URLError, RuntimeError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if a.grep:
        g = a.grep.lower()
        active = [s for s in active if g in str(s.get("asset_identifier", "")).lower()]
        archived = [s for s in archived if g in str(s.get("asset_identifier", "")).lower()]

    payable, submission, other = classify(active)

    if a.json:
        print(json.dumps({
            "team": {k: v for k, v in team.items() if k != "structured_scopes"},
            "active": active, "archived": archived,
            "payable_count": len(payable),
        }, indent=2))
    elif not a.quiet:
        print(f"{team.get('name')} ({team.get('handle')}) · "
              f"submission_state={team.get('submission_state')} · offers_bounties={team.get('offers_bounties')}")
        print(f"\nACTIVE (archived:false) — {len(active)}")
        for s in active:
            tag = "PAYABLE" if s in payable else ("submission-only" if s in submission else "not payable")
            print(f"  {str(s.get('asset_type')):<12} {str(s.get('asset_identifier'))[:56]:<56} "
                  f"sev={str(s.get('max_severity')):<9} {tag}")
        if not active:
            print("  (no active assets)")
        archived_bounty = [s for s in archived if s.get("eligible_for_bounty")]
        if archived_bounty:
            print(f"\nARCHIVED but still looks in scope — do not hunt here ({len(archived_bounty)})")
            for s in archived_bounty[:12]:
                when = str(s.get("archived_at") or "")[:10]
                print(f"  {str(s.get('asset_type')):<12} {str(s.get('asset_identifier'))[:56]:<56} archived {when}")

    verdict = f"OK — {len(payable)} payable asset(s)" if payable else "STOP — no payable asset, do not hunt here"
    print(verdict)
    return 0 if payable else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
