# Style Presets Reference

Quick-lookup table for all 26 `--style` presets and their default dimension mappings.

---

## Preset Table (26 styles)

Each `--style` preset sets default values for `--palette` and `--rendering`. Individual dimension flags override the preset defaults.

| `--style`                  | Palette     | Rendering     |
|----------------------------|-------------|---------------|
| `elegant`                  | elegant     | hand-drawn    |
| `blueprint`                | cool        | digital       |
| `chalkboard`               | dark        | chalk         |
| `dark-atmospheric`         | dark        | digital       |
| `editorial-infographic`    | cool        | digital       |
| `fantasy-animation`        | pastel      | painterly     |
| `flat-doodle`              | pastel      | flat-vector   |
| `intuition-machine`        | retro       | digital       |
| `minimal`                  | mono        | flat-vector   |
| `nature`                   | earth       | hand-drawn    |
| `notion`                   | mono        | digital       |
| `pixel-art`                | vivid       | pixel         |
| `playful`                  | pastel      | hand-drawn    |
| `retro`                    | retro       | digital       |
| `sketch-notes`             | warm        | hand-drawn    |
| `vector-illustration`      | retro       | flat-vector   |
| `vintage`                  | retro       | hand-drawn    |
| `warm`                     | warm        | hand-drawn    |
| `warm-flat`                | warm        | flat-vector   |
| `hand-drawn-edu`           | macaron     | hand-drawn    |
| `watercolor`               | earth       | painterly     |
| `poster-art`               | retro       | screen-print  |
| `mondo`                    | mono        | screen-print  |
| `art-deco`                 | elegant     | screen-print  |
| `propaganda`               | vivid       | screen-print  |
| `cinematic`                | duotone     | screen-print  |

---

## Convenience Presets for audio-to-social

`visual_preset`（`knowledge-card` / `cozy-story` / `bold-warning` / `minimal-opinion`）到五维的映射（含 dual palette 备选语义）是 `visual-preset-mapping.md` 的职责，不在此重复。详见 [visual-preset-mapping.md](visual-preset-mapping.md)。

---

## Override Examples

Style presets set defaults, but any individual dimension flag overrides the preset value.

### Example 1: Override rendering within a style
```
--style blueprint --rendering hand-drawn
```
Result: `cool` palette (from blueprint) with `hand-drawn` rendering (overridden from digital).

### Example 2: Override palette within a style
```
--style elegant --palette warm
```
Result: `warm` palette (overridden from elegant) with `hand-drawn` rendering (from elegant).

### Example 3: Full override
```
--style minimal --palette vivid --rendering pixel --mood bold --type hero
```
Result: All dimensions overridden; the `--style minimal` is effectively ignored except as a fallback label.

### Example 4: Convenience preset with override
```
--visual_preset knowledge-card --palette earth
```
Result: `conceptual` type, `flat-vector` rendering, `balanced` mood, `none` text (all from knowledge-card), but `earth` palette overrides the default `cool / mono`.
