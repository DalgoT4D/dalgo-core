# Design Review Checklist

Use this checklist when reviewing any Dalgo UI component or page.

## Accessibility (WCAG AA)

- [ ] Color contrast meets 4.5:1 for normal text, 3:1 for large text
- [ ] All interactive elements have visible focus states (2px ring with offset)
- [ ] Tab order follows logical reading order
- [ ] Enter/Space activates buttons and controls
- [ ] Escape closes modals, dropdowns, and overlays
- [ ] Icon-only buttons have `aria-label`
- [ ] Dynamic content updates use `aria-live="polite"`
- [ ] Form inputs have associated `<Label>` elements
- [ ] Toggle switches have both visual AND `aria-checked` state
- [ ] Touch targets are at least 44x44px on mobile
- [ ] Images and charts have alt text or `aria-label`

## Usability

- [ ] Primary action is visually prominent and easy to find
- [ ] Destructive actions require confirmation
- [ ] Loading states shown during async operations
- [ ] Error messages are inline, specific, and suggest recovery
- [ ] Success messages confirm what happened with specifics
- [ ] Empty states have helpful messaging and a clear next action
- [ ] Forms validate inline (not just on submit)
- [ ] Required fields are marked with `*` indicator
- [ ] Long lists have pagination or virtual scrolling
- [ ] Navigation breadcrumbs for deep page hierarchies

## Visual Consistency

- [ ] Page follows the fixed header + scrollable content layout pattern
- [ ] Heading uses `text-3xl font-bold` for page title
- [ ] Subheading uses `text-muted-foreground mt-1`
- [ ] CTA buttons use `variant="ghost"` with `backgroundColor: var(--primary)`
- [ ] Colors reference CSS variables, not hardcoded hex
- [ ] Spacing follows the 4px grid (Tailwind defaults)
- [ ] Icons are from Lucide, sized at h-4 w-4 (16px)
- [ ] Cards use Shadcn `Card` with 8px border-radius

## Interactive Elements

- [ ] All buttons have `data-testid` attributes
- [ ] All form inputs have `data-testid` and `id` attributes
- [ ] List items use unique `key` props (not array index)
- [ ] List items have `data-testid` with unique identifiers

## Content & Copy

- [ ] No technical jargon without explanation
- [ ] Button labels use specific verbs ("Create Schedule" not "Submit")
- [ ] Loading states use specific text ("Sending..." not "Loading...")
- [ ] Error messages explain what went wrong AND suggest what to do
- [ ] Success messages include specifics ("Report sent to 3 recipients")

## Mobile & Responsive

- [ ] Layout works on viewports < 768px
- [ ] Complex forms use bottom sheets on mobile
- [ ] Native input types used where appropriate (`type="time"`, `type="date"`)
- [ ] Horizontal scrolling avoided (or intentional with indicators)
- [ ] Fixed header + footer with scrolling content on mobile

## NGO User Specific

- [ ] Screen purpose is clear within 5 seconds
- [ ] Smart defaults reduce required user input
- [ ] Progressive disclosure hides advanced options
- [ ] Consequences of actions stated upfront
- [ ] Recovery paths provided for errors
- [ ] No abbreviations or acronyms without explanation
