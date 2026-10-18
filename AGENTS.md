# Working instructions

- Use Jujutsu (`jj`) for version control; this is a colocated Git-backed repository.
- Keep this repository local until the maintainer explicitly requests publishing.
- Read `schema/README.md` before editing entries.
- Keep source snapshots byte-for-byte unchanged; add a new snapshot for a new edition.
- Preserve source wording and provenance. Do not invent meanings, examples, usage
  restrictions, pronunciation rules, or editorial rationale.
- Keep imported records marked `imported` until a human reviews them.
- Keep word identities distinct by written form and canonical TL reading. Alternate
  input mappings are not grounds to merge unrelated senses or homophones.
- Validate TOML against the entry schema and verify source rows after data edits.
- Store meaningful notes in TOML fields, not comments. Omit unknown optional fields.
- Write project documentation in English; preserve Taiwanese and source-language data.
- Use Conventional Commit descriptions. Do not upload or configure a remote implicitly.
