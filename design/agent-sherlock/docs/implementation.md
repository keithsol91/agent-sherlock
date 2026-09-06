# Agent Sherlock — implementation foundation

Version 1.0.0. Use this with the approved homepage in `../reference/approved-homepage.png` and the main design guide. These CSS files are a visual foundation, not a working app, a component framework, or an interaction-complete library.

The approved reference wins on composition and character. Tokens below are deliberately chosen implementation values; they are not claims about colors or measurements recovered from an original Figma file. Keep the playful young detective, warm cream ground, bold serif headings, simple hand-drawn props, and generous space. Do not turn this into a priced SaaS sales funnel.

## 1. Files and dependency order

1. `styles/fonts.css` registers the supplied fonts with local `@font-face` declarations.
2. `styles/tokens.css` defines the `--sherlock-*` custom properties.
3. `styles/components.css` applies the opt-in `.sherlock` styles.
4. Project-specific CSS may follow, but should reuse the tokens and approved component anatomy.

```html
<link rel="stylesheet" href="/styles/fonts.css">
<link rel="stylesheet" href="/styles/tokens.css">
<link rel="stylesheet" href="/styles/components.css">
<body class="sherlock">
  <!-- Semantic page content belongs here. -->
</body>
```

These URLs assume deployment at the domain root; adapt them when serving a GitHub Pages project under a repository subpath. Files are not copied or hosted automatically. Apply `.sherlock` to the page body or the complete component subtree. The starter deliberately does not reset the surrounding application. For a standalone page, set the body margin to zero in the project's own stylesheet.

The package supplies `fonts/Fraunces-variable.ttf` and `fonts/Inter-variable.ttf` with their license files. Preserve those licenses on redistribution. Do not add a third font family. Fraunces headings use weight 700 and axes `opsz: 72`, `SOFT: 0`, `WONK: 0`; Inter uses `opsz: 14`, body weight 400, UI weight 600. Use the system monospace stack for code. The component stylesheet sets those intended variations and leaves browser fallbacks available while fonts load.

## 2. Token contract

`tokens/tokens.json` uses the **custom** `agent-sherlock.tokens/1.0` schema. It does not claim DTCG compliance. Each entry has a `type`, a `value`, and a matching CSS variable name. A whole value in braces, such as `{palette.cream}`, is an alias to another token key. Resolve aliases transitively and reject missing references or circular chains.

Use semantic colors in components: `--sherlock-color-page`, `--sherlock-color-heading`, `--sherlock-color-primary`, and similar. Primitive `--sherlock-palette-*` tokens are the palette source; `coat` and `skin` are illustration-only colors. Add a token only when a real repeated need is established. Do not silently create new accent colors.

Native CSS media query conditions cannot use these custom properties. Their literal breakpoints must stay synchronized with `breakpoint.small` 640px, `breakpoint.medium` 960px, and `breakpoint.large` 1280px. Keep units intact. `rem` typography scales with user preferences; do not set a fixed root font size to defeat that behavior.

## 3. Layout and type

| Rule | Implementation |
| --- | --- |
| Page width | 1200px maximum content width, centered |
| Prose | 65ch maximum; hero lead approximately 38ch |
| Gutters | 24px below 640px; 32px from 640px; 48px from 960px |
| Hero | Copy first, art second in DOM; stacked below 960px, equal columns above |
| Skills | One column below 640px; two from 640px; four from 960px |
| Grid gaps | 24px on mobile/tablet; 32px on desktop |
| Section space | One-sided bottom padding: 64px mobile; 96px desktop; adjacent sections do not each add a top gap |
| Spacing scale | 0, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128px |
| Hero title | Fraunces 700, fluid 44–80px, line-height 1.04 |
| Section heading | Fraunces 700, fluid 32–48px, line-height 1.12 |
| Skill heading | Fraunces 700, fluid 24–28px, line-height 1.2 |
| Body / lead | Inter 400, 16px / 20–22px; body line-height 1.6, lead 1.5 |
| Caption | Inter 400 or 600, 14px; 12px is the absolute floor |

Keep skills as open illustration-and-text columns, without four floating boxed cards. Use the blue panel for one explanatory case sequence. Keep the page's primary story compact: introduction, four skills, example case, repository invitation. Supplemental docs and implementation states should not crowd the homepage.

The hero owns its internal top and bottom padding. Standard sections add only bottom spacing, so a 64px gap does not accidentally become 128px between adjacent sections. Place a padded blue panel inside a section wrapper; do not combine panel interior padding and section exterior spacing on the same element.

