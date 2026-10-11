## Plan: Ledger Fraud Intelligence UI Redesign

Refine the existing Streamlit interface into a cohesive light enterprise-finance experience without changing its application architecture or analytical behavior. Work in three incremental phases: establish the shared shell, improve Business Analytics, then polish Model Lab and Transaction Scoring.

**Phases**
1. **Phase 1: Shared Shell and Navigation**
    - **Objective:** Create a consistent visual foundation, clearer workspace navigation, and shared page-header hierarchy.
    - **Files/Functions to Modify/Create:** `app.py`; add focused UI smoke coverage only if supported by the existing Streamlit startup path.
    - **Tests to Write:** `test_navigation_shows_selected_workspace`; `test_page_header_matches_workspace`; existing `tests/test_ledger_logic.py` suite remains a regression check.
    - **Steps:**
        1. Check whether Streamlit AppTest can exercise the current app despite its Spark and dataset initialization; add the smallest navigation/header smoke checks where feasible and observe their baseline behavior.
        2. Update shared CSS tokens, sidebar branding/navigation, and page-header/content spacing without changing routes, data setup, or session-state behavior.
        3. Run the focused UI check and existing logic tests; inspect all three workspaces at laptop and narrow widths when the app can start.
2. **Phase 2: Business Analytics Hierarchy**
    - **Objective:** Improve the reading order and legibility of existing analytics, charts, tables, filters, and data-quality information.
    - **Files/Functions to Modify/Create:** `app.py`; no analytical or data-processing files.
    - **Tests to Write:** `test_analytics_workspace_renders_existing_sections`; existing logic tests remain unchanged and must pass.
    - **Steps:**
        1. Add a focused rendering/smoke check for existing analytics sections and run it before changing their presentation.
        2. Refine KPI hierarchy, section grouping, chart labels and tooltips, table readability, and filter alignment while retaining existing measures, data, and caveats.
        3. Run focused checks and inspect both segment tabs, tables, filters, and missing-value displays with project data.
3. **Phase 3: Model Lab and Transaction Scoring**
    - **Objective:** Clarify training-result context and improve upload, threshold, workload, status, table, and download presentation.
    - **Files/Functions to Modify/Create:** `app.py`; preserve `ledger_logic.py` and model/scoring behavior.
    - **Tests to Write:** `test_model_lab_renders_training_states`; `test_scoring_workspace_renders_upload_and_results_states`; run the full `tests/test_ledger_logic.py` suite.
    - **Steps:**
        1. Add or extend focused UI smoke checks for training and scoring states, then run them against the current UI.
        2. Improve the presentation of existing controls and outputs without changing training, validation, threshold inclusivity, sorting, counts, row limits, or downloads.
        3. Run focused and existing automated checks; smoke-test before/after training, valid/invalid uploads, threshold behavior, and download completeness, then inspect the resulting layouts.

**Open Questions**
1. None; the approved visual direction and scope are defined in the task request.