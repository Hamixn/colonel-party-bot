import aiosqlite
import random
from typing import Optional, List, Dict, Any
from config import DB_PATH
import guest_list
import game

async def init_db() -> None:
    """Initializes the SQLite database schema with full game mechanics."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                telegram_username TEXT,
                full_name TEXT NOT NULL,
                has_car INTEGER DEFAULT 0,
                role TEXT DEFAULT NULL,
                is_hunter INTEGER DEFAULT 0,
                serial_number INTEGER UNIQUE,
                soul_pin TEXT,
                social_mission_id INTEGER DEFAULT 1,
                is_immune INTEGER DEFAULT 0,
                is_possessed INTEGER DEFAULT 0,
                possessed_by TEXT,
                team_name TEXT DEFAULT NULL,
                team_number INTEGER DEFAULT NULL,
                is_traitor INTEGER DEFAULT 0,
                car_number INTEGER DEFAULT NULL,
                riddle_1_solved INTEGER DEFAULT 0,
                riddle_2_solved INTEGER DEFAULT 0,
                got_stickered INTEGER DEFAULT 0,
                stickered_at TEXT,
                registered_at TEXT DEFAULT (datetime('now'))
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_state (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

        # Competitive accusations and immutable first-winner record.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS team_accusations (
                team_number INTEGER PRIMARY KEY CHECK (team_number BETWEEN 1 AND 3),
                suspect TEXT NOT NULL,
                evidence_1 TEXT NOT NULL DEFAULT '',
                evidence_2 TEXT NOT NULL DEFAULT '',
                rationale TEXT NOT NULL DEFAULT '',
                submitted_by INTEGER NOT NULL,
                first_submitted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                is_correct INTEGER NOT NULL DEFAULT 0,
                evidence_valid INTEGER NOT NULL DEFAULT 0,
                is_valid INTEGER NOT NULL DEFAULT 0
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_winner (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                team_number INTEGER NOT NULL UNIQUE CHECK (team_number BETWEEN 1 AND 3),
                submitted_by INTEGER NOT NULL,
                winning_at TEXT NOT NULL,
                suspect TEXT NOT NULL,
                evidence_1 TEXT NOT NULL,
                evidence_2 TEXT NOT NULL,
                rationale TEXT NOT NULL
            );
        """)
        await db.execute(
            "INSERT OR IGNORE INTO game_state (key, value) VALUES ('deductions_closed', '0')"
        )

        # Migration helper
        cursor = await db.execute("PRAGMA table_info(guests)")
        columns = [row[1] for row in await cursor.fetchall()]

        new_columns = [
            ("soul_pin", "TEXT"),
            ("social_mission_id", "INTEGER DEFAULT 1"),
            ("is_immune", "INTEGER DEFAULT 0"),
            ("is_possessed", "INTEGER DEFAULT 0"),
            ("possessed_by", "TEXT"),
            ("team_name", "TEXT DEFAULT NULL"),
            ("team_number", "INTEGER DEFAULT NULL"),
            ("is_traitor", "INTEGER DEFAULT 0"),
            ("car_number", "INTEGER DEFAULT NULL"),
            ("riddle_1_solved", "INTEGER DEFAULT 0"),
            ("riddle_2_solved", "INTEGER DEFAULT 0"),
            ("got_stickered", "INTEGER DEFAULT 0"),
            ("stickered_at", "TEXT"),
            ("character_role", "TEXT DEFAULT NULL"),
            ("alibi_shields", "INTEGER DEFAULT 0"),
            ("alibi_shield_used", "INTEGER DEFAULT 0"),
            ("accusation", "TEXT DEFAULT NULL"),
        ]
        for col_name, col_type in new_columns:
            if col_name not in columns:
                await db.execute(f"ALTER TABLE guests ADD COLUMN {col_name} {col_type}")

        # Ensure missions are unlocked by default for smooth gameplay
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('force_unlock_missions', '1')")

        await db.commit()

