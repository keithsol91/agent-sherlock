# Bundled fonts

These are the production font choices for v1.0.0. The generated reference does not provide identifiable font metadata; these families are deliberate close visual matches, not recovered source fonts.

| File | Origin | Usage |
| --- | --- | --- |
| Fraunces-variable.ttf | [Google Fonts: Fraunces](https://github.com/google/fonts/tree/main/ofl/fraunces) | Headings, weight 700; SOFT 0, WONK 0, optical size 72 |
| Inter-variable.ttf | [Google Fonts: Inter](https://github.com/google/fonts/tree/main/ofl/inter) | Body weight 400; labels/actions 600; optical size 14 |

Downloaded 6 September 2026 from the official Google Fonts repository. The original, unmodified variable TTF files and each family's OFL notice are included. Preserve the notices when redistributing. These notices apply to the font files; they do not set a license for Sherlock's repository, art, or this design-system package.

Load `styles/fonts.css` before the tokens and component styles. Font URLs are relative to that stylesheet. The TTFs are ready to load and to use in design tools. A production team can create appropriately licensed WOFF2/subsets for performance as a later asset optimization; none are claimed to be included here.

Only upright styles are bundled. Avoid synthesizing italic display headings. For code, use the system monospace stack defined in tokens; there is no third downloadable font family.
