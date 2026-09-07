# Reubarb Pi Core 0.1 contract

Status: Core 0.1 Foundation frozen by explicit user approval at I-23.
Contract target: Core 0.1. Document revision: I-23.3 (portable release instructions), 2026-09-07.
Scope: accepted Foundation behavior through I-21.

## 1. What this contract covers

Core 0.1 provides exact source handling, one reviewed-text reading instruction,
five separately recognized native glyphs, an inert glyph-identity value, and a
bounded occurrence-continuity assessment. The reference implementation uses
Python 3.13. The general dynamically typed language is the next stage.

This document consolidates existing decisions. **CONFIRMED** clauses below
restate accepted behavior; their clause labels are document references only.
**CONFIRMED CONCEPTUAL** material preserves design commitments without claiming
an operational implementation. **OPEN** and **DEFERRED** items are listed
explicitly. Writing this document does not approve new semantics or freeze it.

[AGENTS.md](AGENTS.md) remains the authoritative active rule and gate record.
Its conflict order remains: latest explicit user decision, accepted decision
records, AGENTS.md, this specification, then tests and implementation. A test
does not settle a conflicting semantic decision. The historical
[handoff](CONVENTIONAL_FOUNDATIONS_HANDOFF.md) retains detailed provenance.

**C01 — CONFIRMED: versioned guarantee.** Once the user freezes Core 0.1,
conforming implementations must preserve its frozen clauses. A deviation is a
bug; an intended change to a guarantee requires an explicitly new version.
Passing tests provide bounded evidence, not infallibility. Host profile names,
font versions, document revisions, and the public STUTT version are distinct.

| Implemented surface | Explicit input | Observable endpoint |
| --- | --- | --- |
| I-1 transport | UTF-8 bytes and caller-supplied source ID | Exact decoded text or transport reasons |
| I-2 transcript admission | Separately reviewed and accepted scalar text | Immutable `textus` or admission diagnostic |
| I-2 observation | One `textus` | Complete unchanged transcript payload |
| I-4/I-5/I-6 preparation | Decoded source, then checked lexical records | Profile, lexical stream, and parser support records |
| I-7/I-21 reading | One reading unit and one supplied label/value | Existing `ReadObservationResult` containing the I-2 observation |
| I-11 recognition | One already separated decoded candidate | `RECOGNIZED`, `UNRECOGNIZED`, or `INVALID_INPUT` |
| I-15/I-16/I-20 glyph path | One standalone candidate in decoded source | Existing inert `GlyphIdentityValue`, or a result with no value |
| I-18 continuity | Five already established host observations | `same-occurrence` or `classification-stopped` |

These are separate host interfaces. There is no common dispatcher, combined
program grammar, shared result envelope, or automatic routing between them.

## 2. Source transport and positions

**C02 — CONFIRMED: exact transport and coordinates.** The laboratory source
extension is lowercase `.gart`. Canonical source bytes use strict UTF-8 without
a leading `EF BB BF` BOM. Invalid UTF-8 is rejected without replacement decoding.
The BOM and invalid-UTF-8 checks are independent; both reasons may be reported.
Any transport reason withholds decoded text. The BOM reason has byte span
`[0, 3)`; I-1 does not assign a decoder-specific location to `INVALID_UTF8`.

Successful decoding preserves the complete ordered Unicode scalar sequence.
No trimming, normalization, case folding, transliteration, confusable repair,
or newline rewriting occurs. Decoding supplies neither transcript review nor
permission to observe or execute anything.

Scalar offsets are zero-based; line and column numbers are one-based. Span ends
are exclusive. Columns count Unicode scalars, with TAB counting as one column.
CRLF retains two scalar offsets but constitutes one line break. The position
between CR and LF remains on the preceding line; the next line starts after LF.
EOF is zero-width and inserts no newline, value, or terminator. Byte locations
and scalar locations remain distinct host record types and units.

Reference: [I-1 transport](core_0_1_transport_kernel.py),
[I-4 source profile](core_0_1_source_profile.py).

## 3. Source profile and incomplete context

**C03 — CONFIRMED: bounded source checking.** `inspect_source_profile` accepts
an exact built-in decoded string. Bytes, `textus`, string subclasses, and
lookalikes are not implicitly converted. Input beyond the profile ceiling is
stopped before scalar validation; surrogate-containing host text receives no
invented scalar coordinates.

The accepted source rules are:

- SPACE U+0020 and TAB U+0009 are the only horizontal whitespace.
- LF and CRLF are the only line endings. Indentation has no semantic role.
- `//` starts a line comment in known lexical context. The comment excludes
  its terminating LF or CRLF and may end at EOF.
- NUL; prohibited C0 and C1 controls; lone CR; U+2028/U+2029; and U+FEFF are
  invalid even inside comments. The CR belonging to CRLF is allowed.
- U+202A–U+202E and U+2066–U+2069 bidirectional controls are invalid everywhere.
- U+061C, U+200E, U+200F and other pinned default-ignorable characters are
  allowed only as exact comment content, subject to the global exclusions.
- Unlisted forms receive no invented whitespace, literal, or operator meaning.
  U+007F, for example, is not given a new universal ban by the C0/C1 rule.

The inspector knows context across ASCII word-like material, approved trivia,
and line endings. At unresolved syntax it returns `context-required`, stops
inferring later comments, and continues unconditional checks. A later global
violation still rejects the profile. Incomplete checking never releases a
successful source map; only `profile-checked` does so.

The Unicode property data is the existing pinned Unicode 17.0.0
`Default_Ignorable_Code_Point` table: 4,174 points in 17 merged intervals,
including its retained notice in the reference module. No runtime download or
ambient Unicode database determines this profile.

Source rules do not filter admitted transcript payloads. A scalar-valid control
or bare CR can be transcript data even when it is invalid instruction source.

## 4. Lexical and parser-support boundary

**C04 — CONFIRMED: exact words and complete input.** Ordinary identifiers use:

