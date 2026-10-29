"""
E2E Isolation and Accusation Test Suite for Bāgh-e Sarhang Murder Mystery.
Covers Tiers 1 & 2:
- Strict Team Isolation (zero cross-team leaks)
- Canonical 6 Answer Keys & Comprehensive Normalization (Persian/Arabic/Latin)
- Rejection of Competitor Team Codes (OTHER_TEAM_CODE_ALERT)
- Idempotent Solves & Exact-Once Team Completion Signal
- Concurrency & Race-Condition Safety
- Structured Accusation Evaluation against Independent Team Dossiers
- Competitive Winner Determination & Timestamp Preservation
- Accusation Revisions & Deductions Close/Open Lifecycle
- Boundary and Corner Conditions
"""

import os
import asyncio
import unittest
from pathlib import Path
import uuid
import aiosqlite

import database
import game
import texts


class BaseIsolationTestCase(unittest.IsolatedAsyncioTestCase):
    """Base fixture providing an isolated, Windows-safe temporary database for each test."""

    async def asyncSetUp(self):
        self.unique_id = uuid.uuid4().hex[:10]
        self.test_db_file = Path(f"test_isolation_{self.unique_id}_{self._testMethodName}.db")
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.test_db_file
        database._riddle_lock = asyncio.Lock()

        await database.init_db()

        # Seed 3 test teams with 2 investigators each
        # Team 1: 101, 111 (خون)
        # Team 2: 102, 112 (سایه)
        # Team 3: 103, 113 (سکوت)
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES 
                (101, 'investigator_1a', 'بازرس اول الف', 'role_player', 1, 'تیم ۱ (خون)'),
                (111, 'investigator_1b', 'بازرس اول ب', 'role_player', 1, 'تیم ۱ (خون)'),
                (102, 'investigator_2a', 'بازرس دوم الف', 'role_player', 2, 'تیم ۲ (سایه)'),
                (112, 'investigator_2b', 'بازرس دوم ب', 'role_player', 2, 'تیم ۲ (سایه)'),
                (103, 'investigator_3a', 'بازرس سوم الف', 'role_player', 3, 'تیم ۳ (سکوت)'),
                (113, 'investigator_3b', 'بازرس سوم ب', 'role_player', 3, 'تیم ۳ (سکوت)')
            """)
            await db.commit()

    async def asyncTearDown(self):
        database.DB_PATH = self.orig_db_path
        await asyncio.sleep(0.01)
        if self.test_db_file.exists():
            for _ in range(5):
                try:
                    os.remove(self.test_db_file)
                    break
                except Exception:
                    await asyncio.sleep(0.05)


class TestCanonicalAnswerKeysAndNormalization(BaseIsolationTestCase):
    """Tier 1 & Tier 2: Canonical Answer Keys, Normalization, and Aliases."""

    async def test_team1_envelope_1a_canonical_and_aliases(self):
        """Team 1 Envelope 1-A: 'خون', 'blood', 'خون سرخ', whitespace, and punctuation."""
        keys = ["خون", "blood", "خون سرخ", "  خون  ", "خون!", "«خون»", "blood "]
        for key in keys:
            # Reset riddle 1
            await database.set_game_state("team_1_riddle_1", "0")
            res = await database.check_team_riddle(101, key)
            self.assertEqual(res["status"], "riddle_solved", f"Failed for key '{key}'")
            self.assertEqual(res["riddle_num"], 1)
            self.assertIn("مدرک جسمانی ثبت شد", res["response_text"])

    async def test_team1_envelope_1b_canonical_and_numeral_variants(self):
        """Team 1 Envelope 1-B: '1356', '۱۳۵۶', Arabic digits, whitespace."""
        keys = ["1356", "۱۳۵۶", "١٣٥٦", " 1356 ", "۱۳۵۶!"]
        for key in keys:
            await database.set_game_state("team_1_riddle_2", "0")
            res = await database.check_team_riddle(101, key)
            self.assertIn(res["status"], ["riddle_solved", "both_solved"], f"Failed for key '{key}'")
            self.assertEqual(res["riddle_num"], 2)
            self.assertIn("صفحهی حسابها ثبت شد", res["response_text"])

    async def test_team2_envelope_2a_canonical_and_aliases(self):
        """Team 2 Envelope 2-A: 'سایه', 'shadow', 'سايه' (Arabic Yeh), whitespace."""
        keys = ["سایه", "shadow", "سايه", "  سایه  ", "«سایه»"]
        for key in keys:
            await database.set_game_state("team_2_riddle_1", "0")
            res = await database.check_team_riddle(102, key)
            self.assertEqual(res["status"], "riddle_solved", f"Failed for key '{key}'")
            self.assertEqual(res["riddle_num"], 1)
            self.assertIn("تصویر ثبت شد", res["response_text"])

    async def test_team2_envelope_2b_canonical_and_numeral_variants(self):
        """Team 2 Envelope 2-B: '2910', '۲۹۱۰', Arabic digits, whitespace."""
        keys = ["2910", "۲۹۱۰", "٢٩١٠", "  2910  ", "۲۹۱۰!"]
        for key in keys:
            await database.set_game_state("team_2_riddle_2", "0")
            res = await database.check_team_riddle(102, key)
            self.assertIn(res["status"], ["riddle_solved", "both_solved"], f"Failed for key '{key}'")
            self.assertEqual(res["riddle_num"], 2)
            self.assertIn("زمان ثبت تصویر تأیید شد", res["response_text"])

    async def test_team3_envelope_3a_canonical_and_aliases(self):
        """Team 3 Envelope 3-A: 'سکوت', 'silence', 'سکوت مطلق', 'سكوت' (Arabic Kaf)."""
        keys = ["سکوت", "silence", "سکوت مطلق", "سكوت", "  سکوت...  "]
        for key in keys:
            await database.set_game_state("team_3_riddle_1", "0")
            res = await database.check_team_riddle(103, key)
            self.assertEqual(res["status"], "riddle_solved", f"Failed for key '{key}'")
            self.assertEqual(res["riddle_num"], 1)
            self.assertIn("شهادت ثبت شد", res["response_text"])

    async def test_team3_envelope_3b_canonical_and_word_aliases(self):
        """Team 3 Envelope 3-B: '5', '۵', 'پنج', Arabic '٥', whitespace."""
        keys = ["5", "۵", "پنج", "٥", "  ۵  ", "«پنج»"]
        for key in keys:
            await database.set_game_state("team_3_riddle_2", "0")
            res = await database.check_team_riddle(103, key)
            self.assertIn(res["status"], ["riddle_solved", "both_solved"], f"Failed for key '{key}'")
            self.assertEqual(res["riddle_num"], 2)
            self.assertIn("فهرست بایگانی تأیید شد", res["response_text"])

    async def test_team3_envelope_3b_rejection_of_three(self):
        """Team 3 Envelope 3-B: strictly rejects '3', '۳', 'سه' as wrong answer."""
        wrong_keys = ["3", "۳", "سه", "٣"]
        for key in wrong_keys:
            res = await database.check_team_riddle(103, key)
            self.assertEqual(res["status"], "wrong")
            self.assertEqual(res["response_text"], game.WRONG_ANSWER_TEXT)


class TestCompetitorCodeRejection(BaseIsolationTestCase):
    """Tier 1 & Tier 2: Rejection of Competitor Codes without Leaking Answers."""

    async def test_team1_rejects_competitor_codes(self):
        """Team 1 member submitting Team 2 or Team 3 codes gets OTHER_TEAM_CODE_ALERT."""
        competitor_codes = ["سایه", "2910", "۲۹۱۰", "سکوت", "5", "۵", "پنج", "shadow", "silence"]
        for code in competitor_codes:
            res = await database.check_team_riddle(101, code)
            self.assertEqual(res["status"], "other_team_riddle", f"Expected rejection for '{code}'")
            self.assertEqual(res["response_text"], game.OTHER_TEAM_CODE_ALERT)
            # Ensure no leak of answer or team name in alert text
            self.assertNotIn("نادر", res["response_text"])
            self.assertNotIn(code, res["response_text"])

    async def test_team2_rejects_competitor_codes(self):
        """Team 2 member submitting Team 1 or Team 3 codes gets OTHER_TEAM_CODE_ALERT."""
        competitor_codes = ["خون", "1356", "۱۳۵۶", "سکوت", "5", "۵", "پنج", "blood", "silence"]
        for code in competitor_codes:
            res = await database.check_team_riddle(102, code)
            self.assertEqual(res["status"], "other_team_riddle", f"Expected rejection for '{code}'")
            self.assertEqual(res["response_text"], game.OTHER_TEAM_CODE_ALERT)

    async def test_team3_rejects_competitor_codes(self):
        """Team 3 member submitting Team 1 or Team 2 codes gets OTHER_TEAM_CODE_ALERT."""
        competitor_codes = ["خون", "1356", "۱۳۵۶", "سایه", "2910", "۲۹۱۰", "blood", "shadow"]
        for code in competitor_codes:
            res = await database.check_team_riddle(103, code)
            self.assertEqual(res["status"], "other_team_riddle", f"Expected rejection for '{code}'")
            self.assertEqual(res["response_text"], game.OTHER_TEAM_CODE_ALERT)


class TestIdempotencyAndStateIsolation(BaseIsolationTestCase):
    """Tier 1: Idempotent Solves, Exact-Once Completion, and State Isolation."""

    async def test_idempotent_first_envelope_submission(self):
        """Resubmitting already-solved envelope 1 is idempotent and does not advance state."""
        res1 = await database.check_team_riddle(101, "خون")
        self.assertEqual(res1["status"], "riddle_solved")

        # Second submission by same player
        res1_dup = await database.check_team_riddle(101, "خون")
        self.assertEqual(res1_dup["status"], "already_solved")
        self.assertEqual(res1_dup["riddle_num"], 1)

        # Submission by teammate 111
        res1_teammate = await database.check_team_riddle(111, "خون")
        self.assertEqual(res1_teammate["status"], "already_solved")
        self.assertEqual(res1_teammate["riddle_num"], 1)

    async def test_exact_once_team_completion_signal(self):
        """Team completion triggers just_completed=True exactly once upon solving both envelopes."""
        # Solve Riddle 1
        res1 = await database.check_team_riddle(101, "خون")
        self.assertEqual(res1["status"], "riddle_solved")
        self.assertFalse(res1.get("just_completed", False))

        # Solve Riddle 2 -> exactly triggers both_solved & just_completed=True
        res2 = await database.check_team_riddle(101, "1356")
        self.assertEqual(res2["status"], "both_solved")
        self.assertTrue(res2.get("just_completed", False))

        # Timestamp recorded
        ts = await database.get_game_state("team_1_completed_at")
        self.assertTrue(ts is not None and len(ts) > 0)

        # Duplicate solve of Riddle 2
        res2_dup = await database.check_team_riddle(101, "1356")
        self.assertEqual(res2_dup["status"], "already_both_solved")

        # Duplicate solve of Riddle 1
        res1_dup = await database.check_team_riddle(111, "خون")
        self.assertEqual(res1_dup["status"], "already_both_solved")

        # Verify timestamp was not altered
        ts_after = await database.get_game_state("team_1_completed_at")
        self.assertEqual(ts, ts_after)

    async def test_complete_state_isolation_between_teams(self):
        """Progress in Team 1 does not alter or leak into Team 2 or Team 3 states."""
        await database.check_team_riddle(101, "خون")
        await database.check_team_riddle(101, "1356")

        # Check Team 1 states are 1
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")
        self.assertEqual(await database.get_game_state("team_1_riddle_2"), "1")
        self.assertEqual(await database.get_game_state("team_1_both_solved"), "1")

        # Check Team 2 states remain strictly 0
        self.assertEqual(await database.get_game_state("team_2_riddle_1", "0"), "0")
        self.assertEqual(await database.get_game_state("team_2_riddle_2", "0"), "0")
        self.assertEqual(await database.get_game_state("team_2_both_solved", "0"), "0")

        # Check Team 3 states remain strictly 0
        self.assertEqual(await database.get_game_state("team_3_riddle_1", "0"), "0")
        self.assertEqual(await database.get_game_state("team_3_riddle_2", "0"), "0")
        self.assertEqual(await database.get_game_state("team_3_both_solved", "0"), "0")


class TestStructuredAccusationRubric(BaseIsolationTestCase):
    """Tier 1 & Tier 2: Dossier Evidence Rubric Validation per Team."""

    def test_team1_valid_accusation_evaluation(self):
        """Team 1 accusation requires Nader Vosough + Pool Blood/Trauma + Ledger Embezzlement."""
        # Valid Persian
        res = database.evaluate_accusation(
            team_number=1,
            suspect="نادر وثوق",
            motive="اختلاس و انتقال مالی بدون مجوز در دفتر حساب‌ها",
            evidence_point_1="جراحت سر و آثار خون لبه استخر پیش از ورود به آب",
            evidence_point_2="شماره حساب ۸۴۱۰۲ و تطبیق انتقال مالی در دفترچه سال ۵۶"
        )
        self.assertTrue(res["is_suspect_correct"])
        self.assertTrue(res["has_cat_a"])
        self.assertTrue(res["has_cat_b"])
        self.assertTrue(res["has_two_distinct_points"])
        self.assertTrue(res["is_correct"])

    def test_team1_missing_evidence_point_fails(self):
        """Team 1 accusation naming Nader but lacking one evidence point fails."""
        # Missing Cat B (Embezzlement)
        res_no_b = database.evaluate_accusation(
            team_number=1,
            suspect="نادر وثوق",
            evidence_point_1="ضربه به سر و خون لبه استخر"
        )
        self.assertTrue(res_no_b["has_cat_a"])
        self.assertFalse(res_no_b["has_cat_b"])
        self.assertFalse(res_no_b["is_correct"])

        # Missing Cat A (Head trauma / pool blood)
        res_no_a = database.evaluate_accusation(
            team_number=1,
            suspect="نادر وثوق",
            evidence_point_1="اختلاس مالی از حساب 84102 در دفتر"
        )
        self.assertFalse(res_no_a["has_cat_a"])
        self.assertTrue(res_no_a["has_cat_b"])
        self.assertFalse(res_no_a["is_correct"])

    def test_team2_valid_accusation_evaluation(self):
        """Team 2 accusation requires Nader Vosough + 22:19 window reflection + departure timeline contradiction."""
        res = database.evaluate_accusation(
            team_number=2,
            suspect="نادر وثوق",
            motive="حضور مخفیانه در باغ هنگام حادثه",
            evidence_point_1="عکس و سایه فرد در بازتاب شیشه پنجره",
            evidence_point_2="تناقض زمانی: ثبت عکس در ۲۲:۱۹ در حالی که ادعا کرده بود قبل از ساعت ۲۲:۰۰ خارج شده"
        )
        self.assertTrue(res["is_suspect_correct"])
        self.assertTrue(res["has_cat_a"])
        self.assertTrue(res["has_cat_b"])
        self.assertTrue(res["is_correct"])

    def test_team2_wrong_suspect_fails(self):
        """Team 2 naming Keyvan Rastegar (the photographer) fails even with valid dossier evidence."""
        res = database.evaluate_accusation(
            team_number=2,
            suspect="کیوان رستگار (عکاس)",
            evidence_point_1="عکس و بازتاب پنجره ۲۲:۱۹",
            evidence_point_2="تناقض زمان خروج و ادعای ساعت ۲۲"
        )
        self.assertFalse(res["is_suspect_correct"])
        self.assertFalse(res["is_correct"])

    def test_team3_valid_accusation_evaluation(self):
        """Team 3 accusation requires Nader Vosough + witness concealment + 5 individuals archive index."""
        res = database.evaluate_accusation(
            team_number=3,
            suspect="نادر وثوق",
            motive="تهدید شاهدان برای کتمان حقیقت قتل",
            evidence_point_1="شهادت شاهدان: شیرین نوری و کیوان تهدید به مرگ شده بودند و از ترس سکوت کردند",
            evidence_point_2="فهرست بایگانی پرونده سرهنگ شامل ۵ نفر مظنون که با تطبیق شهادت‌ها تنها نادر مظنون باقی می‌ماند"
        )
        self.assertTrue(res["is_suspect_correct"])
        self.assertTrue(res["has_cat_a"])
        self.assertTrue(res["has_cat_b"])
        self.assertTrue(res["is_correct"])

    def test_team_using_competitor_dossier_evidence_fails(self):
        """Team 1 attempting to use Team 2's evidence (window reflection) fails Team 1 rubric."""
        res = database.evaluate_accusation(
            team_number=1,
            suspect="نادر وثوق",
            evidence_point_1="عکس بازتاب شیشه پنجره و سایه مبهم",
            evidence_point_2="زمان ثبت تصویر ۲۲:۱۹ و تناقض خروج قبل از ۲۲"
        )
        # For Team 1, Cat A requires pool blood/head injury and Cat B requires ledger embezzlement
        self.assertFalse(res["has_cat_a"])
        self.assertFalse(res["has_cat_b"])
        self.assertFalse(res["is_correct"])


