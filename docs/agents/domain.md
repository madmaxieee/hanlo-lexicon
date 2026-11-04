# Domain documentation

This repository has one domain glossary: [GLOSSARY.md](../../GLOSSARY.md).
Use its vocabulary when naming concepts in documentation, tickets, and code.
Read the glossary before changing terminology; surface conflicting meanings
rather than silently redefining an existing term.

## Read by task

- Entry fields, identity, or filing: [entry schema](../../schema/README.md).
- Editorial policy, writing conventions, or an earlier adoption:
  [decision index](../../decisions/README.md), then the relevant records.
- Vocabulary operations: [maintain-lexicon](../../.agents/skills/maintain-lexicon/SKILL.md).
- Tool behavior and commands: [maintenance guide](../../tools/README.md).

## Keep each document's role clear

The glossary defines concepts, without commands or implementation decisions.
The schema owns field semantics and record conventions. Skills own editorial
procedures; tool guides own command reference. Link to the authoritative document
instead of copying its instructions into each consumer.

`decisions/` is this project's decision-record location, including the role that
the engineering suite normally assigns to `docs/adr/`. Use the existing location
and index rather than introducing a parallel decision archive.
Historical imports record what was authorized and done at that time; their
counts and pending states are not a current inventory or open-ticket list.

When changing a decision, cite the earlier record and explain the explicit new
resolution. Preserve original evidence and distinguish inherited recommendations
from maintainer choices. Record reasons only when supported by the discussion or
source. The [decision guide](../../decisions/README.md#record-a-decision) explains
when and how to add a record.
