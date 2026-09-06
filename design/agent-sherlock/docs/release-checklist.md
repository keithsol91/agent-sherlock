# Release and review checklist

Use this for the surface being changed. It is a design-quality checklist, not a new authority or approval policy.

## Visual identity

- [ ] Opened the approved reference and compared it with the actual output.
- [ ] Sherlock's face, curls, hat, coat, apparent age, contour weight, and demeanor match.
- [ ] Cream/ink/gold/blue hierarchy survives at a glance; no new dominant palette.
- [ ] Fraunces headings and Inter body match the specified weights and scale.
- [ ] Four capabilities remain understandable; no feature inventory crowds the hero.
- [ ] Whitespace and grouping do the work before borders, cards, and shadows.
- [ ] No photography, watercolor actor likeness, cinematic scenery, 3D rendering, or unrelated mascot style has crept in.

## Copy and product truth

- [ ] GitHub, docs, and participation remain the useful actions.
- [ ] No pricing/demo gate, fake proof, fear pitch, or invented success metrics.
- [ ] Actual repo URL, docs destinations, supported integrations, commands, and license are verified where used.
- [ ] Example data is labeled; factual findings have sources and observed dates where appropriate.
- [ ] Inferences are distinguishable from observed facts.
- [ ] Proposed, saving, saved, and failed states reflect real operation results.
- [ ] Separate writes have separate statuses when outcomes can differ.
- [ ] Costs of providers/services are distinguished from free Sherlock software near setup when relevant.

## Responsive and accessible implementation

- [ ] Checked 390, 768, 1440 px and 320 px overflow; checked text zoom at 200%.
- [ ] No clipped headings, squashed illustrations, overlapping controls, or image-only important text.
- [ ] All actions can be reached and used with the keyboard; focus is visible and not hidden under sticky UI.
- [ ] Interactive controls have useful accessible names and real semantic elements.
- [ ] Native disabled controls and `aria-disabled` custom controls actually prevent actions.
- [ ] Text contrast meets the chosen threshold on the actual background. Never assume the accent name proves compliance.
- [ ] Focus indicators and necessary control boundaries are visible; error/status is not color-only.
- [ ] Standalone interactive targets meet the system's 44 x 44 px minimum; default buttons are 48 px high. Prose links stay inline and visibly underlined.
- [ ] Reduced-motion preferences remove nonessential movement.
- [ ] Empty, loading, partial success, success, failure, offline/unavailable, and retry states are handled if applicable.
- [ ] Dialogs and menus use the application's existing tested behavior; style alone is not behavior.

## Asset and package integrity

- [ ] Art exists at the stated path and format; transparent assets really have clean transparency.
- [ ] Asset status is accurate: reference, candidate, approved-production, or specified-not-produced.
- [ ] No full-page screenshot is presented as editable component source or a functioning webpage.
- [ ] Font notices remain alongside redistributed font files.
- [ ] Exact values match tokens and CSS; relevant contrast pairs were recalculated after a palette change.
- [ ] New or changed patterns are documented; version/changelog reflect the change.
- [ ] Handoff states what was verified and what remains unimplemented without implying a full audit.

## Acceptance outcome

Record one: **Ready for the requested handoff**, **Needs revision**, or **Blocked by missing source/behavior**. Include the concrete reason and the smallest next action. Do not label an entire product accessible solely because a few colors pass a calculation.
