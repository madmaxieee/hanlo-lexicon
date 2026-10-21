---
name: jj-workspaces
description: Create, reuse, hand off, and clean up Jujutsu workspaces while preserving unrelated work. Use when a task involves separate working copies in a jj repository.
---

# Jujutsu workspaces

Use installed `jj <command> --help` for syntax and version-specific behavior.
Keep repository instructions and the user's requested base and destination.

## Choose the workspace and base

- Check that jj is available and the repository is already managed by jj. If not,
  follow its existing VCS workflow; do not initialize jj to use this skill.
- Inspect `jj workspace list`, `jj status`, and a short `jj log`. Reuse a suitable
  workspace unless the user asks for another one. Record the original workspace,
  its working change, and any unrelated modifications before creating a new one.
- A normal status/log command can snapshot files and write repository metadata.
  For inspection that must avoid snapshotting, use `--ignore-working-copy`;
  the recorded state can be stale. Do not use that flag for workspace creation
  or checkout. A metadata permission error does not mean jj is unavailable.
- Choose the base explicitly. `jj workspace add` without `-r` creates a sibling
  change on the current working change's parents; it does not copy that change's
  modifications. With `-r REV`, the new working change is a child of `REV`.
- If current work is required, snapshot and inspect it first, then use that
  revision as the base. If it is unrelated, use the intended ancestor instead.
  Explain that choice in the handoff; do not silently include unrelated work or
  omit changes the task depends on.

## Create and work

Choose an unused destination outside existing checkouts, in an allowed writable
location. From the source repository, after resolving the base:

```sh
jj workspace add /absolute/destination --name task-name -r BASE_REVISION
```

Replace the example destination, name, and revision with actual values. Run all
subsequent edits, builds, and jj commands with the new directory as the working
directory. Confirm it with `jj workspace root` and inspect `jj status` before edits.
The original checkout remains in place; creating a workspace does not change the
shell's working directory.

Workspaces share repository history and bookmarks, but have separate working-copy
changes and sparse patterns. Rewriting a shared ancestor can affect other workspaces;
avoid rebasing or editing another task's changes as incidental setup.

Ignored caches, dependencies, credentials, and build outputs are not supplied by
the revision. Check what the task actually needs and use the documented setup.
Preserve pinned/checksummed inputs when reusing caches; do not copy the entire old
checkout or assume its local paths exist in the new workspace.

Use `jj describe` for the task's change description and `jj new` when another
change is useful. A dirty working change is normal in jj; there is no Git staging
step to reproduce. Inspect command help before unfamiliar history operations.
If jj reports a stale workspace, inspect its state and use
`jj workspace update-stale` in that workspace before continuing. If an operation
fails after partial setup, inspect the registered workspace and its files before
retrying; do not overwrite the destination or assume nothing happened.

## Verify and hand off

Run the checks appropriate to the changed files in the task workspace. Review
`jj diff` and `jj status` against the chosen base for accidental unrelated edits.
Report the absolute workspace path, workspace name, change ID, base, validation,
and any remaining work. Change IDs are useful handoff references even when a
rewrite changes the commit ID.

Finishing a workspace task does not itself request integration into another active
workspace or publication. When integration is requested, inspect the destination's
current work and choose the jj operation that preserves both tasks; do not apply
a Git cherry-pick recipe mechanically. Resolve conflicts and verify the result.

Keep the workspace available for review. When cleanup is appropriate, first
preserve needed changes and ignored artifacts and confirm no task still uses it.
`jj workspace forget NAME` removes registration without deleting files; filesystem
deletion is a separate action. Retain the change ID before forgetting a workspace
so its work remains easy to find.