class TestCompetitiveWinnerDetermination(BaseIsolationTestCase):
    """Tier 1: Winner Determination, Timestamps, and Revision Rules."""

    async def test_first_valid_accusation_wins(self):
        """The first team committing a valid, fully supported accusation wins and is recorded."""
        res1 = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=101,
            motive_opportunity="اختلاس حساب مالی 84102",
            evidence_point_1="جراحت سر و خون لبه استخر",
            evidence_point_2="دفتر حسابداری و ته چک انتقال بدون مجوز"
        )
        self.assertEqual(res1["status"], "recorded")
        self.assertTrue(res1["is_correct"])
        self.assertTrue(res1["is_winner"])
        self.assertTrue(res1["just_won"])

        winner_data = await database.get_winning_accusation()
        self.assertIsNotNone(winner_data)
        self.assertEqual(winner_data["team_number"], 1)
        self.assertEqual(winner_data["suspect_name"], "نادر وثوق")

    async def test_second_valid_accusation_does_not_usurp_winner(self):
        """When Team 1 has won, a subsequent valid accusation by Team 2 does not reset the winner."""
        # Team 1 wins first
        await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=101,
            motive_opportunity="اختلاس مالی",
            evidence_point_1="خون استخر",
            evidence_point_2="حساب 84102"
        )

        initial_ts = await database.get_game_state("game_winner_recorded_at")

        # Team 2 submits valid accusation later
        res2 = await database.record_team_accusation(
            team_number=2,
            suspect="نادر وثوق",
            telegram_id=102,
            motive_opportunity="تناقض زمان خروج ۲۲:۱۹",
            evidence_point_1="عکس بازتاب پنجره",
            evidence_point_2="ادعای خروج قبل ۲۲:۰۰"
        )
        self.assertTrue(res2["is_correct"])
        self.assertFalse(res2["is_winner"])
        self.assertFalse(res2["just_won"])

        # Winner is still Team 1
        winner_data = await database.get_winning_accusation()
        self.assertEqual(winner_data["team_number"], 1)

        # Winning timestamp was not altered
        current_ts = await database.get_game_state("game_winner_recorded_at")
        self.assertEqual(initial_ts, current_ts)

    async def test_winning_team_revision_preserves_timestamp_and_win(self):
        """Winning team revising its submission increments revision_count without altering winning timestamp."""
        res1 = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=101,
            evidence_point_1="خون استخر و جراحت سر",
            evidence_point_2="حساب ۸۴۱۰۲ و اختلاس"
        )
        self.assertTrue(res1["is_winner"])
        self.assertEqual(res1["revision_count"], 1)
        orig_ts = await database.get_game_state("winning_timestamp")

        # Team 1 revises
        res_rev = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق (مدیر امور مالی)",
            telegram_id=101,
            evidence_point_1="خون استخر و جراحت سر",
            evidence_point_2="حساب ۸۴۱۰۲ و دفترچه مالی"
        )
        self.assertTrue(res_rev["is_winner"])
        self.assertFalse(res_rev["just_won"])
        self.assertEqual(res_rev["revision_count"], 2)

        # Timestamp is preserved
        self.assertEqual(await database.get_game_state("winning_timestamp"), orig_ts)

    async def test_close_and_reopen_deductions(self):
        """When deductions are closed, submissions are rejected until reopened."""
        await database.close_deductions()
        self.assertTrue(await database.is_deductions_closed())

        res_closed = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=101,
            evidence_point_1="خون استخر",
            evidence_point_2="حساب 84102"
        )
        self.assertEqual(res_closed["status"], "deductions_closed")

        await database.open_deductions()
        self.assertFalse(await database.is_deductions_closed())

        res_open = await database.record_team_accusation(
            team_number=1,
            suspect="نادر وثوق",
            telegram_id=101,
            evidence_point_1="خون استخر",
            evidence_point_2="حساب 84102"
        )
        self.assertEqual(res_open["status"], "recorded")


