# Triage roles

Local tickets record these canonical roles in their `Status:` line.

| Role | Meaning |
| --- | --- |
| `needs-triage` | Maintainer needs to evaluate the issue. |
| `needs-info` | More information is needed before deciding. |
| `ready-for-agent` | Fully specified and ready for agent implementation. |
| `ready-for-human` | Requires human implementation or judgment. |
| `wontfix` | Will not be implemented. |

`claimed` and `resolved` record execution progress as described in
[the local tracker conventions](issue-tracker.md). These statuses concern work
items; lexicon entry review statuses are defined separately in the
[schema](../../schema/README.md).
