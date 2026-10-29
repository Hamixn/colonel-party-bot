# E2E Test Infra: Bāgh-e Sarhang Murder Mystery

## Test Philosophy
- Opaque-box, requirement-driven. Derives strictly from `ORIGINAL_REQUEST.md` and user requirements.
- Zero internal implementation dependencies; interacts via public APIs, handlers, and database contracts.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Scenarios.

## Feature Inventory & Test Mapping
| # | Feature | Source (Requirement) | Tier 1 (Coverage) | Tier 2 (Boundary/Corner) | Tier 3 (Pairwise/Cross) | Tier 4 (Scenario) |
|---|---------|---------------------|:-----------------:|:------------------------:|:-----------------------:|:-----------------:|
| 1 | Team Isolation & Competition | R1 | 5 tests | 5 tests | ✓ | ✓ |
| 2 | Canonical 6 Answer Keys & Normalization | R2 | 6 tests | 6 tests | ✓ | ✓ |
| 3 | Other Teams' Code Rejection | R2, R4 | 5 tests | 5 tests | ✓ | ✓ |
| 4 | Paper-Only Evidence Materials | R3 | 5 tests | 5 tests | ✓ | ✓ |
| 5 | Independent Physical Envelopes | R3 | 5 tests | 5 tests | ✓ | ✓ |
| 6 | Progressive Hints Mechanism | R3 | 5 tests | 5 tests | ✓ | ✓ |
| 7 | Atomic Solve & Concurrency | R4 | 5 tests | 5 tests | ✓ | ✓ |
| 8 | Structured `/accuse` Validation | R5 | 5 tests | 5 tests | ✓ | ✓ |
| 9 | Winner Determination & First Timestamp | R5 | 5 tests | 5 tests | ✓ | ✓ |
| 10 | Revision & Neutral Responses | R5 | 5 tests | 5 tests | ✓ | ✓ |
| 11 | Host Reveal & Witness/Killer Separation | R6 | 5 tests | 5 tests | ✓ | ✓ |
| 12 | Unblocked `/rescue` Safety Alert | R6 | 5 tests | 5 tests | ✓ | ✓ |

## Test Architecture
- **Test Runner**: Python `unittest` (`python -m unittest tests/test_e2e_mystery.py` and `python -m unittest tests/test_game_systems.py`).
- **Isolation Mechanism**: Clean per-test temporary database using in-memory SQLite or explicit Windows file handle closing in `asyncSetUp`/`asyncTearDown`.
- **Pass/Fail Semantics**: Exit code 0, all assertions pass, zero uncaught exceptions.
- **Directory Layout**:
  - `tests/test_game_systems.py`: System regression suite (17 tests).
  - `tests/test_e2e_mystery.py`: End-to-end multi-team competitive scenario test suite.
  - `tests/test_isolation_accuse.py`: Detailed isolation, race condition, and accusation scoring tests.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Three-Team Competition Run | F1, F2, F3, F7, F8, F9, F11, F12, F15 | High |
| 2 | Simultaneous Solve Race by Teammates | F7, F8, F9, F10 | Medium |
| 3 | Premature/Insufficient Accusation Followed by Correct Revision | F8, F9, F10, F11, F13, F14 | High |
| 4 | Host Climax, Paper Darkroom Finale & Reveal | F4, F6, F11, F18, F19 | Medium |
| 5 | Emergency Rescue Alert During Active Riddle Solving | F7, F12, F20 | Medium |

## Coverage Thresholds
- Tier 1 (Feature Coverage): ≥5 tests per core feature (≥60 tests).
- Tier 2 (Boundary & Corner Cases): ≥5 tests per core feature (≥60 tests).
- Tier 3 (Cross-Feature Combinations): Pairwise interactions of all key features.
- Tier 4 (Real-World Scenarios): ≥5 complete realistic event scenarios.