```text
ASCII_LETTER       ::= "A".."Z" | "a".."z"
ASCII_DIGIT        ::= "0".."9"
IdentifierStart    ::= ASCII_LETTER | "_"
IdentifierContinue ::= IdentifierStart | ASCII_DIGIT
Identifier         ::= IdentifierStart IdentifierContinue*
```

Whole ASCII identifier runs become `WORD` items. Exact spelling is compared
only after the complete run is bounded: `WITHIN` is one word. Case is preserved.
Recognized spelling metadata does not establish global keyword reservation,
binding, evaluation, or automatic dispatch.

The exact historical spellings are `0`, `WITH`, `OR`, `FALSE`, `RECON`, `DPEND`,
`IDENTITY`, and `BOUNDARY`. The later I-2 approvals add metadata for `textus`,
`transcriptio`, and `leg`. Their research provenance stays distinct. The saved
191-head vocabulary work is evidence, not 191 implemented operations.

An isolated `0` is `EXACT_ATOM`, with no arithmetic value. `00`, `0foo`, `0_`,
direct `0//comment` adjacency, and other digit-leading forms require context.
Digits after an identifier start, as in `a0`, stay within the word. `FALSE`
retains its adopted negation meaning without creating a Boolean value type.
The operator grammar for the historical spellings remains open.

Successful lexing retains exact `WORD`, `EXACT_ATOM`, `SPACE_TAB`, `COMMENT`,
`LF`, and `CRLF` items followed by one EOF. Non-EOF spans are contiguous and
positive-width; concatenating lexemes reproduces the source. A stopped result
releases no partial stream.

I-6 validates the exact I-5 result and its complete stream, including its EOF,
source map, spans, item kinds, and approved metadata. It supplies read-only input,
ranges, and independent cursors without re-lexing. Trivia skipping hides only
SPACE/TAB and COMMENT; line endings remain visible. `finish` distinguishes
unconsumed items from unconsumed EOF without advancing. `prepared` and
`fully-consumed` do not assert a parsed program. I-7 supplies the accepted
reading grammar in Section 6.

References: [I-5 lexer](core_0_1_lexical_frontend.py),
[I-6 parser support](core_0_1_syntax_skeleton.py).

## 5. Reviewed transcripts

**C05 — CONFIRMED: explicit admission and exact observation.** `textus` is a
distinct non-Source reviewed-transcript type. Its accepted scalar sequence is
immutable. Its statements do not thereby become true or immutable facts.

The existing host interfaces are:

```text
transcriptio(payload, *, reviewed=False, accepted=False) -> AdmissionResult
leg(value) -> ObservationResult
```

Admission checks short-circuit in this order: exact Boolean review controls,
review present, acceptance present, exact built-in string payload, inclusive
size ceiling, then scalar validity. Empty text is permitted. Success produces
one complete `textus`. A correction is a separate admission and preserves the
earlier value. Words such as "I approve" inside the payload supply no approval.
The host flags assert review; they do not authenticate a reviewer.

`leg` accepts one supported `textus` and returns its whole unchanged payload.
Observation is repeatable and non-consuming. It performs no interpretation,
source processing, display, logging, transmission, or payload execution.
Derived interpretation remains separate and inherits no automatic authority.

`txt` and case variants are not aliases. Python strings, numbers, booleans,
equality, references, copying and private construction seals do not become
additional target-language semantics. Host read-only carriers are not a sandbox
against hostile Python code in the same process.

Reference: [I-2 runtime](core_0_1_transcript_runtime.py).

## 6. The complete reading unit

**C06 — CONFIRMED: one exact reading instruction.** The accepted grammar is:

```text
ReadUnit ::= Padding WORD('leg') SPACE_TAB WORD Padding EOF
Padding  ::= (SPACE_TAB | COMMENT | LF | CRLF)*
```

`SPACE_TAB` in the middle is one nonempty run of spaces and/or tabs. The target
immediately follows it on the same line. Existing padding may surround the
instruction. The parser consumes the whole unit and its EOF; a valid prefix
followed by extra material cannot be observed. There is no statement sequencing.

The head is exactly lowercase `leg`. The target slot is contextual: even an
approved word such as `RECON` can occupy the name slot without invoking an
operation. `0` is not a `WORD` target.

`parse_read_unit(lexical_result)` only parses. The explicit host adapter
`observe_read_unit(source_text, *, target_name=None, target_value=None)` lexes
once, finishes parsing, validates the supplied ASCII label, requires exact
name agreement, then calls I-2 `leg` once. The label/value association lasts
for this invocation; no binding environment or lookup is implemented.

The endpoint is the existing `ReadObservationResult`, with fields `outcome`,
`parse_result`, `reasons`, and `observation`. It retains the original I-2
observation. Successful observation has exact outcome `observed`, its complete
payload, and no diagnostic. Parsing retains checked source, item/EOF coverage,
head/target/instruction/unit ranges, and upstream boundary information.

Missing or invalid external labels stop before observation. A mismatched label
locates the source target. A matching label with a missing or unsupported value
uses the existing I-2 `EXPECTED_TEXTUS` diagnostic. Nothing falls back to a
previous invocation or another parser.

Reference: [I-7 reading](core_0_1_read_instruction.py).
Accepted evidence anchors remain BHS-P27-LEG, BHS-CTX-NU28.7-LEG, and the saved
Jeremiah 36 / Nehemiah 8 reading relationships in AGENTS.md. I-22 performs no
new corpus verification; the exact payload behavior derives from accepted I-2.

## 7. Native glyphs, encoding, and display

**C07 — CONFIRMED: five distinct mapped forms.** The current inventory is:

| Identity | Review label | Exact scalar | Deliberate editor shortcut | Canonical geometry |
| --- | --- | --- | --- | --- |
| G2 | Congruent statement | U+E100 | `rb.g2` | [G2 SVG](glyphs/v0_1/rp_g02_congruent_statement.svg) |
| G3 | Fulfilled overlay | U+E101 | `rb.g3` | [G3 SVG](glyphs/v0_1/rp_g03_fulfilled_overlay.svg) |
| G4 | Strong | U+E102 | `rb.g4` | [G4 SVG](glyphs/v0_1/rp_g04_strong_variant.svg) |
| G5 | Neutral | U+E103 | `rb.g5` | [G5 SVG](glyphs/v0_1/rp_g05_neutral_variant.svg) |
| G6 | Weak | U+E104 | `rb.g6` | [G6 SVG](glyphs/v0_1/rp_g06_weak_variant.svg) |

