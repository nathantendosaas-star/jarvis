## 2026-08-18 - Avoid Removing React State Dependencies from D3 Rendering Effects

**Learning:** Removing React state variables like `hoveredMilestone` from `useEffect` dependency arrays when rendering D3 components is an anti-pattern that triggers stale closure warnings and fails code review checks even if state setter functions inside event listeners appear to work out-of-band. D3 rendering logic and React hover/tooltip state management should either be cleanly decoupled or handled via direct DOM event listeners if DOM rebuilding is an issue.

**Action:** Avoid removing hooks dependency array elements to prevent renders; instead refactor the component to separate DOM creation from state updates.
