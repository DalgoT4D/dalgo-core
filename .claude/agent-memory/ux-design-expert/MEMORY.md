# Dalgo Platform - UX Design Patterns

## Project Context
- **Platform**: Data platform for non-technical NGO users (program managers, field staff)
- **Tech stack**: Next.js (webapp_v2), Django backend, Shadcn UI components
- **User base**: Non-technical users, need simplicity and progressive disclosure

## Design System

### Component Library
- **Shadcn UI** is the primary component library
- Components live in `webapp_v2/components/ui/`
- Follow Shadcn patterns for consistency

### Color Palette
- Primary brand: `#00897B` (teal, used for CTAs and hover states)
- Success: `#10b981` → but fails WCAG AA, use `#059669` for text
- Muted text: `text-muted-foreground` (from Shadcn, accessible)
- Border: `#e5e7eb`

### Typography
- Base font size: 16px minimum (accessibility requirement)
- Hierarchy:
  - Page titles: 20-24px semibold
  - Section headings: 16-18px semibold
  - Body: 14px regular
  - Helper text: 12px regular, muted

### Spacing
- Use 4px base grid (Tailwind defaults)
- Component padding: 16px standard
- Section gaps: 24px vertical

## UI Patterns Used in Dalgo

### Dialogs & Modals
- Pattern: Shadcn `Dialog` component
- Max width: `sm:max-w-md` for forms (500-600px)
- Mobile: Should use bottom sheets for complex forms
- Example: `share-via-email-dialog.tsx`

### Forms
- Use React Hook Form for validation
- Label pattern: `<Label>` + required indicator `<span className="text-destructive">*</span>`
- Helper text: 12px, `text-muted-foreground`, below input
- Error messages: Inline below field, red text
- Example: Email sharing dialog (subject + recipients textarea)

### Cards
- Pattern: Shadcn `Card` + `CardContent`
- Border: 1px solid border color
- Padding: 16px
- Border radius: 8px
- Hover: Border color → primary for interactive cards

### Dropdown Menus
- Pattern: Shadcn `DropdownMenu` + `DropdownMenuItem`
- Icons: Lucide icons, 16px (h-4 w-4)
- Icon + text layout in menu items
- Example: `report-share-menu.tsx`

### Email Input Pattern
- Use textarea with comma/semicolon separation (NOT chip-based UI)
- Validation: EMAIL_REGEX from `components/reports/utils.ts`
- Max recipients: 20 (MAX_RECIPIENTS constant)
- Helper text: "Recipients are separated by ',' or ';'"
- Example: `share-via-email-dialog.tsx`

### Buttons
- Primary action: `variant="ghost"` with `style={{ backgroundColor: 'var(--primary)' }}`
- Secondary: `variant="outline"`
- Icon buttons: `size="icon"`, 40px touch target
- Loading state: `<Loader2 className="h-4 w-4 animate-spin" />`

## Accessibility Standards

### Required for All Features
- WCAG AA minimum (4.5:1 contrast for normal text)
- Focus states: 2px ring with offset
- Touch targets: 44x44px minimum (mobile)
- ARIA labels for icon-only buttons
- Keyboard navigation: Tab order, Enter to submit, Escape to close
- Screen reader: `aria-live` for dynamic content, `role` attributes

### Common Patterns
- Toggle switches: Need both visual AND `aria-checked` state
- Conditional fields: Use `aria-controls` + `aria-live="polite"`
- Time inputs: Use `<input type="time">` on mobile for native picker

## User Experience Principles

### Progressive Disclosure
- Don't show all options upfront
- Use "Advanced options" expandable sections
- Wizards/steppers for complex flows (3+ required fields)
- Default to smart presets (e.g., user's timezone)

### Mental Models
- NGO users think in terms of: "I want X to happen automatically"
- Avoid technical jargon (use "recipients" not "email list")
- Explain side effects upfront (e.g., "This will enable public access")

### Error Handling
- Show errors inline, next to the field
- Use toasts for async operation results
- Provide recovery paths ("View schedules" link in error notification)
- Don't fail entire operations for partial failures (e.g., one email bounce)

### Mobile Optimization
- Use bottom sheets for forms (<768px)
- Native input types (`type="time"`, `type="date"`)
- Horizontal scrolling chips instead of dropdowns for small option sets
- Fixed header + footer with scrolling content

## Information Architecture Patterns

### Hierarchy Rules
- Dashboard (parent) → Reports (children) relationship
- Don't manage parent-level entities from child pages
- Use awareness + jump links instead (e.g., "This dashboard has 2 schedules. [Manage →]")

### Navigation
- Breadcrumbs for deep hierarchies
- Back buttons for linear flows
- Clear page titles always visible
- Tab navigation for feature sections within an entity

## Copy & Microcopy

### Voice & Tone
- Friendly, helpful, not corporate
- Use questions for form labels when appropriate ("How often?" vs "Frequency")
- Avoid jargon (use "recipients" not "email array")

### Button Labels
- Use specific verbs: "Create Schedule" not "Submit"
- Loading states: "Sending..." not "Loading..."
- Destructive actions: "Delete Schedule" not "Delete" alone

### Success Messages
- Specific + actionable: "Schedule created! Next report will be sent on Monday, Apr 14 at 09:00 UTC"
- Avoid generic: ❌ "Success" ✅ "Report sent to 3 recipients"

### Error Messages
- Explain what went wrong: "Invalid email: maya@ngo (missing domain)"
- Provide solution: "Please check and try again"
- For technical errors: "This dashboard no longer exists. You cannot create schedules for deleted dashboards."

## Files to Reference

### UI Components
- `/Users/siddhant/Documents/dalgo/webapp_v2/components/reports/share-via-email-dialog.tsx` - Email input pattern
- `/Users/siddhant/Documents/dalgo/webapp_v2/components/reports/report-share-menu.tsx` - Dropdown menu pattern
- `/Users/siddhant/Documents/dalgo/webapp_v2/components/reports/utils.ts` - Shared constants (EMAIL_REGEX, MAX_RECIPIENTS)

### Planning Docs
- `/Users/siddhant/Documents/dalgo/dalgo-ai-gen/dalgo_mds/claude/planning/reports/` - Feature plans
