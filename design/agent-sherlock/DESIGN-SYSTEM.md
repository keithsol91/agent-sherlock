# Agent Sherlock design system

Version 1.0.0 · 6 September 2026 · Website, documentation, illustration, and future interface guidance

## 1. Start here

Agent Sherlock is a free, open-source AI detective. He investigates competitors, reads and updates CRM records, maintains living case files, and remembers facts other agents need. The design should make those capabilities understandable and make the code easy to explore.

**The approved visual source is `reference/approved-homepage.png`.** Inspect that image before designing or implementing anything. Its cartoon character, warm cream canvas, large editorial headings, generous space, approachable illustrations, yellow GitHub buttons, and pale blue example panel define this system.

The realistic watercolor portrait supplied later is historical context. The user explicitly chose the newer cartoon direction. Do not blend the two, reproduce the portrait, change Sherlock's apparent age, or introduce actor likeness. Preserve the approved cartoon's youthful adult, curious, capable, relaxed personality.

The screenshot is an approved visual direction, not a working interface, extracted asset library, or proof of software behavior. The numerical values, font choices, component states, and responsive rules below are **proposed production specifications** chosen to translate it into a consistent system. They were not recovered from an original source design. Future application patterns are labeled separately.

The user's latest explicit instructions take precedence. Within this package, the approved image owns the character and visual direction, this handbook owns brand intent, `tokens/tokens.json` owns exact numeric values, and `docs/components.md` owns component behavior. CSS and the visual PDF consume those specifications; correct them if they drift. Task-specific instructions fill in the requested surface and outcome. Resolve conflicts using these ownership rules rather than inventing a new brand.

## 2. What the brand must communicate

**Curiosity with a purpose.** Sherlock finds useful facts, connects relevant evidence, and helps a team act with context. A magnifying glass, a folder, a record, and a note explain the product better than generic glowing AI imagery.

**Friendly competence.** The character can be playful while the interface remains precise. Use a relaxed smile, alert eyebrows, clear labels, and straightforward language. Avoid smug expressions, sinister investigation themes, surveillance imagery, or exaggerated genius claims.

**Open-source generosity.** The central invitation is to explore, use, and contribute to the repository. GitHub and documentation are the main destinations. Do not add pricing tiers, sales forms, countdowns, fabricated testimonials, lead capture gates, “book a demo,” or “start a free trial.”

**Room to understand.** Each section has one job. Use large illustrations and concise explanations, with visible space between them. Do not turn every sentence into a bordered card or surround the mascot with a cloud of interface screenshots.

**Evidence before certainty.** Product copy may explain intended capabilities; a real workflow must distinguish observations, interpretations, proposed edits, and completed actions. Detective language never excuses ambiguous status or unsupported claims.

The memorable combination is warm paper, dark ink, a yellow invitation, a blue case folder, and one curious detective. Preserve that combination across pages.

## 3. Canonical Sherlock

### Identity and silhouette

Sherlock is a simplified, illustrated young adult detective with black curls, a tan deerstalker, tan coat, white shirt, dark tie and lapels, and warm skin. The face is expressive and slightly oversized. He holds a magnifying glass over one eye and works behind a blue case folder in the hero.

These features are invariant:

| Feature | Required treatment |
|---|---|
| Hair | Dark, rounded curls visible beneath the hat; keep their chunky silhouette. |
| Hat | Tan deerstalker, curved brim, simple darker check lines, small tied top detail. |
| Face | Warm skin, compact curved nose, large dark eyes, expressive brows, small relaxed smile. |
| Magnifying glass | Round dark rim, blue glass tint, visible handle, one visibly enlarged eye. |
| Outfit | Tan coat with broad collar; dark inner lapels and tie; small white shirt area. |
| Folder | Muted blue, dark outline, simple cream label; strong horizontal foreground shape. |
| Outline | Confident near-black, rounded joins, slightly organic; consistent visual weight. |
| Personality | Curious, attentive, helpful, calm; a collaborator other agents can trust. |

For new artwork, preserve the relative proportions visible in the reference: an oversized head, compact torso, rounded hands, and barely emphasized neck. Compare new art directly with the approved silhouette at thumbnail size and at its intended crop. Do not impose one numeric head-to-body ratio on full-body, bust, and head-only artwork. A change of pose must still read as the same person.

