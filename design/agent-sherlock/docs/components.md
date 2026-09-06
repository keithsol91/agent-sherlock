# Agent Sherlock component specification

Version 1.0.0 · Production specifications derived from `../reference/approved-homepage.png`

This specifies expected appearance and behavior. It is not a shipped component library. Homepage components translate the approved image; docs and application patterns are extensions. Use `../tokens/tokens.json`, `../styles/tokens.css`, and `../DESIGN-SYSTEM.md`; `../styles/components.css` supplies implementation starting styles, not proof that behaviors exist.

## Shared rules

- Use semantic HTML behavior before visual styling. A destination is a link; an in-page action is a button.
- Primary buttons use gold with ink text, a 12 px radius, and a 48 px minimum height. Compact controls may be 44 px. Fields use an 8 px radius; grouped panels use 16 px.
- Use a 3 px link-colored focus ring with a 3 px offset. Keep focus visible at clipping boundaries.
- Interactive text is 16 px by default. Labels remain visible; placeholders are examples, not labels.
- Illustrations explain a section. Functional icons explain an action. Do not substitute one for the other.
- Do not add states the underlying implementation cannot report. A button animation cannot prove an external update succeeded.

## Website and documentation components

| Component | Anatomy and appearance | Responsive behavior | Interaction and required states |
|---|---|---|---|
| Header/navigation | Cream background; linked mascot/wordmark; Skills, Docs, Contribute; GitHub destination. Use generous vertical space and no heavy toolbar container. | At narrow widths, preserve the brand and show a labeled menu disclosure when links no longer fit. Expand links in reading order; do not shrink labels. | Default, hover, focus-visible, current location, menu open/closed. Toggle exposes expanded state. Escape closes a menu where applicable and returns focus. No fake link destinations. |
| Brand lockup | Small mascot head beside live “Agent Sherlock” text; dark serif wordmark. Standalone approved asset remains pending. | Reduce size within legibility limits; do not crop the face or force a two-line wordmark. | Home link has a useful accessible name. Decorative head has empty alt when wordmark supplies the name. A temporary text-only identity is acceptable. |
| Hero | Short uppercase eyebrow; one large H1; capability summary; GitHub primary action; docs link; large cartoon Sherlock with blue folder. | Two columns from 960 px when comfortable; below that, text first and artwork second. Actions wrap or stack. Avoid fixed heights. | Links provide hover and keyboard focus. Artwork is static by default. Loading an image must reserve its space and not displace the heading. Missing art never hides the text. |
| Primary action | Gold fill, ink label, optional leading official GitHub icon, 12 px radius, comfortable horizontal padding. | Full-width only when needed; minimum 48 px high. A long label may wrap without clipping. | Gold-hover fill; focus ring; restrained pressed treatment. Disabled actions retain a readable label and a visible reason. Busy action shows a spinner plus a specific label such as “Saving…”. |
| Text/secondary link | Link color or ink with clear underline; optional simple trailing arrow. No competing gold fill. | Let labels wrap; keep the arrow with the last word when possible. | Underline or another persistent cue distinguishes inline links. Hover must not be the only sign. Do not force new tabs; if a workflow needs one, communicate it. |
| Capability item | Large illustration; short serif heading; one or two lines of supporting text. Unboxed, without repeated card shadows. | Four columns at desktop, two at tablet, one on small screens. Maintain consistent illustration area and logical order. | Static unless a real detailed destination exists. If linked, use a clear heading link and a visible focus treatment. Do not give static blocks pointer cursors. |
| Example workflow panel | Soft blue surface; large serif heading; folder/mascot art on one side; short sequence with status-like illustration on the other. Include “Example workflow.” | Two columns on desktop; stack heading, illustration, and steps on narrow screens. Sequence stays vertical and ordered. | Explanatory, not live. Illustrated checkmarks are decorative. Use an ordered list for the narrative. Never animate checks to imply real completed writes. |
| Open-source invitation | Large serif statement; short text; GitHub or verified getting-started action; contribution link; books/hat art; external-service cost note. | Stack copy and art; keep the cost note near the primary action and readable at 14 px or larger. | Buttons and links follow shared rules. “Get started” must resolve to actual setup documentation or repository guidance. No modal signup or sales capture. |
| Footer | Quiet top rule; compact wordmark; Docs, GitHub, Contribute. Optional factual license text only when verified. | Wrap into sensible rows and preserve comfortable touch targets. | Standard link states. Do not add invented company, social accounts, copyright ownership, or certification claims. |
| Documentation navigation | Labeled list of real sections, clear current-page indication, restrained separators. | Desktop side column; mobile contents disclosure before article. | Current page exposes its semantic state. Disclosure supports keyboard input. Active state uses more than color alone. |
| Article/prose | 65ch reading width; serif title and headings; Inter body; ordinary lists and useful tables. | No fixed page height. Tables may scroll inside a labeled region; prose reflows. | Correct heading hierarchy; descriptive anchor links; focusable code/table scrollers where required. Avoid replacing readable content with collapsed sections by default. |
| Code block | Monospace live text on a quiet contrasting surface; language label when useful; optional copy button. | Preserve code formatting with local horizontal scroll. Copy control remains reachable. | Idle, copying, copied, failed. “Copied” appears only after clipboard success and is announced politely. Commands must be verified; never show a fabricated installation command as executable. |

