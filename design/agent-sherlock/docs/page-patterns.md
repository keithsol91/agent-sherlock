# Page patterns and reusable copy

These are design specifications. Only the homepage's visual direction has been approved; documentation, setup, and case-file patterns are consistent extensions for future work. They are not claims that those screens exist.

## Homepage: preserve the approved composition

At a 1440 px viewport, center content in a maximum 1200 px container. Use a two-column hero at 960 px and above, close to a 50/50 split, with the mascot toward the right. Let the headline wrap naturally; do not insert a forced desktop line break that damages the mobile layout.

1. **Header.** Head icon plus Agent Sherlock wordmark; Skills, Docs, Contribute; GitHub link. Keep the header on the cream canvas. No sticky conversion bar.
2. **Hero.** Left: eyebrow, heading, short description, gold GitHub action, understated docs link. Right: approved character with case folder and a few clues. Put text first in mobile reading order.
3. **Capabilities.** One heading and four illustrated items on the open cream surface. Four columns above 960 px, two from 640 px, one below 640 px. Each item has an illustration, heading, and one short description. No tiny dashboard screenshots.
4. **Example.** One broad pale-blue panel. Example case at left, three plain outcomes at right. It must say Example, not Live. Stack on mobile.
5. **Participation.** Compact invitation to use and contribute. One gold Get started action, one contribution link, optional small supporting illustration. No signup gate.
6. **Footer.** Wordmark and simple Docs, GitHub, Contribute links. Do not add a license label until the repository license is known.

## Approved homepage copy

| Element | Copy |
| --- | --- |
| Eyebrow | Free & open source |
| Heading | Meet your new AI detective. |
| Body | Sherlock investigates competitors, keeps your CRM and case files current, and remembers the facts your other agents need. |
| Primary action | View on GitHub |
| Secondary action | Read the docs |
| Capability heading | A few things Sherlock can do. |
| Skill 1 | Investigate competitors |
| Skill 1 description | Follow their moves. Connect the clues. |
| Skill 2 | Keep your CRM current |
| Skill 2 description | Read records, add facts, update the details. |
| Skill 3 | Build living case files |
| Skill 3 description | Keep evidence and account history together. |
| Skill 4 | Remember for the team |
| Skill 4 description | Give other agents the context they need. |
| Example heading | From a clue to shared context. |
| Example request | What changed with our competitor? |
| Example outcomes | New signal found / CRM and case file updated / Context ready for other agents |
| Participation heading | Your detective. Your repo to explore. |
| Participation body | Use Sherlock. Explore the code. Help make him better. |
| Participation links | Get started / Contribute on GitHub |
| Setup cost note | Sherlock is free. Model providers and connected services may charge separately. |

The wording above preserves the image. If actual repository behavior cannot support a capability, qualify the wording or mark it as planned before publication. The illustrative workflow is not a blanket claim that a CRM write and a case-file write are atomic.

## Documentation extension

Use the same cream, headings, links, and spacing in a quieter reading surface. Give each page a title, a one-sentence purpose, prerequisites when necessary, steps, and a concrete result. Main prose is no wider than 65ch. Use a left topic rail only when there are enough real pages to justify it; keep it collapsible on small screens.

Show real commands as selectable text in code blocks. Copy controls must announce Copied and a failed copy. Do not invent installation commands from the project name. Keep costs, credentials, and prerequisites near the step where the user needs them. Decorative Sherlock can appear once at the top or in an empty state; he must not interrupt every paragraph.

Recommended information architecture, populated only when content exists: Overview; Getting started; Skills; Integrations; Case files and memory; Configuration; Troubleshooting; Contributing. The public header remains short; do not promote all these into top navigation.

## Skill detail extension

Use: skill name, plain summary, inputs, actions, outputs, prerequisites, example, and limitations. For example, a competitor skill can show a source URL and a requested question, then the kind of evidence returned. The example is labeled; supported sources and scheduling behavior must come from code. Do not show universal website support or round-the-clock monitoring without implementation evidence.

## Case file extension

Use a readable document with grouped rows, not an evidence-board wallpaper. Recommended fields: account or subject; concise summary; evidence with source links and observed dates; relevant facts; open questions; activity history; proposed next action. Compact status text shows Fresh, Needs review, or Could not refresh only when supported by state.

Keep inferred meaning separate from observed evidence. Explain whether a fact was retrieved from a saved case file or newly researched. Do not promise perfect recall or pretend missing context is known.

## CRM change extension

If an interface for updates is requested, show the affected record, fields changing, old and proposed values, and source/context. Match the application's existing permission model. Use a review step where the existing workflow calls for one; the design system does not create a new approval policy.

Show independent results if CRM and case-file writes can succeed separately. Example: "Case file saved. CRM update failed." Give a useful retry action for the failed step; never repeat successful writes unnecessarily.

## GitHub README and social use

README header: one compact mascot/wordmark image, one sentence describing the project, genuine setup and docs links. Keep core information as Markdown text. Avoid a giant homepage screenshot as the only introduction. Show stars, license, version, CI, or package badges only if backed by real repository data.

Social preview specification: 1200 x 630 px, cream canvas, short ink heading, one mascot, generous margins. Keep essential content inside a 72 px safe zone. The asset is specified but not included in this release; see the registry.

## Layout guardrails

Use 48-64 px vertical section spacing on mobile and 64-96 px on desktop. Keep related heading/body elements 12-24 px apart. A section is not improved by adding another illustration. Two typography families, one main action per decision area, and a restrained surface palette should remain obvious at a glance.

Build at 390, 768, and 1440 px; inspect 320 px for overflow. The CSS starter allows short navigation links to wrap; when implementing a full narrow-screen header, use a labeled menu disclosure if the links do not fit comfortably. Do not hide navigation until its toggle and keyboard behavior are implemented. At 640-959 px, keep the hero stacked while capabilities form two columns. At 960+ px the hero and example can split into columns.
