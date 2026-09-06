# Third-party notices and artwork

The [MIT license](LICENSE) applies to original Sherlock code and skill
instructions. It does not relicense the third-party materials or brand marks
below.

## Fonts

The bundled Fraunces and Inter fonts retain their SIL Open Font License notices:

- [Fraunces license](public-facing/assets/fonts/Fraunces-OFL.txt)
- [Inter license](public-facing/assets/fonts/Inter-OFL.txt)

Equivalent copies in the design-system package retain their accompanying notices.

## Product names and marks

These marks identify products discussed in the documentation. They do not imply
partnership, endorsement, or verified interoperability. Each remains subject to
its owner's applicable trademark and brand guidance; Sherlock's code license
does not grant trademark rights.

| Files in `public-facing/assets/brands/` | Source |
| --- | --- |
| `claude-mark.png` | [Claude Code](https://claude.com/product/claude-code) |
| `chatgpt-mark.svg` | [OpenAI brand guidelines](https://openai.com/brand/) |
| `hermes-mark.png` | [Hermes Agent](https://hermes-agent.nousresearch.com/) |
| `openclaw-mark.svg` | [OpenClaw](https://openclaw.ai/) |
| `slack-logo.svg`, `slack-mark.png` | [Slack media kit](https://slack.com/media-kit) |

## Sherlock artwork and examples

The bundled design reference was supplied for this project. The existing
`sherlock-hero-candidate.png` is a generated character illustration and retains
its candidate status. These images are visual material, not proof of functioning
software. Artwork and Sherlock branding are excluded from the software license;
no separate blanket redistribution or trademark license is asserted here.

The Slack screenshots are authored, fictional examples, with matching sample
data in `public-facing/assets/examples/slack-examples.js`. Names, messages,
counts, and projects in those images are fictional. They are not customer
testimonials or captures from a connected Slack workspace.

## Runtime dependencies

Direct and transitive runtime dependencies are recorded in
[uv.lock](public-facing/runtime/uv.lock). They are installed separately and
retain their own licenses. This repository does not vendor their code or the
local virtual environment. Consult each package's distribution metadata for
its license and notices.
