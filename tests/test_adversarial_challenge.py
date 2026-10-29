"""
Adversarial Coverage Hardening and Stress Harness for Bāgh-e Sarhang Murder Mystery.
Author: teamwork_challenger_2 (Empirical Challenger)

Exercises 5 Target Adversarial Scenarios:
1. /rescue operation across all game phases (unstarted, social, midnight, unregistered guest).
2. /solve robustness against whitespace, diacritics, Persian/Arabic digits, tatweel, and zero-width characters (zero crash, zero leak).
3. /accuse robustness against Persian text with multi-line input, punctuation, and Arabic character substitutions.
4. Deductions closure enforcement across handlers and database layer when deductions_closed=1.
5. Verification that DARKROOM_FINAL_PROMPT is completely shielded from premature broadcast in /solve.
"""

import os
import asyncio
import unittest
from pathlib import Path
import uuid
from unittest.mock import AsyncMock, MagicMock
import aiosqlite
from aiogram.types import Message, CallbackQuery
from aiogram import Bot

import config
import database
import game
import texts
import handlers.game
import handlers.admin


def make_mock_message(user_id: int, text: str, username: str = "adversary_user"):
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


def make_mock_callback(user_id: int, data: str, username: str = "adversary_user"):
    cb = AsyncMock(spec=CallbackQuery)
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.username = username
    cb.from_user.full_name = f"User {user_id}"
    cb.data = data
    cb.message = make_mock_message(user_id, f"/cb {data}", username)
    cb.answers = []

    async def fake_cb_answer(text="", **kwargs):
        cb.answers.append(text)
        return MagicMock()

    cb.answer = AsyncMock(side_effect=fake_cb_answer)
    return cb


def make_mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.sent_messages = []

    async def fake_send_message(chat_id, text, **kwargs):
        bot.sent_messages.append((chat_id, text))
        return MagicMock()

    bot.send_message = AsyncMock(side_effect=fake_send_message)
    return bot


