# Dalgo UI Patterns Reference

Established patterns used across the Dalgo platform. Use these as the baseline when reviewing new UI work.

## Component Library

- **Primary library:** Shadcn UI (Radix UI headless primitives with custom styling)
- **Components location:** `webapp_v2/components/ui/`
- **Icon library:** Lucide icons, 16px (h-4 w-4)

## Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | `#00897B` (teal) | CTAs, active states, brand elements |
| `text-muted-foreground` | (from Shadcn) | Subtext, descriptions, subtitles |
| `text-destructive` | (from Shadcn) | Delete buttons, error states |
| `bg-background` | (from Shadcn) | Page/section backgrounds |
| `text-foreground` | (from Shadcn) | Main text color |

**Rule:** Never hardcode hex values. Always use CSS variables or Tailwind theme classes.

## Typography

| Class | Usage |
|-------|-------|
| `text-3xl font-bold` | Page headings (Charts, Pipelines, etc.) |
| `text-xl font-semibold` | Section headings, card titles, modal titles |
| `text-base` | Form labels, body text |
| `text-sm` | Table cells, form hints, secondary text |
| `text-xs` | Badges, timestamps, metadata |

**Font:** Anek Latin via `var(--font-anek-latin)`, set globally. Never set per-component.

## Page Layout Pattern

All list/index pages follow this structure:

```
Fixed header (border-bottom, bg-background)
  ├── Title (text-3xl font-bold) + Subheading (text-muted-foreground)
  └── Optional CTA button (top-right)
Scrollable content area
  └── Tables, cards, lists, etc.
```

**Reference:** `app/charts/page.tsx`, `components/pipeline/pipeline-list.tsx`

## Button Patterns

### Primary CTA
```tsx
<Button
  variant="ghost"
  className="text-white hover:opacity-90 shadow-xs"
  style={{ backgroundColor: 'var(--primary)' }}
>
  <Plus className="h-4 w-4 mr-2" />
  ACTION LABEL
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

## Dialog / Modal Pattern

- Component: Shadcn `Dialog`
- Max width: `sm:max-w-md` for forms
- Mobile: Should use bottom sheets for complex forms
- Reference: `components/reports/share-via-email-dialog.tsx`

## Form Patterns

- **Complex forms:** React Hook Form (uncontrolled)
- **Simple inputs:** useState (controlled)
- **Labels:** `<Label>` + required indicator `<span className="text-destructive">*</span>`
- **Helper text:** 12px, `text-muted-foreground`, below input
- **Errors:** Inline below field, red text
- **Validation:** Inline as user types, not just on submit

## Card Pattern

- Shadcn `Card` + `CardContent`
- Border: 1px solid
- Padding: 16px
- Border radius: 8px
- Hover: Border color changes to primary for interactive cards

## Dropdown Menu Pattern

- Shadcn `DropdownMenu` + `DropdownMenuItem`
- Icons: Lucide, h-4 w-4, left-aligned
- Reference: `components/reports/report-share-menu.tsx`

## Email Input Pattern

- Textarea with comma/semicolon separation (NOT chip-based UI)
- Validation: EMAIL_REGEX from `components/reports/utils.ts`
- Max recipients: 20 (MAX_RECIPIENTS constant)
- Helper text: "Recipients are separated by ',' or ';'"

## Toast Notifications

- Library: Sonner
- Always use helpers from `lib/toast.ts`: `toastSuccess`, `toastError`, `toastInfo`, `toastPromise`
- Never call `toast()` directly
- Success: Specific + actionable ("Report sent to 3 recipients")
- Error: Explain + suggest recovery ("Invalid email: maya@ngo (missing domain)")

## Spacing System

- Base grid: 4px (Tailwind defaults)
- Component padding: 16px
- Section gaps: 24px vertical
- Page padding: `p-6`

## Information Architecture

- Dashboard (parent) -> Reports (children) hierarchy
- Don't manage parent entities from child pages
- Use awareness + jump links: "This dashboard has 2 schedules. [Manage ->]"
- Breadcrumbs for deep hierarchies
- Back buttons for linear flows

## Data Display

- Tables for structured data with sorting
- Cards for entity summaries
- Empty states always have a message + primary action CTA
- Loading skeletons preferred over spinners for content areas
