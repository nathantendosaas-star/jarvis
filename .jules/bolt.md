## 2026-08-20 - High-Frequency HUD Animation & Inline Random Re-evaluations
**Learning:** Components undergoing high-frequency re-renders (such as `HUDView` driven by 60fps `requestAnimationFrame` mic audio volume updates) should never execute inline math/random calculations in JSX render loops. Inline `Math.random()` in chart bar components caused unneeded DOM diffing and layout updates every frame tick.
**Action:** Extract dynamic chart or bar visualizations into `React.memo` subcomponents with `useMemo` for static dataset generation.