class TestConcurrencyAndRaceSafety(BaseIsolationTestCase):
    """Tier 2: Concurrent Solves and Rapid Accusation Revisions."""

    async def test_concurrent_teammate_solves_atomic(self):
        """Two teammates submitting the same solve simultaneously: exactly one gets riddle_solved."""
        # 101 and 111 submit "خون" at the exact same moment
        task1 = database.check_team_riddle(101, "خون")
        task2 = database.check_team_riddle(111, "خون")
        results = await asyncio.gather(task1, task2)

        statuses = [r["status"] for r in results]
        self.assertIn("riddle_solved", statuses)
        self.assertIn("already_solved", statuses)
        # Exactly one riddle_solved
        self.assertEqual(statuses.count("riddle_solved"), 1)
        self.assertEqual(statuses.count("already_solved"), 1)

    async def test_rapid_accusation_revisions(self):
        """A team rapidly submitting 5 revisions: all 5 are recorded with sequential revision_counts."""
        for i in range(1, 6):
            res = await database.record_team_accusation(
                team_number=1,
                suspect=f"نادر وثوق نسخه {i}",
                telegram_id=101,
                evidence_point_1="خون استخر",
                evidence_point_2="حساب 84102"
            )
            self.assertEqual(res["revision_count"], i)

        final_acc = await database.get_team_accusation(1)
        self.assertEqual(final_acc, "نادر وثوق نسخه 5")


