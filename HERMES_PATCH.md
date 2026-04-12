# Hermes Scheduler Patch — Zero-Token Cron Runs

By default, when a cron script produces no output, Hermes still instantiates the agent
(burning tokens) before suppressing delivery. This patch makes the scheduler bail out
**before** touching the LLM when the script has nothing to report.

Apply to: `~/.hermes/hermes-agent/cron/scheduler.py`

---

## Patch 1 — `_build_job_prompt()`: return sentinel on empty script output

Find the `else` branch under `if script_output:` (around line 501) and replace:

```python
# BEFORE
else:
    prompt = (
        "[Script ran successfully but produced no output.]\n\n"
        f"{prompt}"
    )

# AFTER
else:
    # Script ran but produced no output — nothing to act on.
    # Return a sentinel so the scheduler can skip the LLM entirely.
    return "__SCRIPT_EMPTY__"
```

---

## Patch 2 — job runner: bail before agent instantiation

Find where `_build_job_prompt(job)` is called and add the sentinel check immediately after:

```python
# BEFORE
prompt = _build_job_prompt(job)
origin = _resolve_origin(job)

# AFTER
prompt = _build_job_prompt(job)

# Script produced no output — skip entirely, don't wake the LLM.
if prompt == "__SCRIPT_EMPTY__":
    logger.info("Job '%s' (ID: %s): script empty, skipping.", job_name, job_id)
    return True, None, None, None

origin = _resolve_origin(job)
```

---

## Patch 3 — tick loop: guard `save_job_output` against None

```python
# BEFORE
output_file = save_job_output(job["id"], output)
if verbose:
    logger.info("Output saved to: %s", output_file)

# AFTER
if output is not None:
    output_file = save_job_output(job["id"], output)
    if verbose:
        logger.info("Output saved to: %s", output_file)
```

---

## Result

- Script exits with no stdout → scheduler logs one line and returns
- Zero API calls, zero tokens, zero cost
- Only when the script actually outputs data does the agent wake up
