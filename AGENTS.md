# Working instructions

- Use Jujutsu (`jj`) for version control; this is a colocated Git-backed repository.
- Keep this repository local until the maintainer explicitly requests publishing.
- Use the project-local `.agents/skills/maintain-lexicon/SKILL.md` for vocabulary
  maintenance. Read `schema/README.md` before editing entries.
- Keep source snapshots byte-for-byte unchanged; add a new snapshot for a new edition.
- Preserve source wording and provenance. Do not invent meanings, examples, usage
  restrictions, pronunciation rules, or editorial rationale.
- Keep imported records marked `imported` until a human reviews them.
- Treat written form plus canonical TL as a duplicate-check candidate, not a unique
  editorial identity. Preserve unrelated homographs with distinct `identity_note`s.
- Use `tools/lexicon.py` for duplicate checks, ID allocation, formatting, and validation.
  Never manually allocate an ID or skip offline MOE checks when adding an entry.
- Run `python3 tools/lexicon.py validate` and `format --check` after data edits;
  run `python3 -m unittest discover -s tests -v` after changing maintenance tools.
- Store meaningful notes in TOML fields, not comments. Omit unknown optional fields.
- Write project documentation in English; preserve Taiwanese and source-language data.
- Use Conventional Commit descriptions. Do not upload or configure a remote implicitly.
