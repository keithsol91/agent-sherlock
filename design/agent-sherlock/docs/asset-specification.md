# Character and asset specification

## Source of truth and availability

The only supplied visual art asset is `reference/approved-homepage.png`: the complete approved concept image. It preserves the character, composition, illustration language, and relative color balance. It is not a vector library, sprite sheet, production logo, or implemented webpage.

Do not slice the page into a collection of final UI assets. For production, generate or commission separate art from the approved reference, then inspect it for character consistency at its intended size. Keep the original reference unchanged. The registry explicitly distinguishes available reference material from specified assets that have not been produced.

The uploaded realistic watercolor is historical context only. Do not use its actor likeness, blue scarf, coat texture, painting style, or facial proportions to alter the approved mascot.

## Canonical Sherlock

| Feature | Preserve |
| --- | --- |
| Character | Original youthful adult detective, curious and quietly confident |
| Face | Rounded, friendly face; large expressive dark eyes; strong curved brows; small smile |
| Hair | Black or deep-ink curls visible below the hat, with the same silhouette |
| Hat | Warm tan deerstalker, recognizable checks, small bow on top |
| Clothing | Tan trench coat with tan outer collar, small white shirt collar, dark tie; very limited detail |
| Signature prop | Oversized magnifying glass enlarging one eye |
| Secondary prop | Muted blue case folder; papers and clues only when meaningful |
| Drawing | Clear dark contours, rounded joins, broad flat fills, restrained two-tone shading |
| Mood | Interested, thoughtful, helpful; never smug, frightened, clueless, or manic |

Preserve the oversized head, compact torso, and rounded hands visible in the reference. Keep the lens large enough to make the magnified eye the focal point. Compare facial spacing, hat/hair contour, and head-to-body balance directly with the approved image at the intended crop and size. Do not apply a fixed anatomy ratio across full-body, bust, and head-only assets.

The image has gentle tonal variation. Preserve that softness in art, but remove paper grain and gradients from functional UI surfaces. Do not add realistic cloth texture, pores, cinematic lighting, glossy plastic, 3D volume, or hard dramatic shadows.

## Permitted pose family

All poses reuse the same face, curls, hat, clothing, outline, and colors. These are future variations, not alternative characters.

| Pose | Purpose | Limits |
| --- | --- | --- |
| Inspecting | Homepage hero / competitor investigation | One eye behind lens; at most three small clues |
| Organizing | CRM or case-file explanation | One folder and one record; no busy desktop |
| Remembering | Recall or context explanation | Thoughtful expression; one fact card, no floating brain |
| Sharing | Agent-to-agent context | Pass a single fact card; do not introduce a conflicting mascot style |
| Welcoming | Getting started | Small wave or open stance; no sales gesture |
| Waiting | Empty state | Calm, available; never visually imply background progress that is not running |

Do not change his apparent age per pose. A blue scarf, older face, different species, or robot adaptation would be a new direction requiring an explicit request.

## Output rules

Prefer separate transparent PNG/WebP illustration exports at 2x the intended display size. Retain clean layered source when available. A raster file renamed `.svg` is not vector art. An SVG wrapper around a PNG is still raster. Commission a faithful vector redraw if scalable paths are required.

For illustration artwork rendered at 400 px high, aim for a visual contour around 3-5 px and one lighter internal line weight. Scale naturally with the art. For a 24 px UI icon, use a separate consistent 2 px icon stroke; do not shrink an intricate cartoon illustration to serve as a functional icon.

Keep essential details at least 8% away from illustration edges. Transparent exports must have clean edge pixels on cream and pale blue; no white rectangles, accidental halos, or clipped hat tips. Do not bake captions, controls, or helper text into art. Semantic text belongs in HTML or document text layers.

## Required production asset inventory

| Asset ID | Intended delivery | Main use | Current status |
| --- | --- | --- | --- |
| `reference-homepage` | Existing PNG, original resolution | Visual direction | Supplied |
| `sherlock-hero` | 1600 x 1600 transparent PNG/WebP | Hero; display around 400-560 px | Specified, not produced |
| `sherlock-avatar` | 1024 x 1024 transparent PNG | GitHub/avatar; separate small-size simplification | Specified, not produced |
| `sherlock-head-small` | Dedicated 32/48/64 px variants | Header/favicons at small scale | Specified, not produced |
| `wordmark-horizontal` | True vector plus PNG fallback | Site header and README | Specified, not produced |
| `skill-competitors` | 640 x 480 transparent PNG/WebP | Binoculars and two simple paper clues | Specified, not produced |
| `skill-crm` | 640 x 480 transparent PNG/WebP | Record, pencil, confirmation symbol | Specified, not produced |
| `skill-case-files` | 640 x 480 transparent PNG/WebP | Three simple folder tabs | Specified, not produced |
| `skill-shared-context` | 640 x 480 transparent PNG/WebP | Detectives sharing a fact card | Specified, not produced |
| `example-case` | 1200 x 900 transparent PNG/WebP | Case-folder vignette; text separate | Specified, not produced |
| `books-and-hat` | 1000 x 800 transparent PNG/WebP | Three books and deerstalker in the participation section | Specified, not produced |
| `sherlock-welcome` | 1200 x 1200 transparent PNG/WebP | Setup and docs | Specified, not produced |
| `social-preview` | 1200 x 630 PNG | GitHub/social link preview | Specified, not produced |
| `favicon-set` | SVG if true vector; PNG 16/32/48 + ICO | Browser identity | Specified, not produced |

Use consistent optical size for the four capability illustrations. Their bounding boxes may differ; align the apparent baseline and visual weight, not arbitrary object edges. A masthead head icon needs its own simplification; don't squeeze the full hero into 24 px.

## Logo handling

Preferred future lockup: head icon on the left, Agent Sherlock in the heading family on the right. Keep the words on one line when possible. Clear space around the lockup: at least half the icon height. Suggested minimum widths: full lockup 160 px, standalone head 32 px. At 16 px, use a deliberately simplified favicon, not the hero.

Until a final lockup exists, render the wordmark as live text. Do not imply that an exact vector logotype is included. Official GitHub marks should come from GitHub's provided assets; do not redraw their mark using a prompt or CSS.

## Asset acceptance checklist

- Face, hair, hat, age, and coat match the approved reference.
- The silhouette works at actual display size; a small version stays recognizable.
- No extra fingers, uneven lens geometry, unintended text, distorted folder tabs, or cropped details.
- Clean edges on cream and blue; correct aspect ratio; appropriate resolution.
- No unsupported brand logos or actor portrait blended into the mascot.
- File has accurate format, dimensions, version, status, source, and intended use in `asset-registry.json`.
- Export reviewed at 100% and in its actual page context before being promoted to approved status.
