## 2026-08-20 - High-Frequency HUD Animation & Inline Random Re-evaluations
**Learning:** Components undergoing high-frequency re-renders (such as `HUDView` driven by 60fps `requestAnimationFrame` mic audio volume updates) should never execute inline math/random calculations in JSX render loops. Inline `Math.random()` in chart bar components caused unneeded DOM diffing and layout updates every frame tick.
**Action:** Extract dynamic chart or bar visualizations into `React.memo` subcomponents with `useMemo` for static dataset generation.
## 2026-08-17 - Avoid D3 SVG teardown on hover state updates

**Learning:** Including temporary UI state (such as `hoveredNode` or `hoveredMilestone`) in a `useEffect` dependency array that manages D3 SVG DOM construction causes D3 to completely tear down (`svg.selectAll("*").remove()`) and re-render the entire SVG DOM tree on every hover event (`mouseenter` and `mouseleave`). Since hover tooltips are rendered via React JSX overlay on top of the SVG canvas, the D3 canvas effect only needs to depend on layout dimensions and underlying data models.

**Action:** Ensure D3 simulation/rendering effects in React components only depend on structural properties like `dimensions` and `data`. Manage hover and tooltip overlays in React state without adding hover state variables to the D3 rendering `useEffect` dependencies.