The host design indices and review labels are not target spellings or numbers.
The scalars are a project private agreement. The centerless four-dot component
is construction material and has no glyph mapping or shortcut. I-9 approval
supersedes the historical I-8 proposal status without rewriting that history.

The approved frame is 1000 by 1200 drawing units. Equal circles have radius 70,
centered north `(500,150)`, west `(220,500)`, east `(780,500)`, and south
`(500,950)`. G4/G5/G6 share this frame and differ at the center. G2 contains the
two exact connected paths; G3 contains those paths with the four circles.
The linked SVGs and [I-9 registry](core_0_1_glyph_geometry.py) specify all paths,
30-unit strokes, and round caps/joins. Complete drawings may translate and
scale uniformly, preserving north/up, 5:6 frame proportions, circular dots,
and relative positions. Rotation, reflection, skew, cropping, and independent
component repositioning are not approved transformations. Raster antialiasing
does not define identity. Handwriting-recognition tolerances remain open.

The [workspace snippets](.vscode/reubarb-glyphs.code-snippets) insert exactly
one mapped scalar after deliberate completion in `.gart` files. Shortcut text
is not parsed or expanded by Reubarb and causes no automatic submission.

SVG geometry is canonical. The existing
[Reubarb Pi Symbols font](fonts/v0_1/ReubarbPiSymbols-Regular.ttf) is a display
artifact, described by its [font manifest](fonts/v0_1/font-manifest.json).
[Display references](core_0_1_glyph_display.py) supply accessible labels and
fallbacks such as `[Reubarb G2 U+E100]`. Raw PUA rendering depends on the host.
The [font preview](fonts/v0_1/font-preview.html) and
[encoding preview](reubarb_glyph_encoding_preview.html) show the local assets.
Display, font installation, and glyph size create no semantic operation.

The user confirmed editor rendering after reboot in I-14. Static I-12/build
records still contain earlier installation/review labels; those are artifact
history, not a live machine-state check. Ordinary editor text remains at 24px
under the user's current preference; glyph enlargement is a display concern.

**C08 — CONFIRMED: recognition and identity endpoint.** I-11 receives one
already separated decoded candidate. Exact mapped scalars return `RECOGNIZED`.
Other nonempty scalar sequences return `UNRECOGNIZED` without splitting or
repair. Empty and surrogate-containing strings return `INVALID_INPUT`.
Wrong host types raise `TypeError`; an oversized candidate raises
`CandidateLimitError`. These host failures are outside the three classifications.
Only `UNRECOGNIZED` is eligible for a separate nomination; eligibility creates
no queue, record, glyph, or promotion. I-11 observations retain no candidate text.

I-15 accepts decoded source and resolves only a standalone candidate context
after I-4's unconditional checks. One non-trivia token containing exactly one
scalar can be observed. Empty input, multiple tokens, and contiguous
multi-scalar forms stop explicitly. On I-4 `context-required`, its narrow
scanner recognizes comments between tokens; direct PUA/comment adjacency is
not silently split. The I-4 `profile-checked` branch instead uses the existing
source-map trivia. These are documented existing branches, not a new general
delimiter rule. Candidate spans and the full instruction span are retained;
the contextual branch has no successful I-4 source map to invent.

I-16's `form_glyph_identity_value(source_text)` calls I-15 and validates exact
I-10 mapping metadata. Recognized G2–G6 produce `value-available` with the inert
carrier's `design_id` and `code_point_label`. Unrecognized candidates produce
`no-value`. Other stopped outcomes and reasons are retained with no value.
The result retains its preceding source observation, including transient source
provenance; the value itself contains no source, partner, event, or state.

I-20 accepts this identity-only result as the terminal glyph endpoint. G3
identifies the G3 form; it is not evidence that an event was fulfilled. Missing
partners do not invalidate mapped glyph identity. Pairing, congruence, matrix
classification, fulfillment, Source authorization, and transitions are deferred.
The general I-5 lexer continues to request context for the PUA scalars.

References: [I-10 encoding](core_0_1_glyph_encoding.py),
[I-11 recognizer](core_0_1_glyph_recognizer.py),
[I-15 source integration](core_0_1_glyph_source_integration.py),
[I-16 identity value](core_0_1_glyph_identity_value.py).

## 8. Occurrence continuity

**C09 — CONFIRMED: classification from explicit premises.** I-18's
`assess_same_occurrence(evidence)` receives an exact `SameOccurrenceEvidence`
record with all five already-established observations:

| Field | Allowed host observations |
| --- | --- |
| `entity_anchor` | `UNCHANGED`, `DIFFERENT`, `UNAVAILABLE` |
| `unresolved_need_anchor` | `UNCHANGED`, `DIFFERENT`, `UNAVAILABLE` |
| `authorized_boundary_anchor` | `UNCHANGED`, `DIFFERENT`, `UNAVAILABLE` |
| `intervening_fulfillment` | `ABSENT`, `PRESENT`, `UNAVAILABLE` |
| `explicit_closure` | `ABSENT`, `PRESENT`, `UNAVAILABLE` |

Exactly three `UNCHANGED` anchors plus both end observations `ABSENT` yield
`same-occurrence` with no issues. Every other well-formed combination yields
`classification-stopped` with the applicable issues. Stopping establishes
neither a new occurrence nor a different occurrence. Issues follow field order
in this table; impossible alternative pairs and duplicate issues are rejected.

The caller supplies the premises. This function does not examine actual entity
identities, establish equality, prove evidence, call Source, retry, store history,
or create/close an occurrence. Wrong host record types raise `TypeError`;
malformed supported records raise `ValueError`. All 243 combinations of these
five three-valued inputs are covered by the existing eighteen-test suite.