Use one `h1`, descriptive `h2` sections, and `h3` skill names. Do not force desktop line breaks with `<br>` when they produce awkward mobile copy. Copy should stay readable at 200% zoom and reflow at 320 CSS pixels without page-level horizontal scrolling. Wide code is the deliberate local overflow exception.

## 4. Components and states

| Component | Class / anatomy | Required behavior |
| --- | --- | --- |
| Primary action | `.sherlock-button`, gold, ink text, radius 12px, 48px minimum | Use a real anchor for navigation, a real button for an action. Label the destination or result. |
| Secondary action | `.sherlock-link`, underline; or `.sherlock-button--secondary` for a secondary button | Use links for Docs and Contribute. Do not surround every action with a button. |
| Compact / icon button | `--compact` 44px minimum; `--icon` 48px square | Icon-only controls need an accessible name. Prefer visible text. |
| Navigation | `.sherlock-nav`, `.sherlock-brand`, `.sherlock-nav-list`, `.sherlock-nav-link` | Starter CSS wraps links. The production design requires a tested disclosure below 640px; CSS alone does not implement it. Add `aria-current="page"` only to the current page. |
| Input | `.sherlock-field`, `.sherlock-label`, `.sherlock-input`, optional `.sherlock-error` | Visible label; connected help/error; native required/disabled/readonly as appropriate. |
| Badge | `.sherlock-badge`, optional `--success` / `--error` | Plain visible status label. Not a button. Never use color as the only status cue. |
| Alert | `.sherlock-alert`, icon + content, optional `--success` / `--error` | Choose live-region semantics only when needed; do not announce static page copy. |
| Skill grid | `.sherlock-skills` list; `.sherlock-skill`; illustration, heading, copy | Decorative images have empty alt text when the heading repeats their meaning. |
| Skill row | `.sherlock-skill-row`; small illustration + content | For documentation directories or longer skill descriptions. Keep the homepage grid open. |
| Example case | `.sherlock-case-panel`, `.sherlock-case-steps`, `.sherlock-case-step` | Mark examples as examples. Use an ordered list for sequence; state labels must match real data in a live interface. |
| Code block | `.sherlock-code`, `.sherlock-code-header`, `<pre><code>` | Exact verified commands only; locally scroll long code. A Copy button requires a working clipboard handler. |

Buttons expose default, hover, active, focus, disabled, and busy styles. Native `disabled` prevents button interaction. `aria-disabled="true"` only communicates state: it does **not** prevent clicks or keyboard activation. Prefer native disabling for form buttons; if an ARIA-disabled control must stay focusable, implement and test its event handling. A disabled link should usually become plain text with an explanation, rather than a dead anchor pretending to be useful.

`aria-busy="true"` is a visual/semantic hint, not an asynchronous implementation. Announce a meaningful progress label and prevent duplicate actions in application code. Never display a completed CRM update until the underlying integration confirms it. Pending, error, and disconnected are ordinary states; the detective can stay friendly without claiming success.

Inputs support placeholder, focus, invalid, disabled, and readonly styling. Validation must be real. Placeholders supplement a visible label, never replace it. For an error, add `aria-invalid="true"` and include the error element ID in `aria-describedby`. Keep useful submitted values after a failed attempt.

## 5. Semantic examples

These are markup patterns, not live product features. Supply actual page IDs, asset paths, data, event handlers, and destinations when implementing them. Do not publish placeholder links or invent a repository URL.

```html
<!-- In-page navigation points at a section that actually exists. -->
<a class="sherlock-link" href="#skills">Explore Sherlock's skills</a>

<section class="sherlock-section" id="skills" aria-labelledby="skills-title">
  <h2 id="skills-title">A few things Sherlock can do.</h2>
  <ul class="sherlock-skills">
    <li class="sherlock-skill">
      <!-- Add a delivered illustration here; do not ship a broken image. -->
      <h3>Investigate competitors</h3>
      <p>Follow their moves. Connect the clues.</p>
    </li>
  </ul>
</section>

<!-- A presentational status, not an interactive chip. -->
<span class="sherlock-badge sherlock-badge--success">
  Case file updated
</span>

<!-- Static documentation example: label the demonstration clearly. -->
<section class="sherlock-case-panel" aria-labelledby="case-title">
  <h2 id="case-title">Example case</h2>
  <ol class="sherlock-case-steps">
    <li class="sherlock-case-step sherlock-case-step--text" data-state="complete">
      <span>New signal found</span>
    </li>
    <li class="sherlock-case-step sherlock-case-step--text" data-state="pending">
      <span>CRM update pending</span>
    </li>
  </ol>
</section>
```

