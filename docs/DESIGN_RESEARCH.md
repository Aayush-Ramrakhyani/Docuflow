# Design Research — DocuFlow

## Research Methodology

Internet browsing was unavailable during this session. Research is based on direct knowledge of production SaaS products, enterprise software, and document-processing platforms accumulated through the knowledge cutoff (August 2025).

Products studied: Linear, Raycast, Ramp, Mercury, Stripe, Vercel, Retool, DocuSign, Ironclad, ABBYY FlexiCapture, Coda, Notion, GitHub, Figma, Airtable, Klipfolio, Domo, Hyperscience, Rossum, Instabase.

---

## Product Category Analysis

### Document Intelligence Platforms (Core Competitors)
| Product | Aesthetic | Strengths | Weaknesses |
|---|---|---|---|
| ABBYY FlexiCapture | Enterprise blue, dated | Powerful processing | UI feels 2015 |
| Rossum | Clean, blue-accented | Modern extraction UI | Generic SaaS look |
| Hyperscience | Dark + orange | Bold confidence | Busy layout |
| Instabase | Minimal, blue | Developer-first | Lacks warmth |

### Adjacent Design References
| Product | Aesthetic | Takeaway |
|---|---|---|
| Linear | Dark, monochromatic, dense | Keyboard-first, operational efficiency |
| Ramp | Light, emerald accent, trust | Financial precision, clean |
| Mercury | Off-white, slate tones | Premium banking feel, whitespace |
| Vercel | Pure dark, monospace | Technical authenticity |
| Stripe | Purple, documentation-first | Confidence through clarity |
| GitHub | Dark sidebar, light content | Proven enterprise split layout |

---

## Three Visual Directions Evaluated

### Direction 1 — "Obsidian Intelligence"
**Philosophy:** Technical mastery expressed through pure darkness. The UI disappears; the data speaks.

| Element | Value |
|---|---|
| Page background | `#09090B` (zinc-950) |
| Card surface | `#18181B` (zinc-900) |
| Sidebar | `#09090B` |
| Primary accent | `#06B6D4` (cyan-500) |
| Secondary accent | `#0EA5E9` (sky-500) |
| Primary text | `#FAFAFA` |
| Muted text | `#71717A` (zinc-500) |
| Border | `#27272A` (zinc-800) |
| Font | Geist Mono + Geist Sans |
| Layout | Full-dark, icon+label sidebar, monospace data cells |

**Strengths:** Highly differentiated, technical, premium. Document review area would pop.  
**Weaknesses:** Dark themes are becoming overused in developer tools. May feel cold for enterprise document review workflows.

---

### Direction 2 — "Arctic Precision" ✅ SELECTED
**Philosophy:** Trust through clarity. Light, structured, and unambiguous — like the best financial SaaS tools. The dark sidebar anchors the layout; the content area is an open workspace.

| Element | Value |
|---|---|
| Page background | `#F8FAFC` (slate-50) |
| Card surface | `#FFFFFF` |
| Sidebar | `#0F172A` (slate-900) |
| Sidebar highlight | `#1E293B` (slate-800) |
| Primary accent | `#F59E0B` (amber-500) |
| Accent hover | `#D97706` (amber-600) |
| Primary text | `#0F172A` (slate-900) |
| Secondary text | `#475569` (slate-600) |
| Muted text | `#94A3B8` (slate-400) |
| Border | `#E2E8F0` (slate-200) |
| Success | `#22C55E` (green-500) |
| Warning | `#EAB308` (yellow-500) |
| Error | `#EF4444` (red-500) |
| Info | `#3B82F6` (blue-500) |
| Heading font | Inter, 600–700 weight |
| Body font | Inter, 400–500 weight |
| Data/mono font | JetBrains Mono |

**Layout:**
- Dark slate left sidebar (240px), collapsible
- Light content area with max-width constraint
- Document review: full-height split view (viewer left, extraction panel right)
- Tables: minimal borders, hover highlights, amber active states

**Why amber accent?**
Amber is rare in enterprise software (most use blue, purple, or green) but conveys precision, attention, and value — qualities central to document intelligence. It creates immediate visual differentiation without being aggressive.

**Strengths:** Highly distinctive. Communicates reliability and precision. Easy to read. Scales well across light and dark scenarios. Familiar split-panel enterprise layout but with a distinctive accent palette.

---

### Direction 3 — "Zinc Intelligence"
**Philosophy:** Warm neutral surfaces with rich indigo energy. Workflow-tool aesthetic.

| Element | Value |
|---|---|
| Page background | `#FAFAFA` (zinc-50) |
| Sidebar | `#18181B` (zinc-900) |
| Primary accent | `#4F46E5` (indigo-600) |
| Secondary accent | `#7C3AED` (violet-600) |
| Border | `#E4E4E7` (zinc-200) |
| Font | Plus Jakarta Sans + Fira Code |

**Strengths:** Modern, energetic. Feels like a workflow tool.  
**Weaknesses:** Indigo-to-violet gradient is precisely the "generic AI SaaS" pattern to avoid.

---

## Selected Direction: Arctic Precision

**Rationale:**
1. Amber accent is genuinely unusual and distinctive in enterprise software
2. Dark sidebar / light content is a proven, efficient enterprise layout (GitHub, Linear)
3. Document review workflows require maximum readability — light content area delivers this
4. Communicates trust and financial-grade precision (comparable to Ramp, Mercury)
5. Inter + JetBrains Mono is a proven, readable pairing for data-heavy interfaces
6. Clear differentiation from every common AI SaaS template

**Key UI patterns:**
- Sidebar items: icon + label, amber left border on active state
- Buttons: primary = amber-500 with white text; secondary = slate-100 with slate-900 text
- Tables: slate-50 header, white rows, border-b on each row
- Badges: colored pill shapes with 50% opacity background + full color text
- Document viewer: clean white background, PDF page shadows, page navigation at bottom
- Extraction panel: grouped field sections, confidence indicator bars, green/amber/red status dots
- Forms: slate-100 inputs with amber focus ring

---

## References Used in Design System

- Ramp (ramp.com) — table patterns, header layout
- GitHub (github.com) — dark sidebar + light content split
- Linear (linear.app) — sidebar navigation density and hierarchy
- Mercury (mercury.com) — card elevation and whitespace approach
- Stripe (stripe.com) — form design, error states