Reference: [I-18 continuity](core_0_1_occurrence_continuity.py).

## 9. Outcomes, limits, and diagnostics

**C10 — CONFIRMED: preserve each boundary's result.** A success applies only to
its named operation. No failure is replaced with target `FALSE`, boundary-local
`0`, an empty successful payload, or the novel exception/rule-change chain.

| Boundary | Existing outcome observations |
| --- | --- |
| I-1 | `succeeded` from availability of decoded text; transport JSON uses `decoded` / `failed` |
| I-2 admission | `admitted`, `rejected`, `limited`, `host-failed` |
| I-2 observation | `observed`, `rejected`, `host-failed` |
| I-4 | `profile-checked`, `profile-rejected`, `context-required`, `input-rejected`, `limited`, `host-failed` |
| I-5 | `lexed`, `source-rejected`, `context-required`, `input-rejected`, `limited`, `host-failed` |
| I-6 preparation | `prepared`, `upstream-stopped`, `input-rejected`, `limited`, `host-failed` |
| I-6 consumption | `fully-consumed`, `incomplete` |
| I-7 parse/observe | `parsed`, `syntax-rejected`, `target-rejected`, applicable upstream stops, and unchanged I-2 outcomes |
| I-11 | `RECOGNIZED`, `UNRECOGNIZED`, `INVALID_INPUT`; host type/limit errors remain exceptions |
| I-15 | `parsed` / `observed`, `input-rejected`, `source-rejected`, `syntax-rejected`, and its resource-stop compatibility value below |
| I-16 | `value-available`, `no-value`, `host-failed`, or the exact preceding stopped outcome |
| I-18 | `same-occurrence`, `classification-stopped`; malformed host arguments remain exceptions |

Compatibility detail: I-15 currently uses the exact string
`GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED` as both its resource-stop outcome and
reason. I-16 preserves that upstream outcome; its own allocation/invariant
failure uses `host-failed`. I-15 also wraps I-4 input/limit/host stops as
`source-rejected` while retaining the original `source_profile_outcome` and
reasons. Readers must inspect the boundary provenance rather than assume all
outer outcome strings have one universal shape. I-22 records these accepted,
tested behaviors without normalizing them during consolidation.

| Existing host profile | Inclusive bound |
| --- | --- |
| I-2 transcript input | 65,536 host code points, checked before scalar validity |
| I-4 source input, inherited by I-5/I-6/I-7 and I-15 | 65,536 host code points, checked before scalar validity |
| I-4 source diagnostics | 128 source reasons, plus one explicit diagnostic-limit reason when needed |
| I-5/I-6 lexical items | 16,384 non-EOF items including trivia, plus one EOF |
| I-11 candidate input | 65,536 host code points, checked before scalar validity |

These are per-call laboratory policies, not total-memory or time guarantees.
I-1 has no separately enforced byte-count ceiling. A guarded allocation failure
withholds partial success. Unhandled defects, cancellation, and failures while
allocating even the diagnostic itself may propagate as host failures. They do
not become Source decisions, target exceptions, or automatic recovery.

Reason identities use `GART.CORE_0_1.<DOMAIN>.<REASON_NAME>`, with uppercase ASCII
letter/digit words; reason-name words may be separated by underscores. The
meaning of a frozen code must not be recycled. Human messages are explanatory.
Different host reason records stay distinct: for example, I-2 diagnostics have
`operation` and `reason`, while source reasons have `code` and optional location.

The general duplicate identity is code plus exact location, including absent
location. I-1/I-4 ordering is located before locationless, then start offset,
end offset, and ASCII code. I-2 follows its accepted first-failure sequence;
I-7 stops at the applicable boundary; I-18 uses its explicit field order.
No generic aggregation rule overrides those accepted package contracts.

### Existing reason catalogue

Each entry below is a complete existing code and its bounded meaning. The
catalogue covers the active `core_0_1_*.py` runtime modules, not historical
research probes or proposed future reason families.

