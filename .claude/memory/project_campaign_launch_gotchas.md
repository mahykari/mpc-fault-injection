---
name: project_campaign_launch_gotchas
description: Two traps when launching a campaign — --runs is per grid point, and campaign.db reattaches instead of starting fresh
metadata:
  type: project
---

Both of these bite silently; neither errors.

**`--runs` is per grid point, not the campaign total.** `dispatch.py --runs N`
feeds `CampaignPlan.runs_per_config`, and `total_runs = len(grid_points) * N`.
The default grid is 3 protocols x 4 party counts = 12 points, so `--runs 1000`
queues 12,000 experiments. For a small sanity run, shrink the grid with
`--protocols` / `--party-counts` and size `--runs` against what is left.

**A new campaign reattaches to the old one.** `continuous.py` hardcodes
`DISPATCH_DB = /app/runs/campaign.db`, and `populate()` is `INSERT OR IGNORE`
by design so a restarted dispatcher rejoins a live campaign rather than cloning
it. The consequence: launching a "new" campaign while `runs/campaign.db` still
holds the old one just hands workers the old pending rows. The 2026-08-06 file
had ~1.69M of them. Move it to `campaign-archived-<stamp>.db` first — the
existing archives in `runs/` are that same move done by hand.

Rebuild before launching: the worker image bakes the repo into `/app`, so code
changes need `./containers/build.sh pipeline` (and `dispatch` if anything under
`pipeline/store.py`, `campaign.py`, or `wire.py` moved).
