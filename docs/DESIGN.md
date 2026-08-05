---
name: SmartReco
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#444651'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#757682'
  outline-variant: '#c5c5d3'
  surface-tint: '#4059aa'
  primary: '#00236f'
  on-primary: '#ffffff'
  primary-container: '#1e3a8a'
  on-primary-container: '#90a8ff'
  inverse-primary: '#b6c4ff'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#4b1c00'
  on-tertiary: '#ffffff'
  tertiary-container: '#6e2c00'
  on-tertiary-container: '#f39461'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b6c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#264191'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#ffdbcb'
  tertiary-fixed-dim: '#ffb691'
  on-tertiary-fixed: '#341100'
  on-tertiary-fixed-variant: '#773205'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 48px
  xl: 80px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style

The design system is anchored in a **Modern Minimalist** aesthetic tailored for high-stakes educational environments. It prioritizes cognitive ease, utilizing expansive whitespace and a "content-first" hierarchy to reduce the mental load of AI-generated narratives. The emotional response is one of **calm authority and technological precision**.

The visual language balances the clinical efficiency of a developer tool with the approachability of a premium consumer app. Surfaces are kept clean and predominantly flat, using subtle tonal shifts rather than heavy textures to define structure. The result is a professional, reliable environment that fosters deep focus and trust in automated recommendations.

## Colors

This design system utilizes a restricted, high-intent palette to ensure clarity.

- **Primary (Deep Indigo):** Used for primary actions, active navigation states, and brand-critical identifiers. It conveys stability and academic rigor.
- **Secondary (Professional Teal):** Reserved for success states, progress indicators, and interactive highlights that require distinction from the primary action.
- **Neutrals:** A range of Slate and Gray scales are used for background layering. The default background is pure white, with `neutral_color_hex` (Slate 50) used for container fills to create soft separation.
- **Accents:** Use pure black (#000000) sparingly for high-impact headlines to maximize contrast against the soft background.

## Typography

Typography is the core of this design system. It utilizes **Geist** for headlines and UI labels to provide a technical, modern edge, while **Inter** is employed for long-form body text to ensure maximum readability.

- **Leading:** Generous line-height (1.5x to 1.6x) is mandated for all body text to prevent visual crowding in dense AI descriptions.
- **Tracking:** Headlines use slightly negative letter spacing to feel "tight" and intentional, while labels use positive tracking for legibility at small sizes.
- **Hierarchy:** Use font weight (SemiBold/Bold) rather than color to distinguish hierarchy wherever possible, keeping the interface clean and monochromatic.

## Layout & Spacing

The system follows a **Fixed-Fluid Hybrid Grid**. Content is housed in a centered container with a maximum width of 1280px for desktop.

- **Desktop (1280px+):** 12-column grid, 24px gutters, 40px side margins.
- **Tablet (768px - 1279px):** 8-column grid, 20px gutters, 24px side margins.
- **Mobile (Up to 767px):** 4-column grid, 16px gutters, 16px side margins.

Spacing follows an 8px linear scale. Section-level vertical spacing should default to `lg` (48px) to maintain the "Premium/Calm" feel. Use `xl` (80px) for hero-to-content transitions to emphasize whitespace.

## Elevation & Depth

This design system avoids heavy shadows in favor of **Tonal Layering** and **Crisp Outlines**.

- **Level 0 (Base):** Pure White (#FFFFFF).
- **Level 1 (Subtle Surface):** Slate 50 (#F8FAFC) fill with a 1px solid border in Slate 200 (#E2E8F0). No shadow.
- **Level 2 (Active/Floating):** Used for cards and dropdowns. Pure White fill, 1px Slate 200 border, and a very soft "Ambient Shadow": `0 4px 12px rgba(15, 23, 42, 0.03)`.
- **Level 3 (Overlay):** Used for modals. 1px border and a more defined shadow: `0 12px 32px rgba(15, 23, 42, 0.08)`.

Depth is primarily communicated through the contrast between the #FFFFFF background and the #F8FAFC "Surface" containers.

## Shapes

The shape language is consistently **Rounded**, reflecting a modern and accessible EdTech persona.

- **Small Components:** Checkboxes and small tags use 4px (rounded-sm) to maintain a crisp look.
- **Standard Components:** Buttons and Input fields use 8px (base roundedness).
- **Large Containers:** Cards and Modals use 16px (rounded-xl) to soften the large surface areas and create a friendly, premium appearance.
- **Pill Shapes:** Exclusively for status badges (e.g., "In Progress") and search bars.

## Components

- **Buttons:** 
    - **Primary:** Solid Deep Indigo with white text. 8px radius. No shadow, flat color.
    - **Secondary/Ghost:** Transparent background with a 1px Slate 200 border. Text in Text-Secondary.
- **Cards:** White background, 16px radius, 1px Slate 200 border. Use padding of `md` (24px) for content within cards.
- **Input Fields:** Slate 50 background, 8px radius, 1px Slate 200 border. On focus, the border transitions to Deep Indigo with a 2px soft outer glow in the same color (0.1 opacity).
- **Chips/Badges:** Small font size (label-sm), 4px radius, subtle background tint based on status (e.g., light teal for "Completed").
- **Lists:** Horizontal dividers should be 1px Slate 100. Use generous vertical padding (16px) between list items to maintain the "Premium" feel.
- **AI Narrative Blocks:** Distinguish AI-generated text using a very subtle left-border accent (2px solid Teal) and a slightly lighter text weight to differentiate from user-authored headers.

## SmartReco-Specific Components

Additions made when applying this system to the actual app (`app/static/css/style.css`), not present in the original Stitch sample:

- **Product Cover (monogram).** The seeded catalog has no product images. Instead of stock photos, product cards render a deterministic tonal cover: a hash of `category` (stable, not Python's randomized `hash()`) picks one of 6 tones cycling through the palette's fixed/container colors, with the category's first letter as a large monogram. Implemented in `app/services/ui.py::category_cover`, exposed as the Jinja filter `cover` (registered wherever product cards/rows render — `catalog.py`, `admin.py`). No schema change, no external calls, no seed-script change.
- **Recommendations — cold-start empty state only.** The full "My Recommendations" page (AI narrative + match-scored cards) requires the Phase 4 agent and `Recommendation` model, which don't exist yet. Only the cold-start empty state ("Your journey starts here") is implemented now, at `GET /recommendations` — true for every user today. The populated state is a Phase 4 task, not a restyle of this stub.
- **AI Suggestion box (Catalog sidebar).** Static, generic placeholder copy only — explicitly *not* real AI output. Do not wire this to any model call until the Phase 4 agent exists.
- **Match-percentage badges** (seen in the Stitch sample as "98% Match") are deferred, not fabricated. Qdrant returns a real similarity score per retrieved point, so once Phase 4's retrieval is wired up, this badge can show a genuine number — it should not be added before that data exists.
- **Skill Level filter** from the sample is intentionally omitted — the SRS's `products` schema (FR-2.2) has no such field, and this pass didn't add one.
- **Fonts:** Geist + Inter loaded via Google Fonts (`https://fonts.googleapis.com/css2?family=Geist:...&family=Inter:...`) in `base.html`, with system-font fallbacks in the CSS `font-family` stack. This is the one new external network dependency this pass introduced.