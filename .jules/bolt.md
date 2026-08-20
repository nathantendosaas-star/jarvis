## 2026-08-19 - React + D3 State Dependency Decoupling

**Learning:** Including React hover/tooltip state in a D3 `useEffect` dependency array forces D3 to execute `svg.selectAll("*").remove()` and rebuild the entire SVG DOM tree on every hover enter/leave event. When tooltip visibility is managed via React JSX overlays, D3 canvas reconstruction is completely redundant.
**Action:** Keep D3 SVG structure creation in a `useEffect` scoped only to container `dimensions` or data props, while managing floating tooltips via React state outside the SVG rebuild loop.
## 2026-08-17 - Avoid D3 SVG teardown on hover state updates

**Learning:** Including temporary UI state (such as `hoveredNode` or `hoveredMilestone`) in a `useEffect` dependency array that manages D3 SVG DOM construction causes D3 to completely tear down (`svg.selectAll("*").remove()`) and re-render the entire SVG DOM tree on every hover event (`mouseenter` and `mouseleave`). Since hover tooltips are rendered via React JSX overlay on top of the SVG canvas, the D3 canvas effect only needs to depend on layout dimensions and underlying data models.

**Action:** Ensure D3 simulation/rendering effects in React components only depend on structural properties like `dimensions` and `data`. Manage hover and tooltip overlays in React state without adding hover state variables to the D3 rendering `useEffect` dependencies.
