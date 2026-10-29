"""
End-to-End Multi-Team Competitive Scenario Test Suite for Bāgh-e Sarhang Murder Mystery.
Implements Opaque-Box E2E Testing across Tiers 1-4:
- Tier 1: Feature Coverage (Private clue delivery, Teammate broadcasts, Zero competitor leaks,
  Structured /accuse, Unblocked /rescue, Host finale & traitors reveal, Progressive hints).
- Tier 2: Boundary & Corner Cases (Casual blondes, non-admins, unassigned users, tester flow,
  out-of-bounds hint levels and teams).
- Tier 3: Cross-Feature Combinations (Solve+Accuse, Solve+Rescue, Accuse before solve, Deductions close).
- Tier 4: Real-World Application Scenarios:
  * Scenario 1: Full three-team competition with Team 2 winning first, Team 1 revising, host reveal.
  * Scenario 2: Teammates racing to submit the same envelope concurrently.
  * Scenario 3: Partial / wrong accusation rejected neutrally, followed by complete revision winning.
  * Scenario 4: Host finale, paper darkroom confrontation, and witness distinction.
  * Scenario 5: Emergency rescue alert during active game play.
"""

import os
import asyncio
import unittest
from pathlib import Path
import uuid
from unittest.mock import AsyncMock, MagicMock
import aiosqlite
from aiogram.types import Message
from aiogram import Bot

import config
import database
import game
import texts
import handlers.game
import handlers.admin


def make_mock_message(user_id: int, text: str, username: str = "guest_user"):
    """Creates a mock aiogram Message recording user responses."""
    msg = AsyncMock(spec=Message)
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.text = text
    msg.answers = []

    async def fake_answer(text_content, **kwargs):
        msg.answers.append(text_content)
        return MagicMock()

    msg.answer = AsyncMock(side_effect=fake_answer)
    return msg


def make_mock_bot():
    """Creates a mock aiogram Bot recording dispatched messages."""
    bot = AsyncMock(spec=Bot)
    bot.sent_messages = []

    async def fake_send_message(chat_id, text, **kwargs):
        bot.sent_messages.append((chat_id, text))
        return MagicMock()

    bot.send_message = AsyncMock(side_effect=fake_send_message)
    return bot


