# E2E Test Infra: SubFynn Tauri v2 Desktop Rebuild

## Test Philosophy
- **Requirement-driven & Opaque-box**: Derived strictly from `ORIGINAL_REQUEST.md` and user-facing requirements, independent of internal implementation code.
- **Methodology**: Systematic 4-tier testing (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, Real-World Workload Testing).
- **Zero Emojis Enforced**: Strict verification that zero emojis exist in the UI output, code, and test assertions.

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Combinations) | Tier 4 (Workload) |
|---|---------|-------------|:----------------:|:-----------------:|:---------------------:|:-----------------:|
| 1 | Tauri Host & Splashscreen | Req R1.1, R2.3 | ≥5 | ≥5 | ✓ | ✓ |
| 2 | Python Engine Sidecar IPC | Req R1.2 | ≥5 | ≥5 | ✓ | ✓ |
| 3 | File Dialog & Drag-and-Drop | Req R1.3 | ≥5 | ≥5 | ✓ | ✓ |
| 4 | React Glassmorphic UI & Theme | Req R2.1, R2.2 | ≥5 | ≥5 | ✓ | ✓ |
| 5 | Model Controls & Defaults | Req R2.5 | ≥5 | ≥5 | ✓ | ✓ |
| 6 | Interactive Subtitle Editor | Req R2.4 | ≥5 | ≥5 | ✓ | ✓ |
| 7 | Time Shifting (+/-0.5s & bulk) | Req R2.4 | ≥5 | ≥5 | ✓ | ✓ |
| 8 | SRT & VTT Export | Req R2.4 | ≥5 | ≥5 | ✓ | ✓ |
| 9 | Soft-mux Subtitles | Req R2.5 | ≥5 | ≥5 | ✓ | ✓ |
| 10| Hard Burn-in Video | Req R2.5 | ≥5 | ≥5 | ✓ | ✓ |
| 11| Standalone Packaging & Icon | Req R3.1, R3.2 | ≥5 | ≥5 | ✓ | ✓ |

## Minimum Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per feature (11 features × 5 = ≥55 tests).
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature (11 features × 5 = ≥55 tests).
- **Tier 3 (Cross-Feature Combinations)**: ≥11 pairwise combination tests.
- **Tier 4 (Real-World Workload Scenarios)**: ≥6 realistic end-to-end user workflows.
- **Total Minimum**: ≥127 automated opaque-box test cases.

## Test Runner Architecture
- **Location**: `tests/`
- **Execution Command**: `node tests/runner.mjs` or `python tests/runner.py`
- **Pass/Fail Semantics**: Exit code 0 indicates all tests passed; exit code 1 indicates failure with structured error report.
- **Output**: Generates `TEST_READY.md` upon 100% completion of test cases.
