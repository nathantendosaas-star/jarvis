## 2026-08-15 - Memoize Dynamic Render Array Calculations in React
**Learning:** In React components with frequent state updates (like HUD chat inputs or mic volume meters), inline calculations generating random values or dynamic layout heights on every render cause unnecessary recalculations, DOM layout thrashing, and flickering.
**Action:** Always wrap static/mock dataset generator arrays in `useMemo` when rendering UI widgets inside high-frequency reactive components.
