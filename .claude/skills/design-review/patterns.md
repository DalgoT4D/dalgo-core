# Dalgo UI Patterns Reference

**Source of truth:** [`DalgoT4D/dalgo-design-system`](https://github.com/DalgoT4D/dalgo-design-system)  
— `tokens.css` (design tokens) + `components.css` (component specs, all values reference `var(--*)`).

This file maps design-system tokens → Tailwind / Shadcn class names for `webapp_v2`.  
Do not hardcode hex values or pixel sizes — reference CSS variables or the mappings below.

---

## Component Library

- **Primary library:** Shadcn UI (Radix UI headless primitives with custom styling)
- **Components location:** `webapp_v2/components/ui/`
- **Icon library:** Lucide (size is context-specific — see Icon Sizes section)

---

## Design Tokens → Tailwind / Shadcn Mapping

### Colors

| Design system token | Value | Tailwind / Shadcn equivalent | Role |
|---------------------|-------|------------------------------|------|
| `--color-brand-primary` | `#00897b` | `style={{ backgroundColor: 'var(--color-brand-primary)' }}` | CTAs, active states, brand |
| `--color-brand-primary-hover` | `#00796b` | hover on brand elements | Button hover |
| `--color-brand-primary-light` | `#e8f4f3` | — | Light teal backgrounds |
| `--color-text-primary` | `#1a1a2e` | `text-foreground` | Main body text |
| `--color-text-secondary` | `#5c5c6d` | `text-muted-foreground` | Subtext, descriptions, subtitles |
| `--color-text-tertiary` | `#7a7a8c` | — | De-emphasised labels |
| `--color-text-placeholder` | `#b0b0be` | `placeholder:text-muted-foreground` | Input placeholders |
| `--color-bg` | `#f8fafb` | `bg-background` | Page background |
| `--color-surface` | `#ffffff` | `bg-white` / `bg-card` | Cards, panels, header |
| `--color-surface-hover` | `#f5f7f8` | `hover:bg-muted` | Table row hover |
| `--color-border` | `#e8ecef` | `border` | Default borders |
| `--color-row-divider` | `#f1f5f9` | — | Between table rows |
| `--color-alert` | `#ef5350` | `text-destructive` | Errors, delete actions |

**Rule:** Never hardcode hex values. Reference `var(--color-*)` directly, or the Tailwind class equivalents above.

**Missing (not yet in `tokens.css`):** RAG status colors — on-track, at-risk, off-track, stale.  
These need to be added to the design system repo. Use the design-system token names when they land:  
`--color-status-on-track`, `--color-status-at-risk`, `--color-status-off-track`, `--color-status-stale`.

### Typography

| Design system token | Value | Tailwind equivalent | Usage |
|---------------------|-------|---------------------|-------|
| `--font-size-3xl` | 32px | `text-3xl` | Page headings |
| `--font-size-2xl` | 28px | `text-[28px]` | Large modal titles |
| `--font-size-xl` | 26px | `text-[26px]` | Section headings |
| `--font-size-lg` | 22px | `text-[22px]` | Card titles |
| `--font-size-md` | 16px | `text-base` | Form labels, body text |
| `--font-size-base` | 15px | `text-[15px]` | Standard body |
| `--font-size-sm` | 14px | `text-sm` | Table cells, hints, secondary text |
| `--font-size-xs` | 13px | `text-xs` | Badges, timestamps, metadata |

| Design system token | Value | Usage |
|---------------------|-------|-------|
| `--font-weight-regular` | 400 | Body text |
| `--font-weight-medium` | 500 | Labels, nav items |
| `--font-weight-semibold` | 600 | Section headings |
| `--font-weight-bold` | 700 | Page headings |
| `--line-height-normal` | 1.5 | Default body |
| `--letter-spacing-button` | 0.3px | Button labels |

**Font:** `--font-sans: 'Anek Latin'` — set globally, never per-component.  
Requires: `<link href="https://fonts.googleapis.com/css2?family=Anek+Latin:wght@400;500;600;700&display=swap" rel="stylesheet">`

### Spacing

The spacing scale is **not Tailwind's standard 4px multiples** — use the named semantic aliases:

| Semantic alias | Resolves to | Value | Use |
|----------------|-------------|-------|-----|
| `--spacing-page-x` | `--space-12` | 32px | Horizontal page padding |
| `--spacing-page-y` | `--space-11` | 28px | Vertical page padding |
| `--spacing-section` | `--space-11` | 28px | Between major sections |
| `--spacing-form-group` | `--space-10` | 24px | Between form field groups |
| `--spacing-label` | `--space-3` | 8px | Label → input gap |
| `--spacing-header-gap` | `--space-7` | 16px | Elements inside the header |
| `--spacing-tag-gap` | `--space-2` | 6px | Between tags |
| `--spacing-frequency-gap` | `--space-3` | 8px | Between frequency buttons |

Raw scale (partial): `--space-3`=8px · `--space-5`=12px · `--space-7`=16px · `--space-9`=20px · `--space-10`=24px · `--space-11`=28px · `--space-12`=32px · `--space-13`=40px · `--space-14`=48px

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Inputs, tags, small chips |
| `--radius-md` | 8px | Cards, modals, buttons |
| `--radius-lg` | 12px | Large panels |
| `--radius-full` | 50% | Avatars, circular badges |

### Layout Dimensions

| Token | Value | Usage |
|-------|-------|-------|
| `--sidebar-width` | 224px | Left navigation rail |
| `--header-height` | 60px | Top bar |

### Shadows

| Token | Usage |
|-------|-------|
| `--shadow-modal` | Dialog / modal overlay |
| `--shadow-dropdown` | Dropdown menus, popovers |
| `--shadow-focus` | Focus ring on interactive elements (3px, brand-primary-ring) |

### Transitions

| Token | Value | Usage |
|-------|-------|-------|
| `--transition-fast` | 0.10s ease | Hover on small elements |
| `--transition-normal` | 0.15s ease | Most interactive states |
| `--transition-slow` | 0.25s ease | Page-level transitions |

---

## Page Layout Pattern

All list / index pages follow this structure:

```
Fixed header (border-bottom, bg: --color-surface, height: --header-height 60px)
  ├── Title (--font-size-3xl / --font-weight-bold / --color-text-primary)
  ├── Subheading (--font-size-sm / --color-text-secondary)
  └── Optional CTA button (top-right)

Scrollable content area
  padding: --spacing-page-y (28px) --spacing-page-x (32px)
  └── Tables, cards, lists, etc.
```

**Reference:** `app/charts/page.tsx`, `components/pipeline/pipeline-list.tsx`

---

## Button Patterns

### Primary CTA
```tsx
<Button
  variant="ghost"
  className="text-white hover:opacity-90 shadow-xs"
  style={{ backgroundColor: 'var(--color-brand-primary)' }}
>
  <Plus className="h-4 w-4 mr-2" />
  Create Report
</Button>
```

### Secondary
```tsx
<Button variant="outline">Secondary Action</Button>
```

### Icon Button
```tsx
<Button size="icon" aria-label="Description">
  <Icon className="h-4 w-4" />
</Button>
```

### Loading State
```tsx
<Button disabled>
  <Loader2 className="h-4 w-4 animate-spin mr-2" />
  Sending...
</Button>
```

**Note:** `components.css` applies `text-transform: uppercase` on `.btn`. In `webapp_v2` (Tailwind/Shadcn)
this is not inherited; follow the label casing of existing Shadcn buttons in the codebase.  
This is an open conflict — see the constitution once it is written.

---

## Icon Sizes

Sizes are context-specific — do not apply a blanket 16px rule:

| Context | Size | Tailwind class |
|---------|------|----------------|
| Button icons | 16px | `h-4 w-4` |
| Nav rail icons | 18px | `h-[18px] w-[18px]` |
| Table action icons | 14px | `h-3.5 w-3.5` |
| Empty state illustration | 40–48px | `h-10 w-10` or `h-12 w-12` |

---

## Dialog / Modal Pattern

- Component: Shadcn `Dialog`
- Shadow: `--shadow-modal`
- Max width: `sm:max-w-md` for forms
- Mobile: bottom sheets for complex forms
- Reference: `components/reports/share-via-email-dialog.tsx`

---

## Form Patterns

- **Complex forms:** React Hook Form (uncontrolled)
- **Simple inputs:** useState (controlled)
- **Label gap:** `--spacing-label` (8px) between label and input
- **Labels:** `<Label>` + required indicator `<span className="text-destructive">*</span>`
- **Helper text:** `--font-size-xs` (13px), `--color-text-secondary`, below input
- **Errors:** Inline below field, `--color-alert` (`#ef5350`) text
- **Validation:** Inline as user types, not just on submit

---

## Card Pattern

- Shadcn `Card` + `CardContent`
- Border: 1px solid `--color-border`
- Padding: `--space-7` (16px)
- Border radius: `--radius-md` (8px)
- Hover: border → `--color-brand-primary` for interactive cards

---

## Dropdown Menu Pattern

- Shadcn `DropdownMenu` + `DropdownMenuItem`
- Shadow: `--shadow-dropdown`
- Icons: Lucide, `h-4 w-4`, left-aligned
- Reference: `components/reports/report-share-menu.tsx`

---

## Email Input Pattern

- Textarea with comma/semicolon separation (NOT chip-based UI)
- Validation: `EMAIL_REGEX` from `components/reports/utils.ts`
- Max recipients: 20 (`MAX_RECIPIENTS` constant)
- Helper text: "Recipients are separated by ',' or ';'"

---

## Toast Notifications

- Library: Sonner
- Always use helpers from `lib/toast.ts`: `toastSuccess`, `toastError`, `toastInfo`, `toastPromise`
- Never call `toast()` directly
- Success: specific + actionable ("Report sent to 3 recipients")
- Error: explain + suggest recovery ("Invalid email: maya@ngo (missing domain)")

---

## Information Architecture

- Dashboard (parent) → Reports (children) hierarchy
- Don't manage parent entities from child pages
- Use awareness + jump links: "This dashboard has 2 schedules. [Manage →]"
- Breadcrumbs for deep hierarchies
- Back buttons for linear flows

---

## Data Display

- Tables for structured data with sorting
- Cards for entity summaries
- Empty states always have a message + primary action CTA
- Loading skeletons preferred over spinners for content areas
