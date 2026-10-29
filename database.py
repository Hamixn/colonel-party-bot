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

async def record_team_accusation(team_number: int, suspect: str, telegram_id: int) -> Dict[str, Any]:
    """
    Records an accusation for the team at the central deduction table.
    Teams can revise their theory until the host closes deduction.
    """
    cleaned = suspect.strip()
    await set_game_state(f"team_{team_number}_accusation", cleaned)
    await set_game_state(f"team_{team_number}_accusation_by", str(telegram_id))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE guests SET accusation = ? WHERE team_number = ?", (cleaned, team_number))
        await db.commit()
    return {
        "status": "recorded",
        "team_number": team_number,
        "suspect": cleaned
    }

async def get_team_accusation(team_number: int) -> Optional[str]:
    """Retrieves current recorded accusation for a team."""
    val = await get_game_state(f"team_{team_number}_accusation", "")
    return val if val else None

async def get_all_accusations() -> Dict[int, str]:
    """Retrieves all submitted accusations across all teams."""
    results = {}
    for t_num in (1, 2, 3):
        acc = await get_team_accusation(t_num)
        if acc:
            results[t_num] = acc
    return results

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

async def start_social_game(count: int = 5) -> Dict[str, Any]:
    """
    Starts Phase 2 (19:15 Social Game):
    1. Selects 5 random players as Secret Infected (is_hunter=1).
    2. Marks social_game_started=1 in game_state.
    3. Returns dict with 'hunters' and 'regular_players'.
    """
    await assign_random_hunters(count=count)
    await set_game_state("social_game_started", "1")
    await set_game_state("force_unlock_missions", "1")

    all_players = await get_players()
    hunters = [p for p in all_players if p.get("is_hunter") == 1]
    regular_players = [p for p in all_players if p.get("is_hunter") != 1]
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
    Assigns the 4 canonical character roles among active mystery players:
    1. Shirin Nouri (witness 1, sticker carrier): Team 1 member
    2. Keyvan Rastegar (witness 2, sticker carrier): Team 2 member
    3. Dr. Fereydoun Mehr (witness 3, sticker carrier): Team 3 member
    4. Nader Vosough (actual killer, hidden role): active player in any team, distinct from witnesses.
    Never assigns to role_blonde.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check if already assigned
        if not force_reassign:
            async with db.execute("SELECT * FROM guests WHERE character_role IS NOT NULL AND role = 'role_player'") as cursor:
                rows = [dict(r) for r in await cursor.fetchall()]
                existing = {r["character_role"]: r for r in rows}
                if len(existing) >= 4 and all(k in existing for k in ["shirin", "keyvan", "fereydoun", "nader"]):
                    return existing

        # Get active players
        async with db.execute("SELECT * FROM guests WHERE role = 'role_player' ORDER BY id ASC") as cursor:
            players = [dict(r) for r in await cursor.fetchall()]

        if not players:
            return {}

        # Reset existing character roles
        await db.execute("UPDATE guests SET character_role = NULL, is_hunter = 0")

        # Separate players by team (1, 2, 3)
        t1_players = [p for p in players if p.get("team_number") == 1]
        t2_players = [p for p in players if p.get("team_number") == 2]
        t3_players = [p for p in players if p.get("team_number") == 3]

        if not t1_players or not t2_players or not t3_players:
            # Distribute players across 3 teams first
            for idx, p in enumerate(players):
                t_num = (idx % 3) + 1
                t_names = {1: "تیم ۱ (خون)", 2: "تیم ۲ (سایه)", 3: "تیم ۳ (سکوت)"}
                await db.execute("UPDATE guests SET team_number = ?, team_name = ? WHERE id = ?", (t_num, t_names[t_num], p["id"]))
                p["team_number"] = t_num
                p["team_name"] = t_names[t_num]

            t1_players = [p for p in players if p.get("team_number") == 1]
            t2_players = [p for p in players if p.get("team_number") == 2]
            t3_players = [p for p in players if p.get("team_number") == 3]

        shirin = random.choice(t1_players) if t1_players else players[0]
        keyvan = random.choice(t2_players) if t2_players else players[min(1, len(players) - 1)]
        fereydoun = random.choice(t3_players) if t3_players else players[min(2, len(players) - 1)]

        # Nader must be distinct from the 3 witnesses
        candidates = [p for p in players if p["id"] not in {shirin["id"], keyvan["id"], fereydoun["id"]}]
        nader = random.choice(candidates) if candidates else random.choice(players)

        # Update in database (witnesses are sticker carriers: is_hunter=1)
        await db.execute("UPDATE guests SET character_role = 'shirin', is_hunter = 1 WHERE id = ?", (shirin["id"],))
        await db.execute("UPDATE guests SET character_role = 'keyvan', is_hunter = 1 WHERE id = ?", (keyvan["id"],))
        await db.execute("UPDATE guests SET character_role = 'fereydoun', is_hunter = 1 WHERE id = ?", (fereydoun["id"],))
        await db.execute("UPDATE guests SET character_role = 'nader', is_hunter = 0 WHERE id = ?", (nader["id"],))
        await db.commit()

        shirin["character_role"] = "shirin"
        shirin["is_hunter"] = 1
        keyvan["character_role"] = "keyvan"
        keyvan["is_hunter"] = 1
        fereydoun["character_role"] = "fereydoun"
        fereydoun["is_hunter"] = 1
        nader["character_role"] = "nader"
        nader["is_hunter"] = 0

        return {
            "shirin": shirin,
            "keyvan": keyvan,
            "fereydoun": fereydoun,
            "nader": nader
        }

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
    Starts Phase 3 (The 24:00 Midnight Investigation Game):
    1. Splits active mystery players into 3 teams (تیم ۱ to ۳) of 4-5 players each.
    2. Appoints 1 secret traitor per team (is_traitor=1).
    3. Resets riddles (riddle_1_solved=0, riddle_2_solved=0).
    4. Marks midnight_game_started=1 and game_phase='midnight_investigation' in game_state.
    5. Returns teams dict keyed by team_number (1..3).
    """
    players = await get_players()
    if not players:
        return {}

    team_names = {
        1: "تیم ۱ (خون)",
        2: "تیم ۲ (سایه)",
        3: "تیم ۳ (سکوت)",
        4: "تیم ۴ (آینه)"
    }
    actual_count = min(team_count, 4)

    random.shuffle(players)
    assigned: Dict[int, Dict[str, Any]] = {
        i: {"name": team_names[i], "members": [], "traitor": None}
        for i in range(1, actual_count + 1)
    }

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE guests
            SET team_number = NULL, team_name = NULL, is_traitor = 0,
                riddle_1_solved = 0, riddle_2_solved = 0
        """)

        for idx, p in enumerate(players):
            team_num = (idx % actual_count) + 1
            t_name = team_names[team_num]
            p["team_number"] = team_num
            p["team_name"] = t_name
            assigned[team_num]["members"].append(p)
            await db.execute(
                "UPDATE guests SET team_number = ?, team_name = ? WHERE id = ?",
                (team_num, t_name, p["id"])
            )

        # Select 1 traitor per team
        for team_num in range(1, actual_count + 1):
            members = assigned[team_num]["members"]
            if members:
                traitor = random.choice(members)
                traitor["is_traitor"] = 1
                assigned[team_num]["traitor"] = traitor
                await db.execute(
                    "UPDATE guests SET is_traitor = 1 WHERE id = ?",
                    (traitor["id"],)
                )

        await db.commit()

    # Clear riddle game state
    for i in range(1, actual_count + 1):
        await set_game_state(f"team_{i}_riddle_1", "0")
        await set_game_state(f"team_{i}_riddle_2", "0")

    await set_game_state("midnight_game_started", "1")
    await set_game_state("game_phase", "midnight_investigation")
    return assigned

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
    """
    Checks answer against player's assigned team riddles.
    Team 1: Riddle 1 = خون | Riddle 2 = 1356
    Team 2: Riddle 1 = سایه | Riddle 2 = 2910
    Team 3: Riddle 1 = سکوت | Riddle 2 = 5
    """
    guest = await get_guest_by_telegram_id(telegram_id)
    if not guest:
        return {"status": "not_registered"}

    team_num = guest.get("team_number")
    if not team_num or team_num < 1 or team_num > 4:
        return {"status": "no_team"}

    team_riddle_answers = {
        1: {
            1: ["خون", "blood", "خون سرخ"],
            2: ["1356", "۱۳۵۶"]
        },
        2: {
            1: ["سایه", "shadow", "سايه"],
            2: ["2910", "۲۹۱۰"]
        },
        3: {
            1: ["سکوت", "silence", "سکوت مطلق"],
            2: ["5", "پنج", "۵"]
        },
        4: {
            1: ["آینه", "mirror", "اینه", "آيينه"],
            2: ["12", "۱۲", "2400", "۲۴۰۰"]
        }
    }

    answers = team_riddle_answers.get(team_num, {})

    r1_solved = (await get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2_solved = (await get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"

    if r1_solved and r2_solved:
        return {
            "status": "already_both_solved",
            "team_number": team_num,
            "response_text": game.CLIMAX_INSTRUCTIONS
        }

    # Check match with Riddle 1
    match_r1 = any(_matches_candidate(answer, cand) for cand in answers.get(1, []))
    # Check match with Riddle 2
    match_r2 = any(_matches_candidate(answer, cand) for cand in answers.get(2, []))

    if match_r1:
        if r1_solved:
            return {
                "status": "already_solved",
                "riddle_num": 1,
                "team_number": team_num,
                "response_text": "⚠️ این مدرک (معمای شماره ۱) قبلاً توسط تیم شما ثبت شده است!"
            }
        await set_game_state(f"team_{team_num}_riddle_1", "1")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE guests SET riddle_1_solved = 1 WHERE team_number = ?", (team_num,))
            await db.commit()

        resp_text = game.RIDDLE_RESPONSES.get((team_num, 1), "✅ مدرک با موفقیت ثبت شد.")
        all_collected = await is_all_evidence_collected()
        if r2_solved:
            return {
                "status": "both_solved",
                "team_number": team_num,
                "just_solved": 1,
                "riddle_num": 1,
                "response_text": resp_text,
                "all_teams_solved": all_collected
            }
        return {
            "status": "riddle_solved",
            "riddle_num": 1,
            "team_number": team_num,
            "response_text": resp_text,
            "all_teams_solved": all_collected
        }

    if match_r2:
        if r2_solved:
            return {
                "status": "already_solved",
                "riddle_num": 2,
                "team_number": team_num,
                "response_text": "⚠️ این مدرک (معمای شماره ۲) قبلاً توسط تیم شما ثبت شده است!"
            }
        await set_game_state(f"team_{team_num}_riddle_2", "1")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE guests SET riddle_2_solved = 1 WHERE team_number = ?", (team_num,))
            await db.commit()

        resp_text = game.RIDDLE_RESPONSES.get((team_num, 2), "✅ مدرک با موفقیت ثبت شد.")
        all_collected = await is_all_evidence_collected()
        if r1_solved:
            return {
                "status": "both_solved",
                "team_number": team_num,
                "just_solved": 2,
                "riddle_num": 2,
                "response_text": resp_text,
                "all_teams_solved": all_collected
            }
        return {
            "status": "riddle_solved",
            "riddle_num": 2,
            "team_number": team_num,
            "response_text": resp_text,
            "all_teams_solved": all_collected
        }

    # Check if answer matches another team's riddle (cross-team submission)
    for other_team, other_riddles in team_riddle_answers.items():
        if other_team != team_num:
            for r_idx, cands in other_riddles.items():
                if any(_matches_candidate(answer, cand) for cand in cands):
                    return {
                        "status": "other_team_riddle",
                        "team_number": team_num,
                        "other_team": other_team,
                        "response_text": game.OTHER_TEAM_CODE_ALERT
                    }

    return {
        "status": "wrong",
        "team_number": team_num,
        "response_text": game.WRONG_ANSWER_TEXT
    }

async def assign_tester_team(telegram_id: int, team_number: int) -> Dict[str, Any]:
    """Assigns or switches a tester's team (1, 2, 3, or 4)."""
    team_names = {
        1: "تیم ۱ (خون)",
        2: "تیم ۲ (سایه)",
        3: "تیم ۳ (سکوت)",
        4: "تیم ۴ (آینه)"
    }
    t_name = team_names.get(team_number, f"تیم {team_number}")
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

        # Reset all game progression states
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
            'traitors_revealed'
        ]
        placeholders = ','.join(['?'] * len(keys_to_clear))
        await db.execute(f"DELETE FROM game_state WHERE key IN ({placeholders})", keys_to_clear)
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
    """Resets solved riddle states for testing."""
    async with aiosqlite.connect(DB_PATH) as db:
        if team_number:
            await db.execute("""
                UPDATE guests 
                SET riddle_1_solved = 0, riddle_2_solved = 0
                WHERE team_number = ?
            """, (team_number,))
            await db.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                (f"team_{team_number}_riddle_1", "0")
            )
            await db.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                (f"team_{team_number}_riddle_2", "0")
            )
        else:
            await db.execute("UPDATE guests SET riddle_1_solved = 0, riddle_2_solved = 0, is_immune = 0, got_stickered = 0")
            for i in range(1, 5):
                await db.execute(
                    "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                    (f"team_{i}_riddle_1", "0")
                )
                await db.execute(
                    "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                    (f"team_{i}_riddle_2", "0")
                )
        await db.commit()
    return True

async def get_reveal_manifest() -> Dict[str, Any]:
    """Returns hunters and traitors for the 02:00 AM reveal."""
    hunters = await get_hunters()
    traitors = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guests WHERE is_traitor = 1 ORDER BY team_number ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            traitors = [dict(r) for r in rows]
    return {
        "hunters": hunters,
        "traitors": traitors
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
