# Frontend Patterns

## Directory Structure

```
webapp_v2/
├── app/                      # Next.js App Router pages
│   ├── charts/              # Chart management and builder
│   ├── dashboards/          # Dashboard CRUD operations
│   ├── data-quality/        # Data quality management
│   ├── explore/             # Data exploration
│   ├── impact/              # Impact tracking
│   ├── ingest/              # Data ingestion workflows
│   ├── login/               # Authentication pages
│   ├── notifications/       # Notification management
│   ├── orchestrate/         # Orchestration management
│   ├── pipeline/            # Pipeline management
│   ├── settings/            # Application settings
│   ├── share/               # Shared/public dashboard views
│   └── transform/           # Data transformation tools
├── components/
│   ├── ui/                  # Reusable Radix-based UI components (GLOBAL)
│   ├── charts/              # Chart-specific components
│   ├── dashboard/           # Dashboard builder components
│   ├── dashboards/          # Dashboard list and management
│   ├── pipeline/            # Pipeline-specific components
│   └── settings/            # Settings-specific components
├── hooks/
│   ├── api/                 # SWR-based API hooks
│   └── [custom hooks]       # Utility hooks (toast, mobile, etc.)
├── stores/                  # Zustand stores (currently just authStore)
├── lib/                     # Global utilities (API client, SWR config, utils)
└── constants/               # Application constants (GLOBAL)
```

---

## State Management Decision Tree

| State Type | When to Use | Example |
|------------|-------------|---------|
| `useState` | Component-local, UI-only state | Modal open/close, form inputs, accordion expanded |
| Zustand | Global state needed across unrelated components, persists across routes | Auth state, selected org, user preferences |
| SWR | Server data that needs caching/revalidation | Charts list, dashboards, API data |
| URL params | State that should be shareable/bookmarkable (optional) | Pagination, filters, search query |

---

## Component Architecture

### UI Components (`components/ui/`)

- Pure presentational components
- Receive data and callbacks via props
- No API calls or business logic inside
- Focus on rendering and styling
- Examples: `Button`, `Card`, `Input`, `Dialog`, `Select`

### Functional/Feature Components

- Contain business logic and state management
- Make API calls and handle data
- Use UI components for rendering
- Live in feature directories (`components/charts/`, `components/dashboard/`)

```typescript
// UI Component - pure presentation
function Card({ title, children, className }: CardProps) {
  return (
    <div className={cn('rounded-lg border p-4', className)}>
      {title && <h3 className="font-semibold">{title}</h3>}
      {children}
    </div>
  );
}

// Functional Component - has logic and API calls
function ChartCard({ chartId }: { chartId: number }) {
  const { data: chart, mutate } = useChart(chartId);

  const handleFavorite = useCallback(async () => {
    await apiPost(`/api/charts/${chartId}/favorite`);
    mutate();
  }, [chartId, mutate]);

  return (
    <Card title={chart?.title}>
      <button onClick={handleFavorite}>
        <StarIcon filled={chart?.isFavorite} />
      </button>
    </Card>
  );
}
```

**Exception — UI components with inherent functionality:**
Some UI components have functionality that is intrinsic to their purpose (like a favorite star that must call an API). In these cases:
- The API call defines the component's core behavior
- Keep the functionality within the component
- Document clearly that this component has side effects

---

## Memoization Patterns

