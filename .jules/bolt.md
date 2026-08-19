## 2026-08-19 - React + D3 State Dependency Decoupling

**Learning:** Including React hover/tooltip state in a D3 `useEffect` dependency array forces D3 to execute `svg.selectAll("*").remove()` and rebuild the entire SVG DOM tree on every hover enter/leave event. When tooltip visibility is managed via React JSX overlays, D3 canvas reconstruction is completely redundant.
**Action:** Keep D3 SVG structure creation in a `useEffect` scoped only to container `dimensions` or data props, while managing floating tooltips via React state outside the SVG rebuild loop.