### Permitted variations

New poses may show Sherlock examining a note, updating a record, placing evidence in a folder, offering a fact to another detective, reading a book, or peeking from behind a case file. Keep the face, hair, hat, coat, line style, and relative proportions stable.

Use surprise sparingly and gently: lifted brows or a small discovery gesture. For errors, use a neutral attentive face; for success, a modest smile. The user should never feel mocked by the mascot. Do not introduce new facial hair, glasses, pipe, scars, gray hair, photoreal skin, different clothing colors, or a new age interpretation.

The second detective in the memory illustration represents another agent. It does not establish a named character or a new product. Additional agent characters remain an extension requiring a clear brief; reuse simple silhouettes without inventing a cast.

### Rendering and asset production

Use 2D cartoon illustration with broad color areas and restrained soft shading. Preserve the reference's hand-drawn warmth without adding complex fabric weave, dramatic lighting, 3D depth, glossy plastic, heavy paper grain, or tiny decorative hatching. Soft pale blue grounding shadows are permitted beneath larger objects. Small yellow discovery marks are accents, not confetti.

The screenshot is currently the only approved complete artwork. There is no approved standalone vector mascot, transparent hero cutout, logo file, favicon, or pose library in this specification. Newly produced assets must be labeled candidates until checked against the source. A screenshot crop is a reference crop, not a production-ready logo or clean reusable illustration.

For new delivery assets, prefer transparent SVG when truly vector-authored and appropriate, or transparent PNG/WebP for raster art. Do not wrap a raster image in SVG and describe it as vector. Export at enough resolution for the intended display size, retain the source, and record provenance and review status.

## 4. Illustration, logo, and interface icons

Brand illustrations tell the story: binoculars for competitor investigation; a record, pencil, and check for CRM updates; layered folders for living case files; two detectives sharing a record for memory. Keep the four illustrations distinct but similar in apparent size, density, outline weight, and color balance.

A functional interface icon has a different job. Use one consistent simple outline icon family for search, navigation, copy, external links, loading, and disclosure. A proposed default is a 20 or 24 px icon on a consistent stroke grid. Do not miniaturize the illustrated binoculars into a toolbar control. Pair unfamiliar icons with visible text.

The approved header uses a small illustrated head with an “Agent Sherlock” wordmark. Preserve that relationship while a proper logo asset is developed. The wordmark should remain readable without the head. As a proposed production rule, leave at least half the mascot head height around a logo lockup; do not place it on a noisy surface or force it into a tiny header.

Use GitHub's official mark only from a verified official source and follow its applicable usage guidance. Do not redraw it with an image model, imply sponsorship, or treat the reference's rendered mark as an approved asset. A text GitHub link is an acceptable interim implementation.

## 5. Color system

These are selected production colors inspired by the approved image, **not sampled or exact recovered values**. Use semantic tokens for interfaces. Brand color alone does not communicate status.

| Role | Value | Intended use |
|---|---|---|
| Canvas | `#FAF8F1` | Primary warm cream page background. |
| Ink | `#151820` | Headings, primary labels, illustrations' dark outline. |
| Body | `#343C49` | Paragraphs and ordinary interface text. |
| Muted | `#59616D` | Supporting text, timestamps, captions. |
| Gold | `#F4BD50` | Primary button background and discovery accents. |
| Gold hover | `#E6A83B` | Primary button hover; retain ink label. |
| Ochre | `#966016` | Restrained eyebrow text and warm emphasis. |
| Blue soft | `#E3F0F5` | Example panel and light contextual surfaces. |
| Blue | `#527A91` | Folder illustration and decorative brand detail. |
| Link | `#215B78` | Functional text links and focus indication. |
| Sage | `#537764` | Confirmed success indicator. |
| Sage soft | `#E8F0E8` | Success surface. |
| Red | `#A2342B` | Error text and failed action indicator. |
| Red soft | `#FAE9E4` | Error surface. |
| Line | `#CAC8BE` | Nonessential dividers and decorative boundaries. |
| Control border | `#7B817B` | Input boundaries and necessary UI outlines. |
| White | `#FFFFFF` | Select control surfaces and approved inverse labels. |
| Coat | `#CEA164` | Mascot-only tan. |
| Skin | `#EFC58E` | Mascot-only warm skin. |

