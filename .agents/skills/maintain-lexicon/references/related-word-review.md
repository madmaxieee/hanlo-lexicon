# Standalone related-word review

Use this procedure for standalone discovery and post-import recommendations.
See the [related-word command reference](../../../../tools/related-words.md) for
commands, matching rules, report fields, and import flags.

1. Establish a verified Hanji seed from recorded forms or an explicitly cited MOE
   identity; a homophone or reading-only match supplies no Hanji. Seed readings
   come from matching existing entries, falling back to the exact MOE form only
   when no seed entry exists (an unalignable existing reading cannot fall back to
   a different dictionary reading). Verify each relation using recorded
   `combo_matches` proofs and complete sourced readings.
2. After a batch import, finish its conflict resolutions before generating the
   report, scoped to the resulting entry IDs and current inventory. Present the
   new-only Markdown index with original MOE readings, definitions, matching
   patterns, source rows, and linked evidence pages. Keep existing-entry
   candidates and explicit rejections in JSON while hiding them from that index;
   pre-import checks remain audit evidence rather than current recommendations.
3. Retain the matching seed spelling at shared positions. Shorter words remove
   extra aligned units; longer words use fresh combo evidence only for added
   positions, including evidence from the newly imported seed. Keep inventory
   conflicts as audit evidence without reopening the adopted seed spelling.
   Present both sides of conflicts and obtain explicit choices for unknown or
   conflicting positions rather than selecting by majority. Keep
   canonical-headword proposals separate from dictionary variants so an uncertain
   variant does not demote the main proposal.
4. Keep decisions `pending` until separately authorized. Each approval selects the
   complete preferred form, canonical reading, and any alternates in that item's
   `review` object. Shorter words inherit spelling but still need word-level
   adoption. Match `review_status` to the authority exercised:
   - Use `reviewed` after the maintainer explicitly selects that word's spelling
     and readings and resolves any unknowns or conflicts.
   - Use `machine-reviewed` under the standing exception for batch-authorized,
     contextually screened, consistent complete proposals (including shorter words
     with complete inherited spellings). Retain the selected spelling/readings and
     record the model/agent, scope, and original dictionary/combo evidence in
     `editorial_rationale` and `sources`. Leave conflicting, incomplete, or
     existing-entry-overlapping proposals pending under the
     [import-conflict rule](import-conflicts.md).
5. Preview `import-related`, then apply only the separately authorized approved
   decisions, preserving the selected review status and original MOE sources.
   Human-adopted recommendations omit `rule_generated`; pending and rejected
   suggestions stay unimported. Edit only the report's `review` objects, keeping
   sealed evidence unchanged. If entries, dictionary, or implementation change,
   regenerate and review the new evidence before importing remaining suggestions.