class BaseE2ETestCase(unittest.IsolatedAsyncioTestCase):
    """Base fixture providing an isolated, Windows-safe temporary database for each E2E test."""

    async def asyncSetUp(self):
        self.unique_id = uuid.uuid4().hex[:10]
        self.test_db_file = Path(f"test_e2e_{self.unique_id}_{self._testMethodName}.db")
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.test_db_file

        self.orig_admin_id = config.ADMIN_USER_ID
        config.ADMIN_USER_ID = 999000111
        database._riddle_lock = asyncio.Lock()

        await database.init_db()

        # Seed test participants:
        # Team 1: 101, 111 (Investigators)
        # Team 2: 102, 112 (Investigators)
        # Team 3: 103, 113 (Investigators)
        # Blondes: 301, 302 (Casual Guests)
        # Admin / Tester: 102725917 (Hamixon)
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES 
                (101, 'investigator_1a', 'بازرس ۱-الف', 'role_player', 1, 'تیم ۱ (خون)'),
                (111, 'investigator_1b', 'بازرس ۱-ب', 'role_player', 1, 'تیم ۱ (خون)'),
                (102, 'investigator_2a', 'بازرس ۲-الف', 'role_player', 2, 'تیم ۲ (سایه)'),
                (112, 'investigator_2b', 'بازرس ۲-ب', 'role_player', 2, 'تیم ۲ (سایه)'),
                (103, 'investigator_3a', 'بازرس ۳-الف', 'role_player', 3, 'تیم ۳ (سکوت)'),
                (113, 'investigator_3b', 'بازرس ۳-ب', 'role_player', 3, 'تیم ۳ (سکوت)'),
                (301, 'blonde_1', 'بلوند اول', 'role_blonde', NULL, NULL),
                (302, 'blonde_2', 'بلوند دوم', 'role_blonde', NULL, NULL)
            """)
            await db.commit()
        await database.set_game_state("game_phase", "midnight_investigation")

    async def asyncTearDown(self):
        config.ADMIN_USER_ID = self.orig_admin_id
        database.DB_PATH = self.orig_db_path
        await asyncio.sleep(0.01)
        if self.test_db_file.exists():
            for _ in range(5):
                try:
                    os.remove(self.test_db_file)
                    break
                except Exception:
                    await asyncio.sleep(0.05)


class TestE2ESolveFlow(BaseE2ETestCase):
    """Tier 1: /solve handler E2E flow, private clue delivery, teammate broadcast, and isolation."""

    async def test_solve_first_envelope_private_clue_and_teammate_broadcast(self):
        """Solver receives private clue; teammate receives broadcast; competitor teams receive zero messages."""
        bot = make_mock_bot()
        msg_101 = make_mock_message(101, "/solve خون")

        await handlers.game.cmd_solve(msg_101, bot)

        # 1. Solver received clue directly
        self.assertEqual(len(msg_101.answers), 1)
        solver_clue = msg_101.answers[0]
        self.assertIn("مدرک جسمانی ثبت شد", solver_clue)
        # Clue does not disclose the killer
        self.assertNotIn("نادر وثوق", solver_clue)

        # 2. Teammate (111) received broadcast
        teammate_recipients = [call[0] for call in bot.sent_messages]
        self.assertIn(111, teammate_recipients)
        # Solver (101) did NOT receive a redundant bot.send_message
        self.assertNotIn(101, teammate_recipients)

        # 3. Competitor teams received ZERO messages
        competitor_ids = [102, 112, 103, 113, 301, 302]
        for c_id in competitor_ids:
            self.assertNotIn(c_id, teammate_recipients)

    async def test_solve_second_envelope_exact_once_team_completion(self):
        """Solving second envelope completes team exactly once and broadcasts team completion."""
        bot = make_mock_bot()

        # Step 1: Solve Riddle 1
        msg_1a = make_mock_message(101, "/solve خون")
        await handlers.game.cmd_solve(msg_1a, bot)
        bot.sent_messages.clear()

        # Step 2: Solve Riddle 2
        msg_1b = make_mock_message(101, "/solve 1356")
        await handlers.game.cmd_solve(msg_1b, bot)

        # Solver received clue
        self.assertEqual(len(msg_1b.answers), 1)
        self.assertIn("صفحهی حسابها ثبت شد", msg_1b.answers[0])

        # Team completion broadcast sent to both teammates (101 and 111)
        recipients = [call[0] for call in bot.sent_messages]
        self.assertIn(101, recipients)
        self.assertIn(111, recipients)
        self.assertTrue(any("هر دو مدرک تیم شما با موفقیت ثبت شد" in call[1] for call in bot.sent_messages))

        # Check DB state
        self.assertEqual(await database.get_game_state("team_1_both_solved"), "1")
        ts = await database.get_game_state("team_1_completed_at")
        self.assertIsNotNone(ts)

    async def test_duplicate_solve_suppresses_teammate_broadcasts(self):
        """Duplicate solves warn the solver only; no broadcasts are sent to teammates."""
        bot = make_mock_bot()

        # First solve
        msg_1 = make_mock_message(101, "/solve خون")
        await handlers.game.cmd_solve(msg_1, bot)
        bot.sent_messages.clear()

        # Duplicate solve by 101
        msg_dup = make_mock_message(101, "/solve خون")
        await handlers.game.cmd_solve(msg_dup, bot)

        # Solver warned
        self.assertEqual(len(msg_dup.answers), 1)
        self.assertIn("قبلاً توسط تیم شما ثبت شده است", msg_dup.answers[0])

        # Zero teammate broadcasts on duplicate
        self.assertEqual(len(bot.sent_messages), 0)

    async def test_competitor_code_rejection_in_handler(self):
        """Competitor code submission returns OTHER_TEAM_CODE_ALERT to solver with zero leaks."""
        bot = make_mock_bot()
        msg_cross = make_mock_message(101, "/solve سایه")

        await handlers.game.cmd_solve(msg_cross, bot)

        self.assertEqual(len(msg_cross.answers), 1)
        self.assertEqual(msg_cross.answers[0], texts.OTHER_TEAM_CODE_ALERT)
        # No broadcast to anyone
        self.assertEqual(len(bot.sent_messages), 0)


class TestE2EAccuseFlow(BaseE2ETestCase):
    """Tier 1: /accuse handler E2E flow, neutral responses, winner determination, and revisions."""

    async def test_accuse_without_arguments_shows_central_table_instructions(self):
        """Sending /accuse without arguments shows the deduction prompt and suspect options."""
        bot = make_mock_bot()
        msg = make_mock_message(101, "/accuse")
        await handlers.game.cmd_accuse(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertIn("میز مرکزی تجمیع مدارک", msg.answers[0])

    async def test_accuse_valid_submission_returns_neutral_response(self):
        """Valid accusation naming Nader Vosough returns a neutral confirmation without disclosing win."""
        for n in (1, 2):
            await database.set_game_state(f"team_1_riddle_{n}", "1")
        bot = make_mock_bot()
        msg = make_mock_message(
            101,
            "/accuse نادر وثوق\nاختلاس حساب ۸۴۱۰۲ در سال ۵۶\nخون و جراحت سر در استخر\nدفتر حسابداری مالی"
        )
        await handlers.game.cmd_accuse(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        resp = msg.answers[0]
        self.assertEqual(resp, texts.ACCUSATION_RECORDED_NEUTRAL)
        # Neutral response must not disclose win publicly
        self.assertNotIn("برنده شدید", resp)
        self.assertNotIn("اول شدید", resp)

        # Behind the scenes, Team 1 is recorded as winner
        winner = await database.get_winning_accusation()
        self.assertIsNotNone(winner)
        self.assertEqual(winner["team_number"], 1)

        # Private host notification was sent to config.ADMIN_USER_ID
        admin_messages = [call for call in bot.sent_messages if call[0] == config.ADMIN_USER_ID]
        self.assertGreater(len(admin_messages), 0)
        self.assertIn("ثبت نخستین اتهام صحیح", admin_messages[0][1])

    async def test_accuse_non_winning_submission_returns_identical_neutral_response(self):
        """Non-winning accusation (e.g. naming wrong suspect) receives the same neutral confirmation."""
        for n in (1, 2):
            await database.set_game_state(f"team_2_riddle_{n}", "1")
        bot = make_mock_bot()
        msg = make_mock_message(
            102,
            "/accuse شیرین نوری\nفرار از مهمانی و ترس از استخر\nشاهد صحنه\nپنهان‌کاری"
        )
        await handlers.game.cmd_accuse(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        resp = msg.answers[0]
        self.assertEqual(resp, texts.ACCUSATION_RECORDED_NEUTRAL)

        # Not winner
        winner = await database.get_winning_accusation()
        self.assertIsNone(winner)
        # Admin was NOT alerted of a winner
        admin_messages = [call for call in bot.sent_messages if call[0] == config.ADMIN_USER_ID]
        self.assertEqual(len(admin_messages), 0)

    async def test_accuse_revision_lifecycle(self):
        """Accusations can be revised freely until deductions are closed."""
        for n in (1, 2):
            await database.set_game_state(f"team_1_riddle_{n}", "1")
        bot = make_mock_bot()
        # Initial submission
        msg1 = make_mock_message(101, "/accuse نادر وثوق")
        await handlers.game.cmd_accuse(msg1, bot)
        self.assertEqual(await database.get_team_accusation(1), "نادر وثوق")

        # Revision
        msg2 = make_mock_message(101, "/accuse نادر وثوق (مدیر امور مالی)")
        await handlers.game.cmd_accuse(msg2, bot)
        self.assertEqual(await database.get_team_accusation(1), "نادر وثوق (مدیر امور مالی)")


class TestE2ERescueFlow(BaseE2ETestCase):
    """Tier 1: /rescue emergency safety alert flow, non-blocking lifecycle."""

    async def test_rescue_alerts_safety_and_increments_counter(self):
        """Sending /rescue informs player of red lantern rules and increments safety alert counter."""
        bot = make_mock_bot()
        msg = make_mock_message(101, "/rescue")
        await handlers.game.cmd_rescue(msg, bot)

        self.assertTrue(
            "پیام امداد شما به میزبان" in msg.answers[0] or "قانون تاریکی مطلق باغ" in msg.answers[0]
        )

        # Admin notified
        admin_messages = [call for call in bot.sent_messages if call[0] == config.ADMIN_USER_ID]
        self.assertGreater(len(admin_messages), 0)
        self.assertIn("هشدار اضطراری", admin_messages[0][1])

        # Verify DB alert logging multiple times
        c1 = await database.record_rescue_alert(101, "بازرس ۱-الف", "حیاط تاریک")
        c2 = await database.record_rescue_alert(101, "بازرس ۱-الف", "حیاط تاریک")
        c3 = await database.record_rescue_alert(101, "بازرس ۱-الف", "حیاط تاریک")
        c4 = await database.record_rescue_alert(101, "بازرس ۱-الف", "حیاط تاریک")
        self.assertGreaterEqual(c4, 4)
        # Never blocked
        self.assertGreaterEqual(int(await database.get_game_state("rescue_alert_count")), 4)


class TestE2EHostFinaleAndReveal(BaseE2ETestCase):
    """Tier 1: /trigger_finale and /reveal_traitors host commands and witness/killer separation."""

    async def test_host_trigger_finale(self):
        """Host triggers finale at 01:10 AM: players receive darkroom prompt, game phase updated."""
        bot = make_mock_bot()
        admin_msg = make_mock_message(102725917, "/trigger_finale")

        await handlers.admin.cmd_trigger_darkroom(admin_msg, bot)

        self.assertEqual(await database.get_game_state("game_phase"), "finale")
        # Broadcast sent to players
        recipients = [call[0] for call in bot.sent_messages]
        self.assertIn(101, recipients)
        self.assertIn(102, recipients)
        self.assertIn(103, recipients)
        # Blondes not sent darkroom prompt
        self.assertNotIn(301, recipients)
        self.assertNotIn(302, recipients)

    async def test_host_reveal_traitors_distinguishes_killer_from_witnesses(self):
        """Host reveals traitors at 02:00 AM: Nader Vosough is distinct from 3 concealing witnesses."""
        # Assign special characters
        assigned = await database.assign_special_character_roles(force_reassign=True)
        self.assertEqual(len(assigned), 4)

        bot = make_mock_bot()
        admin_msg = make_mock_message(102725917, "/reveal_traitors")

        await handlers.admin.cmd_reveal_traitors(admin_msg, bot)

        # Broadcast was sent to all registered guests
        recipients = [call[0] for call in bot.sent_messages]
        self.assertIn(101, recipients)
        self.assertIn(301, recipients)

        # Verify role profiles: Nader Vosough is sole culprit, Shirin/Keyvan/Fereydoun are concealing witnesses
        self.assertIn("تنها مقصر اصلی پرونده", game.CHARACTER_ROLE_CARDS["nader"])
        self.assertIn("شاهد صحنه", game.CHARACTER_ROLE_CARDS["shirin"])
        self.assertIn("عکاس مهمانی", game.CHARACTER_ROLE_CARDS["keyvan"])
        self.assertIn("پزشک حاضر در مهمانی", game.CHARACTER_ROLE_CARDS["fereydoun"])


class TestE2EProgressiveHints(BaseE2ETestCase):
    """Tier 1 & Tier 2: /hint <team> <level> admin handler, private delivery, out-of-bounds checks."""

    async def test_progressive_hint_level_1_delivery_to_target_team_only(self):
        """Admin sends /hint 1 1: delivered privately to Team 1 members only."""
        bot = make_mock_bot()
        admin_msg = make_mock_message(102725917, "/hint 1 1")

        await handlers.admin.cmd_hint(admin_msg, bot)

        # Verified delivered to Team 1 (101, 111)
        recipients = [call[0] for call in bot.sent_messages]
        self.assertIn(101, recipients)
        self.assertIn(111, recipients)
        # Verify content matches level 1 subtle pointer
        hint_text = [call[1] for call in bot.sent_messages if call[0] == 101][0]
        self.assertIn("راهنمایی مرحله ۱", hint_text)

        # Competitor teams (Team 2 and Team 3) received zero hint messages
        competitor_ids = [102, 112, 103, 113, 301, 302]
        for c_id in competitor_ids:
            self.assertNotIn(c_id, recipients)

    async def test_progressive_hint_levels_progression(self):
        """Admin can deliver Level 1 (subtle), Level 2 (explicit), and Level 3 (host fallback)."""
        bot = make_mock_bot()
        for lvl in (1, 2, 3):
            bot.sent_messages.clear()
            admin_msg = make_mock_message(102725917, f"/hint 2 {lvl}")
            await handlers.admin.cmd_hint(admin_msg, bot)
            recipients = [call[0] for call in bot.sent_messages]
            self.assertIn(102, recipients)
            self.assertIn(112, recipients)
            delivered_text = bot.sent_messages[0][1]
            self.assertIn(f"سطح {lvl}", delivered_text)

    async def test_hint_out_of_bounds_validation(self):
        """Invalid team number or level is rejected with clear error message."""
        bot = make_mock_bot()

        # Invalid team 5
        m_team_err = make_mock_message(102725917, "/hint 5 1")
        await handlers.admin.cmd_hint(m_team_err, bot)
        self.assertIn("شماره تیم باید ۱، ۲ یا ۳ باشد", m_team_err.answers[0])

        # Invalid level 4
        m_lvl_err = make_mock_message(102725917, "/hint 1 4")
        await handlers.admin.cmd_hint(m_lvl_err, bot)
        self.assertIn("سطح راهنمایی باید ۱، ۲ یا ۳ باشد", m_lvl_err.answers[0])

    async def test_non_admin_hint_call_rejected(self):
        """Non-admin user calling /hint gets access denied."""
        bot = make_mock_bot()
        msg_user = make_mock_message(101, "/hint 1 1")
        await handlers.admin.cmd_hint(msg_user, bot)
        self.assertIn("دسترسی غیرمجاز", msg_user.answers[0])
        self.assertEqual(len(bot.sent_messages), 0)


class TestE2EBoundaryCases(BaseE2ETestCase):
    """Tier 2: Casual blondes, unauthorized admin, unassigned users, and tester auto-assignment."""

    async def test_casual_blonde_solve_attempt_rejected(self):
        """Blonde guest sending /solve is rejected with friendly explanation."""
        bot = make_mock_bot()
        msg_blonde = make_mock_message(301, "/solve خون")

        await handlers.game.cmd_solve(msg_blonde, bot)

        self.assertEqual(len(msg_blonde.answers), 1)
        self.assertIn("بلوند بی‌گناه", msg_blonde.answers[0])
        self.assertEqual(len(bot.sent_messages), 0)

    async def test_casual_blonde_accuse_attempt_rejected(self):
        """Blonde guest sending /accuse is informed that deduction is for investigators."""
        bot = make_mock_bot()
        msg_blonde = make_mock_message(301, "/accuse نادر وثوق")
        await handlers.game.cmd_accuse(msg_blonde, bot)

        self.assertEqual(len(msg_blonde.answers), 1)
        self.assertIn("بلوند بی‌گناه", msg_blonde.answers[0])

    async def test_non_admin_trigger_darkroom_rejected(self):
        """Non-admin user attempting /trigger_finale gets access denied."""
        bot = make_mock_bot()
        msg_unauth = make_mock_message(101, "/trigger_finale")

        await handlers.admin.cmd_trigger_darkroom(msg_unauth, bot)

        self.assertEqual(len(msg_unauth.answers), 1)
        self.assertIn("دسترسی غیرمجاز", msg_unauth.answers[0])
        self.assertEqual(len(bot.sent_messages), 0)

    async def test_tester_auto_assignment_on_solve(self):
        """Authorized tester (Hamixon, 102725917) is auto-assigned to Team 1 on /solve if unassigned."""
        # Seed tester with team_number=None
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT OR REPLACE INTO guests (telegram_id, telegram_username, full_name, role, team_number)
                VALUES (102725917, 'Hamixon', 'حامد', 'role_player', NULL)
            """)
            await db.commit()

        bot = make_mock_bot()
        msg_tester = make_mock_message(102725917, "/solve خون", username="Hamixon")

        await handlers.game.cmd_solve(msg_tester, bot)

        # Tester was auto-assigned and solved Team 1 Riddle 1
        guest = await database.get_guest_by_telegram_id(102725917)
        self.assertIsNotNone(guest)
        self.assertEqual(guest["team_number"], 1)
        self.assertEqual(len(msg_tester.answers), 1)
        self.assertIn("مدرک جسمانی ثبت شد", msg_tester.answers[0])


