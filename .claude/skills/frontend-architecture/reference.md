# Frontend Reference

## Folder Structure for New Features

Follow the **pipeline feature** as the reference implementation:

```
app/
├── pipeline/
│   └── page.tsx                  # Thin page — delegates to a component

components/
├── pipeline/                      # Feature-specific components
│   ├── pipeline-list.tsx          # Separate file — has own state, effects, API calls
│   ├── pipeline-form.tsx          # Separate file — has own state, effects, API calls
│   ├── pipeline-run-history.tsx   # Separate file — has own state, effects, API calls
│   ├── task-sequence.tsx          # Separate file — has own state, effects, API calls
│   ├── utils.ts                   # Feature-specific utility functions
│   └── __tests__/                 # Co-located tests with mock data
│       ├── pipeline.test.tsx
│       ├── pipeline-utils.test.ts
│       └── pipeline-mock-data.ts

hooks/
├── api/
│   └── usePipelines.ts            # SWR read hooks + standalone mutation functions

types/
├── pipeline.ts                    # TypeScript interfaces for API responses

constants/
├── pipeline.ts                    # Named constants (polling intervals, status enums, etc.)
```

**What the pipeline does right:**
- Page is a thin wrapper, all logic lives in components
- Each component with its own state/effects/API calls is a separate file
- SWR hooks for reads (`usePipelines`, `usePipeline`) + standalone async functions for mutations (`createPipeline`, `deletePipeline`)
- Feature-specific `utils.ts` for cron parsing, time formatting, etc. — not inline in components
- Named constants (`POLLING_INTERVAL_WHEN_LOCKED`, `LockStatus`, `FlowRunStatus`) in `constants/pipeline.ts`
- Proper TypeScript types in `types/pipeline.ts`
- Uses `toastSuccess`/`toastError` from `lib/toast.ts` — never raw `toast()`
- Follows the page layout pattern (fixed header + scrollable content)
- Uses the CTA button pattern (`variant="ghost"` + `style={{ backgroundColor: 'var(--primary)' }}`)
- `data-testid` on key elements, `key` using stable IDs, `useCallback`/`useMemo` where appropriate
- Co-located `__tests__/` directory with unit tests and mock data

**Guidelines for component files:**
- **Separate file**: If the component has its own `useState`, `useEffect`, API calls, or event handler logic
- **Same file as parent**: If the component only renders props passed from the parent (no state, no effects, no API calls) and is only used by that parent
- **Always separate**: If the component is used by more than one parent

---

## Utility and Constants Organization

**Global utilities and constants** (used across multiple features):
- `lib/utils.ts` — General utility functions
- `lib/api.ts` — API client functions
- `constants/` — Application-wide constants

**Feature-specific utilities** (used only within one feature/component):
- Always create a `utils.ts` file in the feature folder for utility functions
- Do not keep utility functions inline in component files

```
components/
├── charts/
│   ├── ChartBuilder.tsx
│   ├── utils.ts              # Chart-specific utilities
│   └── constants.ts          # Chart-specific constants
├── pipeline/
│   ├── pipeline-list.tsx
│   ├── utils.ts              # Pipeline-specific utilities (real example)
│   └── ...
```

---

## Test File Conventions

- **Location**: Tests live in `__tests__/` folders **inside** the component directory (e.g., `components/pipeline/__tests__/`)
- **Mock data factories**: Create a `*-mock-data.ts` file in the `__tests__/` folder with factory functions (`createMockPipeline()`, `createMockNotification()`) following the pattern in `components/pipeline/__tests__/pipeline-mock-data.ts`
- **Global API mocks**: API is mocked globally in `jest.setup.ts` — use `mockApiGet`/`mockApiPut` from `test-utils/api.ts` for typed references
- **Test wrappers**: Use `TestWrapper` from `test-utils/render.tsx` for SWR isolation (fresh cache, no deduping, no polling)
- **Permissions**: Mock `useUserPermissions` from `@/hooks/api/usePermissions` — never mock `useAuthStore` directly for permission checks
- **Relative imports for siblings**: Tests import components via relative paths (`../ComponentName`), mock data from `./mock-data`
- **No `__tests__/integration/` or `__tests__/components/` folders**: All tests go in the component's own `__tests__/` directory, integration tests included

### Test Organization

Tests live in `__tests__` directories co-located with source code:
```
components/
├── charts/
│   ├── ChartBuilder.tsx
│   └── __tests__/
│       └── ChartBuilder.test.tsx
```

E2E tests live in `/e2e/` directory.

---

## Key Files & Their Purpose

- `lib/api.ts`: Centralized API client with auth and error handling
- `stores/authStore.ts`: Authentication state management with Zustand
- `app/layout.tsx`: Root layout with SWR provider and client layout wrapper
- `components/ui/`: Radix-based reusable UI component library
- `hooks/api/`: SWR-based hooks for server state management
- `next.config.ts`: Next.js configuration with alias setup and build settings
- `jest.config.ts`: Test configuration with path aliases and coverage settings
- `playwright.config.ts`: E2E test configuration

---

## Configuration Details

- **TypeScript**: Configured with `strict: false` but selective strict options enabled
- **Build Errors Ignored**: Both TypeScript and ESLint errors ignored during build
- **Coverage Thresholds**: Set to minimal 1% for all metrics
- **Path Aliases**: `@/*` maps to project root for clean imports
- **No barrel exports**: We don't use `index.ts` barrel exports