## Proposed workflow components

These apply only if an actual Sherlock application is built. They are not depicted as current software in the approved page.

| Component | Anatomy and appearance | Responsive behavior | Interaction and required states |
|---|---|---|---|
| Investigation input | Visible label, concise helper text, multiline question field if needed, clear submit action. Control-border outline on cream or white. | Field and action stack below comfortable available width. Prevent accidental overflow from long source URLs. | Empty, filled, focus, invalid, disabled, submitting. Error text is associated with the field. Preserve the entered question after failure. Show prerequisites before submission when known. |
| Select/search control | Visible label, current value, simple disclosure or search icon, real available options. | Fit container; long option labels wrap or truncate with a way to inspect them. | Closed/open, focused, selected, no results, loading, unavailable, error. Prefer native controls unless custom behavior is necessary and fully accessible. |
| Tabs | Text labels with clear active treatment and a restrained rule; count only when backed by data. | Use natural wrapping only if semantics stay clear; otherwise allow local scrolling with discoverability. | Active/inactive, focus, disabled when meaningful. Implement tab keyboard behavior for true panels; use ordinary links for page navigation. Do not disguise one as the other. |
| Evidence item | Statement; linked source title; observation time; related record/case; fact or inference label when relevant. Minimal outline only if needed for grouping. | Metadata wraps beneath statement. Long URLs never force page overflow. | Available, retrieving, source unavailable, stale, conflicting evidence. A missing source is explicit. Never replace a broken source with an invented citation. |
| Case-file summary | Case title, subject, latest activity, evidence count when real, brief current finding, open questions indicator. | Single column on narrow screens; related metadata wraps without losing labels. | Empty, loading, available, stale, error, restricted when the real permission model requires it. Empty state gives a useful next action; no invented content fills the gap. |
| Case-file detail | Distinct Facts, Analysis, Open questions, and History sections; source references beside claims. | Stacked sections; optional desktop secondary navigation becomes mobile contents. | Viewing, editing where supported, unsaved changes, saving, saved, failed. Preserve unsaved text on failure. Display real timestamps and destination confirmation. |
| CRM change preview | Record identity; field; current value; proposed value; supporting source; action matching actual permissions. | Two-column comparisons become explicitly labeled stacked values. | Proposed, needs input, saving, saved, failed, partially complete. Do not show “Saved” before the destination confirms it. Provide retry only where safe and supported. |
| Status badge | Short text plus icon where helpful. Ink/neutral, sage success, or red failure with suitable soft surface. Avoid decorative unreadable tiny pills. | Wrap full labels rather than clipping meaningful state. | Not started, in progress, needs input, proposed, saving, saved, failed, partially complete. Color is supplementary; distinguish partial completion from success. |
| Alert/message | Concise outcome title, explanation, relevant next action, optional dismissal. Quiet semantic surface and clear icon. | Full available width; actions wrap below text. | Informational, success, warning/needs input, error. Persistent failures remain visible until resolved or deliberately dismissed. Announce urgent errors appropriately without announcing every background update. |
| Empty state | Small optional mascot/prop, plain heading, specific explanation, one useful action. | Keep art compact so instruction and action remain above unnecessary scrolling. | Truly empty, filtered-to-zero, unavailable data. Distinguish the three. “No results” must not claim the data source is empty. |
| Loading state | Reserved content space; short precise progress label; subdued skeleton only when it matches eventual structure. | Preserve layout across widths without giant blank regions. | Loading, long-running with useful context, complete, failed. Do not invent percent progress or claim an investigation is finished based on elapsed time. |
| Activity/history item | Action, actual result, destination, time, actor/agent when known, link to relevant detail. | Time and metadata may wrap beneath the action. | Pending, confirmed, failed, partial. History records what happened; planned actions are explicitly marked. Avoid exposing private identifiers in public examples. |

## Status and feedback contract

| Situation | Correct interface response | Never imply |
|---|---|---|
| Sherlock generates a suggested CRM edit | “Proposed update” with field-level details. | The external record has changed. |
| A write request is outstanding | “Saving…” tied to the named destination. | Completed or safely persisted. |
| Destination confirms the write | “Saved” with destination and available timestamp. | Other destinations also succeeded. |
| Case file saved, CRM failed | “Partially complete,” followed by both outcomes and a relevant retry. | One generic green “Done.” |
| A clue has incomplete support | A source link and explicit uncertainty or inference label. | A verified fact or calibrated confidence score. |
| Memory lookup finds nothing relevant | Explain no relevant context was found and suggest a narrower question when useful. | The organization has never known that fact. |

## Definition of done

Before accepting any implemented component, verify its keyboard behavior, accessible name, visible focus, actual contrast combinations, smallest supported width, long content, loading/failure behavior, and reduced-motion behavior. Verify only the states relevant to the component and real integration. Screenshots should show default and material alternate states with demonstration content clearly labeled.

Record departures from the approved page or shared tokens. Do not let a new component become a quiet redesign of the rest of the system.