Ink belongs on gold buttons; white is not their default label color. Use body or ink text inside soft blue panels. Decorative blue is not the universal link or status color. Pale dividers must not substitute for required control boundaries. Do not use coat or skin colors for semantic states.

Contrast must be checked for actual foreground, background, weight, and size combinations, including hover, focus, and disabled explanatory text. Use ink or body for small status labels on soft semantic surfaces; sage on sage-soft and decorative blue on blue-soft are unsuitable for normal-size text. Link blue on gold also fails normal-text contrast, so gold buttons use ink. Consult the supplied contrast audit; never assume every pair in the palette is accessible.

## 6. Typography

The proposed production font pair is **Fraunces 700** for editorial headings and the textual wordmark, with **Inter 400/600** for body and interface text. These fonts were selected to match the reference's character; they are not identified original fonts. Use a system monospace stack for code only. The implementation baseline uses Fraunces optical size 72, softness 0, and wonk 0; Inter uses optical size 14. `styles/fonts.css` loads the bundled fonts; the typography tokens and `styles/components.css` apply their settings. Preserve those choices rather than letting agents independently pick variable-font settings.

| Use | Size and treatment |
|---|---|
| Hero heading | Fluid 44–80 px; weight 700; line height about 1.0–1.06. |
| Section heading | Fluid 32–48 px; weight 700; line height about 1.1–1.15. |
| Capability or subsection heading | 24–28 px; weight 700; line height about 1.15–1.2. |
| Lead paragraph | 20–22 px; weight 400; line height 1.4–1.5. |
| Body | 16 px; weight 400; line height 1.6. |
| Button and navigation | 16 px; weight 600; comfortable control height. |
| Caption and supporting label | 14 px; line height about 1.5. |

Use sentence case. A short all-caps eyebrow such as “FREE & OPEN SOURCE” is permitted with restrained tracking; do not use spaced capitals for paragraphs or navigation. Keep paragraphs under roughly 65 characters per line. Avoid thin display type, extreme tracking, condensed techno fonts, and type rendered into images.

Headings must remain live text. Use intentional line breaks only where a specific layout supports them; remove forced breaks when they create awkward mobile wrapping. Load only necessary font weights, define robust serif/sans-serif fallbacks, and preserve font license notices when redistributing font files.

## 7. Layout and spacing

Use a centered container with a maximum width of **1200 px**. Default side gutters are 24 px on mobile, 32 px on tablet, and 48 px on desktop. Prose pages use a maximum reading width of **65ch** within that container.

The spacing scale is **0, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128 px**. Use small steps inside controls, 16–24 px between related content, and 64–96 px between major sections. The page should breathe without wasting a mobile viewport on empty space.

Breakpoints are **640, 960, and 1280 px**. They describe layout transitions, not particular devices. Use a 32 px desktop grid gap and a 24 px tablet grid gap; keep narrow-screen layouts flexible.

| Width | Layout rule |
|---|---|
| Below 640 px | Single-column hero and capabilities; full readable labels; content order follows reading order. |
| 640–959 px | Capabilities may use two columns; hero stays stacked unless both columns remain comfortable. |
| 960–1279 px | Two-column hero, four capability columns, two-column example panel. |
| 1280 px and above | Same structure; stop content growth at the 1200 px container. |

Default radii are **12 px for buttons, 8 px for fields, and 16 px for panels**. Do not use pill-shaped everything. Keep ordinary capabilities unboxed. Use borders and backgrounds only where they establish a meaningful grouping, interactive boundary, or status.

Avoid decorative drop shadows on every element. The cartoon can carry illustrated shadows; functional surfaces should primarily use spacing, a clear background, and a restrained border.

## 8. Approved homepage structure

Preserve the reference's order and hierarchy:

