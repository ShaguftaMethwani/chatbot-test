---
name: Experimental Financial Logic
colors:
  surface: '#16111b'
  surface-dim: '#16111b'
  surface-bright: '#3d3741'
  surface-container-lowest: '#110c15'
  surface-container-low: '#1f1a23'
  surface-container: '#231e27'
  surface-container-high: '#2e2832'
  surface-container-highest: '#39323d'
  on-surface: '#eadfed'
  on-surface-variant: '#cfc2d6'
  inverse-surface: '#eadfed'
  inverse-on-surface: '#342e38'
  outline: '#988d9f'
  outline-variant: '#4d4354'
  surface-tint: '#ddb7ff'
  primary: '#ddb7ff'
  on-primary: '#490080'
  primary-container: '#b76dff'
  on-primary-container: '#400071'
  inverse-primary: '#842bd2'
  secondary: '#c0c1ff'
  on-secondary: '#1000a9'
  secondary-container: '#3131c0'
  on-secondary-container: '#b0b2ff'
  tertiary: '#fabc4e'
  on-tertiary: '#432c00'
  tertiary-container: '#bd871a'
  on-tertiary-container: '#3a2600'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#f0dbff'
  primary-fixed-dim: '#ddb7ff'
  on-primary-fixed: '#2c0051'
  on-primary-fixed-variant: '#6900b3'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#ffdead'
  tertiary-fixed-dim: '#fabc4e'
  on-tertiary-fixed: '#281900'
  on-tertiary-fixed-variant: '#604100'
  background: '#16111b'
  on-background: '#eadfed'
  surface-variant: '#39323d'
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  headline-xl-mobile:
    fontFamily: Sora
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-padding: 24px
  chat-gap: 12px
---

## Brand & Style

The design system is engineered for a high-stakes, high-intelligence financial environment. It bridges the gap between algorithmic precision and human intuition through an **Experimental Web3 aesthetic**. 

The brand personality is authoritative yet ethereal—evoking the feeling of a digital vault that breathes. By utilizing the wide tracking and unique rhythm of Sora alongside the surgical clarity of Hanken Grotesk, the UI feels like a state-of-the-art terminal. 

The visual style is defined by **Dark-Mode Glassmorphism**. This involves deep-layered transparency, ultra-fine borders (0.5px to 1px), and vibrant violet glows that suggest "active intelligence." The emotional response should be one of absolute security combined with the excitement of cutting-edge technology.

## Colors

The palette is anchored in a **Deep Midnight (#0F172A)** foundation. Primary actions utilize a high-energy gradient from **Vibrant Violet (#A855F7)** to **Indigo (#6366F1)**, symbolizing the flow of data and capital.

Surface colors are semi-transparent to allow for "glow-through" effects from background decorative elements. 
- **User Actions:** Gradient-based, high saturation.
- **System Surfaces:** Glassmorphic slate with 50% opacity and a subtle white-tinted border (10% opacity).
- **Status Accents:** Red/Orange tones are reserved strictly for high-priority refusals or market volatility warnings, maintaining high contrast against the dark backdrop.

## Typography

This design system uses a dual-font strategy to balance character with readability:
1. **Sora (Headlines):** Used for all data points, large headings, and currency values. Its geometric construction reinforces the futuristic, algorithmic narrative.
2. **Hanken Grotesk (Body & UI):** Used for chat messages, descriptions, and labels. Its sharp terminals ensure maximum legibility at small sizes during complex financial explanations.

**Type Rules:**
- Use `display-lg` strictly for hero numbers or balance statements.
- `label-sm` should always be tracked out (+5%) for a technical "metadata" feel.
- Body text should maintain high contrast (pure white or very light grey) to ensure WCAG compliance on dark surfaces.

## Layout & Spacing

The layout follows a **Fluid Grid** model with a focus on vertical chat flow. 
- **Desktop:** 12-column grid with wide 32px gutters to emphasize the "Glass" panels.
- **Mobile:** Single column with 20px side margins.

Spacing is based on a **4px base unit**. The rhythm between chat bubbles should be tight (12px) to signify conversation, while major surface containers should have generous internal padding (24px) to allow the glassmorphic background blur to be visible.

## Elevation & Depth

Depth is achieved through **Backdrop Blurs** rather than traditional shadows.
- **Level 1 (Base):** Midnight Blue Background.
- **Level 2 (Chat Bubbles/Cards):** Surface color with `backdrop-filter: blur(12px)` and a `1px` stroke (white at 10% opacity).
- **Level 3 (Modals/Popovers):** Higher blur (20px) with a subtle inner glow (Violet #A855F7 at 5% opacity) to suggest they are floating closer to the user.

**Shadows:** When used, shadows should be "Ambient Glows"—large, soft, and tinted with the primary violet color, appearing only under active elements like primary buttons.

## Shapes

The design system adopts a **Pill-shaped (Level 3)** philosophy to soften the technical nature of financial data.
- **Standard Bubbles:** 1rem (16px) corner radius.
- **Buttons & Chips:** Full pill-shape (circular ends).
- **Large Containers:** 2rem (32px) for a "premium hardware" feel.

The high roundedness contrasts with the sharp typography of Hanken Grotesk, creating a balanced "human-tech" interface.

## Components

### Buttons
- **Primary:** Violet-to-Indigo gradient, white text, pill-shaped. No border, but a subtle violet drop-shadow glow on hover.
- **Secondary:** Transparent with a 1px violet stroke and 10% violet background fill.

### Chat Bubbles
- **User Bubble:** Solid primary gradient, text aligned right.
- **Assistant Bubble:** Glassmorphic grey (Level 2 Elevation), subtle white border, Hanken Grotesk font.

### Input Fields
- **Search/Chat Box:** Semi-transparent dark grey, pill-shaped, with a subtle internal glow when focused. Placeholder text in a muted slate-grey.

### Cards (Financial Data)
- Deep glassmorphism with Sora font for the primary metric. Include a "mini-sparkline" chart in the background using a 20% opacity primary color stroke.

### Chips
- Small, pill-shaped tags used for "Suggested Queries." These should use `label-sm` typography and have a slight 5% white hover state.