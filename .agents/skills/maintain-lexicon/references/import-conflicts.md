# Import conflicts require maintainer review

Present import conflicts directly in the conversation as a readable table or
short list rather than a structured question tool.

When an import approval overlaps an existing entry, show the maintainer the
approved form/reading, existing ID and form/readings, relevant source identities,
and the proposed resolution. Obtain an explicit decision before changing the
existing preferred form, adding or merging readings, treating the approval as
already handled, or creating a separate word. Apply a resolution already given
explicitly by the maintainer in the current conversation; preserve existing IDs
and forms when the maintainer keeps them. Continue nonconflicting imports while
conflicting cases await review.

Sharing a canonical reading alone is not an import conflict. When written forms
and dictionary identities differ, inspect the source context and continue if it
supports both proposals; do not hold solely for homophones. Record an
evidence-backed `identity_note` for a deliberate separate entry. Concerns about a
matched span occurring only inside a compound are separate from duplicate identity
and must state that evidence concern explicitly.

## Standing resolutions

- **Substantive MOE entry vs. surname appendix (`附錄－百家姓`)**: For the same
  written form and canonical reading, always use the substantive MOE entry with
  actual definitions and its original source row; retain the appendix identity
  only in the import audit as excluded. This preference selects dictionary
  identity without establishing sense or standalone word status in a corpus span.
- **Same reading, distinct words**: A word that only shares a reading with an
  existing entry (different MOE headword/definition or curated Hanji) is a
  separate entry with an `identity_note` rather than a conflict hold. See
  [the decision](../../../../decisions/same-reading-distinct-words-2026-11-12.md).
