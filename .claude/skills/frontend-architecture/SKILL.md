# Frontend Architecture Skill

Use this skill when building new frontend features, creating components, adding pages, or working with state management in `webapp_v2/`.

## What's Here

- **`patterns.md`** — Component and code patterns: directory structure, state management decision tree, component architecture (UI vs functional), memoization, page layout template, typography table, form patterns, error handling, container/scrolling, accessibility, NPM package selection, and chart implementation.
- **`reference.md`** — Feature structure and testing: folder structure for new features (pipeline as reference), utility/constants organization, test file conventions, key files & their purpose, and configuration details.

## Quick Reference

The frontend is Next.js 15 + React 19, using Tailwind CSS v4, Radix UI, SWR, and Zustand.

- Pages: `app/{feature}/page.tsx` (thin wrappers)
- Components: `components/{feature}/` (feature-specific) and `components/ui/` (shared)
- Hooks: `hooks/api/` (SWR-based API hooks)
- Stores: `stores/` (Zustand global state)
- Types: `types/` (TypeScript interfaces)

Rules and conventions are in `webapp_v2/CLAUDE.md` (always loaded).