async def get_guest_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a guest by Telegram ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_guest_by_name(full_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a guest by full name."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE full_name = ?", (full_name,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_guest_by_pin(soul_pin: str) -> Optional[Dict[str, Any]]:
    """Retrieves a guest by 3-digit soul pin."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE soul_pin = ?", (soul_pin.strip(),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_next_serial_number(db: Optional[aiosqlite.Connection] = None) -> int:
    """Determines the next available unique serial number (1..53)."""
    if db is not None:
        async with db.execute("SELECT MAX(serial_number) FROM guests") as cursor:
            row = await cursor.fetchone()
            current_max = row[0] if (row and row[0] is not None) else 0
            return current_max + 1

    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT MAX(serial_number) FROM guests") as cursor:
            row = await cursor.fetchone()
            current_max = row[0] if (row and row[0] is not None) else 0
            return current_max + 1

def generate_soul_pin(serial: int) -> str:
    """Generates a memorable 3-digit PIN code."""
    return str((serial * 73 + 137) % 900 + 100)

async def register_or_update_guest(
    telegram_id: int,
    telegram_username: Optional[str],
    full_name: str,
    has_car: int,
    car_number: Optional[int] = None
) -> Dict[str, Any]:
    """Registers or updates guest info, respecting pre-assigned car groups."""
    # Look up predefined guest info
    matched = guest_list.find_matching_guests(full_name)
    predefined = matched[0] if matched else None

    # If car_number is not explicitly specified, check if guest has a pre-assigned car group
    if car_number is None and predefined:
        cg = predefined.get("car_group")
        if cg is not None and cg > 0:
            car_number = cg
        if predefined.get("is_driver"):
            has_car = 1

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            existing = await cursor.fetchone()

        # If not found by telegram_id, check if a placeholder was created by a driver
        placeholder = None
        if not existing:
            async with db.execute(
                "SELECT * FROM guests WHERE full_name = ? AND telegram_id IS NULL", (full_name,)
            ) as cursor:
                placeholder = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE guests
                SET full_name = ?, has_car = ?, car_number = ?, telegram_username = ?
                WHERE telegram_id = ?
                """,
                (full_name, has_car, car_number, telegram_username, telegram_id)
            )
            await db.commit()
            return await get_guest_by_telegram_id(telegram_id)
        elif placeholder:
            car_to_use = car_number if car_number is not None else placeholder["car_number"]
            await db.execute(
                """
                UPDATE guests
                SET telegram_id = ?, telegram_username = ?, full_name = ?, has_car = ?, car_number = ?
                WHERE id = ?
                """,
                (telegram_id, telegram_username, full_name, has_car, car_to_use, placeholder["id"])
            )
            await db.commit()
            return await get_guest_by_telegram_id(telegram_id)
        else:
            serial_number = await get_next_serial_number(db=db)
            soul_pin = generate_soul_pin(serial_number)
            mission_id = ((serial_number * 3 + 7) % 20) + 1  # 1 to 20
            await db.execute(
                """
                INSERT INTO guests (telegram_id, telegram_username, full_name, has_car, car_number, serial_number, soul_pin, social_mission_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (telegram_id, telegram_username, full_name, has_car, car_number, serial_number, soul_pin, mission_id)
            )
            await db.commit()
            return await get_guest_by_telegram_id(telegram_id)

async def set_guest_role(telegram_id: int, role: str) -> Optional[Dict[str, Any]]:
    """Updates the guest's selected role."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guests SET role = ? WHERE telegram_id = ?",
            (role, telegram_id)
        )
        await db.commit()
    return await get_guest_by_telegram_id(telegram_id)

async def grant_alibi_shield(telegram_id: int) -> Dict[str, Any]:
    """
    Grants at most ONE available alibi shield per player upon mission completion.
    Does not grant duplicate or unlimited shields.
    """
    guest = await get_guest_by_telegram_id(telegram_id)
    if not guest or guest.get("role") != "role_player":
        return {"status": "not_player", "shields": 0}

    current_shields = guest.get("alibi_shields") or 0
    if current_shields >= 1:
        return {"status": "already_has_shield", "shields": current_shields}

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guests SET alibi_shields = 1, is_immune = 1 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()
    return {"status": "granted", "shields": 1}

async def use_alibi_shield(telegram_id: int) -> Dict[str, Any]:
    """
    Consumes the one-use alibi shield to cancel a physical sticker.
    """
    guest = await get_guest_by_telegram_id(telegram_id)
    if not guest:
        return {"status": "not_found"}

    current_shields = guest.get("alibi_shields") or 0
    if current_shields <= 0:
        return {"status": "no_shield"}

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE guests 
            SET alibi_shields = 0, 
                alibi_shield_used = 1, 
                got_stickered = 0, 
                is_immune = 0 
            WHERE telegram_id = ?
        """, (telegram_id,))
        await db.commit()
    return {"status": "consumed"}

async def set_mission_completed(telegram_id: int) -> bool:
    """Awards alibi shield to player upon social mission completion."""
    res = await grant_alibi_shield(telegram_id)
    return res.get("status") in ("granted", "already_has_shield")

async def record_rescue_alert(telegram_id: int, guest_name: str) -> int:
    """
    Logs and increments safety rescue alert count.
    Never blocks or caps safety requests.
    """
    current = int(await get_game_state("rescue_alert_count", "0"))
    new_count = current + 1
    await set_game_state("rescue_alert_count", str(new_count))
    from datetime import datetime, timezone
    await set_game_state("last_rescue_alert_at", datetime.now(timezone.utc).isoformat())
    await set_game_state("last_rescue_alert_by", f"{guest_name} ({telegram_id})")
    return new_count


def _classify_team_evidence(team_number: int, evidence: str) -> str | None:
    """Classifies one concise evidence point into a team-specific category."""
    normalized = _normalize_text(evidence)
    if not normalized:
        return None
    categories = {
        1: {
            "medical": ["نمونه b", "خون", "جراحت سر", "اسیب سر", "هموگلوبین", "لبه سنگی"],
            "financial": ["r17", "nv17", "دفتر حساب", "دفتر مالی", "اختلاس", "انتقال مالی", "رسید", "حساب بدون تایید"],
        },
        2: {
            "photo_time": ["انعکاس", "سایه", "عکس", "نگاتیو", "2219", "2910", "فریم", "زمان ثبت تصویر"],
            "identity_alibi": ["nv17", "جلیقه زغالی", "ادعای خروج", "خروج پیش", "تناقض زمانی", "تطبیق هویت", "تایم لاین"],
        },
        3: {
            "witness": ["شهادت شیرین", "شیرین", "هل دادن", "هلدادن", "درگیری کنار استخر", "شاهد مستقیم"],
            "corroboration": ["nv17", "مدیر امور مالی", "گزارش پزشکی", "جراحت سر", "فهرست کارکنان", "اختلاس", "دفتر حساب"],
        },
    }
    hits = [
        category for category, needles in categories.get(team_number, {}).items()
        if any(_normalize_text(needle) in normalized for needle in needles)
    ]
    # One field must be one finding, not a combined answer to the whole case.
    return hits[0] if len(hits) == 1 else None


def validate_team_evidence_points(team_number: int, evidence_1: str, evidence_2: str) -> bool:
    """Requires two distinct, team-relevant evidence categories."""
    e1, e2 = _normalize_text(evidence_1 or ""), _normalize_text(evidence_2 or "")
    if not e1 or not e2 or e1 == e2:
        return False
    c1 = _classify_team_evidence(team_number, evidence_1)
    c2 = _classify_team_evidence(team_number, evidence_2)
    return bool(c1 and c2 and c1 != c2)


async def record_team_accusation(
    team_number: int,
    suspect: str,
    telegram_id: int,
    evidence_1: str | None = None,
    evidence_2: str | None = None,
    rationale: str | None = None,
) -> Dict[str, Any]:
    """
    Stores one team's current private accusation. Legacy suspect-only submissions
    remain drafts but cannot win. Winner selection is serialized by BEGIN IMMEDIATE.
    """
    if team_number not in (1, 2, 3):
        return {"status": "invalid_team", "team_number": team_number}

    from datetime import datetime, timezone
    cleaned = (suspect or "").strip()
    ev1, ev2, reason = (evidence_1 or "").strip(), (evidence_2 or "").strip(), (rationale or "").strip()
    has_details = bool(ev1 and ev2 and reason)
    evidence_valid = validate_team_evidence_points(team_number, ev1, ev2) if has_details else False
    rationale_valid = len(_normalize_text(reason)) >= 12
    normalized_suspect = _normalize_text(cleaned)
    correct_suspect = (
        _normalize_text("نادر وثوق") in normalized_suspect
        or "nader vosough" in normalized_suspect
    )
    is_valid = bool(has_details and evidence_valid and rationale_valid)

    async with aiosqlite.connect(DB_PATH, timeout=10) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT value FROM game_state WHERE key = 'deductions_closed'") as cursor:
            closed_row = await cursor.fetchone()
        if closed_row and closed_row["value"] == "1":
            await db.rollback()
            return {"status": "closed", "team_number": team_number}

        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        await db.execute("""
            INSERT INTO team_accusations (
                team_number, suspect, evidence_1, evidence_2, rationale,
                submitted_by, first_submitted_at, updated_at,
                is_correct, evidence_valid, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team_number) DO UPDATE SET
                suspect = excluded.suspect,
                evidence_1 = excluded.evidence_1,
                evidence_2 = excluded.evidence_2,
                rationale = excluded.rationale,
                submitted_by = excluded.submitted_by,
                updated_at = excluded.updated_at,
                is_correct = excluded.is_correct,
                evidence_valid = excluded.evidence_valid,
                is_valid = excluded.is_valid
        """, (
            team_number, cleaned, ev1, ev2, reason, telegram_id, now, now,
            int(correct_suspect), int(evidence_valid and rationale_valid), int(is_valid)
        ))
        # Keep legacy state keys readable; guest-facing code does not query other teams.
        await db.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
            (f"team_{team_number}_accusation", cleaned)
        )
        await db.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
            (f"team_{team_number}_accusation_by", str(telegram_id))
        )
        await db.execute("UPDATE guests SET accusation = ? WHERE team_number = ?", (cleaned, team_number))

        winner_created = False
        if is_valid and correct_suspect:
            cur = await db.execute("""
                INSERT OR IGNORE INTO game_winner (
                    id, team_number, submitted_by, winning_at, suspect,
                    evidence_1, evidence_2, rationale
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """, (team_number, telegram_id, now, cleaned, ev1, ev2, reason))
            winner_created = cur.rowcount == 1

        async with db.execute("SELECT team_number FROM game_winner WHERE id = 1") as cursor:
            winner_row = await cursor.fetchone()
        async with db.execute(
            "SELECT first_submitted_at, updated_at FROM team_accusations WHERE team_number = ?",
            (team_number,)
        ) as cursor:
            timestamps = await cursor.fetchone()
        await db.commit()

    status = "insufficient_evidence" if has_details and not (evidence_valid and rationale_valid) else "recorded"
    return {
        "status": status,
        "team_number": team_number,
        "suspect": cleaned,
        "evidence_1": ev1,
        "evidence_2": ev2,
        "rationale": reason,
        "is_correct": bool(correct_suspect),
        "evidence_valid": bool(evidence_valid and rationale_valid),
        "is_valid": is_valid,
        "is_winner": bool(winner_row and winner_row["team_number"] == team_number),
        "winner_created": winner_created,
        "winner_team": winner_row["team_number"] if winner_row else None,
        "first_submitted_at": timestamps["first_submitted_at"] if timestamps else None,
        "updated_at": timestamps["updated_at"] if timestamps else None,
    }


async def get_team_accusation(team_number: int) -> Optional[str]:
    """Returns only the specified team's current suspect."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT suspect FROM team_accusations WHERE team_number = ?", (team_number,)) as cursor:
            row = await cursor.fetchone()
    if row:
        return row[0]
    # Compatibility with databases that contain pre-upgrade key/value accusations.
    val = await get_game_state(f"team_{team_number}_accusation", "")
    return val if val else None


async def get_team_accusation_details(team_number: int) -> Optional[Dict[str, Any]]:
    """Returns full detail for one team only; use only in that team's private flow."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM team_accusations WHERE team_number = ?", (team_number,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_accusations() -> Dict[int, str]:
    """Admin-only summary helper; guest handlers must use get_team_accusation."""
    results: Dict[int, str] = {}
    for team_num in (1, 2, 3):
        accusation = await get_team_accusation(team_num)
        if accusation:
            results[team_num] = accusation
    return results


async def get_game_winner() -> Optional[Dict[str, Any]]:
    """Returns the immutable first-winning accusation, if one exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM game_winner WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def trigger_finale_once() -> bool:
    """Closes accusation intake and records the finale trigger exactly once."""
    from datetime import datetime, timezone
    async with aiosqlite.connect(DB_PATH, timeout=10) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT value FROM game_state WHERE key = 'finale_triggered_at'") as cursor:
            existing = await cursor.fetchone()
        if existing and existing[0]:
            await db.commit()
            return False
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('deductions_closed', '1')")
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('game_phase', 'finale')")
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('finale_triggered_at', ?)", (now,))
        await db.commit()
        return True

async def tag_possession(target_pin: str, hunter_name: str) -> Dict[str, Any]:
    """Attempts to possess a guest by PIN."""
    guest = await get_guest_by_pin(target_pin)
    if not guest:
        return {"status": "not_found", "guest": None}

    if guest.get("role") != "role_player":
        return {"status": "not_player", "guest": guest}

    if guest.get("is_immune") == 1:
        return {"status": "immune", "guest": guest}

    if guest.get("is_possessed") == 1:
        return {"status": "already_possessed", "guest": guest}

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guests SET is_possessed = 1, possessed_by = ? WHERE id = ?",
            (hunter_name, guest["id"])
        )
        await db.commit()

    updated = await get_guest_by_pin(target_pin)
    return {"status": "success", "guest": updated}

async def count_role(role: str) -> int:
    """Returns number of guests with given role."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM guests WHERE role = ?", (role,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_stats() -> Dict[str, Any]:
    """Returns party registration and live game statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM guests") as c:
            total = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE role = 'role_player'") as c:
            players = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE role = 'role_blonde'") as c:
            blondes = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE has_car = 1") as c:
            cars = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE is_hunter = 1") as c:
            hunters = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE is_immune = 1") as c:
            immune = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE is_possessed = 1") as c:
            possessed = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE got_stickered = 1") as c:
            stickered = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE alibi_shields > 0") as c:
            alibi_available = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM guests WHERE alibi_shield_used = 1") as c:
            alibi_used = (await c.fetchone())[0]

    # Team stats
    teams_stats = {}
    for t in (1, 2, 3):
        members = await get_team_members(t)
        r1 = (await get_game_state(f"team_{t}_riddle_1", "0")) == "1"
        r2 = (await get_game_state(f"team_{t}_riddle_2", "0")) == "1"
        acc = await get_team_accusation(t)
        teams_stats[t] = {
            "size": len(members),
            "riddle_1_solved": r1,
            "riddle_2_solved": r2,
            "accusation_submitted": bool(acc)
        }

    accusations = await get_all_accusations()
    rescue_alerts = int(await get_game_state("rescue_alert_count", "0"))
    phase = await get_game_state("game_phase", "registration")

    return {
        "total": total,
        "players": players,
        "blondes": blondes,
        "cars": cars,
        "hunters": hunters,
        "immune": immune,
        "possessed": possessed,
        "stickered": stickered,
        "alibi_shields_available": alibi_available,
        "alibi_shields_used": alibi_used,
        "teams": teams_stats,
        "accusations_count": len(accusations),
        "rescue_alerts": rescue_alerts,
        "phase": phase
    }

async def mark_stickered(telegram_id: int) -> bool:
    """Marks that player got stickered."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guests SET got_stickered = 1, stickered_at = datetime('now') WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()
        return True

async def get_all_guests() -> List[Dict[str, Any]]:
    """Returns all registered guests sorted by serial number."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests ORDER BY serial_number ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_players() -> List[Dict[str, Any]]:
    """Returns all guests with role_player."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE role = 'role_player' ORDER BY serial_number ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def assign_random_hunters(count: int = 5) -> List[Dict[str, Any]]:
    """Assigns 5 secret hunters from the player pool."""
    players = await get_players()
    if not players:
        return []

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE guests SET is_hunter = 0")
        await db.commit()

    sample_size = min(count, len(players))
    selected = random.sample(players, sample_size)
    selected_ids = [p["telegram_id"] for p in selected if p.get("telegram_id")]

    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                f"UPDATE guests SET is_hunter = 1 WHERE telegram_id IN ({placeholders})",
                selected_ids
            )
            await db.commit()

    return await get_hunters()


async def start_social_game(count: int = 3) -> Dict[str, Any]:
    """Starts the social phase without prematurely assigning or revealing teams."""
    characters = await assign_special_character_roles(force_reassign=False)
    await set_game_state("social_game_started", "1")
    await set_game_state("force_unlock_missions", "1")
    all_players = await get_players()
    witness_roles = {"shirin", "keyvan", "fereydoun"}
    hunters = [p for p in all_players if p.get("character_role") in witness_roles]
    regular_players = [
        p for p in all_players
        if p.get("character_role") not in witness_roles and p.get("character_role") != "nader"
    ]
    if not characters:
        await assign_random_hunters(count=min(3, max(0, len(all_players) - 1)))
        hunters = await get_hunters()
        hunter_ids = {p["id"] for p in hunters}
        regular_players = [p for p in all_players if p["id"] not in hunter_ids]
    return {"hunters": hunters, "regular_players": regular_players}

async def get_hunters() -> List[Dict[str, Any]]:
    """Returns all designated hunters."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE is_hunter = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def assign_special_character_roles(force_reassign: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Assigns the three witness sticker-carriers and one scripted Nader actor.
    Before midnight this does not create or expose team assignments. If teams
    already exist, one witness is selected from each. Nader is always teamless.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if not force_reassign:
            async with db.execute(
                "SELECT * FROM guests WHERE character_role IS NOT NULL AND role = 'role_player'"
            ) as cursor:
                rows = [dict(r) for r in await cursor.fetchall()]
            existing = {r["character_role"]: r for r in rows}
            if all(k in existing for k in ("shirin", "keyvan", "fereydoun", "nader")):
                await db.execute(
                    "UPDATE guests SET team_number = NULL, team_name = NULL, is_traitor = 0 WHERE character_role = 'nader'"
                )
                await db.commit()
                existing["nader"]["team_number"] = None
                existing["nader"]["team_name"] = None
                existing["nader"]["is_traitor"] = 0
                return existing

        async with db.execute("SELECT * FROM guests WHERE role = 'role_player' ORDER BY id ASC") as cursor:
            players = [dict(r) for r in await cursor.fetchall()]
        if len(players) < 4:
            return {}

        await db.execute("""
            UPDATE guests
            SET character_role = NULL, is_hunter = 0, is_traitor = 0
            WHERE role = 'role_player'
        """)
        team_players = {
            1: [p for p in players if p.get("team_number") == 1],
            2: [p for p in players if p.get("team_number") == 2],
            3: [p for p in players if p.get("team_number") == 3],
        }
        if all(team_players[t] for t in (1, 2, 3)):
            witnesses = {
                "shirin": random.choice(team_players[1]),
                "keyvan": random.choice(team_players[2]),
                "fereydoun": random.choice(team_players[3]),
            }
        else:
            selected = random.sample(players, 3)
            witnesses = dict(zip(("shirin", "keyvan", "fereydoun"), selected))

        witness_ids = {p["id"] for p in witnesses.values()}
        candidates = [p for p in players if p["id"] not in witness_ids]
        if not candidates:
            await db.rollback()
            return {}
        nader = random.choice(candidates)

        for role_name, person in witnesses.items():
            await db.execute(
                "UPDATE guests SET character_role = ?, is_hunter = 1, is_traitor = 0 WHERE id = ?",
                (role_name, person["id"])
            )
        await db.execute("""
            UPDATE guests
            SET character_role = 'nader', is_hunter = 0, is_traitor = 0,
                team_number = NULL, team_name = NULL
            WHERE id = ?
        """, (nader["id"],))
        await db.commit()

        result: Dict[str, Dict[str, Any]] = {}
        for role_name, person in {**witnesses, "nader": nader}.items():
            async with db.execute("SELECT * FROM guests WHERE id = ?", (person["id"],)) as cursor:
                row = await cursor.fetchone()
                result[role_name] = dict(row)
        return result

async def get_special_characters() -> Dict[str, Optional[Dict[str, Any]]]:
    """Returns currently assigned special characters."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE character_role IS NOT NULL AND role = 'role_player'"
        ) as cursor:
            rows = [dict(r) for r in await cursor.fetchall()]
            result: Dict[str, Optional[Dict[str, Any]]] = {
                "shirin": None,
                "keyvan": None,
                "fereydoun": None,
                "nader": None
            }
            for r in rows:
                if r["character_role"] in result:
                    result[r["character_role"]] = r
            return result


async def start_midnight_game(team_count: int = 3) -> Dict[int, Dict[str, Any]]:
    """
    Starts exactly three independent investigations. Witnesses are split one per
    team; the scripted Nader actor is not assigned to a scoring team. Repeated
    calls after the start preserve team progress instead of rerolling it.
    """
    players = await get_players()
    # A complete live game needs 12-15 investigators plus the separate Nader actor.
    if len(players) < 13:
        return {}

    started = (await get_game_state("midnight_game_started", "0")) == "1"
    phase = await get_game_state("game_phase", "registration")
    if started and phase in ("midnight_investigation", "central_deduction", "finale", "completed"):
        labels = {1: "تیم خون", 2: "تیم سایه", 3: "تیم سکوت"}
        current = {}
        for team_num in (1, 2, 3):
            members = await get_team_members(team_num)
            if members:
                current[team_num] = {"name": labels[team_num], "members": members, "traitor": None}
        if current:
            return current

    characters = await assign_special_character_roles(force_reassign=False)
    if not all(characters.get(role) for role in ("shirin", "keyvan", "fereydoun", "nader")):
        characters = await assign_special_character_roles(force_reassign=True)
    if not all(characters.get(role) for role in ("shirin", "keyvan", "fereydoun", "nader")):
        return {}

    players = await get_players()
    candidates = [p for p in players if p.get("character_role") != "nader"]
    if len(candidates) < 3:
        return {}

    team_names = {1: "تیم خون", 2: "تیم سایه", 3: "تیم سکوت"}
    placements: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: []}
    witness_roles = {1: "shirin", 2: "keyvan", 3: "fereydoun"}
    placed_ids = set()
    for team_num, role_name in witness_roles.items():
        witness = characters.get(role_name)
        if witness:
            person = next((p for p in candidates if p["id"] == witness["id"]), None)
            if person:
                placements[team_num].append(person)
                placed_ids.add(person["id"])

    remaining = [p for p in candidates if p["id"] not in placed_ids]
    random.shuffle(remaining)
    for person in remaining:
        smallest = min(len(placements[t]) for t in (1, 2, 3))
        choices = [t for t in (1, 2, 3) if len(placements[t]) == smallest]
        placements[random.choice(choices)].append(person)

    async with aiosqlite.connect(DB_PATH, timeout=10) as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute("""
            UPDATE guests SET team_number = NULL, team_name = NULL, is_traitor = 0,
                riddle_1_solved = 0, riddle_2_solved = 0, accusation = NULL
            WHERE role = 'role_player'
        """)
        for team_num, members in placements.items():
            for person in members:
                await db.execute(
                    "UPDATE guests SET team_number = ?, team_name = ? WHERE id = ?",
                    (team_num, team_names[team_num], person["id"])
                )
        await db.execute("DELETE FROM team_accusations")
        await db.execute("DELETE FROM game_winner")
        await db.execute("""
            DELETE FROM game_state
            WHERE key LIKE 'team_4_%'
               OR key LIKE 'team_1_accusation%'
               OR key LIKE 'team_2_accusation%'
               OR key LIKE 'team_3_accusation%'
               OR key IN ('finale_triggered_at', 'reveal_triggered_at')
        """)
        for team_num in (1, 2, 3):
            for riddle_num in (1, 2):
                await db.execute(
                    "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, '0')",
                    (f"team_{team_num}_riddle_{riddle_num}",)
                )
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('deductions_closed', '0')")
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('midnight_game_started', '1')")
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('game_phase', 'midnight_investigation')")
        await db.commit()

    return {
        team_num: {
            "name": team_names[team_num],
            "members": await get_team_members(team_num),
            "traitor": None,
        }
        for team_num in (1, 2, 3)
    }

async def assign_midnight_teams() -> Dict[str, List[Dict[str, Any]]]:
    """Backward compatibility alias for assign_midnight_teams."""
    t_dict = await start_midnight_game()
    result: Dict[str, List[Dict[str, Any]]] = {}
    for t_info in t_dict.values():
        result[t_info["name"]] = t_info["members"]
    return result

async def get_team_members(team_number: int) -> List[Dict[str, Any]]:
    """Returns all members of a midnight team."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE team_number = ? ORDER BY full_name ASC",
            (team_number,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

PERSIAN_TO_LATIN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def _normalize_text(text: str) -> str:
    """Normalizes Arabic/Persian characters and digits for robust answer matching."""
    if not text:
        return ""
    t = text.strip().lower()
    t = t.replace("ي", "ی").replace("ك", "ک").replace("آ", "ا").replace("ة", "ه")
    t = t.translate(PERSIAN_TO_LATIN_DIGITS)
    for p in [".", ",", "!", "?", "،", "؛", "-", "_", ":", "/", "\\", "'", '"', "(", ")", "[", "]", "{", "}"]:
        t = t.replace(p, "")
    return t.strip()

def _matches_candidate(user_text: str, candidate: str) -> bool:
    """Matches user input against candidate answer key, ensuring digit keys like '5' don't match '3' or '1356'."""
    user_norm = _normalize_text(user_text)
    cand_norm = _normalize_text(candidate)
    if not user_norm or not cand_norm:
        return False
    if user_norm == cand_norm:
        return True
    tokens = user_norm.split()
    if cand_norm in tokens:
        return True
    if len(cand_norm) > 1 and cand_norm in user_norm:
        if not cand_norm.isdigit() or not any(c.isdigit() for c in user_norm if c not in cand_norm):
            return True
    return False

async def is_all_evidence_collected() -> bool:
    """Checks if Team 1, Team 2, and Team 3 have each solved both their riddles."""
    for team_num in [1, 2, 3]:
        r1 = (await get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
        r2 = (await get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
        if not (r1 and r2):
            return False
    return True


async def check_team_riddle(telegram_id: int, answer: str) -> Dict[str, Any]:
    """Atomically validates only the sender's two canonical team answers."""
    team_riddle_answers = {
        1: {1: ["خون", "blood", "خون سرخ"], 2: ["1356", "۱۳۵۶"]},
        2: {1: ["سایه", "shadow", "سايه"], 2: ["2910", "۲۹۱۰"]},
        3: {1: ["سکوت", "silence", "سکوت مطلق"], 2: ["5", "پنج", "۵"]},
    }
    async with aiosqlite.connect(DB_PATH, timeout=10) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT * FROM guests WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            await db.commit()
            return {"status": "not_registered"}

        guest = dict(row)
        team_num = guest.get("team_number")
        if guest.get("role") != "role_player" or team_num not in (1, 2, 3) or guest.get("character_role") == "nader":
            await db.commit()
            return {"status": "no_team"}

        async def solved_state(riddle_num: int) -> bool:
            async with db.execute("SELECT value FROM game_state WHERE key = ?", (f"team_{team_num}_riddle_{riddle_num}",)) as cursor:
                state_row = await cursor.fetchone()
            return bool(state_row and state_row["value"] == "1")

        r1_solved, r2_solved = await solved_state(1), await solved_state(2)
        if r1_solved and r2_solved:
            await db.commit()
            return {"status": "already_both_solved", "team_number": team_num, "response_text": game.CLIMAX_INSTRUCTIONS}

        answers = team_riddle_answers[team_num]
        match_r1 = any(_matches_candidate(answer, candidate) for candidate in answers[1])
        match_r2 = any(_matches_candidate(answer, candidate) for candidate in answers[2])
        if match_r1 and r1_solved:
            await db.commit()
            return {"status": "already_solved", "riddle_num": 1, "team_number": team_num,
                    "response_text": "⚠️ این مدرک (پاکت اول) قبلاً توسط تیم شما ثبت شده است!"}
        if match_r2 and r2_solved:
            await db.commit()
            return {"status": "already_solved", "riddle_num": 2, "team_number": team_num,
                    "response_text": "⚠️ این مدرک (پاکت دوم) قبلاً توسط تیم شما ثبت شده است!"}

        if not match_r1 and not match_r2:
            for other_team, other_riddles in team_riddle_answers.items():
                if other_team == team_num:
                    continue
                if any(
                    _matches_candidate(answer, candidate)
                    for candidates_for_riddle in other_riddles.values()
                    for candidate in candidates_for_riddle
                ):
                    await db.commit()
                    return {"status": "other_team_riddle", "team_number": team_num,
                            "response_text": game.OTHER_TEAM_CODE_ALERT}
            await db.commit()
            return {"status": "wrong", "team_number": team_num, "response_text": game.WRONG_ANSWER_TEXT}

        riddle_num = 1 if match_r1 else 2
        await db.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, '1')",
            (f"team_{team_num}_riddle_{riddle_num}",)
        )
        column = "riddle_1_solved" if riddle_num == 1 else "riddle_2_solved"
        await db.execute(f"UPDATE guests SET {column} = 1 WHERE team_number = ?", (team_num,))
        await db.commit()

    all_collected = await is_all_evidence_collected()
    other_solved = r2_solved if riddle_num == 1 else r1_solved
    return {
        "status": "both_solved" if other_solved else "riddle_solved",
        "team_number": team_num,
        "riddle_num": riddle_num,
        "just_solved": riddle_num,
        "response_text": game.RIDDLE_RESPONSES.get((team_num, riddle_num), "✅ مدرک ثبت شد."),
        "all_teams_solved": all_collected,
    }

async def assign_tester_team(telegram_id: int, team_number: int) -> Dict[str, Any]:
    """Assigns or switches a tester's team (1, 2, or 3)."""
    team_names = {1: "تیم خون", 2: "تیم سایه", 3: "تیم سکوت"}
    if team_number not in team_names:
        return {"status": "invalid_team", "team_number": team_number}
    t_name = team_names[team_number]
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM guests WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            await db.execute("""
                UPDATE guests 
                SET team_number = ?, team_name = ?, role = 'role_player'
                WHERE telegram_id = ?
            """, (team_number, t_name, telegram_id))
        else:
            serial_number = await get_next_serial_number(db=db)
            soul_pin = generate_soul_pin(serial_number)
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name, has_car, serial_number, soul_pin, social_mission_id)
                VALUES (?, 'Hamixon', 'حامد', 'role_player', ?, ?, 0, ?, ?, 1)
            """, (telegram_id, team_number, t_name, serial_number, soul_pin))
        await db.commit()
    return {"team_number": team_number, "team_name": t_name}

async def clean_all_guests() -> int:
    """
    Cleans all registered guests from the database and resets game progression state
    so that guests can start registration afresh via /start.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM guests")
        row = await cursor.fetchone()
        count = row[0] if row else 0

        # Delete all guests
        await db.execute("DELETE FROM guests")
        try:
            await db.execute("DELETE FROM sqlite_sequence WHERE name='guests'")
        except Exception:
            pass

        # Reset game progression, new competitive tables, and one-shot controls.
        await db.execute("DELETE FROM team_accusations")
        await db.execute("DELETE FROM game_winner")
        keys_to_clear = [
            'social_game_started',
            'midnight_game_started',
            'team_1_riddle_1',
            'team_1_riddle_2',
            'team_2_riddle_1',
            'team_2_riddle_2',
            'team_3_riddle_1',
            'team_3_riddle_2',
            'team_1_accusation',
            'team_2_accusation',
            'team_3_accusation',
            'rescue_count',
            'rescue_alert_count',
            'last_rescue_alert_at',
            'last_rescue_alert_by',
            'traitors_revealed',
            'deductions_closed',
            'finale_triggered_at',
            'reveal_triggered_at'
        ]
        placeholders = ','.join(['?'] * len(keys_to_clear))
        await db.execute(f"DELETE FROM game_state WHERE key IN ({placeholders})", keys_to_clear)
        await db.execute("DELETE FROM game_state WHERE key LIKE 'team_4_%'")
        await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('game_phase', 'registration')")

        await db.commit()
        return count

async def delete_guest_by_telegram_id(telegram_id: int) -> bool:
    """Deletes a single guest by their Telegram ID so they can re-register from /start."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM guests WHERE telegram_id = ?", (telegram_id,))
        await db.commit()
        return cursor.rowcount > 0

async def delete_guest_by_identifier(identifier: str) -> Optional[str]:
    """Deletes a guest by telegram_id, username, or full_name."""
    ident = identifier.strip().lstrip("@")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        target = None
        if ident.isdigit():
            cursor = await db.execute("SELECT * FROM guests WHERE telegram_id = ?", (int(ident),))
            target = await cursor.fetchone()
        if not target:
            cursor = await db.execute("SELECT * FROM guests WHERE LOWER(telegram_username) = LOWER(?)", (ident,))
            target = await cursor.fetchone()
        if not target:
            cursor = await db.execute("SELECT * FROM guests WHERE full_name LIKE ?", (f"%{ident}%",))
            target = await cursor.fetchone()
        
        if target:
            name = target["full_name"]
            await db.execute("DELETE FROM guests WHERE id = ?", (target["id"],))
            await db.commit()
            return name
        return None


async def reset_team_riddles(team_number: int | None = None) -> bool:
    """Resets team progress for tests; emergency/safety requests are unaffected."""
    async with aiosqlite.connect(DB_PATH) as db:
        if team_number:
            if team_number not in (1, 2, 3):
                return False
            await db.execute(
                "UPDATE guests SET riddle_1_solved = 0, riddle_2_solved = 0, accusation = NULL WHERE team_number = ?",
                (team_number,)
            )
            for riddle_num in (1, 2):
                await db.execute(
                    "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, '0')",
                    (f"team_{team_number}_riddle_{riddle_num}",)
                )
            await db.execute("DELETE FROM team_accusations WHERE team_number = ?", (team_number,))
            await db.execute("DELETE FROM game_winner")
        else:
            await db.execute("""
                UPDATE guests SET riddle_1_solved = 0, riddle_2_solved = 0,
                    is_immune = 0, got_stickered = 0, accusation = NULL
            """)
            for team_num in (1, 2, 3):
                for riddle_num in (1, 2):
                    await db.execute(
                        "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, '0')",
                        (f"team_{team_num}_riddle_{riddle_num}",)
                    )
            await db.execute("DELETE FROM team_accusations")
            await db.execute("DELETE FROM game_winner")
            await db.execute("""
                DELETE FROM game_state
                WHERE key IN ('finale_triggered_at', 'reveal_triggered_at')
                   OR key LIKE 'team_4_%'
                   OR key LIKE 'team_1_accusation%'
                   OR key LIKE 'team_2_accusation%'
                   OR key LIKE 'team_3_accusation%'
            """)
            await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('deductions_closed', '0')")
            await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('midnight_game_started', '0')")
            await db.execute("INSERT OR REPLACE INTO game_state (key, value) VALUES ('game_phase', 'registration')")
        await db.commit()
    return True


async def get_reveal_manifest() -> Dict[str, Any]:
    """Returns witnesses, sole killer, and the immutable first-winner record."""
    characters = await get_special_characters()
    witnesses = [characters.get(role) for role in ("shirin", "keyvan", "fereydoun") if characters.get(role)]
    killer = characters.get("nader")
    winner = await get_game_winner()
    return {
        "witnesses": witnesses, "killer": killer, "winner": winner,
        "hunters": witnesses, "traitors": [],
    }

async def get_carpool_manifest() -> Dict[int, Dict[str, Any]]:
    """
    Builds the current 13-car convoy manifest based on pre-assigned roster
    and dynamically registered guests, including driver Telegram contacts.
    """
    pre_drivers = {
        1: "سارا (Sara)",
        2: "عارف (Aref)",
        5: "فرهود (Farhood)",
        6: "سیاوش (Siavash)"
    }

    manifest: Dict[int, Dict[str, Any]] = {}
    for i in range(1, 14):
        manifest[i] = {
            "driver": pre_drivers.get(i),
            "driver_telegram_id": None,
            "driver_telegram_username": None,
            "passengers": [],
            "total_count": 0,
            "seats_left": 4
        }

    # Pre-assigned passengers from GUEST_ROSTER
    for g in guest_list.GUEST_ROSTER:
        cg = g.get("car_group")
        if cg and 1 <= cg <= 13 and not g.get("is_driver"):
            if g["name"] not in manifest[cg]["passengers"]:
                manifest[cg]["passengers"].append(g["name"])

    # Overlay live DB registrations
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guests WHERE car_number IS NOT NULL") as c:
            rows = await c.fetchall()
            for r in rows:
                c_num = r["car_number"]
                if 1 <= c_num <= 13:
                    if r["has_car"] == 1:
                        manifest[c_num]["driver"] = r["full_name"]
                        manifest[c_num]["driver_telegram_id"] = r["telegram_id"]
                        manifest[c_num]["driver_telegram_username"] = r["telegram_username"]
                    else:
                        if r["full_name"] not in manifest[c_num]["passengers"]:
                            manifest[c_num]["passengers"].append(r["full_name"])

        # Also search for pre-drivers in DB if their telegram_id isn't filled yet
        for c_num, car_data in manifest.items():
            if car_data["driver"] and not car_data["driver_telegram_id"]:
                async with db.execute(
                    "SELECT telegram_id, telegram_username FROM guests WHERE full_name = ? AND telegram_id IS NOT NULL",
                    (car_data["driver"],)
                ) as cur:
                    d_row = await cur.fetchone()
                    if d_row:
                        car_data["driver_telegram_id"] = d_row["telegram_id"]
                        car_data["driver_telegram_username"] = d_row["telegram_username"]

    # Calculate final occupancy
    for c_num in range(1, 14):
        tot = (1 if manifest[c_num]["driver"] else 0) + len(manifest[c_num]["passengers"])
        manifest[c_num]["total_count"] = tot
        manifest[c_num]["seats_left"] = max(0, 4 - tot)

    return manifest

async def find_or_create_car_for_driver(driver_tid: int, driver_name: str) -> int:
    """
    Finds or allocates a car number (1..13) for a driver.
    """
    # 1. Check if driver is already assigned in DB
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT car_number FROM guests WHERE telegram_id = ? AND has_car = 1 AND car_number IS NOT NULL",
            (driver_tid,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["car_number"] and 1 <= row["car_number"] <= 13:
                return row["car_number"]

    # 2. Check if pre-assigned in GUEST_ROSTER as driver
    matched = guest_list.find_matching_guests(driver_name)
    if matched and matched[0].get("is_driver") and matched[0].get("car_group"):
        cg = matched[0]["car_group"]
        if 1 <= cg <= 13:
            return cg

    # 3. Find first car (1..13) that has no active driver
    manifest = await get_carpool_manifest()
    for c_num in range(1, 14):
        if not manifest[c_num]["driver"]:
            return c_num

    # 4. Fallback: car with fewest people
    best_car = 1
    min_count = 999
    for c_num in range(1, 14):
        if manifest[c_num]["total_count"] < min_count:
            min_count = manifest[c_num]["total_count"]
            best_car = c_num
    return best_car

async def assign_named_passengers_to_car(car_num: int, companion_names: List[str]) -> List[str]:
    """
    Groups driver's companions under their car in the database.
    If a companion is not yet in the DB, inserts a placeholder row so that
    when they register later, their car assignment is automatically recognized.
    """
    confirmed_names: List[str] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for raw_name in companion_names:
            clean_name = raw_name.strip()
            if not clean_name:
                continue

            matched = guest_list.find_matching_guests(clean_name)
            canonical_name = matched[0]["name"] if matched else clean_name

            # Check if companion already in DB
            async with db.execute(
                "SELECT * FROM guests WHERE full_name = ?", (canonical_name,)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                await db.execute(
                    "UPDATE guests SET car_number = ?, has_car = 0 WHERE id = ?",
                    (car_num, existing["id"])
                )
            else:
                serial_number = await get_next_serial_number(db=db)
                soul_pin = generate_soul_pin(serial_number)
                mission_id = ((serial_number * 3 + 7) % 20) + 1
                await db.execute(
                    """
                    INSERT INTO guests (telegram_id, telegram_username, full_name, has_car, car_number, serial_number, soul_pin, social_mission_id)
                    VALUES (NULL, NULL, ?, 0, ?, ?, ?, ?)
                    """,
                    (canonical_name, car_num, serial_number, soul_pin, mission_id)
                )

            confirmed_names.append(canonical_name)

        await db.commit()

    return confirmed_names

async def find_best_carpool_match(guest_name: str) -> int:
    """
    Finds the most suitable car (1..13) for a passenger, auto-drafting
    them to fill each car to 4:
    1. If already assigned in DB, keep it.
    2. If pre-assigned in GUEST_ROSTER with car_group and seats < 4, keep it.
    3. Draft into cars that have a driver and open seats (< 4 people total).
    4. Fallback: Any car with < 4 people total.
    """
    manifest = await get_carpool_manifest()

    # 1. Existing DB assignment
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT car_number FROM guests WHERE full_name = ? AND car_number IS NOT NULL",
            (guest_name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["car_number"] and 1 <= row["car_number"] <= 13:
                return row["car_number"]

    # 2. Pre-assigned in roster with available room
    matched = guest_list.find_matching_guests(guest_name)
    if matched:
        cg = matched[0].get("car_group")
        if cg and 1 <= cg <= 13:
            if manifest[cg]["total_count"] < 4:
                return cg

    # 3. Draft into cars with a driver and open seats (< 4 people)
    for c_num in range(1, 14):
        car = manifest[c_num]
        if car["driver"] and car["total_count"] < 4:
            return c_num

    # 4. Fallback: any car with open seats (< 4 people)
    for c_num in range(1, 14):
        if manifest[c_num]["total_count"] < 4:
            return c_num

    return 1

async def get_driver_info_for_car(car_num: int) -> Dict[str, Any]:
    """Retrieves driver full name, Telegram ID, and username for a car."""
    manifest = await get_carpool_manifest()
    car_info = manifest.get(car_num, {})
    d_name = car_info.get("driver")
    d_tid = car_info.get("driver_telegram_id")
    d_uname = car_info.get("driver_telegram_username")

    if d_name and not d_tid:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT telegram_id, telegram_username FROM guests WHERE full_name = ? AND telegram_id IS NOT NULL",
                (d_name,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    d_tid = row["telegram_id"]
                    d_uname = row["telegram_username"]

    return {
        "name": d_name,
        "telegram_id": d_tid,
        "telegram_username": d_uname
    }

def format_driver_contact(driver_info: dict) -> str:
    """Formats driver contact information including Telegram ID and username."""
    name = driver_info.get("name")
    tid = driver_info.get("telegram_id")
    uname = driver_info.get("telegram_username")

    if not name or name == "در حال تعیین راننده":
        return "تعیین راننده به زودی توسط کاروان"

    if uname:
        return f"{name} (@{uname})"
    elif tid:
        return f"{name} ([ارسال پیام در تلگرام](tg://user?id={tid}) — آیدی تلگرام: `{tid}`)"
    else:
        return f"{name} (در انتظار ورود به بات — آیدی تلگرام به زودی اعلام می‌شود)"

async def get_car_passengers(car_num: int) -> List[Dict[str, Any]]:
    """Returns list of passengers registered for a car."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE car_number = ? AND (has_car = 0 OR has_car IS NULL)",
            (car_num,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_game_state(key: str, default: str = "") -> str:
    """Reads game state string."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM game_state WHERE key = ?", (key,)) as c:
            row = await c.fetchone()
            return row[0] if row else default

async def set_game_state(key: str, value: str) -> None:
    """Sets game state string."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO game_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value))
        )
        await db.commit()

async def get_all_telegram_ids(role_filter: Optional[str] = None) -> List[int]:
    """Retrieves all Telegram IDs, optionally filtered by role."""
    async with aiosqlite.connect(DB_PATH) as db:
        if role_filter:
            query = "SELECT telegram_id FROM guests WHERE telegram_id IS NOT NULL AND role = ?"
            params = (role_filter,)
        else:
            query = "SELECT telegram_id FROM guests WHERE telegram_id IS NOT NULL"
            params = ()
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows if r[0]]