| Code | Meaning |
| --- | --- |
| `GART.CORE_0_1.TRANSPORT.INVALID_UTF8` | Source bytes cannot be strictly decoded as UTF-8. |
| `GART.CORE_0_1.TRANSPORT.UTF8_BOM_FORBIDDEN` | Source begins with the prohibited three-byte BOM. |
| `GART.CORE_0_1.TRANSCRIPT.INVALID_REVIEW_STATE` | Review/acceptance flags are not exact host booleans. |
| `GART.CORE_0_1.TRANSCRIPT.REVIEW_REQUIRED` | Review was not asserted. |
| `GART.CORE_0_1.TRANSCRIPT.ACCEPTANCE_REQUIRED` | Reviewed input lacks explicit acceptance. |
| `GART.CORE_0_1.TRANSCRIPT.EXPECTED_TEXT` | Admission payload is not an exact built-in string. |
| `GART.CORE_0_1.TRANSCRIPT.NON_SCALAR_CONTENT` | Admission payload contains a surrogate. |
| `GART.CORE_0_1.TRANSCRIPT.EXPECTED_TEXTUS` | Observation argument is not the supported `textus` carrier. |
| `GART.CORE_0_1.SOURCE.EXPECTED_DECODED_TEXT` | Source-profile argument is not an exact built-in string. |
| `GART.CORE_0_1.SOURCE.NON_SCALAR_INPUT` | Decoded host source contains a surrogate. |
| `GART.CORE_0_1.SOURCE.FORBIDDEN_CONTROL` | A globally prohibited control occurs. |
| `GART.CORE_0_1.SOURCE.UNSUPPORTED_LINE_BREAK` | A lone CR or another prohibited line-breaking scalar occurs. |
| `GART.CORE_0_1.SOURCE.FEFF_FORBIDDEN` | U+FEFF occurs in decoded source. |
| `GART.CORE_0_1.SOURCE.BIDI_CONTROL_FORBIDDEN` | A prohibited stateful bidirectional control occurs. |
| `GART.CORE_0_1.SOURCE.COMMENT_ONLY_CHARACTER` | A comment-only character occurs outside a known comment. |
| `GART.CORE_0_1.SOURCE.LEXICAL_CONTEXT_REQUIRED` | An unselected source form requires a contextual decision. |
| `GART.CORE_0_1.LEXICAL.ZERO_BOUNDARY_REQUIRED` | A zero-leading form lacks an approved atom boundary. |
| `GART.CORE_0_1.LEXICAL.DIGIT_FORM_REQUIRED` | A nonzero digit-leading form lacks an approved lexical rule. |
| `GART.CORE_0_1.SYNTAX.EXPECTED_LEXICAL_RESULT` | Parser preparation requires the exact I-5 result type. |
| `GART.CORE_0_1.SYNTAX.UNCONSUMED_ITEMS` | A cursor has not consumed all non-EOF items. |
| `GART.CORE_0_1.SYNTAX.EOF_NOT_CONSUMED` | Only the required EOF consumption remains. |
| `GART.CORE_0_1.SYNTAX.EXPECTED_READ_HEAD` | The reading unit lacks exact lowercase `leg` as its head. |
| `GART.CORE_0_1.SYNTAX.EXPECTED_HORIZONTAL_GAP` | The head is not followed by its required space/tab run. |
| `GART.CORE_0_1.SYNTAX.EXPECTED_TARGET_NAME` | The required same-line target is not a WORD. |
| `GART.CORE_0_1.SYNTAX.EXPECTED_READ_EOF` | Extra non-padding content follows the target. |
| `GART.CORE_0_1.READ.INVALID_TARGET_LABEL` | The supplied host label is missing or has the wrong type/shape. |
| `GART.CORE_0_1.READ.TARGET_NAME_MISMATCH` | The supplied label differs from the exact parsed name. |
| `GART.CORE_0_1.GLYPH_SOURCE.EMPTY_GLYPH_SOURCE` | No non-trivia glyph candidate exists. |
| `GART.CORE_0_1.GLYPH_SOURCE.INCOMPLETE_GLYPH_RELATIONSHIP` | More than one non-trivia token occurs in the standalone context. |
| `GART.CORE_0_1.GLYPH_SOURCE.UNAUTHORIZED_SOURCE_FORM` | The single token contains more than one scalar. |
| `GART.CORE_0_1.GLYPH_SOURCE.UNRECOGNIZED_GLYPH` | The observed single candidate has no approved glyph mapping. |
| `GART.CORE_0_1.RESOURCE.TRANSCRIPT_LIMIT` | Transcript input exceeds the I-2 ceiling. |
| `GART.CORE_0_1.RESOURCE.SOURCE_PROFILE_LIMIT` | Source input exceeds the I-4 ceiling. |
| `GART.CORE_0_1.RESOURCE.SOURCE_DIAGNOSTIC_LIMIT` | Further source diagnostics exceed the bounded inventory. |
| `GART.CORE_0_1.RESOURCE.LEXICAL_ITEM_LIMIT` | Lexing would exceed the non-EOF item ceiling. |
| `GART.CORE_0_1.RESOURCE.SYNTAX_INPUT_LIMIT` | Supplied syntax input exceeds the I-6 item ceiling. |
| `GART.CORE_0_1.HOST.EXPECTED_STRING` | I-15 source argument is not an exact built-in string. |
| `GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED` | A guarded host allocation failed. |
| `GART.CORE_0_1.HOST.TRANSCRIPT_INVARIANT_FAILURE` | A supported transcript carrier violates its host invariants. |
| `GART.CORE_0_1.HOST.LEXICAL_RESULT_INVARIANT_FAILURE` | An I-5 result has inconsistent fields or boundary metadata. |
| `GART.CORE_0_1.HOST.LEXICAL_STREAM_INVARIANT_FAILURE` | A purported complete stream/map/item sequence violates its invariants. |
| `GART.CORE_0_1.HOST.GLYPH_IDENTITY_INVARIANT_FAILURE` | I-16 cannot establish consistent recognized mapping metadata. |
| `GART.CORE_0_1.CONTINUITY.ENTITY_ANCHOR_DIFFERENT` | The supplied entity-anchor observation is DIFFERENT. |
| `GART.CORE_0_1.CONTINUITY.ENTITY_ANCHOR_UNAVAILABLE` | The entity-anchor observation is UNAVAILABLE. |
| `GART.CORE_0_1.CONTINUITY.NEED_ANCHOR_DIFFERENT` | The unresolved-need-anchor observation is DIFFERENT. |
| `GART.CORE_0_1.CONTINUITY.NEED_ANCHOR_UNAVAILABLE` | The unresolved-need-anchor observation is UNAVAILABLE. |
| `GART.CORE_0_1.CONTINUITY.BOUNDARY_ANCHOR_DIFFERENT` | The authorized-boundary-anchor observation is DIFFERENT. |
| `GART.CORE_0_1.CONTINUITY.BOUNDARY_ANCHOR_UNAVAILABLE` | The authorized-boundary-anchor observation is UNAVAILABLE. |
| `GART.CORE_0_1.CONTINUITY.INTERVENING_FULFILLMENT_PRESENT` | Intervening fulfillment is observed PRESENT. |
| `GART.CORE_0_1.CONTINUITY.INTERVENING_FULFILLMENT_UNAVAILABLE` | The fulfillment observation is UNAVAILABLE. |
| `GART.CORE_0_1.CONTINUITY.EXPLICIT_CLOSURE_PRESENT` | Explicit closure is observed PRESENT. |
| `GART.CORE_0_1.CONTINUITY.EXPLICIT_CLOSURE_UNAVAILABLE` | The closure observation is UNAVAILABLE. |

**C11 — CONFIRMED: external presentation and privacy.** I-1 alone supplies a
transport JSON serializer. Its exact identifiers are schema
`gart-transport-observation-0.1`, profile `core-0.1`, and observation kind
`source-transport`. It includes the supplied `source_id`, `transport_result`,
and `reasons`; only success includes `decoded_scalar_count`. It omits raw source,
uses deterministic reference field order and ASCII-escaped JSON, and returns no
trailing newline. Its members do not introduce Reubarb types. There is no
approved serializer for a combined Core result.