- **`React.memo`**: Wrap components that re-render without prop changes (e.g., parent state updates that don't affect the child)
- **`useMemo`**: Memoize calculations that iterate over arrays or transform data (e.g., sorting, filtering lists)
- **`useCallback`**: Wrap functions passed as props to memoized child components to prevent their re-renders

```typescript
// Wrap prop functions in useCallback
const handleFavorite = useCallback((chartId: number) => {
  // API call or state update
}, [dependencies]);

// Memoize expensive computations
const sortedCharts = useMemo(() => {
  return [...charts].sort((a, b) => a.title.localeCompare(b.title));
}, [charts]);

// Wrap component when parent re-renders but this component's props don't change
const ChartCard = memo(function ChartCard({ chart, onFavorite }: ChartCardProps) {
  // ...
});
```

**SWR Caching:**
- SWR automatically caches and deduplicates requests
- Use `mutate` to update cache after mutations
- Use unique, stable keys for SWR hooks

---

## Page Layout Pattern

All list/index pages (Charts, Pipelines, Orchestrate, etc.) follow this consistent layout:

1. **Fixed header** with border-bottom and background
2. **Title section** with heading + subheading + optional action button (top-right)
3. **Scrollable content area** below the header

```tsx
<div className="h-full flex flex-col">
  {/* Fixed Header */}
  <div className="flex-shrink-0 border-b bg-background">
    <div className="flex items-center justify-between mb-6 p-6 pb-0">
      <div>
        <h1 className="text-3xl font-bold">Page Title</h1>
        <p className="text-muted-foreground mt-1">
          Page description or subtitle
        </p>
      </div>

      {/* Optional action button (top-right) */}
      <Button
        variant="ghost"
        className="text-white hover:opacity-90 shadow-xs"
        style={{ backgroundColor: 'var(--primary)' }}
      >
        <Plus className="h-4 w-4 mr-2" />
        ACTION LABEL
      </Button>
    </div>
  </div>

  {/* Scrollable Content */}
  <div className="flex-1 min-h-0 overflow-hidden px-6 pb-6 mt-6">
    <div className="h-full overflow-y-auto">
      {/* Page content (tables, cards, lists, etc.) */}
    </div>
  </div>
</div>
```

**Real examples:** `app/charts/page.tsx`, `components/pipeline/pipeline-list.tsx`

---

## Typography Table

| Class | Where it's used |
|-------|-----------------|
| `text-3xl font-bold` | Page headings — Charts, Pipelines, Dashboards, Settings |
| `text-xl font-semibold` | Section headings, card titles, modal titles |
| `text-base` | Form labels, body text in settings/user management |
| `text-sm` | Table cells, form hints, secondary text |
| `text-xs` | Badges, timestamps, chart metadata |

---

## Form Patterns

**Complex forms (multiple fields, validation):**
- Use React Hook Form (uncontrolled inputs)
- Define form schema with TypeScript interfaces
- Use form's built-in validation

```typescript
const { register, handleSubmit, formState: { errors } } = useForm<FormData>();
```

**Simple inputs (single field, quick interaction):**
- Use `useState` (controlled inputs)
- Suitable for search boxes, single toggles, quick filters

```typescript
const [search, setSearch] = useState('');
<Input value={search} onChange={(e) => setSearch(e.target.value)} />
```

---

## Error Handling Patterns

**API Errors:**
- `lib/api.ts` handles auth errors and token refresh automatically
- API errors are thrown as Error objects with meaningful messages
- Use try/catch in components and show toast notifications

**Frontend Errors (graceful degradation):**
```typescript
// Safe object access
const userName = user?.profile?.name ?? 'Anonymous';

// Safe array access
const firstChart = charts?.[0] ?? null;

// Defensive rendering
{chart?.data && <ChartRenderer data={chart.data} />}
```

---

## Container and Scrolling Behavior

- **Preserve scrolling**: Ensure content can scroll when it overflows
- **Don't overflow**: Items should not spill outside their container bounds
- **Use appropriate overflow classes**: `overflow-auto`, `overflow-y-auto`, `overflow-x-hidden`
- **Consider max-height**: Use `max-h-[value]` with overflow for scrollable areas

```typescript
// Scrollable container example
<div className="max-h-[400px] overflow-y-auto">
  {items.map(item => <Item key={item.id} />)}
</div>
```

---

## Accessibility

- Preserve Radix UI's built-in accessibility props
- Add `aria-label` for icon-only buttons
- Ensure keyboard navigation works (Tab, Enter, Escape)
- Use semantic HTML elements (`button`, `nav`, `main`, `section`)
- Ensure sufficient color contrast

```typescript
<button aria-label="Add to favorites" onClick={handleFavorite}>
  <StarIcon />
</button>
```

---

## NPM Package Selection

Before adding a new package:

1. **Check existing packages first**: Review `package.json` to see if a similar package is already installed
2. **Evaluate new packages based on:** bundle size (bundlephobia.com), maintenance status, community adoption, TypeScript support

**Prefer packages that:** have smaller post-build size, are continuously updated, have high download counts, provide TypeScript types.

**Already installed for complex UI:**
- Date pickers: `react-day-picker`
- Drag and drop: `@dnd-kit`
- Grid layouts: `react-grid-layout`
- Charts: ECharts

---

## Chart Implementation

- **Use ECharts**: All charts are implemented using ECharts library
- **Use existing patterns**: Follow established chart component patterns in `components/charts/`
- **Handle data formatting**: Transform API data to chart-compatible formats
- **Export capabilities**: Implement PNG/PDF export using existing utilities