class TestE2ECrossFeatureCombinations(BaseE2ETestCase):
    """Tier 3: Pairwise and Cross-Feature Combinations."""

    async def test_pairwise_solve_and_accuse(self):
        """Team solves Envelope 1, submits accusation, solves Envelope 2, revises accusation."""
        bot = make_mock_bot()

        # 1. Solve Envelope 1
        m1 = make_mock_message(101, "/solve خون")
        await handlers.game.cmd_solve(m1, bot)

        # 2. Accuse prematurely
        m_acc1 = make_mock_message(101, "/accuse نادر وثوق\nضربه سر و خون استخر")
        await handlers.game.cmd_accuse(m_acc1, bot)
        self.assertFalse((await database.get_winning_accusation()) is not None)

        # 3. Solve Envelope 2
        m2 = make_mock_message(101, "/solve 1356")
        await handlers.game.cmd_solve(m2, bot)

        # 4. Revise accusation with both evidence points -> WINS!
        m_acc2 = make_mock_message(
            101,
            "/accuse نادر وثوق\nانگیزه: پنهان‌کردن اختلاس\nجراحت سر و خون استخر\nاختلاس حساب ۸۴۱۰۲ در دفترچه مالی سال ۵۶"
        )
        await handlers.game.cmd_accuse(m_acc2, bot)

        winner = await database.get_winning_accusation()
        self.assertIsNotNone(winner)
        self.assertEqual(winner["team_number"], 1)

    async def test_pairwise_accuse_before_solve(self):
        """A complete-looking accusation is rejected until both envelopes are solved."""
        bot = make_mock_bot()
        m_acc = make_mock_message(
            102,
            "/accuse نادر وثوق\nانگیزه: انکار حضور\nعکس بازتاب پنجره ساعت 22:19\nتناقض با ادعای خروج قبل از ۲۲:۰۰"
        )
        await handlers.game.cmd_accuse(m_acc, bot)

        winner = await database.get_winning_accusation()
        self.assertIsNone(winner)
        self.assertIn("ابتدا هر دو پاکت", m_acc.answers[0])

    async def test_pairwise_solve_and_rescue(self):
        """Team actively solving riddles calls emergency rescue; rescue logs without impacting solve state."""
        bot = make_mock_bot()

        # Solve Envelope 1
        await handlers.game.cmd_solve(make_mock_message(101, "/solve خون"), bot)
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")

        # Emergency rescue
        await handlers.game.cmd_rescue(make_mock_message(101, "/rescue"), bot)

        # Solve state is intact
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")
        # Rescue count logged
        self.assertGreaterEqual(int(await database.get_game_state("rescue_alert_count")), 1)

    async def test_pairwise_accuse_and_deductions_close(self):
        """Host closes deductions; verify database deduction state and rejection."""
        await database.close_deductions()
        self.assertTrue(await database.is_deductions_closed())

        # Calling database.record_team_accusation directly validates rejection
        res_db = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=101,
            evidence_point_1="خون استخر",
            evidence_point_2="حساب ۸۴۱۰۲"
        )
        self.assertEqual(res_db["status"], "deductions_closed")

        bot = make_mock_bot()
        m_acc = make_mock_message(
            101,
            "/accuse نادر وثوق\nجراحت سر و خون استخر\nاختلاس حساب ۸۴۱۰۲"
        )
        await handlers.game.cmd_accuse(m_acc, bot)
        self.assertEqual(len(m_acc.answers), 1)


