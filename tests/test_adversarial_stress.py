"""
Adversarial Stress and Concurrency Test Suite for Bāgh-e Sarhang Murder Mystery.
Created by Empirical Challenger (teamwork_challenger_1).

Covers 5 Critical Adversarial Dimensions:
1. Concurrent /solve calls from teammates (race conditions, clue progression, duplicate prevention).
2. Concurrent /accuse calls from multiple teams (deterministic first-winner, timestamp preservation on revisions).
3. Cross-team code submissions (strict rejection, zero leaks, digit collision prevention).
4. Dossier validation permutations (subtle name variations, other-suspect combinations, 1 vs 2 evidence points, cross-dossier poisoning).
5. Progressive hints delivery across teams and levels (access control, Persian digit parsing, recipient isolation, boundary validation).
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
    msg.from_user.full_name = f"User {user_id}"
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


class BaseAdversarialTestCase(unittest.IsolatedAsyncioTestCase):
    """Base fixture providing an isolated, Windows-safe temporary database for each stress test."""

    async def asyncSetUp(self):
        self.unique_id = uuid.uuid4().hex[:10]
        self.test_db_file = Path(f"test_adv_{self.unique_id}_{self._testMethodName}.db")
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.test_db_file

        self.orig_admin_id = config.ADMIN_USER_ID
        config.ADMIN_USER_ID = 999000111
        database._riddle_lock = asyncio.Lock()

        await database.init_db()

        # Seed 10 investigators for Team 1 (IDs 101-110)
        # Seed 5 investigators for Team 2 (IDs 201-205)
        # Seed 5 investigators for Team 3 (IDs 301-305)
        # Seed 2 blondes (IDs 401-402)
        async with aiosqlite.connect(self.test_db_file) as db:
            team1_tuples = [
                (100 + i, f"inv_1_{i}", f"بازرس تیم ۱ شماره {i}", "role_player", 1, "تیم ۱ (خون)")
                for i in range(1, 11)
            ]
            team2_tuples = [
                (200 + i, f"inv_2_{i}", f"بازرس تیم ۲ شماره {i}", "role_player", 2, "تیم ۲ (سایه)")
                for i in range(1, 6)
            ]
            team3_tuples = [
                (300 + i, f"inv_3_{i}", f"بازرس تیم ۳ شماره {i}", "role_player", 3, "تیم ۳ (سکوت)")
                for i in range(1, 6)
            ]
            blondes = [
                (401, "blonde_1", "بلوند اول", "role_blonde", None, None),
                (402, "blonde_2", "بلوند دوم", "role_blonde", None, None),
            ]
            all_guests = team1_tuples + team2_tuples + team3_tuples + blondes
            await db.executemany("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, all_guests)
            await db.commit()
        await database.set_game_state("game_phase", "midnight_investigation")

    async def asyncTearDown(self):
        database.DB_PATH = self.orig_db_path
        config.ADMIN_USER_ID = self.orig_admin_id
        await asyncio.sleep(0.01)
        if self.test_db_file.exists():
            for _ in range(5):
                try:
                    os.remove(self.test_db_file)
                    break
                except Exception:
                    await asyncio.sleep(0.05)


class TestAdversarialConcurrentSolve(BaseAdversarialTestCase):
    """Stress testing concurrent solve submissions from teammates."""

    async def test_high_concurrency_same_riddle_ten_teammates(self):
        """10 teammates concurrently submit the exact same solve answer via asyncio.gather."""
        bot = make_mock_bot()
        messages = [
            make_mock_message(100 + i, "/solve خون")
            for i in range(1, 11)
        ]

        # Launch all 10 simultaneously
        tasks = [handlers.game.cmd_solve(m, bot) for m in messages]
        await asyncio.gather(*tasks)

        all_answers = []
        for m in messages:
            all_answers.extend(m.answers)

        # Check answers: exactly 1 must receive the clue text, and exactly 9 must receive already_solved
        clue_count = sum(1 for a in all_answers if "مدرک جسمانی ثبت شد" in a)
        already_count = sum(1 for a in all_answers if "قبلاً توسط تیم شما ثبت شده است" in a)

        self.assertEqual(clue_count, 1, f"Expected exactly 1 clue delivery, got {clue_count}")
        self.assertEqual(already_count, 9, f"Expected 9 already_solved notices, got {already_count}")

        # Find which teammate received the first-time solve
        solver_id = next(m.from_user.id for m in messages if any("مدرک جسمانی ثبت شد" in a for a in m.answers))

        # Check teammate broadcast: exactly one broadcast was dispatched (to the other 9 teammates)
        broadcast_recipients = [chat_id for chat_id, _ in bot.sent_messages]
        self.assertEqual(len(broadcast_recipients), 9)
        self.assertEqual(set(broadcast_recipients), {100 + i for i in range(1, 11)} - {solver_id})

        # Check DB state
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")
        self.assertEqual(await database.get_game_state("team_1_riddle_2", "0"), "0")

    async def test_simultaneous_dual_envelope_solve_race(self):
        """Teammate 101 solves 1-A ('خون') and Teammate 102 solves 1-B ('1356') simultaneously."""
        bot = make_mock_bot()
        m1 = make_mock_message(101, "/solve خون")
        m2 = make_mock_message(102, "/solve 1356")

        await asyncio.gather(
            handlers.game.cmd_solve(m1, bot),
            handlers.game.cmd_solve(m2, bot)
        )

        # Both envelopes must be marked solved in DB
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")
        self.assertEqual(await database.get_game_state("team_1_riddle_2"), "1")
        self.assertEqual(await database.get_game_state("team_1_both_solved"), "1")

        # Exactly ONE completion notification "هر دو مدرک تیم شما با موفقیت ثبت شد" must be dispatched
        all_bot_texts = [text for _, text in bot.sent_messages]
        completion_dispatches = [t for t in all_bot_texts if "هر دو مدرک تیم شما با موفقیت ثبت شد" in t]
        # Sent to 10 teammates once
        self.assertEqual(len(completion_dispatches), 10)

    async def test_spamming_solve_after_both_solved(self):
        """Multiple teammates flood /solve after both envelopes are solved: all safely rejected without errors."""
        # Pre-solve both
        await database.set_game_state("team_1_riddle_1", "1")
        await database.set_game_state("team_1_riddle_2", "1")
        await database.set_game_state("team_1_both_solved", "1")

        bot = make_mock_bot()
        messages = [
            make_mock_message(100 + i, "/solve 1356")
            for i in range(1, 11)
        ]
        await asyncio.gather(*[handlers.game.cmd_solve(m, bot) for m in messages])

        for m in messages:
            self.assertEqual(len(m.answers), 1)
            self.assertIn("قبلاً هر دو مدرک را ثبت کرده است", m.answers[0])

        # Zero new broadcasts sent
        self.assertEqual(len(bot.sent_messages), 0)


class TestAdversarialConcurrentAccuse(BaseAdversarialTestCase):
    """Stress testing concurrent accusations and revision timestamp integrity."""

    async def test_simultaneous_three_team_winning_accusations(self):
        """Team 1, Team 2, and Team 3 all submit valid, fully supported accusations at the exact same instant."""
        for team_num in (1, 2, 3):
            await database.set_game_state(f"team_{team_num}_riddle_1", "1")
            await database.set_game_state(f"team_{team_num}_riddle_2", "1")
        # Team 1: 101, Team 2: 201, Team 3: 301
        payload_t1 = (
            "/accuse نادر وثوق\n"
            "انگیزه: اختلاس مالی از حساب ۸۴۱۰۲ سال ۱۳۵۶\n"
            "مدرک اول: جراحت سر و خون لبه استخر پیش از ورود به آب\n"
            "مدرک دوم: دفترچه مالی و حواله بانکی ۸۴۱۰۲"
        )
        payload_t2 = (
            "/accuse نادر وثوق\n"
            "انگیزه: حضور مخفیانه در باغ هنگام حادثه\n"
            "مدرک اول: بازتاب سایه فرد در شیشه پنجره در عکس ثبت‌شده\n"
            "مدرک دوم: لاگ عکاسی ساعت ۲۲:۱۹ و تناقض با ادعای خروج قبل از ۲۲:۰۰"
        )
        payload_t3 = (
            "/accuse نادر وثوق\n"
            "انگیزه: تهدید شاهدان برای کتمان نزاع کنار استخر\n"
            "مدرک اول: شهادت مستقیم شاهدان عینی مبنی بر تهدید و سکوت\n"
            "مدرک دوم: فهرست بایگانی ۵ نفر مظنون که تنها نادر را منزوی می‌سازد"
        )

        bot = make_mock_bot()
        m1 = make_mock_message(101, payload_t1)
        m2 = make_mock_message(201, payload_t2)
        m3 = make_mock_message(301, payload_t3)

        await asyncio.gather(
            handlers.game.cmd_accuse(m1, bot),
            handlers.game.cmd_accuse(m2, bot),
            handlers.game.cmd_accuse(m3, bot)
        )

        # Verify exactly ONE winner was assigned in database
        winner = await database.get_winning_accusation()
        self.assertIsNotNone(winner)
        winning_team = winner["team_number"]
        self.assertIn(winning_team, [1, 2, 3])

        # Verify game state
        recorded_winner_team = await database.get_game_state("game_winner_team")
        self.assertEqual(str(winning_team), recorded_winner_team)

        # In competitive murder mystery (R5), ALL teams receive ACCUSATION_RECORDED_NEUTRAL
        # so that players never learn whether they won or whether their deduction was correct before 02:00
        for m in (m1, m2, m3):
            self.assertEqual(m.answers[0], texts.ACCUSATION_RECORDED_NEUTRAL)

        # Check that Admin received exactly ONE private alert for the first winner
        admin_messages = [text for chat_id, text in bot.sent_messages if chat_id == config.ADMIN_USER_ID]
        self.assertEqual(len(admin_messages), 1)
        self.assertIn("ثبت نخستین اتهام صحیح", admin_messages[0])
        self.assertIn(f"تیم {winning_team}", admin_messages[0])

    async def test_non_winning_team_cannot_overwrite_winner_on_revision(self):
        """Team 2 wins first. Team 1 submits 5 rapid revisions: winner and timestamp remain intact."""
        for team_num in (1, 2):
            await database.set_game_state(f"team_{team_num}_riddle_1", "1")
            await database.set_game_state(f"team_{team_num}_riddle_2", "1")
        # Step 1: Team 2 wins
        bot = make_mock_bot()
        m_t2 = make_mock_message(
            201,
            "/accuse نادر وثوق\nتناقض با ادعای خروج پیش از ۲۲:۰۰\nسایه در شیشه پنجره ساعت 22:19\nتناقض زمانی با ادعای خروج قبل از ۲۲"
        )
        await handlers.game.cmd_accuse(m_t2, bot)
        initial_win_ts = await database.get_game_state("winning_timestamp")
        initial_winner = await database.get_game_state("game_winner_team")
        self.assertEqual(initial_winner, "2")

        # Step 2: Team 1 submits 5 rapid revisions
        for i in range(1, 6):
            m_t1 = make_mock_message(
                101,
                f"/accuse نادر وثوق\nانگیزه: پنهان‌کردن اختلاس\nجراحت سر و خون استخر\nحساب 84102 اختلاس نسخه {i}"
            )
            await handlers.game.cmd_accuse(m_t1, bot)
            self.assertEqual(m_t1.answers[0], texts.ACCUSATION_RECORDED_NEUTRAL)

        # Verify winner is STILL Team 2 and timestamp is completely unaltered
        self.assertEqual(await database.get_game_state("game_winner_team"), "2")
        self.assertEqual(await database.get_game_state("winning_timestamp"), initial_win_ts)

    async def test_winning_team_revision_preserves_original_timestamp(self):
        """Team 1 wins. Team 1 revises 3 times: winner status preserved, original timestamp never modified."""
        await database.set_game_state("team_1_riddle_1", "1")
        await database.set_game_state("team_1_riddle_2", "1")
        bot = make_mock_bot()
        m1 = make_mock_message(
            101,
            "/accuse نادر وثوق\nانگیزه: پنهان‌کردن اختلاس\nجراحت سر و خون استخر\nحساب 84102 اختلاس"
        )
        await handlers.game.cmd_accuse(m1, bot)
        orig_win_ts = await database.get_game_state("winning_timestamp")
        self.assertIsNotNone(orig_win_ts)

        await asyncio.sleep(0.05)

        # 3 revisions by Team 1
        for i in range(1, 4):
            m_rev = make_mock_message(
                101,
                f"/accuse نادر وثوق\nانگیزه: پنهان‌کردن اختلاس\nجراحت سر و خون استخر ویرایش {i}\nحساب 84102 اختلاس"
            )
            await handlers.game.cmd_accuse(m_rev, bot)
            # Timestamp must NEVER change
            curr_ts = await database.get_game_state("winning_timestamp")
            self.assertEqual(curr_ts, orig_win_ts)

        # Verify original winning record is preserved
        winner = await database.get_winning_accusation()
        self.assertEqual(winner["team_number"], 1)
        self.assertEqual(winner["is_winner"], 1)

        # Verify all 4 submissions were stored with incrementing revision counts
        async with aiosqlite.connect(self.test_db_file) as db:
            cursor = await db.execute("SELECT revision_count, is_winner FROM team_accusations WHERE team_number = 1 ORDER BY id ASC")
            rows = await cursor.fetchall()
            self.assertEqual(len(rows), 4)
            self.assertEqual([r[0] for r in rows], [1, 2, 3, 4])
            # All revisions by the winning team maintain is_winner = 1
            self.assertTrue(all(r[1] == 1 for r in rows))


class TestAdversarialCrossTeamCodeSubmissions(BaseAdversarialTestCase):
    """Stress testing rejection of competitor team codes with zero leaks."""

    async def test_exhaustive_cross_team_code_rejections(self):
        """Every team submits all keys of other teams: must return other_team_riddle and OTHER_TEAM_CODE_ALERT."""
        # Key map:
        # Team 1: خون, 1356
        # Team 2: سایه, 2910
        # Team 3: سکوت, 5
        # Team 4: آینه, 2400
        test_cases = [
            # (Submitting User ID, Submitting Team, Code Submitted, Belongs to Team)
            (101, 1, "سایه", 2),
            (101, 1, "shadow", 2),
            (101, 1, "2910", 2),
            (101, 1, "۲۹۱۰", 2),
            (101, 1, "سکوت", 3),
            (101, 1, "silence", 3),
            (101, 1, "5", 3),
            (101, 1, "پنج", 3),
            (101, 1, "۵", 3),
            (201, 2, "خون", 1),
            (201, 2, "blood", 1),
            (201, 2, "1356", 1),
            (201, 2, "۱۳۵۶", 1),
            (201, 2, "سکوت", 3),
            (201, 2, "5", 3),
            (301, 3, "خون", 1),
            (301, 3, "1356", 1),
            (301, 3, "سایه", 2),
            (301, 3, "2910", 2),
        ]

        for user_id, team_num, code, other_team in test_cases:
            res = await database.check_team_riddle(user_id, code)
            self.assertEqual(
                res["status"],
                "other_team_riddle",
                f"User in Team {team_num} submitting '{code}' (Team {other_team}) was not rejected as other_team_riddle!"
            )
            # Ensure response text matches canonical OTHER_TEAM_CODE_ALERT
            self.assertEqual(res["response_text"], game.OTHER_TEAM_CODE_ALERT)

            # Ensure zero information leakage in response text:
            # Does NOT contain other team's number or name
            self.assertNotIn(str(other_team), res["response_text"])
            self.assertNotIn("تیم ۱", res["response_text"])
            self.assertNotIn("تیم ۲", res["response_text"])
            self.assertNotIn("تیم ۳", res["response_text"])
            self.assertNotIn(code, res["response_text"])

    async def test_digit_substring_collision_prevention(self):
        """Ensure digit '5' (Team 3) does NOT trigger other_team_riddle when Team 1 submits '1356'."""
        # Team 1 solves '1356' containing digit '5'
        res1 = await database.check_team_riddle(101, "1356")
        self.assertEqual(res1["status"], "riddle_solved")
        self.assertEqual(res1["riddle_num"], 2)

        # Team 3 solves '5'
        res3 = await database.check_team_riddle(301, "5")
        self.assertEqual(res3["status"], "riddle_solved")
        self.assertEqual(res3["riddle_num"], 2)


class TestAdversarialDossierValidationPermutations(BaseAdversarialTestCase):
    """Stress testing suspect variations, multi-suspect traps, and partial evidence rubrics."""

    def test_suspect_name_subtle_variations(self):
        """Test valid aliases and subtle naming variations for Nader Vosough."""
        valid_variations = [
            "نادر وثوق",
            "نادر",
            "وثوق",
            "nader vosough",
            "Nader Vosough",
            "NADER VOSOUGH",
            "آقای نادر وثوق",
            "نادر وثوق (مدیر امور مالی)",
            "نادر وثوقی",
            "  نادر وثوق  ",
            "«نادر وثوق»",
        ]
        for name in valid_variations:
            res = game.evaluate_structured_accusation(
                team_number=1,
                suspect_name=name,
                motive_opportunity="اختلاس حساب ۸۴۱۰۲",
                evidence_point_1="خون استخر و ضربه سر",
                evidence_point_2="دفترچه مالی و حساب ۸۴۱۰۲"
            )
            self.assertTrue(res["is_correct"], f"Expected valid for suspect variation '{name}'")

    def test_naming_witnesses_or_other_suspects_fails(self):
        """Naming witnesses or other suspects (even alongside Nader) must strictly fail."""
        invalid_suspects = [
            "شیرین نوری",
            "شیرین",
            "کیوان رستگار",
            "کیوان",
            "دکتر فریدون مهر",
            "دکتر مهر",
            "سرهنگ بهرام فرهمند",
            "سرهنگ",
            "آرش",
            "shirin",
            "keyvan",
            "fereydoun",
            "نادر وثوق و شیرین نوری",
            "نادر وثوق یا کیوان رستگار",
            "نادر و فریدون مهر",
            "شیرین نوری و نادر وثوق",
        ]
        for name in invalid_suspects:
            res = game.evaluate_structured_accusation(
                team_number=1,
                suspect_name=name,
                motive_opportunity="اختلاس حساب ۸۴۱۰۲",
                evidence_point_1="خون استخر و ضربه سر",
                evidence_point_2="دفترچه مالی و حساب ۸۴۱۰۲"
            )
            self.assertFalse(res["is_correct"], f"Expected failure for suspect '{name}'")

    def test_evidence_permutations_1_vs_2_valid_points(self):
        """Testing exact 1 valid point vs 2 valid points across all three teams."""
        # Team 1: Point 1 = Pool blood / head injury; Point 2 = Embezzlement / account 84102
        # Case 1A: Only Point 1
        res1_only_p1 = game.evaluate_structured_accusation(
            team_number=1,
            suspect_name="نادر وثوق",
            motive_opportunity="حضور در باغ",
            evidence_point_1="ضربه به سر و خون لبه استخر",
            evidence_point_2="هوای سرد باغ"
        )
        self.assertEqual(len(res1_only_p1["matched_points"]), 1)
        self.assertFalse(res1_only_p1["is_correct"])

        # Case 1B: Only Point 2
        res1_only_p2 = game.evaluate_structured_accusation(
            team_number=1,
            suspect_name="نادر وثوق",
            motive_opportunity="اختلاس حساب ۸۴۱۰۲",
            evidence_point_1="دفتر مالی و حواله بانکی",
            evidence_point_2="عدم تطابق ارقام"
        )
        self.assertEqual(len(res1_only_p2["matched_points"]), 1)
        self.assertFalse(res1_only_p2["is_correct"])

        # Case 1C: Both Points
        res1_both = game.evaluate_structured_accusation(
            team_number=1,
            suspect_name="نادر وثوق",
            motive_opportunity="انگیزه مالی",
            evidence_point_1="ضربه سر و خون استخر",
            evidence_point_2="اختلاس حساب ۸۴۱۰۲"
        )
        self.assertEqual(len(res1_both["matched_points"]), 2)
        self.assertTrue(res1_both["is_correct"])

        # Team 2: Point 1 = Window reflection 22:19; Point 2 = Departure timeline contradiction
        res2_only_p1 = game.evaluate_structured_accusation(
            team_number=2,
            suspect_name="نادر وثوق",
            motive_opportunity="انگیزه شخصی",
            evidence_point_1="عکس بازتاب سایه در شیشه پنجره ۲۲:۱۹",
            evidence_point_2="لباس تیره"
        )
        self.assertEqual(len(res2_only_p1["matched_points"]), 1)
        self.assertFalse(res2_only_p1["is_correct"])

        res2_both = game.evaluate_structured_accusation(
            team_number=2,
            suspect_name="نادر وثوق",
            motive_opportunity="انگیزه قتل",
            evidence_point_1="عکس بازتاب سایه در پنجره ۲۲:۱۹",
            evidence_point_2="تناقض زمانی و ادعای خروج قبل از ۲۲:۰۰"
        )
        self.assertEqual(len(res2_both["matched_points"]), 2)
        self.assertTrue(res2_both["is_correct"])

        # Team 3: Point 1 = Witness statements/threat; Point 2 = 5 suspects archive index
        res3_only_p1 = game.evaluate_structured_accusation(
            team_number=3,
            suspect_name="نادر وثوق",
            motive_opportunity="انگیزه پنهان‌کاری",
            evidence_point_1="شهادت شاهدان عینی مبنی بر تهدید و سکوت",
            evidence_point_2="ترس شاهدان"
        )
        self.assertEqual(len(res3_only_p1["matched_points"]), 1)
        self.assertFalse(res3_only_p1["is_correct"])

        res3_both = game.evaluate_structured_accusation(
            team_number=3,
            suspect_name="نادر وثوق",
            motive_opportunity="تهدید به قتل",
            evidence_point_1="شهادت شاهدان عینی شیرین و کیوان",
            evidence_point_2="تطبیق فهرست بایگانی ۵ نفر مظنون"
        )
        self.assertEqual(len(res3_both["matched_points"]), 2)
        self.assertTrue(res3_both["is_correct"])

    def test_cross_dossier_evidence_poisoning(self):
        """Team 1 attempting to use Team 2's or Team 3's evidence does not match Team 1 rubric."""
        res = game.evaluate_structured_accusation(
            team_number=1,
            suspect_name="نادر وثوق",
            motive_opportunity="سایه پنجره در ساعت 22:19",
            evidence_point_1="شهادت شیرین نوری",
            evidence_point_2="فهرست بایگانی ۵ مظنون"
        )
        # 0 points matched for Team 1
        self.assertEqual(len(res["matched_points"]), 0)
        self.assertFalse(res["is_correct"])


class TestAdversarialProgressiveHints(BaseAdversarialTestCase):
    """Stress testing hint delivery, access control, Persian digits, and team isolation."""

    async def test_hint_command_non_admin_rejected(self):
        """Non-admin sending /hint command is rejected."""
        bot = make_mock_bot()
        m = make_mock_message(101, "/hint 1 1")  # Investigator 101 is not admin
        await handlers.admin.cmd_hint(m, bot)
        self.assertEqual(m.answers[0], "⛔️ دسترسی غیرمجاز.")
        self.assertEqual(len(bot.sent_messages), 0)

    async def test_hint_command_out_of_bounds_validation(self):
        """Admin sending invalid team numbers or levels receives clear validation errors."""
        bot = make_mock_bot()
        admin_id = config.ADMIN_USER_ID

        invalid_calls = [
            ("/hint", "فرمت صحیح دستور"),
            ("/hint 0 1", "شماره تیم باید ۱، ۲ یا ۳ باشد"),
            ("/hint 4 1", "شماره تیم باید ۱، ۲ یا ۳ باشد"),
            ("/hint 1 0", "سطح راهنمایی باید ۱، ۲ یا ۳ باشد"),
            ("/hint 1 4", "سطح راهنمایی باید ۱، ۲ یا ۳ باشد"),
            ("/hint abc def", "شماره تیم و سطح باید عدد باشند"),
        ]
        for cmd_text, expected_err in invalid_calls:
            m = make_mock_message(admin_id, cmd_text)
            await handlers.admin.cmd_hint(m, bot)
            self.assertTrue(any(expected_err in a for a in m.answers), f"Failed for '{cmd_text}'")

    async def test_hint_persian_digits_and_strict_recipient_isolation(self):
        """Admin sending /hint with Persian digits: delivered strictly to target team, zero leaks to competitors."""
        bot = make_mock_bot()
        admin_id = config.ADMIN_USER_ID

        # Deliver Hint Level 2 to Team 2 using Persian digits: /hint ۲ ۲
        m = make_mock_message(admin_id, "/hint ۲ ۲")
        await handlers.admin.cmd_hint(m, bot)

        # Check that admin received confirmation
        self.assertTrue(any("راهنمایی سطح 2 با موفقیت برای 5 عضو تیم 2 ارسال شد" in a for a in m.answers))

        # Check recipients: ONLY Team 2 members (201-205) received messages
        recipients = [chat_id for chat_id, _ in bot.sent_messages]
        self.assertEqual(len(recipients), 5)
        self.assertEqual(set(recipients), {201, 202, 203, 204, 205})

        # Ensure NO Team 1 (101-110) or Team 3 (301-305) or blondes (401-402) received anything
        self.assertTrue(set(recipients).isdisjoint({100 + i for i in range(1, 11)}))
        self.assertTrue(set(recipients).isdisjoint({300 + i for i in range(1, 6)}))
        self.assertTrue(set(recipients).isdisjoint({401, 402}))

        # Verify hint text matches Team 2 Level 2 and does NOT leak Team 1 or Team 3 answers
        hint_text = bot.sent_messages[0][1]
        self.assertIn("۲۲:۱۹", hint_text)
        self.assertNotIn("خون", hint_text)
        self.assertNotIn("1356", hint_text)
        self.assertNotIn("سکوت", hint_text)
        self.assertNotIn("۸۴۱۰۲", hint_text)

    async def test_all_nine_progressive_hints_content_integrity(self):
        """Verify all 9 progressive hints exist and contain expected progressive guidance."""
        persian_nums = {1: "۱", 2: "۲", 3: "۳"}
        for team_num in [1, 2, 3]:
            for level in [1, 2, 3]:
                hint = game.PROGRESSIVE_HINTS.get(team_num, {}).get(level)
                self.assertIsNotNone(hint, f"Missing hint for Team {team_num} Level {level}")
                p_digit = persian_nums[level]
                self.assertIn(f"راهنمایی مرحله {p_digit}", hint)
                if level == 3:
                    self.assertIn("راهنمای مستقیم میزبان", hint)


if __name__ == "__main__":
    unittest.main()
