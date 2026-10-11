---
name: Workshop Diagnostic Utility
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3e4947'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6e7977'
  outline-variant: '#bdc9c6'
  surface-tint: '#006a63'
  primary: '#005c55'
  on-primary: '#ffffff'
  primary-container: '#0f766e'
  on-primary-container: '#a3faef'
  inverse-primary: '#80d5cb'
  secondary: '#575e70'
  on-secondary: '#ffffff'
  secondary-container: '#d9dff5'
  on-secondary-container: '#5c6274'
  tertiary: '#7f4025'
  on-tertiary: '#ffffff'
  tertiary-container: '#9c573a'
  on-tertiary-container: '#ffe5db'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#9cf2e8'
  primary-fixed-dim: '#80d5cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#dce2f7'
  secondary-fixed-dim: '#c0c6db'
  on-secondary-fixed: '#141b2b'
  on-secondary-fixed-variant: '#404758'
  tertiary-fixed: '#ffdbce'
  tertiary-fixed-dim: '#ffb598'
  on-tertiary-fixed: '#370e00'
  on-tertiary-fixed-variant: '#72361b'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  data-mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
  data-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  data-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-compact: 0.5rem
  margin: 1rem
  margin-panel: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system delivers a professional workshop diagnostic tool engineered for automotive technicians, master mechanics, and workshop diagnostic specialists. The aesthetic combines clean utilitarian minimalism with ergonomic, high-density data layouts inspired by dedicated handheld scanners and diagnostic workstations.

### Core Principles
- **Ergonomic Neutrality:** Non-fatiguing visual architecture built for prolonged indoor bay use under harsh fluorescent and shop lighting.
- **Diagnostic Precision:** Immediate, unambiguous data hierarchy prioritizing vehicle telemetry, DTC status flags, and live sensor feeds over decorative flourishes.
- **Utilitarian Discipline:** Crisp micro-borders, dense grids, and tactile precision surfaces devoid of unnecessary car graphics or skeuomorphic embellishments.
- **Dual-Surface Density:** A deep graphite command rail paired with a calm, high-contrast industrial light canvas to distinguish persistent system-level navigation from active telemetry readouts.

## Colors

The palette balances clinical workshop neutrality with unambiguous status signaling.

### Palette Architecture
- **Primary Accent (`#0F766E`):** Deep workshop teal for focused interactions, primary actions, and confirmed diagnostic states. Secondary interaction state uses `#115E59`, backed by neutral tint container surfaces (`#F0FDFA`) and subtle structural boundaries (`#CCFBF1`).
- **Sidebar & Structural Anchor (`#111827`):** Slate graphite anchor establishing the tool shell, contextual side panels, and elevated contrast boundaries.
- **Canvas & Surfaces:** Cool industrial grey base canvas (`#F6F8FA`) hosting bright white operational cards (`#FFFFFF`) to maximize contrast without glare.
- **Typography Scale:** Deep slate black (`#0F172A`) for primary readings and metrics, balanced by muted slate (`#64748B`) for technical subtitles, physical units, and labels. Structural divisions utilize `#E2E8F0`.

### Diagnostic & Status Semantics
- **Confirmed Fault / DTC Critical:** Text `#DC2626` on background `#FEE2E2`.
- **Pending Fault / Warning:** Text `#D97706` on background `#FEF3C7`.
- **Connection Active / Valid Telemetry:** Text `#16A34A` on background `#DCFCE7`.
- **Simulation Mode Active:** Text `#4338CA` on background `#EEF2FF`.

## Typography

Typography enforces strict separation between structural application labels and diagnostic telemetry data.

- **Primary Interface (Inter):** Applied across global controls, diagnostics navigation, parameter designations (ex: *Tensão de bateria*, *Sensor de massa de ar*), and general copy. Weights remain strictly at 400 and 600 for high-visibility reading at arm's length.
- **Telemetry & Technical Codes (JetBrains Mono):** Reserved for DTC codes (ex: `P0301`, `U0100`), live numeric sensor outputs, hex ECU memory addresses, PID identifiers, and freeze-frame buffers. Provides tabular tabular alignment and instantaneous distinction between structural labels and raw telemetry.

## Layout & Spacing

The layout model optimizes screen space for high-density diagnostic operations, split between global control infrastructure and real-time operational feeds.