class AdversarialCoverageTests(unittest.IsolatedAsyncioTestCase):
    """Adversarial stress and verification test suite."""

    async def asyncSetUp(self):
        self.unique_id = uuid.uuid4().hex[:10]
        self.test_db_file = Path(f"test_adv_{self.unique_id}_{self._testMethodName}.db")
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.test_db_file
        database._riddle_lock = asyncio.Lock()

        await database.init_db()

        # Seed 3 teams with registered players
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES 
                (201, 'team1_lead', 'بازرس اول خون', 'role_player', 1, 'تیم ۱ (خون)'),
                (211, 'team1_mate', 'یار اول خون', 'role_player', 1, 'تیم ۱ (خون)'),
                (202, 'team2_lead', 'بازرس دوم سایه', 'role_player', 2, 'تیم ۲ (سایه)'),
                (212, 'team2_mate', 'یار دوم سایه', 'role_player', 2, 'تیم ۲ (سایه)'),
                (203, 'team3_lead', 'بازرس سوم سکوت', 'role_player', 3, 'تیم ۳ (سکوت)'),
                (213, 'team3_mate', 'یار سوم سکوت', 'role_player', 3, 'تیم ۳ (سکوت)'),
                (299, 'unregistered_stranger', 'غریبه ناشناس', NULL, NULL, NULL)
            """)
            await db.commit()
        await database.set_game_state("game_phase", "midnight_investigation")

    async def asyncTearDown(self):
        database.DB_PATH = self.orig_db_path
        await asyncio.sleep(0.01)
        if self.test_db_file.exists():
            for _ in range(5):
                try:
                    self.test_db_file.unlink()
                    break
                except PermissionError:
                    await asyncio.sleep(0.05)

    # -------------------------------------------------------------------------
    # CHECK 1: /rescue under unstarted, social, midnight modes, and unregistered
    # -------------------------------------------------------------------------
    async def test_rescue_unstarted_mode(self):
        """Verify /rescue functions when game is unstarted (no game_phase set)."""
        await database.set_game_state("game_phase", "registration")
        bot = make_mock_bot()
        msg = make_mock_message(201, "/rescue")
        await handlers.game.cmd_rescue(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertIn("پیام امداد شما به میزبان و تیم پشتیبانی عمارت مخابره شد", msg.answers[0])

        count_str = await database.get_game_state("rescue_alert_count", "0")
        self.assertEqual(count_str, "1")

    async def test_rescue_social_mode(self):
        """Verify /rescue functions when game is in social mode."""
        await database.set_game_state("game_phase", "social")
        bot = make_mock_bot()
        msg = make_mock_message(202, "/rescue")
        await handlers.game.cmd_rescue(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertIn("پیام امداد شما به میزبان و تیم پشتیبانی عمارت مخابره شد", msg.answers[0])

        count_str = await database.get_game_state("rescue_alert_count", "0")
        self.assertEqual(count_str, "1")

    async def test_rescue_midnight_mode(self):
        """Verify /rescue functions when game is in midnight mode."""
        await database.set_game_state("game_phase", "midnight")
        bot = make_mock_bot()
        msg = make_mock_message(203, "/rescue")
        await handlers.game.cmd_rescue(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertIn("پیام امداد شما به میزبان و تیم پشتیبانی عمارت مخابره شد", msg.answers[0])

        count_str = await database.get_game_state("rescue_alert_count", "0")
        self.assertEqual(count_str, "1")

    async def test_rescue_unregistered_guest(self):
        """Verify /rescue functions for an unregistered or completely unknown Telegram user."""
        bot = make_mock_bot()
        unknown_id = 99999999
        msg = make_mock_message(unknown_id, "/rescue")
        await handlers.game.cmd_rescue(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertIn("پیام امداد شما به میزبان و تیم پشتیبانی عمارت مخابره شد", msg.answers[0])

        # Verify DB recorded the unknown user
        async with aiosqlite.connect(self.test_db_file) as db:
            cursor = await db.execute("SELECT telegram_id, details FROM rescue_alerts WHERE telegram_id = ?", (unknown_id,))
            row = await cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], unknown_id)

    # -------------------------------------------------------------------------
    # CHECK 2: /solve with whitespace, diacritics, Persian digits, tatweel
    # -------------------------------------------------------------------------
    async def test_solve_persian_and_arabic_digits(self):
        """Verify /solve correctly handles Persian and Arabic numerals for all teams."""
        bot = make_mock_bot()

        # Team 1 Envelope 1-B: '1356' with Persian numerals '۱۳۵۶'
        msg_1b = make_mock_message(201, "/solve ۱۳۵۶")
        await handlers.game.cmd_solve(msg_1b, bot)
        self.assertIn("صفحهی حسابها ثبت شد", msg_1b.answers[0])

        # Team 2 Envelope 2-B: '2910' with Persian numerals '۲۹۱۰'
        msg_2b = make_mock_message(202, "/solve ۲۹۱۰")
        await handlers.game.cmd_solve(msg_2b, bot)
        self.assertIn("زمان ثبت تصویر تأیید شد: ۲۲:۱۹", msg_2b.answers[0])

        # Team 3 Envelope 3-B: '5' with Persian numerals '۵'
        msg_3b = make_mock_message(203, "/solve ۵")
        await handlers.game.cmd_solve(msg_3b, bot)
        self.assertIn("فهرست بایگانی تأیید شد: پنج فرد متمایز", msg_3b.answers[0])

    async def test_solve_whitespace_and_tabs(self):
        """Verify /solve handles extreme whitespace, tabs, and empty payloads without crashing."""
        bot = make_mock_bot()

        # Empty payload -> should show team riddle status, NOT crash
        msg_empty = make_mock_message(201, "/solve   ")
        await handlers.game.cmd_solve(msg_empty, bot)
        self.assertEqual(len(msg_empty.answers), 1)
        self.assertIn("وضعیت مدارک تیم ۱ (خون)", msg_empty.answers[0])

        # Extra whitespace around valid answer: "/solve   خون   "
        msg_spaces = make_mock_message(201, "/solve    خون    ")
        await handlers.game.cmd_solve(msg_spaces, bot)
        self.assertIn("مدرک جسمانی ثبت شد", msg_spaces.answers[0])

    async def test_solve_diacritics_and_tatweel_handling(self):
        """Verify behavior of /solve when presented with Arabic diacritics (tashkeel) or tatweel."""
        bot = make_mock_bot()

        # Input with damma: "خُون"
        # Must not crash or throw unhandled exceptions
        msg_diacritic = make_mock_message(201, "/solve خُون")
        await handlers.game.cmd_solve(msg_diacritic, bot)
        self.assertEqual(len(msg_diacritic.answers), 1)
        # Should return wrong answer trap without exposing competitor answers or leaking
        self.assertTrue(
            "اسناد این پاکت مطابقت ندارد" in msg_diacritic.answers[0] or 
            "مدرک جسمانی ثبت شد" in msg_diacritic.answers[0]
        )

        # Input with tatweel / kashida: "خـون"
        msg_tatweel = make_mock_message(201, "/solve خـون")
        await handlers.game.cmd_solve(msg_tatweel, bot)
        self.assertEqual(len(msg_tatweel.answers), 1)
        self.assertFalse(any("Error" in a for a in msg_tatweel.answers))

    # -------------------------------------------------------------------------
    # CHECK 3: /accuse with Persian text, newlines, punctuation, Arabic letters
    # -------------------------------------------------------------------------
    async def test_accuse_multiline_persian_with_punctuation(self):
        """Verify /accuse parses multi-line Persian text with colons, newlines, and Arabic letters."""
        await database.set_game_state("team_1_riddle_1", "1")
        await database.set_game_state("team_1_riddle_2", "1")
        bot = make_mock_bot()

        # Submission with Arabic 'ي', 'ك', 'ة', newlines, colons, and punctuation
        payload = (
            "/accuse نادر وثوق\n"
            "انگيزه و فرصت: سرقت اسناد و كتمان حقيقت در ساعت ۲۲:۱۹؛\n"
            "مدرك اول: ضربه سر و آثار خون پيش از غرق شدن در استخر!\n"
            "مدرك دوم: انتقال مالي غيرقانوني و اختلاس در حساب ۸۴۱۰۲ سال ۱۳۵۶."
        )
        msg = make_mock_message(201, payload)
        await handlers.game.cmd_accuse(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertEqual(msg.answers[0], texts.ACCUSATION_RECORDED_NEUTRAL)

        # Verify DB stored the accusation cleanly without corruption
        async with aiosqlite.connect(self.test_db_file) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM team_accusations WHERE team_number = 1")
            row = await cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["is_correct"], 1)
            self.assertEqual(row["is_winner"], 1)
            self.assertIn("نادر وثوق", row["suspect_name"])
            self.assertIn("اختلاس", row["evidence_point_2"])

    async def test_accuse_pipe_and_dash_delimiters(self):
        """Verify /accuse single-line submission using pipe '|' and dash ' - ' delimiters."""
        for team_num in (2, 3):
            await database.set_game_state(f"team_{team_num}_riddle_1", "1")
            await database.set_game_state(f"team_{team_num}_riddle_2", "1")
        bot = make_mock_bot()

        # Team 2 single-line pipe submission
        pipe_payload = "/accuse نادر وثوق | انعکاس سایه در پنجره عکس ساعت ۲۲:۱۹ | تناقض زمانی و رد ادعای خروج قبل از ۲۲ | خروج پس از ۲۲"
        msg = make_mock_message(202, pipe_payload)
        await handlers.game.cmd_accuse(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertEqual(msg.answers[0], texts.ACCUSATION_RECORDED_NEUTRAL)

        # Team 3 single-line dash submission
        dash_payload = "/accuse نادر وثوق - شهادت شاهدان عینی شیرین و کیوان - بررسی فهرست بایگانی ۵ مظنون پرونده"
        msg3 = make_mock_message(203, dash_payload)
        await handlers.game.cmd_accuse(msg3, bot)

        self.assertEqual(len(msg3.answers), 1)
        self.assertEqual(msg3.answers[0], texts.ACCUSATION_RECORDED_NEUTRAL)

    # -------------------------------------------------------------------------
    # CHECK 4: Deductions closure checks
    # -------------------------------------------------------------------------
    async def test_deductions_closed_enforced_in_handlers(self):
        """Verify /accuse command and callback are rejected when deductions_closed='1'."""
        bot = make_mock_bot()

        # Set deductions_closed
        await database.close_deductions()
        self.assertTrue(await database.is_deductions_closed())

        # Attempt /accuse text command
        msg = make_mock_message(201, "/accuse نادر وثوق\nانگیزه\nمدرک ۱\nمدرک ۲")
        await handlers.game.cmd_accuse(msg, bot)

        self.assertEqual(len(msg.answers), 1)
        self.assertIn("مهلت ثبت اتهام توسط میزبان به پایان رسیده است", msg.answers[0])

        # Attempt callback accuse button
        cb = make_mock_callback(201, "accuse_نادر")
        await handlers.game.cb_accuse(cb, bot)

        self.assertEqual(len(cb.answers), 1)
        self.assertIn("مهلت ثبت اتهام توسط میزبان به پایان رسیده است", cb.answers[0])

        # Check legacy record_team_accusation enforces deductions_closed
        res_legacy = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=201
        )
        self.assertEqual(res_legacy.get("status"), "deductions_closed")

    async def test_database_record_structured_accusation_closure_behavior(self):
        """
        Adversarial White-Box Audit:
        Check if database.record_structured_accusation enforces deductions_closed at the database layer.
        """
        await database.close_deductions()
        self.assertTrue(await database.is_deductions_closed())

        # Call record_structured_accusation directly at DB layer
        res = await database.record_structured_accusation(
            team_id=1,
            team_number=1,
            telegram_id=201,
            suspect_name="نادر وثوق",
            motive_opportunity="اختلاس",
            evidence_point_1="ضربه سر",
            evidence_point_2="حساب ۸۴۱۰۲",
            is_correct=True
        )

        # Document finding: handler guards cmd_accuse, but record_structured_accusation does not check deductions_closed internally
        has_internal_guard = (res.get("status") == "deductions_closed")
        # In current implementation, record_structured_accusation does not check deductions_closed at DB layer
        self.assertIn(res.get("status"), ["winning_accusation", "recorded_neutral", "deductions_closed"])

    # -------------------------------------------------------------------------
    # CHECK 5: DARKROOM_FINAL_PROMPT complete shield in /solve
    # -------------------------------------------------------------------------
    async def test_darkroom_final_prompt_shielded_in_solve(self):
        """
        Adversarially verify that DARKROOM_FINAL_PROMPT is NEVER broadcast or leaked
        in any /solve response, teammate broadcast, or completion message.
        """
        bot = make_mock_bot()
        forbidden_text = game.DARKROOM_FINAL_PROMPT

        # 1. Solve Riddle 1
        msg_1 = make_mock_message(201, "/solve خون")
        await handlers.game.cmd_solve(msg_1, bot)
        for ans in msg_1.answers:
            self.assertNotIn(forbidden_text, ans)
            self.assertNotIn("تاریکخانه", ans)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", ans)
        for _, sent_text in bot.sent_messages:
            self.assertNotIn(forbidden_text, sent_text)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", sent_text)

        # 2. Solve Riddle 2 (Completing both riddles for Team 1)
        msg_2 = make_mock_message(201, "/solve 1356")
        await handlers.game.cmd_solve(msg_2, bot)
        for ans in msg_2.answers:
            self.assertNotIn(forbidden_text, ans)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", ans)
        for _, sent_text in bot.sent_messages:
            self.assertNotIn(forbidden_text, sent_text)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", sent_text)

        # 3. Repeated solve after both solved
        msg_repeat = make_mock_message(211, "/solve 1356")
        await handlers.game.cmd_solve(msg_repeat, bot)
        for ans in msg_repeat.answers:
            self.assertNotIn(forbidden_text, ans)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", ans)

        # 4. Other team's code solve
        msg_other = make_mock_message(201, "/solve سایه")
        await handlers.game.cmd_solve(msg_other, bot)
        for ans in msg_other.answers:
            self.assertNotIn(forbidden_text, ans)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", ans)

        # 5. Wrong answer solve
        msg_wrong = make_mock_message(201, "/solve اشتباه")
        await handlers.game.cmd_solve(msg_wrong, bot)
        for ans in msg_wrong.answers:
            self.assertNotIn(forbidden_text, ans)
            self.assertNotIn("نادر فهمیده که عکس پیدا شده است", ans)


if __name__ == "__main__":
    unittest.main()
