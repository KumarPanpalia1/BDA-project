## Plan: Ledger Fraud Intelligence Improvements

Improve reliability and analyst usefulness in the existing Streamlit/PySpark dashboard without replacing working features or changing its technology stack. Work incrementally with test-first changes, preserving the README's limits on anonymized features, elapsed time, observed amounts, production generalization, and predictions as review signals.

**Phases**
1. **Phase 1: Establish focused test seams**
    - **Objective:** Introduce tests and extract only the minimum pure logic needed for direct testing; do not refactor the full Streamlit app.
    - **Files/Functions to Modify/Create:** `app.py` only for the narrow extraction; focused test module(s) and any minimal test configuration needed.
    - **Tests to Write:** Tests for valid feature/header checks, binary-label/rate calculations, and review-threshold boundary decisions, limited to logic selected for extraction.
    - **Steps:**
        1. Add focused tests against the intended pure-function behavior.
        2. Run the tests and confirm failures are due to the missing/unimplemented logic.
        3. Extract or implement the minimum pure helpers to satisfy those tests.
        4. Run the focused tests and existing application checks; record environment limitations.
2. **Phase 2: Make scoring complete and actionable**
    - **Objective:** Ensure counts, review totals, and downloaded scores cover every uploaded record while capping only the displayed table; sort by descending score and use precise threshold language.
    - **Files/Functions to Modify/Create:** Scoring logic in `app.py`; scoring tests introduced in Phase 1.
    - **Tests to Write:** Threshold boundary, descending-risk order, full counts/download content, and upload larger than 10,000 rows; include invalid/duplicate header and invalid feature input cases where the scoring path owns validation.
    - **Steps:**
        1. Write failing scoring tests, including a greater-than-10,000-row case.
        2. Run them to confirm the intended failures.
        3. Implement full-result accounting/download with a display-only cap, sorting, precise decision labels, and clear validation diagnostics.
        4. Run focused tests and relevant app checks.
3. **Phase 3: Validate analytical input and denominators**
    - **Objective:** Validate duplicate headers, feature values, and binary labels; compute fraud-rate denominators from valid labeled records only and clearly report invalid input.
    - **Files/Functions to Modify/Create:** Data ingestion and analytics summaries in `app.py`; analytics/validation tests.
    - **Tests to Write:** Duplicate headers, invalid/missing feature values, non-binary/missing labels, valid-label denominator, and clear invalid-input reporting.
    - **Steps:**
        1. Add tests for malformed input and denominator behavior.
        2. Run tests to verify they fail for the intended cases.
        3. Add narrowly scoped validation and correct valid-label denominators without changing valid-data behavior.
        4. Run focused tests and relevant app checks.
4. **Phase 4: Strengthen model evaluation and score interpretation**
    - **Objective:** Retain random split results as a baseline and add chronological holdout where supported; verify both partitions' class representation, disclose limitations, and assess calibration before using scores for workload estimates.
    - **Files/Functions to Modify/Create:** Model training/evaluation in `app.py`; model evaluation tests; README only if verified behavior or limitations require clarification.
    - **Tests to Write:** Deterministic random split baseline, chronological ordering, class representation and unsupported chronological cases, and calibration/threshold reporting behavior.
    - **Steps:**
        1. Add tests for split behavior, class checks, and calibration reporting.
        2. Run tests to confirm the gaps.
        3. Implement the smallest evaluation additions and explicit limitations; do not present uncalibrated scores as calibrated workload estimates.
        4. Run focused tests and relevant app checks.
5. **Phase 5: Improve reliability and presentation**
    - **Objective:** Fix stale cache invalidation and misleading error messages, then make measured, incremental performance and analyst-facing presentation improvements without broad rewrites.
    - **Files/Functions to Modify/Create:** Cache/error handling and selected dashboard presentation/performance paths in `app.py`; targeted tests; README or dependency guidance only when needed.
    - **Tests to Write:** Cache refresh after source replacement, context-appropriate error messages, and tests for any changed analytics/performance helper behavior.
    - **Steps:**
        1. Add focused failing tests for stale-cache and error-context defects.
        2. Run tests and confirm the intended failures.
        3. Apply minimal cache/error fixes, then use observed bottlenecks to choose scoped presentation/performance changes.
        4. Run focused tests and relevant app checks, and verify documentation preserves project limitations.

**Open Questions**
1. None blocking; chronological evaluation will be added only when the available data supports a meaningful holdout.
