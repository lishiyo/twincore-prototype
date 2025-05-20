# Dana - Private Notes - F0 Accessibility Checklist (A11y) - Early Draft

**Goal:** Ensure Framework Zero is usable by people with disabilities, aiming for WCAG 2.1 AA compliance where feasible. Focus on MVP features first.

**Area:** General UI / Navigation

*   [ ] **Keyboard Navigation:** All interactive elements (buttons, inputs, transcript lines, canvas objects?) must be reachable and operable via keyboard alone. Logical focus order.
*   [ ] **Focus Visible:** Clear visual indicator for the element that currently has keyboard focus.
*   [ ] **Skip Links:** Mechanism to bypass large blocks of content (e.g., skip from top controls directly to transcript or canvas).
*   [ ] **Page Titles:** Unique and descriptive `<title>` for different views (if applicable).

**Area:** Transcript Panel

*   [ ] **Screen Reader Compatibility:** Transcript text should be readable by screen readers. Speaker attribution should be announced. Timestamps?
*   [ ] **Keyboard Selection:** Ability to select transcript text using keyboard (e.g., Shift + Arrow keys).
*   [ ] **Visual Clarity:** Sufficient font size and contrast for transcript text.

**Area:** Canvas

*   [ ] **Keyboard Interaction:**
    *   [ ] Navigate between canvas objects (nodes, edges)? (Might be hard)
    *   [ ] Edit text in nodes via keyboard? (Should be possible if using standard text inputs).
    *   [ ] Trigger actions on selected objects (e.g., delete)?
*   [ ] **Screen Reader Access:**
    *   [Challenge] How to represent spatial information and diagrams non-visually?
    *   [Idea] Provide a linear, text-based representation or summary of canvas content? Maybe accessible via ARIA attributes or a separate mode?
    *   [Idea] Ensure text within nodes is readable.
    *   [Idea] Link nodes back to transcript source - screen reader user could navigate to the source text.
*   [ ] **Color Contrast:** Ensure sufficient contrast between text, nodes, edges, and canvas background. Check generated diagram colors.
*   [ ] **Zoom:** Ability to zoom in/out using keyboard shortcuts and mouse wheel. Text should remain readable when zoomed.

**Area:** Twin Chat Panel

*   [ ] **Screen Reader Compatibility:** Queries and responses should be read out clearly. Indicate who sent the message (User vs. Twin).
*   [ ] **Keyboard Navigation:** Navigate between messages, operate input field and send button.
*   [ ] **Visual Clarity:** Sufficient font size and contrast.

**Area:** Controls (Buttons, Inputs)

*   [ ] **Accessible Names:** All buttons and inputs have clear, descriptive labels (via text or `aria-label`).
*   [ ] **State Indication:** Visual indication of button states (hover, focus, active, disabled). `aria-disabled` used correctly.

**Area:** AI-Generated Content (Diagrams)

*   [ ] **Text Alternatives:** Need a strategy for providing non-visual alternatives to the diagram structure itself.
    *   [Idea] AI generates a textual summary alongside the visual diagram?
    *   [Idea] Rely on the linked transcript source text?
    *   [Idea] Structured list/outline view of diagram elements?
*   [ ] **Color Reliance:** Don't rely on color alone to convey information in diagrams. Use labels, shapes, patterns if needed.

**MVP Priorities:**

*   Focus on keyboard navigation and screen reader compatibility for Transcript and Twin Chat first, as these are primarily text-based.
*   Ensure core controls (buttons, inputs) are accessible.
*   Address basic canvas text node accessibility (editing, reading).
*   Defer complex canvas navigation/representation for screen readers post-MVP, but acknowledge the challenge. Rely on transcript linking as partial mitigation.
*   Check color contrast throughout.

**Action Items:**

*   [Dana] Discuss canvas a11y challenges/strategies with Ben/team.
*   [Dana] Use accessibility checking tools (browser devtools, Axe) during development.
*   [Dana/Ben] Ensure chosen libraries (React Flow) have decent accessibility support or can be made accessible.