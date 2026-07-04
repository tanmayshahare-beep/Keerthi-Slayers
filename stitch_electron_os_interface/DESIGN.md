---
name: AROS Core
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1c1b1d'
  surface-container: '#201f21'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#b9cacb'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#313032'
  outline: '#849495'
  outline-variant: '#3b494b'
  surface-tint: '#00dbe9'
  primary: '#dbfcff'
  on-primary: '#00363a'
  primary-container: '#00f0ff'
  on-primary-container: '#006970'
  inverse-primary: '#006970'
  secondary: '#d1bcff'
  on-secondary: '#3c0090'
  secondary-container: '#7000ff'
  on-secondary-container: '#ddcdff'
  tertiary: '#fff5de'
  on-tertiary: '#3b2f00'
  tertiary-container: '#fed639'
  on-tertiary-container: '#715d00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#7df4ff'
  primary-fixed-dim: '#00dbe9'
  on-primary-fixed: '#002022'
  on-primary-fixed-variant: '#004f54'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d1bcff'
  on-secondary-fixed: '#23005b'
  on-secondary-fixed-variant: '#5700c9'
  tertiary-fixed: '#ffe179'
  tertiary-fixed-dim: '#eac324'
  on-tertiary-fixed: '#231b00'
  on-tertiary-fixed-variant: '#554500'
  background: '#131315'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
  electric-blue: '#00F0FF'
  deep-obsidian: '#0A0A0C'
  slate-gray: '#1A1A1E'
  clean-paper: '#F8F9FA'
  agent-active: '#00F0FF'
  agent-thinking: '#7000FF'
  data-positive: '#00FF41'
  data-negative: '#FF3131'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  data-code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.6'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.08em
  headline-md-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.2'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-edge: 24px
  container-max: 1440px
---

## Brand & Style

The design system is a high-precision, technical interface designed for the Retail AI Operating System. It embodies an **"Electron-style"** aesthetic—referencing code editors and professional developer tools—to signal reliability, depth, and intelligence. The brand personality is clinical, authoritative, and fast, catering to data analysts and retail executives who require high-information density without cognitive overload.

The visual style is a hybrid of **Minimalism** and **Glassmorphism**. It utilizes a structured, utilitarian layout paired with subtle translucent layers and "frosted" surfaces to create a sense of digital sophistication. The interface should feel like a high-tech cockpit: everything is intentional, data is paramount, and AI activity is visually distinct through vibrant, energetic accents.

**Key Principles:**
- **Density over Decoration:** Maximize screen real estate for data visualization and agent logs.
- **Visual Intelligence:** Use motion and color primarily to indicate AI reasoning and real-time processing.
- **Structural Integrity:** Heavy reliance on grid alignment and clear visual hierarchies to organize complex multi-agent workflows.

## Colors

The system operates across two distinct themes: **Dark Obsidian** (default) and **Clean Paper**. 

- **Dark Obsidian:** Designed for focus and high-tech immersion. It uses a near-black neutral (`#0A0A0C`) for backgrounds and layered grays for surface elevation.
- **Clean Paper:** A high-contrast light mode that mimics professional technical documentation.
- **Primary Accent (Electric Blue):** Reserved exclusively for interactive elements, AI status indicators, and active workflow states.
- **Secondary Accent (Purple):** Used for "Reasoning" or "Thinking" states within LLM agents to differentiate between execution and processing.

Color should be used sparingly as a functional tool rather than decoration. Data trends use industry-standard Green/Red but are tuned to high-saturation "neon" variants to pop against the dark backgrounds.

## Typography

The typography system strikes a balance between human-readable UI and machine-readable data.

1.  **Inter (UI Elements):** Used for all navigational elements, buttons, and descriptive body text. It provides a modern, neutral foundation that ensures legibility.
2.  **JetBrains Mono (Data & Logic):** Used for all numerical data, JSON outputs, agent logs, and status labels. The monospaced nature ensures that columns of numbers align perfectly, aiding in rapid data comparison.

**Formatting Rules:**
- **Labels:** Always use `label-caps` (JetBrains Mono, Uppercase) for section headers and metadata.
- **Data Tables:** Use `data-code` for all table content to maintain vertical alignment of digits.
- **Hierarchy:** Use tight line heights for headlines to maintain a compact, "terminal" feel.

## Layout & Spacing

This design system employs a **Fixed Grid** philosophy for desktop to maintain rigorous control over data density, switching to a fluid model for mobile.

- **Grid:** A 12-column system with a 16px gutter. In "Data Heavy" views, the gutter may be reduced to 8px to maximize information visibility.
- **Rhythm:** All spacing is based on a 4px baseline grid. Padding and margins should always be multiples of 4 (e.g., 8, 12, 16, 24, 32).
- **Responsive Behavior:** 
    - **Desktop (1024px+):** Fixed sidebars for agent status; multi-pane "dashboard" layout.
    - **Tablet (768px - 1023px):** Sidebars collapse into icons; main content area becomes fluid.
    - **Mobile (<767px):** Single column stack; data tables convert to simplified cards; code blocks horizontal scroll.

## Elevation & Depth

Depth is conveyed through **Tonal Layers** and **Glassmorphism** rather than traditional shadows. 

- **Surface Levels:** 
    - **Level 0 (Background):** Deep Obsidian (`#0A0A0C`).
    - **Level 1 (Panels):** Slate Gray (`#1A1A1E`) with a 1px border.
    - **Level 2 (Overlays/Popovers):** Slate Gray with 80% opacity and a 20px backdrop-blur.
- **Outlines:** Use "Ghost Borders"—low-opacity (10-15%) white or primary-color strokes—to define boundaries without adding visual bulk.
- **AI Activity:** When an agent is active, its container should emit a subtle, 2px outer glow in the Primary Accent color (`#00F0FF`) to indicate "Execution Mode."

## Shapes

The shape language is "Soft-Industrial." It avoids the playfulness of hyper-rounded corners in favor of a precise, engineered look.

- **Components:** Standard buttons, input fields, and cards use a 4px (`0.25rem`) corner radius.
- **Visual Containers:** Larger dashboard sections may use 8px (`0.5rem`) for `rounded-lg`.
- **Status Pills:** Small status indicators (e.g., "LIVE", "STABLE") use a 2px radius to remain sharp and legible at small sizes.
- **Selection States:** Active selections are indicated by a sharp, 2px vertical bar on the left edge rather than large background shifts.

## Components

**Buttons:**
- **Primary:** Solid Electric Blue background, black Inter Bold text. No roundedness beyond 4px.
- **Secondary/Ghost:** 1px Electric Blue border, transparent background, Electric Blue text.
- **Actionable Icons:** Monochromatic white/gray, shifting to Primary color on hover.

**Input Fields:**
- Dark background (`#0A0A0C`) with a 1px border (`#FFFFFF` at 10% opacity). Focus state changes border to Electric Blue with a faint inner glow. Labels always sit above the field in `label-caps`.

**Cards & Panels:**
- No shadows. Use 1px borders. Header of the card should have a slightly darker background than the body to create a "tabbed" appearance.

**AI Agent Logs:**
- Use a code-terminal style container. JetBrains Mono font. Different colors for different agents (e.g., Finance = Blue, Supply Chain = Purple).

**Chips/Tags:**
- Small, rectangular, with 2px radius. Use for `location_id`, `sku`, or `status`.

**Data Visualization:**
- Charts should use thin 1px lines. No fills under lines unless using a 5% opacity gradient. Grid lines in charts should be barely visible (5% opacity white).