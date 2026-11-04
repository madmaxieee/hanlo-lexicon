---
name: implement-spec
description: "Implement the result of /to-spec and /to-tickets in code."
disable-model-invocation: true
---

## Version control

Use `jj root` to detect jj-managed repositories, including colocated repos. Prefer jj there; use Git only in Git-only repositories. If detection fails but the current directory or an ancestor contains `.jj`, resolve the jj problem rather than falling back to Git. Check installed `--help` for version-specific syntax. Preserve unrelated user work by isolating task changes before editing.

In jj use `jj status`, `jj diff`, `jj log`, `jj describe`, and `jj new`; there is no staging step. Use bookmarks for published names and `jj git fetch` / `jj git push` for remotes. Use `gh` for GitHub issues and PRs, passing explicit repo/head/base names when needed. Push through jj before opening a PR; avoid `gh` options that perform local Git operations.

You have been provided a spec. This spec should have tickets associated with it, describing how to implement the spec.

The issue tracker should have been provided to you. If not, tell the user to run `/setup-matt-pocock-skills`.

The goal is the entire spec implemented on a single **integration line** (a jj change stack or Git branch), with every ticket resolved the way the issue tracker closes work.

The tickets are not a list of steps. They are a **task graph** with blocking relationships between them. This means there is always a **frontier** of tickets which are ready to be grabbed.

Start every subagent with a fresh context window.

Communication to and from subagents should be sparse. Communicate primarily through **context pointers**: to the spec, tickets, research notes, and previous commits. Don't duplicate information already available via pointers.

**Implementer subagents** should be run in the background where possible for maximum concurrency.

## Steps

1. Read the spec and tickets to understand the task graph.

2. (optional) Use an **exploration subagent** to conduct any exploration required by the tickets - relevant codebase files or external documentation. Ensure the exploration subagent can save files - it should save its markdown notes in a directory outside the repo, accessible by all future subagents. This lets **implementer subagents** focus on implementation rather than exploration.

3. Record the initial integration base and isolate the build from unrelated user work. In jj, use that revision as the initial integration tip and record its ID; create a dedicated orchestration workspace if needed. Avoid adding an empty placeholder change to the publishable history. In Git-only repos, create an integration branch. Create a bookmark only when publishing requires one. If the tracker closes work through PRs, use `gh pr create --draft` with explicit repo/head/base after pushing the first integrated ticket. Mark the PR as closing the spec and tickets where the tracker supports it.

4. Use a fresh **implementer subagent** for each ready ticket:
   - In jj, create its own workspace with `jj workspace add --name <ticket> -r <integration-tip> <path>`. Record its starting base and task change IDs. Each implementer owns only its workspace and changes. Refresh a stale workspace with `jj workspace update-stale` before editing.
   - In Git-only repos, use a separate worktree and ticket branch based on the integration branch. Preserve existing work rather than resetting an occupied worktree.
   - Call the Skill tool with `tdd`, then describe the completed changes and report their IDs, tests, and conflicts.

5. Serialize integration through a fresh **merger subagent** per completed ticket. In jj, rebase only that ticket's changes onto the latest integration tip with `jj rebase -r '<ticket-revisions>'` and the destination option supported by installed help. Preserve internal ticket ordering and other workers' changes. Resolve conflicts and run relevant checks before advancing the recorded integration tip. Keep the orchestration workspace current with the new tip. In Git-only repos, merge the ticket branch into the integration branch and verify it. If publishing, move the integration bookmark to the verified tip and push through `jj git push` in jj repos.

6. Recompute the **frontier** after each integration. Start newly ready tickets from the latest verified integration tip; already-running tickets integrate through step 5 when complete.

7. Once all tickets are integrated, call the Skill tool with `code-review` against the recorded initial base and explicit integration tip. Fix findings in a single fresh **implementer subagent**, then integrate and verify those changes too.

8. If a draft PR exists, push the final verified tip and mark it ready with `gh pr ready`. Otherwise, resolve each ticket the way the issue tracker closes work. Report the integration change IDs or branch and validation results.

9. Clean up worker workspaces only after retaining their completed work in integration history. In jj, use `jj workspace forget <name>` and remove only the task-owned directory after checking for unintegrated work; forgetting a workspace does not delete its files. In Git-only repos, remove the task-owned worktrees.