The supplied `source_id` is emitted verbatim, so the demonstrated ID is an
opaque fixture label rather than a private filesystem path. Top-level source,
read, transcript and glyph-identity result representations redact source or
payload as documented. Exact content remains available through explicitly
selected in-memory fields, including I-1 decoded text and I-15 candidate
provenance. No claim of universal recursive redaction or physical memory erasure
is made. Core operations have no automatic output, telemetry or persistence.

## 10. Confirmed examples and counterexamples

The following examples restate accepted rules. Python literals in the host
examples, including `\uE100`, are host notation; Reubarb has no adopted quoted
string or Unicode-escape literal. Each Python block is self-contained when run
with this laboratory directory on the Python import path.

### E1 — Complete reviewed-text path

The confirmed Reubarb reading unit is:

```text
leg transcriptA
```

Its separate synthetic reviewed payload is `Core 0.1 observed text.`. The host
demonstration deliberately asserts review/acceptance of that fixed fixture:

```python
import core_0_1_transport_kernel as transport
import core_0_1_transcript_runtime as transcript
import core_0_1_read_instruction as read

source = transport.inspect_source_bytes(b"leg transcriptA", "core-0.1-i21-fixed-read")
assert source.succeeded
value = transcript.transcriptio("Core 0.1 observed text.", reviewed=True, accepted=True)
assert value.outcome == "admitted" and value.value is not None
result = read.observe_read_unit(source.decoded_text, target_name="transcriptA", target_value=value.value)
assert result.outcome == "observed"
assert result.observation.payload == "Core 0.1 observed text."
assert result.observation.diagnostic is None
```

The result is available in memory; it is not automatically printed. Source head,
gap, target and EOF spans are respectively `[0,3)`, `[3,4)`, `[4,15)`, `[15,15)`.

### E2 — Exact target agreement

```python
import core_0_1_transcript_runtime as transcript
import core_0_1_read_instruction as read

value = transcript.transcriptio("Reviewed fixture.", reviewed=True, accepted=True)
assert value.outcome == "admitted" and value.value is not None
result = read.observe_read_unit("leg transcriptA", target_name="transcripta", target_value=value.value)
assert result.outcome == "target-rejected" and result.observation is None
assert result.reasons[0].code == "GART.CORE_0_1.READ.TARGET_NAME_MISMATCH"
```

### E3 — A recognized G2 produces identity only

```python
from core_0_1_glyph_identity_value import form_glyph_identity_value

result = form_glyph_identity_value("\uE100")
assert result.outcome == "value-available"
assert result.value.design_id == 2
assert result.value.code_point_label == "U+E100"
```

### E4 — Unmapped candidate and incomplete glyph relationship

```python
from core_0_1_glyph_identity_value import form_glyph_identity_value

unknown = form_glyph_identity_value("\uE105")
assert unknown.outcome == "no-value" and unknown.value is None
assert unknown.source_observation.observation.outcome == "UNRECOGNIZED"
pair = form_glyph_identity_value("\uE100 \uE102")
assert pair.outcome == "syntax-rejected" and pair.value is None
assert pair.reasons[0].code == "GART.CORE_0_1.GLYPH_SOURCE.INCOMPLETE_GLYPH_RELATIONSHIP"
```

### E5 — Continuity requires all five explicit premises

```python
from core_0_1_occurrence_continuity import (
    AnchorObservation as A, EndObservation as E,
    SameOccurrenceEvidence, assess_same_occurrence,
)

same = assess_same_occurrence(SameOccurrenceEvidence(A.UNCHANGED, A.UNCHANGED, A.UNCHANGED, E.ABSENT, E.ABSENT))
assert same.outcome == "same-occurrence" and same.issues == ()
stopped = assess_same_occurrence(SameOccurrenceEvidence(A.UNCHANGED, A.UNCHANGED, A.UNAVAILABLE, E.ABSENT, E.ABSENT))
assert stopped.outcome == "classification-stopped"
assert stopped.issues[0].code == "GART.CORE_0_1.CONTINUITY.BOUNDARY_ANCHOR_UNAVAILABLE"
```

### E6 — Boundary-specific negative cases

Here `\n` and `\u...` describe scalar characters in host notation, not literal
backslash sequences submitted as Reubarb source.

| Explicit input or action | Existing result |
| --- | --- |
| I-1 bytes `EF BB BF` followed by a valid reading unit | No decoded text; `TRANSPORT.UTF8_BOM_FORBIDDEN` |
| Admit a payload with review omitted | No `textus`; `TRANSCRIPT.REVIEW_REQUIRED` |
| Admit an empty payload with both review flags true | `admitted`; later observation returns the exact empty payload |
| I-7 `LEG transcriptA` | `syntax-rejected`; `SYNTAX.EXPECTED_READ_HEAD` |
| I-7 `leg\ntranscriptA` | `syntax-rejected`; `SYNTAX.EXPECTED_HORIZONTAL_GAP` |
| I-7 `leg 0` | `syntax-rejected`; `SYNTAX.EXPECTED_TARGET_NAME` |
| I-7 `leg transcriptA extra` | `syntax-rejected`; `SYNTAX.EXPECTED_READ_EOF` |
| I-7 `leg RECON`, with supplied label `RECON` and admitted value | Exact text observation; the name does not invoke reconciliation |
| I-7 matching label but raw host text as the value | `rejected`; `TRANSCRIPT.EXPECTED_TEXTUS` |
| I-5 `00` | `context-required`; `LEXICAL.ZERO_BOUNDARY_REQUIRED` |
| I-5 `\uE100` | `context-required`; I-15 is the separate approved resolver |
| I-16 `\uE101` | Inert G3 identity; no fulfilled-event assertion |
| I-16 `\uE100\uE102` | `syntax-rejected`; `GLYPH_SOURCE.UNAUTHORIZED_SOURCE_FORM` |
| I-16 `\uE100//note` | `syntax-rejected`; direct contextual adjacency is one multi-scalar token |
| I-16 `\uE100 //note` | `value-available`; accepted token separation preserves G2 |
| I-11 `rb.g2` | `UNRECOGNIZED`; no shortcut expansion |
| I-11 empty string | `INVALID_INPUT` |