For a form, use a real `<label for="…">`. For navigation use `<nav aria-label="Primary">` and real anchors. Put a working skip link before the navigation and give its main target `id="main"` plus `tabindex="-1"` when necessary for reliable focus. If a code area overflows, consider `tabindex="0"`, `role="region"`, and an accessible label so keyboard users can reach and scroll it; do not add redundant tab stops to every non-overflowing snippet.

Status samples intentionally use text only. When adding icons, use the single UI icon library specified by the design guide, never Unicode symbols as substitute icons. Add `.sherlock-status-icon` to a real icon component and omit the `--text` modifier on the two-column case-step pattern. Decorative icons should be hidden from assistive technology when their visible label repeats the meaning.

Before a production mobile navigation disclosure is added, wrapping links is the honest functional fallback. A real menu control needs an accessible name, `aria-expanded`, `aria-controls`, keyboard operation, and a matching controlled region. Do not ship a menu icon that cannot open a menu.

## 6. Color and accessibility

`tokens/contrast-report.json` records calculated opaque sRGB contrast ratios, the threshold, and whether each tested pair passes. The checks cover prescribed normal text pairs and meaningful control/icon boundaries. They do not certify a future page's overall accessibility.

- Normal text must reach 4.5:1. Meaningful control boundaries and graphics must reach 3:1.
- Use ink on gold buttons. White on gold is 1.72:1 and prohibited.
- Use body or ink text inside sage and blue panels. Sage on sage-soft is 4.31:1; blue on blue-soft is 3.97:1. Both fail the normal text requirement.
- Link blue belongs on cream, white, or tested light panels. Link blue on gold is 4.32:1 and fails normal text.
- The default system never uses white text on blue. That pair narrowly passes at 4.61:1, but it is outside the approved light-surface treatment. Do not infer that it fails the mathematical threshold.
- `line` is decorative only; its 1.58:1 contrast on cream cannot define a required control boundary. `control-border` supplies the stronger accessible boundary.
- The focus ring is link blue, 3px wide with a 3px offset, on tested light surfaces. The dark code block overrides the ring to cream. Do not clip outlines with `overflow: hidden` around controls.
- Disabled controls retain readable text; never lower the entire control's opacity indiscriminately.
- The starter keeps visited inline links in the same link color. They remain visibly underlined. Do not rely on blue alone to distinguish a link from prose.

Supply visible status words alongside icons. Avoid tiny letter-spaced body text, animated typing that blocks reading, decorative text embedded into essential illustrations, or images of code. Include a meaningful accessible name for GitHub links and use the official GitHub mark rather than drawing a new one. Actual logo assets must be delivered or sourced before use.

Standalone controls use at least a 44 x 44px target. Navigation links and direct secondary links in `.sherlock-actions` receive that minimum area; inline prose links remain in the text flow with a visible underline. Use the actions wrapper for a standalone secondary CTA rather than giving every link in a paragraph a 44px line height.

## 7. Motion

Use 120ms for tight feedback, 180ms for normal state changes, and 240ms for an occasional panel transition. Use the supplied easing. The starter transitions control colors only and contains no automatic mascot animation. Decorative movement must stop under `prefers-reduced-motion: reduce`; the included override removes animations and transitions inside the Sherlock subtree. Do not hide task progress or essential status when motion is disabled.

## 8. Agent implementation checklist

1. Read the visual guide and inspect the approved reference before coding.
2. Check what the real repository supports. Only claim confirmed integrations, skills, install steps, and update behavior.
3. Load the delivered fonts and styles in the declared order. Use the semantic token names.
4. Match the open layout before adding optional controls. Do not add pricing, gated access, invented usage counts, customer logos, or fabricated GitHub star counts.
5. Connect GitHub and docs CTAs to verified destinations. Explain separately that model providers or connected services may charge; do not invent a license or say all execution is cost-free.
6. Implement interaction state honestly, including empty, loading, disconnected, error, and success where those features exist.
7. Verify keyboard navigation, visible focus, labels, link targets, 320px reflow, 200% zoom, mobile stacking, and reduced motion in the real implementation.
8. Recalculate contrast after any palette or state change. Sync JSON aliases, CSS declarations, and literal breakpoints together.

The provided verification checks token/CSS consistency and prescribed color contrast. No browser app, backend integration, clipboard interaction, or live CRM operation has been built or tested by this package.
