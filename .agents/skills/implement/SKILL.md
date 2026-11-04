---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

## Version control

Use `jj root` to detect jj-managed repositories, including colocated repos. Prefer jj there; use Git only in Git-only repositories. If detection fails but the current directory or an ancestor contains `.jj`, resolve the jj problem rather than falling back to Git. Check installed `--help` for version-specific syntax. Preserve unrelated user work by isolating task changes before editing.

In jj use `jj status`, `jj diff`, `jj log`, `jj describe`, and `jj new`; there is no staging step. Use bookmarks for published names and `jj git fetch` / `jj git push` for remotes. Use `gh` for GitHub issues and PRs, passing explicit repo/head/base names when needed. Push through jj before opening a PR; avoid `gh` options that perform local Git operations.

Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Call the Skill tool with "tdd" where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, call the Skill tool with "code-review" to review the work.

In jj, describe the completed task change with `jj describe` and report its change ID. In Git-only repositories, commit your work to the current branch. Preserve unrelated user changes.