Reason suffixes in this table all use the full `GART.CORE_0_1.` prefix.

## 11. Traceability and verification

**C12 — CONFIRMED: bounded evidence and reproducible checks.** The fixed
[combined runner](run_core_0_1_checks.py) names every suite and verifies its
exact test count. The active regression contains these 400 methods:

| Gate | Fixed suite | Count | Contract coverage |
| --- | --- | --- | --- |
| I-1 | [TransportKernelTests](test_core_0_1_transport_kernel.py) | 23 | C02, C10, C11 |
| I-2 | [TranscriptRuntimeTests](test_core_0_1_transcript_runtime.py) | 24 | C05, C10, C11 |
| I-3 | [PackageBoundaryTests](test_core_0_1_package_boundaries.py) | 16 | C02/C05 separation, C10, C11 |
| I-4 | [SourceProfileTests](test_core_0_1_source_profile.py) | 36 | C02, C03, C10, C11 |
| I-5 | [LexicalFrontendTests](test_core_0_1_lexical_frontend.py) | 42 | C04, C10, C11 |
| I-6 | [SyntaxSkeletonTests](test_core_0_1_syntax_skeleton.py) | 44 | C04, C10, C11 |
| I-7 | [ReadInstructionTests](test_core_0_1_read_instruction.py) | 60 | C05, C06, C10, C11 |
| I-8 | [GlyphTechnicalTests](test_core_0_1_glyph_technical.py) | 8 | C07 historical frame/proposal record |
| I-9 | [GlyphGeometryTests](test_core_0_1_glyph_geometry.py) | 12 | C07 approved geometry |
| I-10 | [GlyphEncodingTests](test_core_0_1_glyph_encoding.py) | 14 | C07 mappings/snippets |
| I-11 | [GlyphRecognizerTests](test_core_0_1_glyph_recognizer.py) | 20 | C08 recognition |
| I-12 | [GlyphDisplayTests](test_core_0_1_glyph_display.py) | 12 | C07 display references |
| I-13 | [GlyphFontTests](test_core_0_1_glyph_font.py) | 12 | C07 delivered font/provenance |
| I-15 | [GlyphSourceIntegrationTests](test_core_0_1_glyph_source_integration.py) | 11 | C08 candidate context, C10 |
| I-16 | [GlyphIdentityValueTests](test_core_0_1_glyph_identity_value.py) | 16 | C08 inert value, C10, C11 |
| I-18 | [OccurrenceContinuityTests](test_core_0_1_occurrence_continuity.py) | 18 | C09 all 243 input combinations |
| I-20 | [GlyphIdentityPathTests](test_core_0_1_glyph_identity_path.py) | 20 | C08 accepted terminal glyph path |
| I-21 | [ReviewedTextPathTests](test_core_0_1_reviewed_text_path.py) | 12 | C02–C06 accepted terminal read path |
| Total | 18 named classes | 400 | Fixed accepted regression |

I-14 has user-observed display evidence. I-17 and I-19 are conceptual gates;
I-22 consolidates documentation. None adds invented test counts. C01 is the
user's versioning decision, not a theorem established by executing the suite.
The conceptual commitments in Section 12 are not covered as an implemented
Source or RECON engine by these 400 tests.

The runner hashes its 63 named code/test/runner/asset files before and after the
run. The comparison detects changes during that run, not signed authenticity
or every possible side effect. This contract is not yet part of a frozen
artifact manifest. Tests are finite, foreground, synthetic, and require no
network, new dependencies, model, OCR, personal transcript, or GUI launch.
The font tests inspect delivered artifacts without rebuilding/installing them.

From the directory containing the Core 0.1 files, run this in PowerShell:

```powershell
py -3.13 -B .\run_core_0_1_checks_full.py
```

Expected successful footer: `CHECKS PASSED: 400 of 400. All fixed gate files are unchanged.`
The wrapper also reports `Combined checks passed: I-1 through I-21 total 400 tests.`
The elapsed time is measured per run and is not a language performance guarantee.
The accepted final I-21 run took 2.107 seconds.

The [reviewed-text runner](run_core_0_1_reviewed_text_path_checks.py) provides
the twelve-test focused demonstration; the
[glyph-path runner](run_core_0_1_glyph_identity_path_checks.py) provides twenty
focused glyph checks. Neither runner accepts transcript or program arguments.

I-22 verification on 2026-09-06: all five Python examples and the seventeen E6
cases matched their stated results. A static audit verified all 47 local links,
twelve clause labels, every one of the 48 existing reason codes, and the
eighteen test classes/counts. The existing full regression passed 400/400 in
1.566 seconds. All 63 fixed files matched their pre-I-22 hashes, and no matching
foundation runner process remained. These are observations in this existing
checkout; the fresh-entry/freeze verification is still the next gate.

## 12. Confirmed conceptual commitments retained for later layers

These commitments remain **CONFIRMED CONCEPTUAL** as recorded in AGENTS.md.
They constrain later design; they are not additional executable productions or
claims that the Foundation runtime already implements every required actor,
evidence record, transition, or outcome. I-18 is only the bounded reduction
specified in Section 8. The complete decision history remains authoritative.

