# DocuFlow Design System — Arctic Precision

## Identity

DocuFlow communicates **precision**, **intelligence**, **reliability**, and **trust**.  
The visual language is clean, structured, and unambiguous — like the best financial SaaS tools.

---

## Color Tokens

### Primitives
```
slate-50:  #F8FAFC    slate-900: #0F172A
slate-100: #F1F5F9    slate-800: #1E293B
slate-200: #E2E8F0    slate-700: #334155
slate-300: #CBD5E1    slate-600: #475569
slate-400: #94A3B8    slate-500: #64748B

amber-400: #FBBF24    amber-600: #D97706
amber-500: #F59E0B    amber-700: #B45309

green-500: #22C55E    green-100: #DCFCE7
red-500:   #EF4444    red-100:   #FEE2E2
yellow-500:#EAB308    yellow-100:#FEF9C3
blue-500:  #3B82F6    blue-100:  #DBEAFE
```

### Semantic Tokens
```css
--background:         #F8FAFC   /* Page canvas */
--surface:            #FFFFFF   /* Cards, panels */
--surface-raised:     #FFFFFF   /* Elevated cards */
--surface-sunken:     #F1F5F9   /* Input backgrounds, table headers */

--sidebar-bg:         #0F172A   /* Navigation sidebar */
--sidebar-hover:      #1E293B   /* Sidebar item hover */
--sidebar-active:     #1E293B   /* Active sidebar item */
--sidebar-text:       #94A3B8   /* Sidebar muted text */
--sidebar-text-active:#FFFFFF   /* Active sidebar text */

--accent:             #F59E0B   /* Primary amber accent */
--accent-hover:       #D97706   /* Amber on hover */
--accent-muted:       #FEF3C7   /* Amber backgrounds */
--accent-foreground:  #78350F   /* Text on amber backgrounds */

--text-primary:       #0F172A   /* Headings, primary text */
--text-secondary:     #475569   /* Body text */
--text-muted:         #94A3B8   /* Placeholders, helper text */
--text-disabled:      #CBD5E1

--border:             #E2E8F0   /* Default borders */
--border-muted:       #F1F5F9   /* Subtle dividers */
--border-strong:      #CBD5E1   /* Emphasized borders */

--success:            #22C55E
--success-bg:         #DCFCE7
--warning:            #EAB308
--warning-bg:         #FEF9C3
--error:              #EF4444
--error-bg:           #FEE2E2
--info:               #3B82F6
--info-bg:            #DBEAFE
```

---

## Typography

### Font Stack
```css
--font-sans:  'Inter', system-ui, -apple-system, sans-serif;
--font-mono:  'JetBrains Mono', 'Fira Code', monospace;
```

### Scale
| Token | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| `text-xs` | 11px | 400 | 1.5 | Captions, labels |
| `text-sm` | 13px | 400 | 1.5 | Body small, table cells |
| `text-base` | 14px | 400 | 1.6 | Default body |
| `text-md` | 15px | 500 | 1.6 | Emphasized body |
| `text-lg` | 18px | 600 | 1.4 | Section headings |
| `text-xl` | 20px | 700 | 1.3 | Page headings |
| `text-2xl` | 24px | 700 | 1.2 | Major headings |
| `text-3xl` | 30px | 800 | 1.2 | Hero text |

### Rules
- Base font size is 14px (dense information product)
- Headings use Inter 600–800
- Data in tables uses `font-mono` for numbers and IDs
- Never use font-weight below 400

---

## Spacing

8px base unit. Spacing scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px.

Sidebar width: 240px (collapsed: 56px)  
Content max-width: 1280px  
Page padding: 32px  
Card padding: 24px  
Form section gap: 24px  

---

## Components