### Structural Framework
- **Primary Shell:** Fixed dark sidebar (64px collapsed icon-strip or 240px expanded navigation) anchored to the left, paired with an immovable 48px top hardware status bar.
- **Operational Grid:** Fluid modular grid utilizing 8px modular multiples. High-density telemetric tables use 8px spacing (`space-sm`), while card groupings and data cards operate on 16px (`space-md`) bounds.
- **Top Hardware Status Bar:** Fixed single-tier layout displaying active VCI link status, live terminal voltage (e.g., `12.4V`), bus protocol (`ISO 15765-4 CAN`), and mode indicators (`REAL` vs `SIMULAÇÃO`).

## Elevation & Depth

To maintain clarity under bright workshop bay lighting, elevation relies on crisp structural outlines and muted surface layers rather than diffuse drop shadows.

- **Level 0 (App Canvas):** Industrial neutral ground (`#F6F8FA`).
- **Level 1 (Telemetry Panels & Cards):** Pure white surfaces (`#FFFFFF`) delineated by crisp 1px structural outlines (`#E2E8F0`). Flat presentation with zero drop shadow to preserve contrast.
- **Level 2 (Dropdowns, VCI Connect Flyouts, Context Popovers):** Pure white surfaces with a fine 1px border (`#CBD5E1`) and a disciplined ambient shadow: `0 4px 12px rgba(15, 23, 42, 0.08)`.
- **Level 3 (Modal Alerts & Critical DTC Confirmation Dialogs):** Centered surfaces over a semi-opaque neutral backdrop (`#0F172A` at 40% opacity) with a directional containment shadow: `0 12px 24px -4px rgba(15, 23, 42, 0.16)`.

## Shapes

The interface implements a compact curvature scale tailored for utility software. Standard interactive components—buttons, data badges, parameter tiles, and operational card containers—consistently employ a 4px (`roundedness: 1`) to 8px base perimeter. This restrained radius maximizes content area inside dense sensor tables and mirrors the chamfered bezels of physical workshop diagnostic hardware.

## Components

### Persistent Hardware Status Header
- **Layout:** 48px fixed top bar; `#FFFFFF` surface with `#E2E8F0` bottom border.
- **Telemetry Metrics:** Monospace items showing connection status (e.g., `OBD-II: USB/FTDI`), detected protocol (`ISO 15765-4 CAN`), and terminal battery voltage (`12.4V`) with dynamic warning thresholds (< 11.8V amber).
- **Environment Tag:** Prominent contrast pills for `REAL` (Teal filled) or `SIMULAÇÃO` (Indigo/Slate bordered badge).

### Buttons & Quick Actions
- **Primary Action:** `#0F766E` background, `#FFFFFF` text, 36px height, 13px Inter font weight 600. Hover state shifts to `#115E59`.
- **Secondary Utility Action:** `#FFFFFF` background with 1px border `#E2E8F0`, `#0F172A` text. Hover shifts to `#F8FAFC`.
- **Destructive Action (Apagar Falhas / Clear DTCs):** Border `#FCA5A5`, text `#DC2626`, background `#FEF2F2`. Hover shifts to `#DC2626` text with `#FEE2E2`.

### DTC Cards & Sensor Telemetry Rows
- **DTC Diagnostic Cards:** Clean tabular cards split into three visual compartments: fault identifier pill (e.g., `P0301` in monospace bold), localized diagnostic name (*Falha de combustão no cilindro 1*), and mechanical state badge (*Confirmada* / *Pendente*).
- **Live Telemetry Grid (PIDs):** Alternating neutral rows (`#FFFFFF` and `#F8FAFC`) with crisp 1px borders. Metric names in Inter 13px, values in JetBrains Mono 14px bold, and measurement units (*rpm*, *g/s*, *°C*, *bar*) in Inter 11px muted slate.

### Badges & Status Indicators
- **Standard Badges:** 20px height, 6px horizontal padding, 4px border radius.
- **Real Mode:** Solid `#0F766E` background, `#FFFFFF` text, label-sm typography.
- **Simulação Mode:** `#EEF2FF` background, `#4338CA` text, 1px border `#C7D2FE`.
- **DTC Confirmed:** `#FEE2E2` background, `#DC2626` text, 1px border `#FECACA`.

### Diagnostic Data Inputs & Filter Bars
- **Filter Fields:** 32px height, 1px `#E2E8F0` border, 8px horizontal padding. Focus state features a 1px `#0F766E` ring with zero shadow diffusion.