| Area | Preserved commitment | Operational boundary still open/deferred |
| --- | --- | --- |
| Dynamic typing | Types belong to runtime values; exact case remains significant. | General values, bindings, type interactions and mutability rules |
| Source membership | One retrieval, one transfer and one execution value form the fixed three Source identities per runtime, each with distinct type identity. | Bootstrap, construction, state representation and transitions |
| Source authority | Autonomous tasks use the three congruently as a whole; execution has the final bounded manual authorizing role. | Concrete grant/actor/decision machinery |
| Source state | Individual or combined internal changes may preserve the three identities and fixed membership. | State contents, trigger, ordering, atomicity and recovery |
| Facts and disputes | A dispute creates a distinct non-authoritative fact pending manual Source approval; affected rule optimization preserves rule identity and unaffected extent. | Evidence, adjudication, optimization and resumption procedures |
| Optimization purpose | Efficiency preserves the target; effectiveness may preserve or change it through the existing Source's manual approval event. | Concrete transformation and comparison rules |
| Boundary-local zero | Each boundary owns its local zero; other boundaries cannot borrow it. | Target equality, carriers, membership and cross-boundary transitions |
| Source zero | Internal to the existing Source model, strong-positive conceptually, related to approved local zeros through resemblance and absence. | Internal carrier, exact proof predicate and local-zero existence approval |
| Abstract junction | One path identity occupies two orientation roles meeting at the same boundary-owned local zero. | Transition coincidence; no implemented physical time, movement or simultaneity |
| Congruent statement | Represents Source-zero rules and may validate/execute only within prior bounded delegation; outcomes do not create retroactive authority. | Grant representation, validation, activation, execution and revocation |
| Glyph family | G4/G5/G6 retain separate stable identities within one Reversion/Dependence family; centerless G1 is construction material. | Event association and choice of a partner for G2 |
| Individual versus joint result | An exact mapped glyph remains recognizable without its partner; G3 has the conceptual fulfilled-result role. | Pairing and the congruence determination that establishes an event result |
| Event-specific need | Enduring entity identity differs from one unresolved RECON need and from its attempts; prior fulfilled results are not silently erased. | Need detection, scheduling, instance records and storage |
| Equal necessity | Abstract seeking and physical participation are both necessary; the half-and-half description supplies no numeric percentage. | Exact completion/evidence predicate |
| Capability and intent | Authorization polarity is event-relative; neutral RECON intent can occur on either side of a boundary. | Evidence classification and runtime carriers |
| G5 | Neutral/non-seeking intent carries an unresolved event-specific need. | Observation of seeking and event designation transitions |
| First seeking | Established absence of a predecessor selects G4/Strong after seeking begins; unavailable history is not established absence. | Applicable history chain and evidence |
| Repeated seeking | Verified authorized engagement selects G4/Strong even after failure; refusal/failure to engage selects G6/Weak. | Engagement timing, observer and same-event evidence |
| Engagement | At least one observable authorized action toward the objective is required; willingness alone is insufficient. | Evidence format and transition mechanism |
| Transaction qualification | Seeking plus the action qualifies both sides; completion additionally requires a congruence determination. | Congruence actor, predicate and relation to task completion |
| Fulfillment matrix, I-17 | Positive/Negative identity and Strong/Weak charge are necessary placements; neither alone proves fulfillment. Neutral cannot be fulfilled while Neutral. | Classification evidence, timing and runtime representation |
| Hindsight, I-17 | Fulfillment precedes explicit Source certification of event-relative identity and charge; during-task evidence can guide but does not guarantee it. | Certification/history records and forecasting representation |
| Retry, I-17/I-18 | A permitted new attempt may stay in the same unresolved occurrence, with its prior evidence preserved; fulfillment or explicit closure ends it. | Retry trigger/limits, persistence, closure actor and occurrence creation |
| Distinct neutral conditions, I-19 | G5's non-seeking condition differs from unplaced matrix identity; resolving one does not automatically resolve the other. | Combined representation and classification operations |
| Improvement and stopping | Avoiding a previous fault after reconciliation is fallible later improvement; reaching authorized scope supplies a stopping point. | Learning, stop predicates and governed layer topology |
| Unknown candidates | No mapping supplies no authority; explicit nomination is necessary for a separate candidate library. | Admission sufficiency, provenance, storage, queues, quarantine and training |

The Source's authorizing role does not assert infallibility or authority outside
its boundary. A boundedly undefeated comparison needs complete evidence within
a finite approved boundary and revision; incomplete evidence is inconclusive.
Theological design provenance is retained in AGENTS.md and does not supply
unimplemented executable predicates. The withdrawn I-17 G2/G4-only proposal
does not become a pairing rule in this contract.

## 13. Deferred scope and the freeze checkpoint

The accepted spellings do not yet provide general literals, numeric/Boolean
types, arithmetic, comparison, coercion, assignment, scope, operators,
expressions, sequencing, functions, loops, modules, or an evaluator/CLI for
general programs. `WITH`, `OR`, `FALSE`, `RECON`, and `DPEND` still lack the
complete operand, precedence and evaluation contracts needed to execute them.
Their approved names and conceptual meanings remain preserved.

Broader glyph relationships, the Source runtime, boundary decisions, event
history, executable RECON, authorized self-improvement, and language-level
unknown behavior require explicit later semantics. Host diagnostic handling
does not implement the novel exception or rule-change process. Voice, model
providers, tool use, and the public STUTT prototype are separate application
work. Research vocabulary, witness sigla and contextual examples do not enter
the executable registry automatically. Completed BHS pages 22–31 remain saved
evidence; I-22 does not rescan them.

I-20 completed the chosen minimal glyph endpoint. I-21 completed the separate
reviewed-text demonstration. The user accepted I-22's consolidated contract by
explicitly directing continuation to I-23. I-23 prepares a fresh-entry
demonstration, a reviewable candidate file/version inventory and full regression
evidence for the user's explicit freeze decision. I-23.1 changes this document's
gate status only; clauses C01-C12, examples and compatibility details are
unchanged from I-22.1. The separate I-23 review record identifies the candidate,
verification environment, evidence and limits. The user subsequently stated,
"i approve this and lets pause here". This explicitly freezes clauses C01-C12
as the bounded Core 0.1 Foundation. It does not promote Section 12's conceptual
material into executable behavior, claim a clean-machine installation, publish
a release, or begin Stage 0.2 during this paused checkpoint.

Stage 0.2 starts after that freeze. Small accepted changes remain in
[PUBLIC_RELEASE_SYNC_QUEUE.md](PUBLIC_RELEASE_SYNC_QUEUE.md) for a coherent
foundation release with documentation, licensing scope, changelog, examples,
and limitations aligned. This document does not itself publish a release.