1. **Header:** mascot/wordmark left; Skills, Docs, and Contribute navigation; GitHub destination right. Link destinations must be verified before publishing.
2. **Hero:** eyebrow, “Meet your new AI detective.” heading, a short capability summary, yellow “View on GitHub” button, secondary “Read the docs” link, and the large Sherlock illustration. Text appears first in the mobile reading order.
3. **Capabilities:** “A few things Sherlock can do.” followed by four illustrated, unboxed items: Investigate competitors; Keep your CRM current; Build living case files; Remember for the team.
4. **Example panel:** pale blue wide panel titled “From a clue to shared context.” with a folder illustration and a concise sequence explaining discovery, record updates, and reuse by other agents.
5. **Open-source invitation:** “Your detective. Your repo to explore.”, a short invitation, GitHub/documentation action, contribution link, and the stack-of-books illustration.
6. **Footer:** small identity and practical Docs, GitHub, and Contribute links separated from the page with a quiet rule.

The example panel is explanatory. Label it “Example workflow” in production so illustrated green checks do not imply a real completed action. “CRM and case file updated” belongs to an example or a verified successful execution, never a fabricated live feed.

Retain the plain-language note: **“Sherlock is free. Model providers and connected services may charge separately.”** Do not imply free API usage, hosted infrastructure, CRM subscriptions, or unlimited model access.

Do not add a new section solely to fill space. Installation, prerequisites, permissions, supported systems, security documentation, and contribution details should link to verified project documentation as it becomes available. Do not invent a repository URL, software license, package name, install command, authentication method, compatibility badge, or integration logo grid.

## 9. Documentation and future interfaces

### Documentation extension

Docs inherit the cream canvas, ink typography, yellow primary action, plain links, and restrained illustration. Use an obvious page title, task-focused sections, local navigation, and code examples only when checked against the repository. A single small mascot or contextual illustration is enough; large marketing-style heroes should not interrupt instructions.

Long docs may use a desktop navigation column. On mobile it becomes a labeled contents disclosure before the article. Ensure keyboard access and readable headings, and keep the main article at 65ch. Clearly separate requirements, commands, expected results, and troubleshooting. Copy buttons report success only after copying succeeds.

### Future workflow patterns — proposed, not an existing product

If Sherlock later receives an application interface, reuse these foundations without implying a current dashboard. A useful workspace could contain investigations, evidence, case files, CRM changes, and memory retrieval. Introduce only the areas supported by actual implementation.

Show an evidence item with its statement, source, date observed, related account or case, and any uncertainty. A proposed CRM edit should show the record, field, current value, proposed value, and supporting source. A case file should distinguish facts, analysis, open questions, and action history. A memory result should identify where a fact came from and when it was last confirmed.

The interface must match the real permission model. If an action requires review, show the proposed change before the actual write. If automation is authorized, show its real execution status and scope. Do not fabricate an approval requirement or claim a write happened because a suggestion was generated.

Use compact text and simple icons in dense work areas. Mascot art belongs at introductions, empty states, and occasional contextual moments; it must not compete with evidence or occupy a large part of a working screen.

## 10. Voice, terminology, and truthful states

Write like a capable teammate with a little detective personality. Prefer “Sherlock found a new pricing page” to “Unlock unprecedented competitive intelligence.” One detective metaphor per message is plenty. Headings can be charming; instructions and errors must be plain.

| Use | Meaning or example |
|---|---|
| Investigation | A specific research task or question. |
| Clue or signal | Something discovered; not automatically a verified fact. |
| Evidence | Source material supporting an assertion. |
| Case file | Organized context, evidence, history, and open questions. |
| Memory | Stored context that can be retrieved by another agent. |
| CRM record | The actual contact, company, deal, or other supported record type. |
| Proposed update | A suggested write that has not yet been saved. |

Use distinct labels for **Not started, In progress, Needs input, Proposed, Saving, Saved, Failed,** and **Partially complete** when those states exist. “Saved” requires confirmation from the destination. If the case file saved but the CRM write failed, say exactly that and offer a relevant retry. Do not roll both outcomes into a green “Done.”

For uncertain findings, use language such as “Possible match” or “This appears to be…” with source context. Do not show percentage confidence without a defined, implemented basis. “No relevant evidence found” is preferable to inventing a conclusion. “Last checked” is different from “last changed”; label timestamps accordingly.

Good empty state: “No case files yet. Start an investigation to gather your first evidence.” Good error: “The CRM update failed. Your case file was saved. Reconnect your CRM and try again.” These are proposed copy patterns, not claims about existing functionality.

