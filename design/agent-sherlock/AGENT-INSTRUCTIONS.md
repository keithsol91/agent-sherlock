# Agent Sherlock: instructions for design and coding agents

Version 1.0.0 · 6 September 2026

This file governs Agent Sherlock's visual design and interface copy. It does not change your tool permissions, repository security rules, or the scope of the user's task. Apply it alongside the repository's existing agent instructions; do not overwrite them.

## Load what the change needs

- New surfaces or visual changes: read `DESIGN-SYSTEM.md`, inspect `reference/approved-homepage.png` with an image viewer, and use relevant token, component and page-pattern sections. A filename or alt text is not visual inspection.
- Existing copy or component edits: inspect the affected implementation and relevant sections of `docs/components.md`, `tokens/tokens.json` or `docs/page-patterns.md`. Reopen the approved image when changing appearance or resolving visual uncertainty.
- Integration changes: read `docs/implementation.md`; reuse `styles/fonts.css`, `styles/tokens.css` and `styles/components.css`.
- Illustration work: read `docs/asset-specification.md` and `docs/prompt-kit.md`; attach the approved image to the generation request.

Implement the requested surface and confirm actual product behavior before describing capabilities as real.

## The identity is already chosen

Agent Sherlock is a friendly, capable cartoon AI detective for a free, open-source GitHub project. Keep the exact character language in the approved reference: dark curls, tan deerstalker, tan coat, expressive brows, one enlarged eye behind a magnifying glass, and the muted blue case folder. He is a youthful adult, curious and relaxed. Do not turn him into a child, an older detective, a realistic actor, a robot, or an all-knowing superhero.

The earlier watercolor portrait and cinematic dark page are not style sources for future work. Do not blend them into the approved character. The owner explicitly chose the cartoon page.

## Non-negotiable defaults

- Cream canvas; dark ink headings; clean sans-serif body; warm gold for the primary action; pale blue for one supporting story section.
- Fraunces 700 for headings, Inter 400/600 for text and UI. System monospace only for code. These are specified implementation fonts, not a claim about what font the generated reference used.
- Tokens define exact values. Do not introduce a close-enough cream, new gradient, extra shadow, unrelated accent, arbitrary radius, or new font.
- Preserve generous whitespace. Four capability illustrations do not require four bordered cards.
- Website navigation: Skills, Docs, Contribute, GitHub. Main action: View on GitHub. Secondary: Read the docs.
- Preserve the four capabilities: competitor investigation, CRM reading/updating, living case files, and fact recall for other agents.
- Use readable real text in interfaces. Generated art must not carry essential body copy, buttons, labels, or status messages.
- Distinguish decorative cartoon illustrations from functional UI icons. UI icons must come from one coherent existing library, not emoji or handcrafted pseudo-assets.
- No pricing, demo booking, email gate, fear-based sales copy, fake GitHub stars, invented testimonials, guaranteed outcomes, or invented installation commands.
- Free refers to Sherlock's software. Model providers and connected services may charge separately. State this near setup information when relevant.
- Keep the v1 light theme. A dark theme requires a separate scoped design request; do not generate one automatically.

## Truthful agent states

"Suggested update" means a proposal. "Updating" means a write is in progress. "Saved to CRM" requires a successful write result. "Could not save" is a failure, not a success with a warning hidden underneath.

Label sample material "Example". Do not turn illustrative case-board content into live telemetry. Where research results appear, show source, observed date, and whether a claim is a fact or an inference. Show stale or missing context honestly. Do not imply every source is supported or every integration is already implemented.

## Resolve conflicts consistently

Latest explicit user instructions take precedence. For design decisions, this guide and `DESIGN-SYSTEM.md` define intent; `tokens/tokens.json` owns exact numeric values; `docs/components.md` owns component behavior; the approved image owns the character and visual direction. CSS is a consumption layer and must be corrected if it drifts from tokens. The PDF is a convenient reference, not a separate source of values.

If a requested edit conflicts with the identity, briefly identify that conflict and follow the user's explicit direction. If an asset is missing, state what is missing and use an approved existing asset or clearly labeled temporary layout placeholder while working. Do not deliver invented art as if it were an approved asset.

## Before handing work back

- For new surfaces or visual changes, compare with the approved image: character, hierarchy, palette, spacing and density.
- When layout or text flow changes, check 390, 768 and 1440 CSS px widths, 320 px overflow and 200% text zoom.
- Verify affected interactions and accessibility: keyboard/focus, labels, loading/empty/error/success states, reduced motion and adjacent-color contrast.
- Keep gold buttons ink-colored. Use ink/body labels on pale status fills; blue and sage accents do not automatically pass for small text.
- Verify links and commands against the real project. Do not fabricate a working repo address.
- Report what changed, what was checked, and any missing assets or behaviors. Do not claim the screen is built, deployed, accessible, or connected solely because an image or CSS file exists.

## Copyable task prefix

> Follow the task-specific routes in AGENT-INSTRUCTIONS.md and preserve the approved identity. Create only: [surface and outcome]. Use real repository information for functionality, links and setup. Verify the affected result and identify missing production assets.