### Sidebar Navigation
- Background: `sidebar-bg` (#0F172A)
- Item padding: `12px 16px`
- Icon size: 18px
- Active: amber left border (3px), `sidebar-active` background, white text
- Hover: `sidebar-hover` background
- Section labels: `sidebar-text` (slate-400), 11px uppercase, letter-spacing 0.1em

### Buttons
```
Primary:    bg-amber-500 text-white hover:bg-amber-600 shadow-sm
Secondary:  bg-slate-100 text-slate-900 hover:bg-slate-200
Outline:    border border-slate-200 text-slate-700 hover:bg-slate-50
Ghost:      text-slate-600 hover:bg-slate-100 hover:text-slate-900
Danger:     bg-red-500 text-white hover:bg-red-600
```
Border radius: 6px  
Height: 32px (sm), 36px (default), 40px (lg)  
Padding: 12px 16px

### Inputs & Forms
```
Input:      bg-white border border-slate-200 focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20
Label:      text-sm font-medium text-slate-700
Helper:     text-xs text-slate-500
Error:      text-xs text-red-500
```
Border radius: 6px

### Cards
```
Default:   bg-white border border-slate-200 rounded-lg shadow-sm
Elevated:  bg-white border border-slate-200 rounded-xl shadow-md
Flat:      bg-slate-50 border border-slate-100 rounded-lg
```

### Tables
- Header: `bg-slate-50`, `text-xs font-semibold text-slate-500 uppercase tracking-wide`
- Row: `bg-white hover:bg-slate-50 border-b border-slate-100`
- Pagination: slate text, amber active page

### Badges / Status Pills
```
Success:  bg-green-50  text-green-700  border border-green-200
Warning:  bg-yellow-50 text-yellow-700 border border-yellow-200
Error:    bg-red-50    text-red-700    border border-red-200
Info:     bg-blue-50   text-blue-700   border border-blue-200
Muted:    bg-slate-100 text-slate-600  border border-slate-200
Amber:    bg-amber-50  text-amber-700  border border-amber-200
```
Border radius: 9999px (pill)  
Padding: `2px 8px`, font-size 11px, font-weight 500

### Confidence Indicators
Used in extraction review to show AI confidence per field:
```
High (≥90%):   amber filled bar
Medium (70-89%): amber/40 bar
Low (<70%):    red/40 bar
```
Bar width: 120px, height: 4px, border-radius: full

### Modals / Dialogs
- Backdrop: `bg-slate-900/50`
- Panel: `bg-white rounded-xl shadow-xl border border-slate-200`
- Max-width: 480px (default), 640px (wide), 90vw (full)

---

## Page Layouts

### App Shell
```
┌──────────────────────────────────────────────┐
│  Sidebar (240px fixed)  │  Main Content Area │
│  ─────────────────────  │  ────────────────  │
│  Logo + product name    │  Page header       │
│  Primary nav items      │  Content           │
│  ─────────────────────  │                    │
│  Team switcher          │                    │
│  User menu              │                    │
└──────────────────────────────────────────────┘
```

### Document Review Workspace
```
┌──────────────────────────────────────────────────┐
│  Review Header: doc name, status, actions         │
├──────────────────────┬───────────────────────────┤
│  Document Viewer     │  Extraction Panel          │
│  (PDF/image)         │  ──────────────────────── │
│  page navigation     │  Field groups              │
│  zoom controls       │  Confidence indicators     │
│  annotation marks    │  Edit controls             │
│                      │  Approve/Reject actions    │
└──────────────────────┴───────────────────────────┘
```

### Dashboard Layout
```
┌─────────────────────────────────────────────────────┐
│  Page heading + actions                              │
├──────────┬──────────┬──────────┬────────────────────┤
│ KPI card │ KPI card │ KPI card │ KPI card            │
├──────────┴──────────┴──────────┴────────────────────┤
│  Processing chart (line)   │  Status breakdown (pie) │
├─────────────────────────────────────────────────────┤
│  Recent documents table                              │
└─────────────────────────────────────────────────────┘
```

---

## Motion & Interaction

- Transition duration: 150ms (fast), 200ms (default), 300ms (slow)
- Easing: `ease-out` for enters, `ease-in` for exits
- Hover states: immediate color shifts, no delays
- Sidebar collapse: 200ms slide
- Modal enter: scale 0.95 → 1 with opacity, 150ms
- Table row hover: 100ms background fade
- No decorative animations — every motion has a functional purpose

---

## Dark Mode

Dark mode is not part of v1. The document review workspace (white document on white background) requires careful contrast attention. Dark mode will be introduced in v2 after the core product is stable.
