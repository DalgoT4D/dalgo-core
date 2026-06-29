# Tasks: Help Menu (v1)

Working in: `/Users/pradeep/Work/Dalgo/webapp_v2` (branch: `feature/helpmenu`)

## Milestone 1: HelpMenuButton component
- [x] Add `HELP_MENU_OPENED` + `HELP_LINK_CLICKED` to `constants/analytics.ts`
- [x] Create `components/help-menu.tsx` with `HelpMenuButton`
- [x] RED: Write first failing test (renders nothing when env vars unset)
- [x] GREEN: Make test pass
- [x] Add more test slices (all 4 items, link attributes, analytics, collapsed mode)

## Milestone 2: Desktop sidebar integration
- [x] Import `HelpMenuButton` into `components/main-layout.tsx`
- [x] Add bottom section to desktop `<aside>`
- [x] Pass `collapsed={isSidebarCollapsed}` prop

## Milestone 3: Mobile drawer integration
- [x] Add `HelpMenuButton` inside mobile `Sheet` content

## Milestone 4: Final validation
- [x] `npm run test` passes (8/8 new tests green; 2 pre-existing DataPreview failures)
- [x] `npm run lint` passes (warnings only, all pre-existing)
- [x] Browser smoke test: expanded + collapsed modes verified visually
