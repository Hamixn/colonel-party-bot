# Project: Bāgh-e Sarhang Murder Mystery ("Darkness is Coming" Bot)

## Architecture
- **Framework**: Python 3.11, aiogram 3.15, aiosqlite, Pillow (Persian RTL with arabic-reshaper & python-bidi), aiohttp healthcheck.
- **Entry Points**: `bot.py` (polling & server runner), `config.py` (configuration & credentials).
- **Core Modules**:
  - `database.py`: SQLite persistence, additive migrations, atomic riddle solve & accusation states, rescue alerts.
  - `handlers/game.py`: Player game interactions (`/solve`, `/accuse`, `/mission`, `/team`, `/lantern`, `/rescue`, `/carpool`, `/use_alibi`, `/tape`).
  - `handlers/admin.py`: Host commands (`/admin`, `/stats`, `/list`, `/hint`, `/start_social_game`, `/start_midnight_game`, `/broadcast_crisis`, `/trigger_finale`, `/reveal_traitors`, `/clean_guests`, `/reset_guest`, `/test*`).
  - `handlers/user.py`: Guest registration, card retrieval (`/start`, `/card`).
  - `game.py`: Canonical game rules, answer normalization, role profiles, progressive hint definitions.
  - `texts.py`: Persian message templates, RTL formatting, notifications.
  - `card_generator.py`: Generates 1080x1350 PNG invitation cards with RTL Arabic/Persian text.
  - `dossiers/`: Print-ready paper dossiers, documents, photographs, and host print-production assets.

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Three-Team Competitive Architecture | Team 1 (خون), Team 2 (سایه), Team 3 (سکوت) operate as competitors with independent evidence paths to Nader Vosough. | M1 | R1 |
| 2 | Strict Team Isolation | No team can see another team's progress, clue text, submissions, timestamps, or accusations. Zero leaks. | M1 | R1, R4 |
| 3 | Canonical Six Answer Keys & Normalization | Preserve 1-A (`خون`), 1-B (`1356`), 2-A (`سایه`), 2-B (`2910`), 3-A (`سکوت`), 3-B (`5`) with all Persian/Arabic/Latin variants and aliases. | M1 | R2 |
| 4 | Rejection of Other Teams' Codes | Reject competitor codes with concise Persian message (`OTHER_TEAM_CODE_ALERT`) without revealing other teams' answers. | M1 | R2, R4 |
| 5 | Paper-Only Physical Production | Zero 3D props (no physical shirt, cufflink, ledger book, key, negative, locks). All evidence as printed documents, photos, facsimiles. | M2 | R3 |
| 6 | Independent Physical Envelopes & Evidence | Exactly 2 envelopes per team (1-A, 1-B; 2-A, 2-B; 3-A, 3-B) with independent clues linking Nader Vosough's motive, opportunity, or physical evidence. | M2 | R3 |
| 7 | Progressive Hints Mechanism | 3-tier progressive hints (Subtle pointer -> Explicit explanation -> Host fallback) via admin `/hint <team> <level>`. | M1 | R3 |
| 8 | Atomic Solve Transitions | Prevent duplicate broadcasts or race conditions when teammates submit concurrently. | M1 | R4 |
| 9 | Private Clue Delivery & Teammate Broadcast | Deliver clue privately to solver; broadcast completion notification strictly to teammates. | M1 | R4 |
| 10 | Exact-Once Team Completion Signal | Mark team complete once when both envelopes are solved, without prematurely revealing Nader as killer. | M1 | R4 |
| 11 | Structured `/accuse` Submission | Capture suspect name, motive/opportunity explanation, and at least 2 distinct supporting evidence points from team's dossier. | M1 | R5 |
| 12 | Competitive Winner Determination | First team committing a valid, fully supported accusation naming Nader Vosough with 2 valid points wins. High-resolution timestamping. | M1 | R5 |
| 13 | Neutral Response for Non-Winning Accusations | Incorrect or non-winning accusations receive neutral responses without disclosing the true culprit. | M1 | R5 |
| 14 | Accusation Revision Support | Teams can revise accusations without resetting or manipulating original winning timestamps; transactional tie-breaking. | M1 | R5 |
| 15 | Private Host Winner Notification | Notify host/admin privately upon winning submission; withhold public announcement until reveal. | M1 | R5 |
| 16 | Event Flow & Registration Preservation | Preserve guest name entry, roster matching, invitation card generation, PIN, carpool assignment, and role selection. | M1 | R6 |
| 17 | All 25 Commands Preserved | Maintain all existing user and admin commands with full functionality. | M1 | R6 |
| 18 | Host-Controlled Finale & Witness Distinction | `/trigger_finale` and `/reveal_traitors` distinguish Nader as sole killer from Shirin, Keyvan, and Dr. Mehr as concealing witnesses. | M1 | R6 |
| 19 | Paper-Only Darkroom Confrontation | Confrontation uses final printed evidence page/photograph and cassette audio confession (no physical props or physical contact). | M1, M2 | R6 |
| 20 | Unblocked Emergency `/rescue` | Ensure `/rescue` logs safety alert to database and notifies host immediately under all circumstances. | M1 | R6 |
| 21 | Additive DB Schema & Compatibility | Maintain SQLite schema with backward-compatible migrations preserving existing guest records and secrets. | M1 | R7 |
| 22 | Comprehensive Test Suite & Windows Isolation | Fix test DB teardown locking on Windows; pass all existing 17 tests; add new E2E test suites covering R1-R7. | M3 | AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Bot Backend & Competitive Architecture | Database additive schema, atomic solve transitions, structured `/accuse` & winner logic, progressive `/hint`, unblocked `/rescue`, paper-only text sanitization, witness/killer separation. | None | IN_PROGRESS |
| M2 | Paper-Only Evidence Dossiers & Print Assets | Print-ready Persian RTL documents, photographs, facsimiles for Envelopes 1-A, 1-B, 2-A, 2-B, 3-A, 3-B, darkroom paper prop, host print guide. | None | PLANNED |
| M3 | E2E Testing Suite (Tiers 1-4) & Test Harness | Opaque-box E2E test suite covering R1-R7, Windows DB isolation fix, all existing 17 tests passing + new test suites. Publish TEST_READY.md. | M1, M2 | PLANNED |
| M4 | Final Milestone & Adversarial Hardening (Tier 5) | Pass 100% E2E tests, Tier 5 challenger gap analysis, Forensic Integrity Audit (`teamwork_auditor`). | M3 | PLANNED |

