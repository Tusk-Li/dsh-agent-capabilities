---
name: dsh-visualize
description: Create local interactive charts, explanatory HTML tools, and website previews; use for visual comparison or interactive exploration.
---

For a data chart, use bundled Python to run `scripts/chart.py --input <data.json> --output <workspace>/outputs/chart.html`. Input has `title`, `labels` (strings), and `values` (finite numbers of matching length). The result is a self-contained HTML chart with bar/line selection, hover details, a data table, and SVG export. It needs no external network assets. Verify the data and inspect the page using the browser tools before delivery.

For explanations, simulations, and websites requiring richer interactions, author self-contained HTML/CSS/JS or use the project's existing stack. Use real calculations and label assumptions; do not fabricate measurements. Preview locally through a workspace server and use Playwright to check controls and console errors. Use file presentation tools available in the current catalog to show the result. A local page is not a publicly deployed website; deployment needs a selected host and its credentials.

For Word, Excel, PowerPoint, PDF export, rendering, or spreadsheet recalculation use DSH's existing `office`, `office-docx`, `office-xlsx`, `office-pptx`, `office-render`, `office-export-pdf`, and `office-recalculate` skills and dependency tools. Do not replace them with this HTML workflow.
