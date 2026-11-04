# Han-Lo Lexicon

The shared language for Taiwanese writing recommendations and their evidence.
These terms distinguish lexical identity, preferred writing, and review authority.

## Language

### Words and writing

**Han-Lo**:
Taiwanese writing that combines Hanji and romanization. This lexicon also records
fully romanized and pure-Hanji preferred forms.

**Hanji**:
Han characters used to write Taiwanese. A Hanji form can supply lookup evidence
without being the preferred writing.

**Tâi-lô (TL)**:
The Taiwanese romanization used for verified entry readings. Tone marks and
single versus double hyphens carry distinctions preserved by this project.

**Pe̍h-ōe-jī (POJ)**:
A Taiwanese romanization encountered in corpus sources. A source's POJ spelling
and a verified TL reading are distinct representations.

**Lexical identity**:
The particular word an editorial recommendation concerns. Shared spelling or
reading alone does not determine whether two records represent it; related senses
need not become separate identities.
_Avoid_: treating a spelling/reading pair as a unique word.

**Entry**:
An editorial recommendation for a word, with a permanent identity, preferred
form, readings, and source evidence. Its identity survives spelling corrections.

**Homograph**:
An unrelated word sharing a written form with another word. Homographs can also
share a canonical reading while retaining distinct lexical identities.

**Preferred form**:
The adopted written output for an entry. It may differ from a source spelling or
the MOE headword.
_Avoid_: using “MOE form” to mean the adopted recommendation.

**Canonical TL**:
The verified TL reading selected as an entry's filing reference. It does not
rank dialects or exclude supported alternate readings.

**Alternate reading**:
An explicitly supported input reading of the same entry, other than its canonical
TL. An alternate reading does not by itself establish a separate word.

**Contraction**:
An alternate reading with fewer syllables than the canonical reading. The
contracted reading is a complete reading of the word.

**MOE form**:
A verified MOE spelling associated with an entry. Its presence records dictionary
evidence rather than adoption as the preferred form.

**Hanji form**:
A source-backed or explicitly curated Hanji spelling recorded independently of
MOE inclusion. Component evidence does not establish a dictionary compound entry.

**Rule-generated recommendation**:
A preferred spelling inferred solely from writing rules, without supporting
corpus evidence or explicit human adoption of that recommendation.

### Sources and evidence

**LKK**:
The source word list from which this lexicon began. Its original recommendations
remain evidence even when a maintainer adopts a different preferred form.

**MOE**:
The Ministry of Education Taiwanese dictionary used as original dictionary
evidence. A dictionary match supports review; it does not automatically select
this lexicon's preferred writing.

**TSBP**:
台文通訊BONG報, the publication used for corpus discovery and contextual evidence.
An issue is one numbered edition of the publication.

**Source snapshot**:
A preserved edition of original source material. Later editions are distinct
snapshots rather than revisions to the original evidence.

**Provenance**:
The record of where evidence or a decision came from, including the original
source location and any human or model review attribution.

**Source locator**:
A precise position within original evidence, such as a source record, dictionary
sheet and row, or article passage.

**Source spelling**:
The literal written form found in the source. It remains evidence even when
mapped to an entry with a different preferred form.

**Source mapping**:
An explicit whole-word decision associating a source spelling with an existing
entry. It retains that entry's identity and preferred writing.

### Discovery and recommendations

**Candidate**:
A possible word or entry match awaiting identity and evidence review. Discovery
alone does not adopt its spelling or authorize an import.

**Anchor**:
A Roman-triggered source span used to group TSBP review candidates. The triggering
span can be shorter than a custom whole-word proposal.

**Occurrence**:
One literal match at a specific location in a source text. Multiple occurrences
can support one candidate without establishing its intended reading or sense.

**Combo**:
A literal Hanji glyph paired with one TL syllable, preserving tone and neutral
markers. It identifies component evidence rather than a whole-word identity.

**Combo inventory**:
The observed component outputs and supporting entries in the current lexicon.
Multiple supported outputs remain a conflict rather than a majority decision.

**Conditional agreement**:
Agreement among the dictionary readings covering a source position. It does not
prove a word boundary, intended reading, or independent occurrence of a substring.

**Related word**:
A dictionary word found through a supported shared Hanji/TL sequence and a
specified word shape. The relation does not assert semantic kinship or adoption.

### Review and adoption

**Language screening**:
A contextual judgment about whether a corpus occurrence is Taiwanese evidence or
noise. It does not endorse spelling, dictionary sense, or entry review status.

**Import authorization**:
Permission to add selected proposals locally. Batch authorization alone does not
constitute individual human review.

**Identity conflict**:
An overlap with an existing entry that requires deciding whether to retain,
update, or distinguish lexical identities. A shared reading alone is insufficient.

**Review status**:
The recorded extent and authority of an entry's review, independent of whether
its spelling was rule-generated or whether it appears in an export.

**Imported**:
An entry status without recorded contextual review of the recommendation.
Mechanical checks and language screening alone leave this status unchanged.

**Machine-reviewed**:
An entry status after contextual model screening, with the model, scope, and
evidence recorded. It does not claim individual human review.

**Reviewed**:
An entry status reserved for explicit individual human review.
_Avoid_: using “reviewed” for batch authorization or successful validation alone.

**Disputed**:
An entry status recording unresolved editorial concerns.