## Interface Contracts
### M1 ↔ M2 (Dossier & Clue Text Contract)
- Team 1 Dossier matches Envelopes 1-A (`خون`), 1-B (`1356`). Evidence points: Pool blood / head impact (cufflink photo), ledger account #84102 embezzlement.
- Team 2 Dossier matches Envelopes 2-A (`سایه`), 2-B (`2910`). Evidence points: 22:19 window reflection silhouette, timeline contradicting Nader's claimed <22:00 exit.
- Team 3 Dossier matches Envelopes 3-A (`سکوت`), 3-B (`5`). Evidence points: Witness statements (Shirin, Keyvan, Dr. Mehr), archive index of 5 suspects isolating Nader.

### M1 ↔ M3 (Testing API Contract)
- Entry points: aiogram Message / Command handlers and `database` async functions.
- Database: SQLite with schema migrations, testing can run on temporary database files or in-memory SQLite.

## Code Layout
- `database.py`: Persistence, SQLite schema, migrations, concurrency locks, solve & accusation storage.
- `handlers/game.py`: Player game command handlers (`/solve`, `/accuse`, `/rescue`, etc.).
- `handlers/admin.py`: Host/admin command handlers (`/hint`, `/reveal_traitors`, `/trigger_finale`, `/stats`, etc.).
- `game.py`: Canonical game rules, answer normalization, role profiles, hint definitions.
- `texts.py`: Persian message templates, RTL formatting, hint texts, finale texts.
- `dossiers/`: Paper-only printable evidence assets, documents, and host print guide.
- `tests/test_game_systems.py`: Existing and upgraded unit/integration test suite.
- `tests/test_e2e_mystery.py`: Comprehensive E2E test suite for competitive architecture, isolation, and accusation.
