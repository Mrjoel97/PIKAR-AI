# Parallel Codex Runner (Local)

This folder contains a local helper setup for launching multiple `codex exec` workers in parallel on isolated Git worktrees.

It is designed for a fast multi-PR workflow (e.g. `pr0`..`pr6`) and keeps each worker isolated so diffs are easy to review/merge.

## Files

- `launch.ps1`: launch all (or selected) workers in parallel
- `fresh-launch.ps1`: reset old run state, then launch
- `reset.ps1`: stop worker processes + remove worktrees + clear run artifacts
- `doctor.ps1`: preflight checks for Codex CLI, outbound API reachability, proxy envs, and local OSS providers
- `status.ps1`: quick health/status view (running/completed/failed, changed file count)
- `collect.ps1`: inspect diffs/results/stderr per worker
- `prompts/`: one prompt file per worker (`pr0.txt`..`pr6.txt`)
- `worktrees/`: isolated Git worktrees per worker
- `runs/`: `events.jsonl`, `stderr.log`, `result.txt` per worker

## Typical Usage

### 1) Preflight (recommended)

Remote API mode (OpenAI provider):

```powershell
pwsh .tmp\codex-parallel\doctor.ps1 -CheckRemoteApi
```

Local OSS mode (no outbound API dependency):

```powershell
pwsh .tmp\codex-parallel\doctor.ps1 -Oss -LocalProvider ollama
# or
pwsh .tmp\codex-parallel\doctor.ps1 -Oss -LocalProvider lmstudio
```

Run a fresh full parallel launch:

```powershell
Set-Location 'C:\Users\expert\Documents\PKA\Pikar-Ai'
pwsh .tmp\codex-parallel\fresh-launch.ps1 -DropBranches
```

Launch only a subset of workers:

```powershell
pwsh .tmp\codex-parallel\fresh-launch.ps1 -DropBranches -Ids pr1,pr2,pr3
```

Run using a local OSS provider (no outbound API):

```powershell
pwsh .tmp\codex-parallel\fresh-launch.ps1 -DropBranches -Oss -LocalProvider ollama
```

Run through a proxy (remote API mode):

```powershell
pwsh .tmp\codex-parallel\fresh-launch.ps1 -DropBranches -HttpsProxy 'http://proxy.example:8080' -HttpProxy 'http://proxy.example:8080'
```

Check status:

```powershell
pwsh .tmp\codex-parallel\status.ps1
pwsh .tmp\codex-parallel\status.ps1 -VerboseErrors
```

Collect diffs + outputs:

```powershell
pwsh .tmp\codex-parallel\collect.ps1
pwsh .tmp\codex-parallel\collect.ps1 -ShowDiff
```

Reset only (keep prompts, clear run state/worktrees):

```powershell
pwsh .tmp\codex-parallel\reset.ps1 -DropBranches
```

## Notes

- `launch.ps1` sets a writable per-worker `CODEX_HOME` under `.tmp/codex-parallel/codex-home/<id>`.
- Workers are launched from the current repo `HEAD` by default (not your uncommitted changes).
- Use `-BaseRef <commit-or-branch>` on `launch.ps1` / `fresh-launch.ps1` to pin a different base.
- If your environment blocks outbound network access, remote API mode will fail before making edits (check `runs/*/events.jsonl`).
- To avoid outbound API dependency, use local OSS mode: `-Oss -LocalProvider ollama` or `-Oss -LocalProvider lmstudio`.
- `launch.ps1`/`fresh-launch.ps1` also support `-Model` and `-Profile` to target a specific Codex model/profile.
