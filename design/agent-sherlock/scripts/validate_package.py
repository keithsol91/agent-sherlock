#!/usr/bin/env python3
"""Check package integrity and prescribed contrasts; no browser/a11y certification."""
import json
import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


token_data = load_json("tokens/tokens.json")
tokens = token_data["tokens"]
css_text = (ROOT / "styles/tokens.css").read_text(encoding="utf-8")
css = dict(re.findall(r"(--sherlock-[\w-]+)\s*:\s*([^;]+);", css_text))


def resolve(name, visited=()):
    if name in visited:
        raise ValueError("Circular alias: " + name)
    value = tokens[name]["value"]
    if isinstance(value, str) and re.fullmatch(r"\{[^{}]+\}", value):
        return resolve(value[1:-1], visited + (name,))
    return value


for name, token in tokens.items():
    try:
        resolve(name)
    except (ValueError, KeyError) as error:
        errors.append(str(error))
    value = token["value"]
    if isinstance(value, str) and re.fullmatch(r"\{[^{}]+\}", value):
        expected = "var(" + tokens[value[1:-1]]["css"] + ")"
    else:
        expected = str(value)
    check(css.get(token["css"], "").strip() == expected,
          "Token/CSS mismatch: " + name)
check(len(tokens) == len(css), "Token/declaration count mismatch")
component_css = (ROOT / "styles/components.css").read_text(encoding="utf-8")
for name in re.findall(r"var\((--sherlock-[\w-]+)", component_css):
    check(name in css, "Undefined CSS property: " + name)


def luminance(value):
    channels = [int(value[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
              for v in channels]
    return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


contrast = load_json("tokens/contrast-report.json")
approved_count = 0
for pair in contrast["checks"]:
    light, dark = sorted((luminance(pair["foregroundHex"]),
                          luminance(pair["backgroundHex"])), reverse=True)
    ratio = (light + 0.05) / (dark + 0.05)
    check(math.isclose(ratio, pair["ratio"], abs_tol=0.000051),
          "Stale contrast ratio: " + pair["use"])
    check((ratio >= pair["threshold"]) == pair["passesWCAGThreshold"],
          "Incorrect contrast result: " + pair["use"])
    for field in ("foreground", "background"):
        check(resolve("palette." + pair[field]) == pair[field + "Hex"],
              "Contrast palette mismatch: " + pair["use"])
    if pair["systemUse"] == "approved":
        approved_count += 1
        check(ratio >= pair["threshold"], "Failed approved pair: " + pair["use"])

registry = load_json("asset-registry.json")
for asset in registry["assets"]:
    if asset["path"]:
        path = ROOT / asset["path"]
        check(path.is_file(), "Missing registered asset: " + asset["id"])
        if asset.get("format") == "png" and path.is_file():
            header = path.read_bytes()[:24]
            check(header[:8] == b"\x89PNG\r\n\x1a\n", "Invalid PNG header")
            check(struct.unpack(">II", header[16:24]) == (asset["width"], asset["height"]),
                  "PNG dimensions differ from registry")
    else:
        check(asset["status"] == "specified-not-produced", "Missing asset status is misleading")

local_links = 0
for path in ROOT.rglob("*.md"):
    text = path.read_text(encoding="utf-8")
    for destination in re.findall(r"\]\(([^)]+)\)", text):
        if re.match(r"[a-z]+:", destination) or destination.startswith("#"):
            continue
        local_links += 1
        relative = destination.split("#", 1)[0]
        check((path.parent / relative).is_file(),
              f"Broken local link in {path.relative_to(ROOT)}: {destination}")

font_css = (ROOT / "styles/fonts.css").read_text(encoding="utf-8")
for relative in re.findall(r'url\("([^"]+)"\)', font_css):
    check((ROOT / "styles" / relative).is_file(), "Missing font: " + relative)

summary = {"tokens": len(tokens), "cssDeclarations": len(css),
           "approvedContrastPairs": approved_count, "localMarkdownLinks": local_links,
           "registeredAssets": len(registry["assets"]), "errors": errors}
print(json.dumps(summary, indent=2))
raise SystemExit(bool(errors))
