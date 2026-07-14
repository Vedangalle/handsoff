# Hackathon Release Checklist

## Release boundary

The hackathon release remains package version `0.4.0` on branch `main`. It is a simulation-only application: no Home Assistant write adapter, live device actuation, public memory write surface, R3 capability, background worker, or multi-tenant persistence is included.

No Git tag or hosted release is required for the repository freeze. The reviewed commit on `origin/main`, Streamlit Community Cloud deployment, and submission assets form the release artifact.

## Automated freeze gates

Before pushing the release commit:

- [ ] `uv sync --frozen --all-extras`
- [ ] `uv run --frozen --all-extras python scripts/validate.py`
- [ ] native Streamlit `AppTest` covers staged, single-run, reset, isolation, and judge-comparison paths
- [ ] local browser confirms staged and judge-comparison layouts at desktop width
- [ ] `git diff --check`
- [ ] non-disclosing secret scan of Git-visible and staged content
- [ ] exact staged paths inspected
- [ ] no ignored or credential-bearing content staged
- [ ] `main` pushed directly and local `HEAD` verified against `origin/main`

The final handoff reports the observed test count, coverage, dependency-audit result, branch, commit, remote alignment, and Git status. Checkboxes are operational instructions; evidence belongs in the commit/push report rather than a mutable claim embedded in source control.

## Manual release gates

These steps require the repository owner or hackathon submission account:

- [ ] rotate any credential previously shared outside the provider secret store;
- [ ] add provider values only through ignored local secrets or Streamlit Community Cloud Advanced settings;
- [ ] complete the [live-provider acceptance procedure](hackathon-judge-guide.md#live-provider-acceptance);
- [ ] deploy `main` with entrypoint `streamlit_app.py` and Python 3.12;
- [ ] capture a live-provider comparison screenshot only after reviewing it for sensitive content;
- [ ] record the 90-second video using the [judge script](hackathon-judge-guide.md#ninety-second-demonstration);
- [ ] paste the reviewed [submission copy](hackathon-judge-guide.md#submission-copy) into the hackathon portal; and
- [ ] verify the public URL in an incognito browser before submission.

## Rollback

If the public deployment cannot complete provider calls, remove the provider secrets and redeploy the credential-free build. The deterministic baseline and offline memory lab remain complete. Do not weaken policy, expose raw provider responses, or add browser-supplied endpoints to recover a demonstration.