class TestBoundaryAndCornerCases(BaseIsolationTestCase):
    """Tier 2: Extreme inputs, whitespace, punctuation, diacritics, unassigned users."""

    async def test_unregistered_user_riddle_check(self):
        """Unregistered user ID returns status 'not_registered'."""
        res = await database.check_team_riddle(999999, "خون")
        self.assertEqual(res["status"], "not_registered")

    async def test_user_without_team_riddle_check(self):
        """User with team_number=None returns status 'no_team'."""
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, full_name, role, team_number)
                VALUES (200, 'بدون تیم', 'role_player', NULL)
            """)
            await db.commit()

        res = await database.check_team_riddle(200, "خون")
        self.assertEqual(res["status"], "no_team")

    async def test_empty_and_whitespace_only_riddle_check(self):
        """Empty string or spaces returns 'wrong'."""
        res_empty = await database.check_team_riddle(101, "")
        self.assertEqual(res_empty["status"], "wrong")

        res_spaces = await database.check_team_riddle(101, "     ")
        self.assertEqual(res_spaces["status"], "wrong")

    def test_text_normalization_extreme_cases(self):
        """Arabic/Persian character normalization, Alef madda, Teh marbuta, punctuation, and mixed digits."""
        # Arabic Yeh and Kaf
        self.assertEqual(database._normalize_text("سايه"), "سایه")
        self.assertEqual(database._normalize_text("سكوت"), "سکوت")
        # Alef with Madda and Teh Marbuta
        self.assertEqual(database._normalize_text("آرش"), "ارش")
        self.assertEqual(database._normalize_text("ساعتة"), "ساعته")
        # Punctuation stripping
        self.assertEqual(database._normalize_text("خون!"), "خون")
        self.assertEqual(database._normalize_text("(سایه)..."), "سایه")
        self.assertEqual(database._normalize_text("سکوت، آرامش؛"), "سکوت ارامش")
        # Mixed Persian, Arabic, and Latin numerals
        self.assertEqual(database._normalize_text("۱۳56"), "1356")
        self.assertEqual(database._normalize_text("۲9۱0"), "2910")
        self.assertEqual(database._normalize_text("١٣۵6"), "1356")


if __name__ == "__main__":
    unittest.main()