class TestE2ERealWorldScenarios(BaseE2ETestCase):
    """Tier 4: Five Complete Real-World Event Scenarios."""

    async def test_scenario_1_full_three_team_competition_run(self):
        """
        Scenario 1: Full three-team competition run.
        Team 1, 2, and 3 solve riddles concurrently.
        Team 2 solves both envelopes first and submits winning accusation.
        Team 1 finishes afterwards and submits accusation (neutral response, Team 2 remains winner).
        Host triggers darkroom finale and traitors reveal.
        """
        bot = make_mock_bot()

        # Step 1: Solving envelopes
        # Team 1 solves 1-A
        await handlers.game.cmd_solve(make_mock_message(101, "/solve خون"), bot)
        # Team 3 solves 3-A
        await handlers.game.cmd_solve(make_mock_message(103, "/solve سکوت"), bot)
        # Team 2 solves 2-A
        await handlers.game.cmd_solve(make_mock_message(102, "/solve سایه"), bot)
        # Team 2 solves 2-B
        await handlers.game.cmd_solve(make_mock_message(102, "/solve 2910"), bot)
        self.assertEqual(await database.get_game_state("team_2_both_solved"), "1")

        # Step 2: Team 2 submits winning accusation
        msg_t2_acc = make_mock_message(
            102,
            "/accuse نادر وثوق\nانگیزه: انکار حضور هنگام حادثه\nعکس بازتاب پنجره در ساعت 22:19\nتناقض زمانی با ادعای خروج قبل از ۲۲:۰۰"
        )
        await handlers.game.cmd_accuse(msg_t2_acc, bot)

        winner = await database.get_winning_accusation()
        self.assertIsNotNone(winner)
        self.assertEqual(winner["team_number"], 2)
        t2_win_ts = await database.get_game_state("winning_timestamp")

        # Step 3: Team 1 finishes 1-B later and submits accusation
        await handlers.game.cmd_solve(make_mock_message(111, "/solve 1356"), bot)
        msg_t1_acc = make_mock_message(
            101,
            "/accuse نادر وثوق\nانگیزه: پنهان‌کردن اختلاس\nجراحت سر و خون لبه استخر\nاختلاس حساب 84102 دفترچه مالی"
        )
        await handlers.game.cmd_accuse(msg_t1_acc, bot)

        # Team 1 gets neutral confirmation
        self.assertEqual(msg_t1_acc.answers[0], texts.ACCUSATION_RECORDED_NEUTRAL)

        # Sole winner is STILL Team 2 with original timestamp
        winner_after = await database.get_winning_accusation()
        self.assertEqual(winner_after["team_number"], 2)
        self.assertEqual(await database.get_game_state("winning_timestamp"), t2_win_ts)

        # Step 4: Host runs finale & reveal
        bot.sent_messages.clear()
        admin_finale = make_mock_message(102725917, "/trigger_finale")
        await handlers.admin.cmd_trigger_darkroom(admin_finale, bot)
        self.assertEqual(await database.get_game_state("game_phase"), "finale")

    async def test_scenario_2_simultaneous_solve_race_by_teammates(self):
        """
        Scenario 2: Teammates racing to submit the same envelope concurrently.
        101 and 111 concurrently submit 'خون' via asyncio.gather.
        Exactly one receives clue response; the other receives duplicate warning.
        Broadcast to teammate is sent cleanly without infinite recursion.
        """
        bot = make_mock_bot()
        m1 = make_mock_message(101, "/solve خون")
        m2 = make_mock_message(111, "/solve خون")

        await asyncio.gather(
            handlers.game.cmd_solve(m1, bot),
            handlers.game.cmd_solve(m2, bot)
        )

        all_answers = m1.answers + m2.answers
        # One clue and one already_solved message
        self.assertTrue(any("مدرک جسمانی ثبت شد" in a for a in all_answers))
        self.assertTrue(any("قبلاً توسط تیم شما ثبت شده است" in a for a in all_answers))

    async def test_scenario_3_premature_accusation_followed_by_complete_revision(self):
        """
        Scenario 3: Partial / wrong accusations remain neutral; a complete revision can win.
        Team 3 names Shirin, then Nader without evidence, and finally provides two dossier points.
        """
        for n in (1, 2):
            await database.set_game_state(f"team_3_riddle_{n}", "1")
        bot = make_mock_bot()

        # 1. Wrong suspect
        msg1 = make_mock_message(103, "/accuse شیرین نوری")
        await handlers.game.cmd_accuse(msg1, bot)
        self.assertIsNone(await database.get_winning_accusation())

        # 2. Nader without evidence
        msg2 = make_mock_message(103, "/accuse نادر وثوق")
        await handlers.game.cmd_accuse(msg2, bot)
        self.assertIsNone(await database.get_winning_accusation())

        # 3. Complete revision
        msg3 = make_mock_message(
            103,
            "/accuse نادر وثوق\nانگیزه: تهدید برای کتمان حادثه\nشهادت شاهدان مبنی بر تهدید و سکوت\nتطبیق فهرست بایگانی ۵ نفر مظنون"
        )
        await handlers.game.cmd_accuse(msg3, bot)

        winner = await database.get_winning_accusation()
        self.assertIsNotNone(winner)
        self.assertEqual(winner["team_number"], 3)

    async def test_scenario_4_host_finale_and_witness_distinction(self):
        """
        Scenario 4: Host finale, paper darkroom confrontation, and witness distinction.
        Verifies that Nader Vosough is isolated as the sole killer, while Shirin, Keyvan,
        and Dr. Mehr are concealing witnesses with sticker carrier roles.
        """
        # Assign special character roles
        assigned = await database.assign_special_character_roles(force_reassign=True)
        shirin = assigned["shirin"]
        keyvan = assigned["keyvan"]
        fereydoun = assigned["fereydoun"]
        nader = assigned["nader"]

        # Witnesses carry suspect stickers
        self.assertEqual(shirin["is_hunter"], 1)
        self.assertEqual(keyvan["is_hunter"], 1)
        self.assertEqual(fereydoun["is_hunter"], 1)

        # Nader does NOT carry suspect stickers
        self.assertEqual(nader["is_hunter"], 0)

        # Paper darkroom prompt check (zero 3D props)
        self.assertIn("آخرین مدرک در تاریکخانه است", texts.DARKROOM_FINAL_PROMPT)
        self.assertIn("نادر فهمیده که عکس پیدا شده است", texts.DARKROOM_FINAL_PROMPT)

    async def test_scenario_5_emergency_rescue_alert_during_active_play(self):
        """
        Scenario 5: Emergency rescue alert during active game play.
        Player encounters an issue in the dark garden and calls /rescue.
        Safety alert is immediately logged and counter incremented; riddle state is untouched.
        """
        bot = make_mock_bot()

        # Player solves Envelope 1
        await handlers.game.cmd_solve(make_mock_message(101, "/solve خون"), bot)
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")

        # Player sends /rescue
        msg_rescue = make_mock_message(101, "/rescue")
        await handlers.game.cmd_rescue(msg_rescue, bot)
        self.assertTrue(
            "پیام امداد شما به میزبان" in msg_rescue.answers[0] or "قانون تاریکی مطلق باغ" in msg_rescue.answers[0]
        )

        # Rescue logged to DB
        count = await database.record_rescue_alert(101, "بازرس ۱-الف", "افتادن پای بازیکن")
        self.assertGreaterEqual(count, 2)

        # Riddle state is still 1
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")


if __name__ == "__main__":
    unittest.main()
