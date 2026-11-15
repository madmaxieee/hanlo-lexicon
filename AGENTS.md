# Working instructions

## Version control and publishing

- Use Jujutsu (`jj`) for all VCS operations in this repository (`jj status`,
  `jj diff`, `jj log`, `jj describe`, `jj new`, `jj bookmark`); preserve
  unrelated working changes and check `jj <cmd> --help` when syntax is uncertain.
- For `jj` workspace creation, reuse, handoff, or cleanup, read
  [jj-workspaces](.agents/skills/jj-workspaces/SKILL.md).
- Keep commits, remotes, and publishing local until the maintainer asks to push
  or publish; use Conventional Commit descriptions.

## Repository checks and invariants

- Use `tools/lexicon.py` for duplicate checks, ID allocation, formatting, and
  validation, and serialize entry creation across workspaces so IDs stay unique.
- Keep `sources/` snapshots byte-for-byte unchanged (add a new snapshot directory
  for a new edition).
- Write documentation in English; preserve Taiwanese and source-language data.
- Run `just check` (or `python3 tools/lexicon.py validate`, `format --check`,
  and `python3 -m unittest discover -s tests -v`) after edits.

## Navigation

- **Vocabulary maintenance, MOE/LKK checks, and import conflicts**:
  [maintain-lexicon](.agents/skills/maintain-lexicon/SKILL.md) and
  [entry schema](schema/README.md).
- **Tool commands**: [tools/README.md](tools/README.md) (and
  [tools/tsbp/README.md](tools/tsbp/README.md) for TSBP discovery).
- **Domain terminology and decision records**:
  [GLOSSARY.md](GLOSSARY.md), [docs/agents/domain.md](docs/agents/domain.md),
  and [decisions/README.md](decisions/README.md).
- **Engineering specs and tickets (`.scratch/`)**:
  [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md) and
  [docs/agents/triage-labels.md](docs/agents/triage-labels.md).
