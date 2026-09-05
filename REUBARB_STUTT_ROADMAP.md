# Reubarb Pi, STUTT, and public release

Status: working delivery plan, 2026-09-05. The user confirmed that the glyphs
render after a computer restart, requested larger glyphs while keeping ordinary
text at its existing size, and named the intended personal assistant STUTT.
This plan records that direction; new language rules still follow the existing
approval process in AGENTS.md.

## Where we are

The foundation is working, but the general language is not finished:

| Component | Present capability | Remaining work |
| --- | --- | --- |
| Source handling | UTF-8 transport, source checks, exact-case lexing, positions and diagnostics | Additional approved source forms |
| Reviewed text | Immutable `textus`, explicit `transcriptio`, repeatable `leg` | General values, bindings and program composition |
| First instruction | `leg transcriptA` parses and observes one explicitly supplied reviewed value | General evaluator, functions, scope and control flow |
| Native glyphs | G2–G6 geometry, five PUA mappings, snippets, recognition, installed font | Their grammatical roles and executable relationships |
| Identity, boundary and RECON | Confirmed conceptual constraints and bounded experiments | Complete operational contracts and execution tests |
| Voice Bridge | Local draft review, freeze and manual copy | STUTT speech, reasoning, tools and memory |

The 191-head research history and later contextual work remain evidence for
language design. Having a vocabulary entry is different from having a complete
rule for a program to execute. Continue from the saved evidence; do not restart
the completed BHS pages 22–31 scan.

## 1. Finish a defined Reubarb version

Define completion against a finite versioned specification. A language can have
a complete usable release and still gain richer later versions.

First consolidate the accepted core into a readable contract with traceable
tests. Resolve the smallest remaining grammar and semantics needed to write a
real program: native glyph roles, values and literals, names and bindings,
scope, operations, program sequencing, and explicit results. Then add reusable
functions, branching/repetition, modules, and the small library needed by STUTT.
These are capability requirements for review, not invented target spellings.

Identity, boundary, Source authorization, RECON, DPEND, unknown input, event
history and completion need concrete rules and counterexamples. Existing
conceptual approvals stay authoritative; unresolved details are presented one
at a time in plain language with a recommended answer and observable effects.
Routine host implementation and tests proceed under the user's delegation.

Exit criteria: documented source grammar and meanings; an interpreter and CLI;
small programs with exact expected outputs; clear invalid/unknown results;
repeatable tests; bounded execution and a working stop path; a frozen versioned
contract. The first release need not implement every future research idea.

## 2. Build STUTT on that foundation

First prove one useful local interaction from beginning to end: receive typed
input, interpret a requested task, check its allowed scope, perform one harmless
authorized operation, show its result, and stop. The exact first task is chosen
when this stage begins.

Then add voice input/output, a replaceable reasoning model, a small set of
permissioned tools, user-controlled memory and a visible decision history.
Reubarb supplies the program and rule layer. A reasoning model supplies language
understanding and proposals. A new language does not by itself provide model
intelligence; model selection comes after the interface and acceptance task are
clear. Training a model from scratch is not a prerequisite.

The first executable STUTT command path is now scaffolded in
`stutt_command_path.py`:

- expanded allow-list routing for harmless operations:
  `status`, `commands`, `now`, `echo`, `count`, `trim`, `reverse`,
  `upper`, `lower`, `json`, `font`, `glyphs`, `model-backends`,
  `list-files`, `check-glyph-map`, `env-profile`, `readme`, `roadmap`,
  `status-overview`
- optional model-assisted intent normalization through the NVIDIA-first adapter config
- one-shot and interactive modes
- no filesystem mutation or external side-effectful action yet, only local output

Model provider strategy is now explicit:

- NVIDIA/open-weight endpoints are the preferred first stack.
- Reubarb/STUTT core behavior stays unchanged and calls only the adapter contract.
- Model provider integration is replaceable: any OpenAI-compatible backend can be
  added by editing one config file and creating one backend class if needed.
- For NVIDIA, start with `stutt_model_backends.example.json` and `NVIDIA_API_KEY`
  (or your own env var name) and run the adapter without changing STUTT logic.

Test cancellation and complete child-process cleanup, mistakes in tool requests,
unrecognized input, authorization boundaries and recovery. Improvement can
produce reviewable proposals and regression tests; the existing rules do not
grant STUTT authority to silently rewrite its own governing contract.

Exit criteria: the agreed local tasks work reliably; actions and failures are
visible; stop and recovery work; access and retention match the chosen profile;
the assistant passes its task and boundary tests.

## 3. Prepare and publish a reviewable release

Prepare a clean release tree with a quickstart, examples, specification, font
and input instructions, test command, known limitations, issue templates and
contribution guidance. Inventory code, glyph artwork and research-source rights
and select explicit distribution licenses. Keep private transcripts, local logs,
credentials and unapproved corpus files out of that release tree.

Verify installation and tests from a fresh environment. Choose the public
repository and publish a tagged release with reproducible bug-report steps.
Review improvements against the versioned contract; bug fixes preserve that
contract, while intended changes receive a new version. Preparing a release
does not automatically publish the current working folder.

Exit criteria: another person can install, run examples, reproduce tests,
report a defect, and submit a change without this conversation.

## Immediate next gate

Prepare I-15 as the first native-glyph source-integration proposal:

1. Inventory the already accepted meanings and the exact operational gaps.
2. Derive one minimal glyph-bearing `.gart` example from those decisions and
   the saved BHS/contextual evidence, labelling any new rule as a proposal.
3. Pair it with an ordinary successful case, an unknown input, an incomplete
   relationship, and an unauthorized request, each with an explicit result.
4. Bring the first unresolved semantic choice to the user with a concrete
   recommendation; implement and test the accepted slice before expanding it.

The existing `leg transcriptA` behavior remains the executable baseline. This
plan does not claim that the proposed glyph program is already valid syntax.

## Glyph legibility

Ordinary editor text stays at the previous 24px. Current HTML views enlarge
glyphs independently and the Voice Bridge uses a 100px tag only on U+E100–U+E104.
The font binary and canonical drawing proportions are unchanged.

The installed VS Code public decoration API has no per-character `fontSize`
property. Its editor and terminal size settings affect all text. Uniform zoom
therefore does not meet the user's request. Glyph-only enlargement in the normal
VS Code editor remains an explicit host-display task, with a supported custom
reading/editor surface to evaluate; do not inject undocumented CSS or silently
enlarge ordinary text again. Third-party apps and chat have their own rendering
controls and are not changed by project settings.

Engineering reference: [VS Code public decoration API](https://github.com/microsoft/vscode/blob/main/src/vscode-dts/vscode.d.ts).
