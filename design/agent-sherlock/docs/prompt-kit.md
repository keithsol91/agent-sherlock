# Prompts for agents

Always attach `reference/approved-homepage.png` when asking a visual model to make Sherlock art or a page. These prompts are templates for future requested tasks. They do not authorize unrelated feature work or external writes.

## 1. Website or UI implementation

```text
Use the Agent Sherlock design system in this folder. Read AGENT-INSTRUCTIONS.md,
DESIGN-SYSTEM.md, docs/components.md, docs/implementation.md, and the page pattern
for the requested surface. Open reference/approved-homepage.png visually.

Task: [surface and user outcome].

Keep the exact approved cartoon direction: youthful adult Sherlock, tan
deerstalker and coat, black curls, curious face, magnifying glass, blue folder.
Use the supplied cream/ink/gold/blue tokens, Fraunces headings, Inter body text,
and generous spacing. Reuse existing component styles and approved assets.
The product is a free open-source GitHub project. Actions should help people
use the software, read docs, or contribute. Preserve the four stated skills.

Use actual repository information for features, setup, links, and states.
Do not invent commands, integrations, stars, testimonials, pricing, or a demo
funnel. New extensions must not pretend to be existing capabilities.

Do not substitute a screenshot for working UI or invent missing art with code.
Keep text selectable and controls accessible. Inspect desktop and mobile,
keyboard focus, contrast, reduced motion, and loading/error/empty/saved states.
Compare with the approved reference and report remaining limitations.
```

## 2. Standalone mascot production

```text
The attached image is the approved identity reference. Create one standalone
transparent illustration of the SAME Agent Sherlock, not a redesign.

Requested pose: [inspecting / organizing / remembering / sharing / welcoming].
Canvas: [width x height]; intended display size: [size]; no written text.

Preserve the face shape, dark curly hair silhouette, tan checked deerstalker,
top bow, tan coat and outer collar, small white shirt collar, dark tie,
large dark eyes, curved eyebrows,
and small knowing smile of the reference. He is a youthful adult, capable and
curious. Preserve the oversized magnifying glass and muted blue folder when
they belong in the chosen pose. Keep the character's apparent age unchanged.

Use clean dark rounded contours, broad flat warm colors, and restrained
two-tone shading. Keep the background truly transparent, edges clean, and
at least 8 percent clear space. One main prop and at most three tiny clues.

No realistic actor, watercolor portrait, blue scarf, gritty detail, 3D toy,
robot, child proportions, alternate costume, hard lighting, paper backdrop,
captions, logos, watermark, or extra anatomy. Preserve the exact art direction.
```

Treat the result as a candidate until reviewed alongside the source; an image-generation prompt alone cannot guarantee identical character geometry.

## 3. Capability illustration

```text
Use the attached approved Agent Sherlock page as the visual source. Create
one standalone transparent 640 x 480 illustration for [capability].

Subject: [binoculars with two paper clues / CRM record with pencil and check /
three-tab case folder / two matching detectives sharing one fact card].

Match the thick dark outlines, warm tan and gold, muted blue and sage,
simple shapes, modest two-tone shading, and friendly restrained cartoon feel.
Center the optical weight, leave 8 percent safe space, and do not add text.
This will sit above a live-text heading on a cream website. Keep it legible at
160-200 px wide. No card border, background rectangle, dashboard, photorealism,
glass effects, complex diagrams, extra props, or new color palette.
```

## 4. Documentation and product copy

```text
Write [documentation page or interface copy] for Agent Sherlock using the
provided repository facts and Agent Sherlock design system.
Voice: clear, curious, helpful, understated. Detective language is a light
accent. Explain what happens, what is needed, and what to do next.

Keep the free/open-source positioning. State model or connected-service costs
where relevant. Don't write sales copy, promise perfect recall, or invent
supported systems. Clearly separate facts from inferred findings and proposed
changes from successful saves. Include useful recovery instructions for errors.
Do not turn every heading into a Sherlock joke.
```

## 5. Design review

```text
Compare the supplied output directly with reference/approved-homepage.png
and the Agent Sherlock design system. Review only the requested surface.

Check character identity and age, cream/ink/gold/blue balance, typography,
spacing, illustration density, open-source positioning, content accuracy,
component consistency, responsive layout, and accessibility.

Report concrete mismatches with their location and a specific fix. Separate
visual mismatches from unimplemented behavior and unknown facts. Do not call
a token check a full accessibility audit or a screenshot an implemented page.
Keep the approved identity intact when fixing issues.
```