Never publish mock customer names, connector support, repository stars, live counters, performance claims, or testimonials as real data. Clearly label demonstration content and keep private CRM information out of public examples.

## 11. Interaction, motion, and accessibility

Primary controls are at least **48 px high**, with **44 px** allowed for compact controls. This system's 44 px minimum target rule is deliberately stricter than WCAG 2.2 AA's 24 CSS px target-size criterion and its exceptions. Keep adjacent actions separated and avoid tiny icon-only hit areas. See [W3C target size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

Use visible keyboard focus: a **3 px link-colored ring with a 3 px offset**, checked against the actual surface. Hover must never be the only way to discover an action. Provide active, focus-visible, disabled, loading, success, and error states where appropriate; details live in `docs/components.md`.

Keep motion brief: **120 ms** for immediate feedback, **180 ms** for color or small transitions, and **240 ms** for a small disclosure. Avoid continuous floating, parallax, auto-scrolling carousels, blinking clues, or a mascot that follows the pointer. Respect reduced-motion preferences; remove nonessential movement and retain instant state feedback.

Target WCAG 2.2 AA. Normal text needs at least **4.5:1** contrast; qualifying large text needs **3:1**. Necessary control boundaries, state indicators, and graphical objects need **3:1** against adjacent colors. See W3C guidance for [text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). Do not treat decorative lines as compliant control borders.

Use semantic landmarks, a single clear H1, ordered heading levels, descriptive links, visible field labels, and a skip link. Pair status colors with text and meaningful icons. Announce important async results without repeatedly interrupting assistive technology. Do not move focus unexpectedly after background work.

Provide meaningful alt text for standalone artwork that communicates information, for example “Sherlock examining a clue with a magnifying glass.” Use empty alt text when adjacent text already conveys the illustration's entire purpose. Capability icons with matching text headings are usually decorative. Do not bake capability copy into exported artwork.

Check reflow at 320 CSS px, large text settings, 200% text zoom, keyboard-only navigation, and screen reader names. Tables and code may scroll within their own labeled containers; ordinary page content must not force horizontal scrolling.

## 12. Governance and handoff

This package is a design specification, not a published website or verified software implementation. Treat the approved screenshot as the visual baseline and the tokens as the shared numerical contract. Keep prose and component specifications synchronized when values change.

Record changes with version, date, rationale, changed files, approval status, and migration implications. Content corrections and small accessibility fixes may be patch updates. New compatible components are minor updates. Changes to the mascot, palette direction, typography direction, homepage structure, or token meanings require a major review; do not make them silently while completing an unrelated task.

Every asset record should include source, creator or generation method where known, local file, intended use, resolution or format, license information when established, and status: reference, candidate, or approved. Do not invent ownership or license terms. Keep source licenses with redistributed fonts and icons. The repository's actual software license must govern code use; this design package does not choose one.

Before handing work to another agent, include the relevant reference image, this handbook, tokens, the applicable component spec, verified destinations, and a list of unresolved decisions. State which parts are implemented, proposed, awaiting artwork, or blocked by missing project facts. Never represent an image mockup as a functioning page.

### Acceptance checklist

- The result resembles the approved cartoon page at a glance: cream, ink serif, yellow action, blue folder, open space.
- Sherlock's hat, curls, face, proportions, clothing, and relaxed expression remain consistent.
- The four capabilities remain distinct and understandable; no capability is invented as already supported.
- GitHub and documentation lead the experience; no sales funnel or pricing pattern has appeared.
- The free-software note does not imply free external services.
- Font and color values follow the supplied tokens; deviations are recorded and justified.
- Public links, commands, integrations, license statements, and runtime claims are verified or explicitly pending.
- Workflow examples are labeled; proposed, saved, failed, and partial states cannot be confused.
- Desktop, tablet, and narrow mobile layouts preserve reading order and readable controls.
- Keyboard access, focus, contrast, text resizing, image alternatives, and reduced motion are checked.
- Production artwork is identifiable by provenance and approval status; no screenshot crop is mislabeled as a final vector asset.
- Handoff identifies what actually exists and what remains a proposed extension.
