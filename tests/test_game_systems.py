import asyncio
import os
import unittest
from pathlib import Path
import aiosqlite

import database
import game
import texts

class TestColonelGameSystems(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db_file = Path("test_colonel_party.db")
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.test_db_file

        await database.init_db()

        # Seed 3 test investigator guests for Team 1, Team 2, and Team 3
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES 
                (101, 'investigator_1', 'بازرس اول', 'role_player', 1, 'تیم ۱ (خون)'),
                (102, 'investigator_2', 'بازرس دوم', 'role_player', 2, 'تیم ۲ (سایه)'),
                (103, 'investigator_3', 'بازرس سوم', 'role_player', 3, 'تیم ۳ (سکوت)')
            """)
            await db.commit()

    async def asyncTearDown(self):
        database.DB_PATH = self.orig_db_path
        if self.test_db_file.exists():
            try:
                os.remove(self.test_db_file)
            except Exception:
                pass

    def test_normalize_persian_and_arabic_digits(self):
        """Tests normalization of Arabic/Persian letters, digits, and punctuation."""
        self.assertEqual(database._normalize_text("۱۳۵۶"), "1356")
        self.assertEqual(database._normalize_text("۲۹۱۰"), "2910")
        self.assertEqual(database._normalize_text("۵"), "5")
        self.assertEqual(database._normalize_text("۳"), "3")
        self.assertEqual(database._normalize_text("٠١٢٣٤٥٦٧٨٩"), "0123456789")
        self.assertEqual(database._normalize_text("سايه"), "سایه")
        self.assertEqual(database._normalize_text("  خون!  "), "خون")
        self.assertEqual(database._normalize_text("سكوت..."), "سکوت")
        self.assertEqual(database._normalize_text("  ۵  "), "5")

    async def test_riddle_answers_success_team_1(self):
        """Verifies Team 1 riddle keys: خون (1-A) and 1356/۱۳۵۶ (1-B) with safe canonical clues."""
        # 1-A: خون
        res_1a = await database.check_team_riddle(101, "خون")
        self.assertEqual(res_1a["status"], "riddle_solved")
        self.assertEqual(res_1a["riddle_num"], 1)
        self.assertEqual(
            res_1a["response_text"],
            "✅ مدرک جسمانی ثبت شد. آثار خون و جراحت سر آرش نشان میدهند که آسیب پیش از ورود او به آب رخ داده است. این مدرک بهتنهایی مشخص نمیکند چه کسی مسئول بوده است."
        )

        # 1-B: Persian digits ۱۳۵۶
        res_1b = await database.check_team_riddle(101, "۱۳۵۶")
        self.assertEqual(res_1b["status"], "both_solved")
        self.assertEqual(res_1b["riddle_num"], 2)
        self.assertEqual(
            res_1b["response_text"],
            "✅ صفحه‌ی حساب‌ها ثبت شد. یک انتقال مالی بدون تأیید شناسایی شده است. شماره‌ی رسید و کد حساب را با فهرست کارکنان داخل پرونده‌ی خودتان تطبیق دهید؛ این مدرک به‌تنهایی هویت قاتل را ثابت نمی‌کند."
        )

    async def test_riddle_answers_success_team_2(self):
        """Verifies Team 2 riddle keys: سایه (2-A) and 2910/۲۹۱۰ (2-B) with safe canonical clues."""
        # 2-A: سایه (with arabic yeh normalization)
        res_2a = await database.check_team_riddle(102, "سايه")
        self.assertEqual(res_2a["status"], "riddle_solved")
        self.assertEqual(res_2a["riddle_num"], 1)
        self.assertEqual(
            res_2a["response_text"],
            "✅ تصویر ثبت شد. بازتاب شیشه حضور فرد دیگری را مطرح میکند؛ اما عکس بهتنهایی هویت او را ثابت نمیکند."
        )

        # 2-B: Persian digits ۲۹۱۰
        res_2b = await database.check_team_riddle(102, "۲۹۱۰")
        self.assertEqual(res_2b["status"], "both_solved")
        self.assertEqual(res_2b["riddle_num"], 2)
        self.assertEqual(
            res_2b["response_text"],
            "✅ زمان ثبت تصویر تأیید شد: ۲۲:۱۹. این زمان با ادعای خروج پیش از ساعت ۲۲:۰۰ سازگار نیست. برای شناسایی فرد، تصویر را با سایر مدارک تطبیق دهید."
        )

    async def test_riddle_answers_success_team_3(self):
        """Verifies Team 3 riddle keys: سکوت (3-A) and 5/۵/پنج (3-B) with safe canonical clues."""
        # 3-A: سکوت
        res_3a = await database.check_team_riddle(103, "سکوت")
        self.assertEqual(res_3a["status"], "riddle_solved")
        self.assertEqual(res_3a["riddle_num"], 1)
        self.assertEqual(
            res_3a["response_text"],
            "✅ شهادت ثبت شد. یکی از شاهدان، درگیری کنار استخر را دیده و پس از تهدید از باغ فرار کرده است. نام فردی که او دیده، باید با مدارک دیگر تطبیق داده شود."
        )

        # 3-B: Persian digit ۵
        res_3b = await database.check_team_riddle(103, "۵")
        self.assertEqual(res_3b["status"], "both_solved")
        self.assertEqual(res_3b["riddle_num"], 2)
        self.assertEqual(
            res_3b["response_text"],
            "✅ فهرست بایگانی تأیید شد: پنج فرد متمایز در فهرست صحنه ثبت شده‌اند. این عدد به‌تنهایی هیچ‌کس را مجرم نمی‌کند."
        )

    async def test_cross_team_code_rejection(self):
        """
        Verifies that submitting another team's valid code is rejected
        with the exact cross-team warning string.
        """
        expected_alert = game.OTHER_TEAM_CODE_ALERT

        # Team 1 member sends Team 2's code ("سایه")
        res_t1_cross = await database.check_team_riddle(101, "سایه")
        self.assertEqual(res_t1_cross["status"], "other_team_riddle")
        self.assertEqual(res_t1_cross["response_text"], expected_alert)

        # Team 1 member sends Team 3's code ("5")
        res_t1_cross2 = await database.check_team_riddle(101, "5")
        self.assertEqual(res_t1_cross2["status"], "other_team_riddle")
        self.assertEqual(res_t1_cross2["response_text"], expected_alert)

        # Team 2 member sends Team 1's code ("1356")
        res_t2_cross = await database.check_team_riddle(102, "۱۳۵۶")
        self.assertEqual(res_t2_cross["status"], "other_team_riddle")
        self.assertEqual(res_t2_cross["response_text"], expected_alert)

        # Team 3 member sends Team 2's code ("2910")
        res_t3_cross = await database.check_team_riddle(103, "۲۹۱۰")
        self.assertEqual(res_t3_cross["status"], "other_team_riddle")
        self.assertEqual(res_t3_cross["response_text"], expected_alert)

        # Team 1 member sends Team 2's code ("سایه")
        res_t1_cross = await database.check_team_riddle(101, "سایه")
        self.assertEqual(res_t1_cross["status"], "other_team_riddle")
        self.assertEqual(res_t1_cross["response_text"], expected_alert)

        # Team 1 member sends Team 3's code ("5")
        res_t1_cross2 = await database.check_team_riddle(101, "5")
        self.assertEqual(res_t1_cross2["status"], "other_team_riddle")
        self.assertEqual(res_t1_cross2["response_text"], expected_alert)

        # Team 2 member sends Team 1's code ("1356")
        res_t2_cross = await database.check_team_riddle(102, "۱۳۵۶")
        self.assertEqual(res_t2_cross["status"], "other_team_riddle")
        self.assertEqual(res_t2_cross["response_text"], expected_alert)

        # Team 3 member sends Team 2's code ("2910")
        res_t3_cross = await database.check_team_riddle(103, "۲۹۱۰")
        self.assertEqual(res_t3_cross["status"], "other_team_riddle")
        self.assertEqual(res_t3_cross["response_text"], expected_alert)

    async def test_idempotent_solves(self):
        """
        Verifies that resubmitting an already-solved code is completely idempotent
        and does not trigger duplicate state progression.
        """
        # Solve Riddle 1
        res1 = await database.check_team_riddle(101, "خون")
        self.assertEqual(res1["status"], "riddle_solved")

        # Resubmit Riddle 1
        res1_dup = await database.check_team_riddle(101, "خون")
        self.assertEqual(res1_dup["status"], "already_solved")
        self.assertEqual(res1_dup["riddle_num"], 1)

        # Solve Riddle 2
        res2 = await database.check_team_riddle(101, "1356")
        self.assertEqual(res2["status"], "both_solved")

        # Resubmit when both are solved
        res2_dup = await database.check_team_riddle(101, "1356")
        self.assertEqual(res2_dup["status"], "already_both_solved")

        res1_after_both = await database.check_team_riddle(101, "خون")
        self.assertEqual(res1_after_both["status"], "already_both_solved")

    async def test_riddle_3b_rejection_of_3(self):
        """
        CRITICAL TEST: Verifies that '3' and '۳' are strictly REJECTED for Riddle 3-B
        and returns the exact updated hint text.
        """
        expected_hint = "❌ اطلاعات واردشده با اسناد این پاکت مطابقت ندارد. متن گزارش، سال، تاریخ یا شمارش افراد پرونده را مجدداً مرور کنید."

        res_fail_latin = await database.check_team_riddle(103, "3")
        self.assertEqual(res_fail_latin["status"], "wrong")
        self.assertEqual(res_fail_latin["response_text"], expected_hint)

        res_fail_persian = await database.check_team_riddle(103, "۳")
        self.assertEqual(res_fail_persian["status"], "wrong")
        self.assertEqual(res_fail_persian["response_text"], expected_hint)

    async def test_independent_team_state_isolation(self):
        """
        Verifies that solving riddles for Team 1 does NOT alter or advance
        the independent states of Team 2 or Team 3.
        """
        # Team 1 solves both riddles
        await database.check_team_riddle(101, "خون")
        await database.check_team_riddle(101, "1356")

        # Team 1 is fully solved
        t1_r1 = await database.get_game_state("team_1_riddle_1")
        t1_r2 = await database.get_game_state("team_1_riddle_2")
        self.assertEqual(t1_r1, "1")
        self.assertEqual(t1_r2, "1")

        # Team 2 and Team 3 must still be strictly 0 (unsolved)
        t2_r1 = await database.get_game_state("team_2_riddle_1", "0")
        t2_r2 = await database.get_game_state("team_2_riddle_2", "0")
        t3_r1 = await database.get_game_state("team_3_riddle_1", "0")
        t3_r2 = await database.get_game_state("team_3_riddle_2", "0")

        self.assertEqual(t2_r1, "0")
        self.assertEqual(t2_r2, "0")
        self.assertEqual(t3_r1, "0")
        self.assertEqual(t3_r2, "0")

    async def test_mission_alibi_completion(self):
        """Verifies that mission completion records alibi and returns the exact required badge."""
        success = await database.set_mission_completed(101)
        self.assertTrue(success)

        guest = await database.get_guest_by_telegram_id(101)
        self.assertEqual(guest["is_immune"], 1)

        expected_badge = (
            "📋 [آلیبای ثبت شد / مدرک ثبت شد] — روایت و زمان حضور شما در پرونده ثبت گردید. (این نشان به معنای ثبت سرنخ است، نه اثبات قطعی بی‌گناهی)."
        )
        self.assertEqual(texts.ALIBI_LOGGED_BADGE, expected_badge)
        self.assertEqual(game.ALIBI_LOGGED_BADGE, expected_badge)

    def test_narrative_text_compliance(self):
        """Verifies exact narrative texts for Step 1, Step 3, and Step 4."""
        # Step 1: Hook and roles
        self.assertIn("رازِ ناگفته‌ی باغ سرهنگ", texts.START_WELCOME_TEXT)
        self.assertIn("خان‌زنیان", texts.START_WELCOME_TEXT)
        self.assertIn("سرهنگ بهرام فرهمند", texts.START_WELCOME_TEXT)
        self.assertIn("آرش", texts.START_WELCOME_TEXT)
        self.assertIn("رازِ ناگفته‌ی باغ سرهنگ", texts.START_WELCOME_TEXT)
        self.assertNotIn("نقش خود را انتخاب کنید", texts.START_WELCOME_TEXT)
        self.assertNotIn("بلوندهای بی‌گناه (VIP Party & Safe Zone)", texts.START_WELCOME_TEXT)

        # 6 PM Meeting Location link
        self.assertIn("https://maps.app.goo.gl/U6Dz6SzEUdoTnNty7", texts.ACT_1_TEXT)

        # Step 4: Pre-Midnight Crisis Broadcast (23:50)
        expected_crisis = (
            "⚠️ آخرین فایل صوتی سرهنگ از تاریکخانه استخراج شد.\n"
            "یکی از اسناد مفقود است...\n"
            "و یک نفر در این باغ، نمیخواهد حقیقت فاش شود."
        )
        self.assertEqual(texts.CRISIS_BROADCAST_TEXT, expected_crisis)
        self.assertEqual(game.CRISIS_BROADCAST_TEXT, expected_crisis)

        # Step 4: Finale Trigger (01:10 AM)
        expected_finale = (
            "🕯 آخرین مدرک در تاریکخانه است. نادر فهمیده که عکس پیدا شده است. او برای آخرین بار به باغ برگشته تا مدرک را پس بگیرد."
        )
        self.assertEqual(texts.DARKROOM_FINAL_PROMPT, expected_finale)
        self.assertEqual(game.DARKROOM_FINAL_PROMPT, expected_finale)
        self.assertEqual(texts.FINALE_BROADCAST_TEXT, expected_finale)

    def test_invitation_card_generation(self):
        """Verifies that invitation and immunity cards generate successfully without font or bidi crash."""
        import card_generator
        card_buf = card_generator.generate_invitation_card("سمیرا (Samira)", "role_player", 1, soul_pin="310")
        self.assertGreater(len(card_buf.getvalue()), 50000)

        imm_buf = card_generator.generate_immunity_card("سمیرا (Samira)", "310")
        self.assertGreater(len(imm_buf.getvalue()), 10000)

    async def test_tester_flow_and_team_switching(self):
        """Verifies that Hamixon (102725917) can switch teams and reset riddles freely."""
        # Pre-seeded in setUp: 101, 102, 103. Let's seed Hamixon (102725917)
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT OR REPLACE INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES (102725917, 'Hamixon', 'حامد', 'role_player', 1, 'تیم ۱ (خون)')
            """)
            await db.commit()

        # Check Team 1 solve
        res1 = await database.check_team_riddle(102725917, "خون")
        self.assertEqual(res1["status"], "riddle_solved")

        # Switch to Team 2
        await database.assign_tester_team(102725917, 2)
        guest = await database.get_guest_by_telegram_id(102725917)
        self.assertEqual(guest["team_number"], 2)

        # Check Team 2 solve
        res2 = await database.check_team_riddle(102725917, "سایه")
        self.assertEqual(res2["status"], "riddle_solved")

        # Reset Team 2 riddles
        await database.reset_team_riddles(2)
        r2_state = await database.get_game_state("team_2_riddle_1")
        self.assertEqual(r2_state, "0")

    async def test_clean_and_reset_guests(self):
        """Verifies that clean_all_guests clears the guest roster and resets states."""
        # Check that guests currently exist
        guests = await database.get_all_guests()
        self.assertGreater(len(guests), 0)

        # Clean all guests
        deleted_count = await database.clean_all_guests()
        self.assertGreaterEqual(deleted_count, 1)

        # Check roster is now empty
        after_guests = await database.get_all_guests()
        self.assertEqual(len(after_guests), 0)

        # Check game_phase is reset to 'registration'
        phase = await database.get_game_state("game_phase")
        self.assertEqual(phase, "registration")

        # Test single delete
        await database.register_or_update_guest(
            telegram_id=999999,
            telegram_username="test_user",
            full_name="تست تستر",
            has_car=0,
            car_number=None
        )
        found = await database.get_guest_by_telegram_id(999999)
        self.assertIsNotNone(found)
        deleted = await database.delete_guest_by_telegram_id(999999)
        self.assertTrue(deleted)
        after_del = await database.get_guest_by_telegram_id(999999)
        self.assertIsNone(after_del)

    async def test_alibi_shield_lifecycle(self):
        """
        Verifies that alibi shield:
        1. Grants at most 1 available shield on mission completion.
        2. Does not grant unlimited shields on repeat calls.
        3. Can be consumed via use_alibi_shield to neutralize a sticker.
        4. Cannot be consumed again once used.
        """
        # Initial state
        g_init = await database.get_guest_by_telegram_id(101)
        self.assertEqual(g_init.get("alibi_shields", 0), 0)

        # 1. Grant shield
        r1 = await database.grant_alibi_shield(101)
        self.assertEqual(r1["status"], "granted")
        self.assertEqual(r1["shields"], 1)

        # 2. Duplicate grant attempt must NOT give a second shield
        r2 = await database.grant_alibi_shield(101)
        self.assertEqual(r2["status"], "already_has_shield")
        self.assertEqual(r2["shields"], 1)

        # 3. Simulate getting stickered
        await database.mark_stickered(101)
        g_stickered = await database.get_guest_by_telegram_id(101)
        self.assertEqual(g_stickered["got_stickered"], 1)

        # 4. Consume shield
        r_use = await database.use_alibi_shield(101)
        self.assertEqual(r_use["status"], "consumed")

        g_after = await database.get_guest_by_telegram_id(101)
        self.assertEqual(g_after["alibi_shields"], 0)
        self.assertEqual(g_after["alibi_shield_used"], 1)
        self.assertEqual(g_after["got_stickered"], 0)

        # 5. Try consuming again without an active shield
        r_use_again = await database.use_alibi_shield(101)
        self.assertEqual(r_use_again["status"], "no_shield")

    async def test_special_character_role_assignment(self):
        """
        Verifies assignment of 4 canonical roles:
        - Shirin Nouri (witness in Team 1)
        - Keyvan Rastegar (witness in Team 2)
        - Dr. Fereydoun Mehr (witness in Team 3)
        - Nader Vosough (killer, distinct from witnesses)
        - Never assigned to role_blonde
        """
        async with aiosqlite.connect(self.test_db_file) as db:
            # Seed a 4th player and a blonde
            await db.execute("""
                INSERT INTO guests (telegram_id, full_name, role, team_number, team_name)
                VALUES (104, 'بازرس چهارم', 'role_player', 1, 'تیم ۱ (خون)')
            """)
            await db.execute("""
                INSERT INTO guests (telegram_id, full_name, role)
                VALUES (105, 'بلوند بی‌گناه', 'role_blonde')
            """)
            await db.commit()

        assigned = await database.assign_special_character_roles(force_reassign=True)
        self.assertEqual(len(assigned), 4)
        self.assertIn("shirin", assigned)
        self.assertIn("keyvan", assigned)
        self.assertIn("fereydoun", assigned)
        self.assertIn("nader", assigned)

        shirin = assigned["shirin"]
        keyvan = assigned["keyvan"]
        fereydoun = assigned["fereydoun"]
        nader = assigned["nader"]

        # Witnesses must be in their respective teams
        self.assertEqual(shirin["team_number"], 1)
        self.assertEqual(keyvan["team_number"], 2)
        self.assertEqual(fereydoun["team_number"], 3)

        # Nader must be distinct from all witnesses
        self.assertNotIn(nader["id"], [shirin["id"], keyvan["id"], fereydoun["id"]])

        # Witnesses are sticker carriers (is_hunter=1), Nader is not
        self.assertEqual(shirin["is_hunter"], 1)
        self.assertEqual(keyvan["is_hunter"], 1)
        self.assertEqual(fereydoun["is_hunter"], 1)
        self.assertEqual(nader["is_hunter"], 0)

        # Blonde guest must NOT have received any special role
        blonde_g = await database.get_guest_by_telegram_id(105)
        self.assertIsNone(blonde_g.get("character_role"))

    async def test_team_accusation_flow(self):
        """Verifies that teams can submit, retrieve, and revise their conclusions at the central table."""
        # Team 1 submits conclusion
        res1 = await database.record_team_accusation(1, "نادر وثوق", 101)
        self.assertEqual(res1["status"], "recorded")
        self.assertEqual(res1["suspect"], "نادر وثوق")

        acc = await database.get_team_accusation(1)
        self.assertEqual(acc, "نادر وثوق")

        # Revision
        res2 = await database.record_team_accusation(1, "نادر وثوق (مدیر امور مالی)", 101)
        self.assertEqual(res2["suspect"], "نادر وثوق (مدیر امور مالی)")

        acc_rev = await database.get_team_accusation(1)
        self.assertEqual(acc_rev, "نادر وثوق (مدیر امور مالی)")

        # Verify get_all_accusations
        all_acc = await database.get_all_accusations()
        self.assertIn(1, all_acc)
        self.assertEqual(all_acc[1], "نادر وثوق (مدیر امور مالی)")

    async def test_rescue_alert_safety(self):
        """Verifies that rescue safety alerts are never artificially blocked after 3 uses."""
        c1 = await database.record_rescue_alert(101, "بازرس اول")
        c2 = await database.record_rescue_alert(101, "بازرس اول")
        c3 = await database.record_rescue_alert(101, "بازرس اول")
        c4 = await database.record_rescue_alert(101, "بازرس اول")

        self.assertEqual(c1, 1)
        self.assertEqual(c2, 2)
        self.assertEqual(c3, 3)
        self.assertEqual(c4, 4)



    async def test_accusation_requires_distinct_evidence_and_first_valid_wins(self):
        draft = await database.record_team_accusation(1, "نادر وثوق", 101)
        self.assertEqual(draft["status"], "recorded")
        self.assertFalse(draft["is_valid"])
        self.assertIsNone(await database.get_game_winner())

        first = await database.record_team_accusation(
            1, "نادر وثوق", 101,
            "نمونه B و جراحت سر آرش",
            "رسید R-17 و اختلاس مالی",
            "نادر برای پنهان‌کردن اختلاس خود در صحنه حضور داشت و از افشای آن می‌ترسید."
        )
        self.assertTrue(first["is_valid"])
        self.assertTrue(first["winner_created"])
        winner = await database.get_game_winner()
        self.assertEqual(winner["team_number"], 1)
        winning_time = winner["winning_at"]

        second = await database.record_team_accusation(
            2, "نادر وثوق", 102,
            "عکس ۲۲:۱۹ و انعکاس",
            "کد NV-17 روی جلیقه‌ی زغالی",
            "ادعای خروج قبل از ساعت بیست با عکس ۲۲:۱۹ تناقض دارد و حضور نادر را نشان می‌دهد."
        )
        self.assertTrue(second["is_valid"])
        self.assertFalse(second["winner_created"])
        after = await database.get_game_winner()
        self.assertEqual(after["team_number"], 1)
        self.assertEqual(after["winning_at"], winning_time)

    async def test_team_specific_evidence_categories_are_required(self):
        invalid = await database.record_team_accusation(
            1, "نادر وثوق", 101,
            "خون و نمونه B", "خون روی لبه‌ی استخر",
            "نادر می‌خواست حقیقت مالی را پنهان کند و فرار کند."
        )
        self.assertEqual(invalid["status"], "insufficient_evidence")
        self.assertIsNone(await database.get_game_winner())

        valid = await database.record_team_accusation(
            3, "نادر وثوق", 103,
            "شهادت شیرین درباره‌ی هل‌دادن",
            "گزارش پزشکی و جراحت سر",
            "شهادت مستقیم و گزارش جراحت با روایت تصادف سازگار نیستند و نادر را به درگیری وصل می‌کنند."
        )
        self.assertTrue(valid["is_valid"])
        self.assertEqual((await database.get_game_winner())["team_number"], 3)

    async def test_atomic_team_solve_has_single_first_completion(self):
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES (104, 'investigator_1b', 'بازرس هم‌تیمی', 'role_player', 1, 'تیم خون')
            """)
            await db.commit()
        results = await asyncio.gather(
            database.check_team_riddle(101, "خون"),
            database.check_team_riddle(104, "خون"),
        )
        self.assertEqual(sorted(item["status"] for item in results), ["already_solved", "riddle_solved"])
        self.assertEqual(await database.get_game_state("team_1_riddle_1"), "1")
        self.assertEqual(await database.get_game_state("team_2_riddle_1", "0"), "0")

    async def test_three_teams_and_killer_outside_scoring_teams(self):
        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, telegram_username, full_name, role, team_number, team_name)
                VALUES (104, 'investigator_4', 'بازرس چهارم', 'role_player', 1, 'تیم خون')
            """)
            await db.commit()
        assigned = await database.assign_special_character_roles(force_reassign=True)
        self.assertEqual(set(assigned), {"shirin", "keyvan", "fereydoun", "nader"})
        self.assertIsNone(assigned["nader"]["team_number"])
        self.assertEqual(assigned["nader"]["is_traitor"], 0)
        teams = await database.start_midnight_game()
        self.assertEqual(set(teams), {1, 2, 3})
        for team in teams.values():
            self.assertTrue(team["members"])
            self.assertIsNone(team["traitor"])
            self.assertTrue(all(member.get("character_role") != "nader" for member in team["members"]))

        async with aiosqlite.connect(self.test_db_file) as db:
            await db.execute("""
                INSERT INTO guests (telegram_id, full_name, role, team_number, team_name)
                VALUES (105, 'بازیکن تیم چهارم نامعتبر', 'role_player', 4, 'تیم ۴')
            """)
            await db.commit()
        rejected = await database.check_team_riddle(105, "آینه")
        self.assertEqual(rejected["status"], "no_team")

    async def test_finale_closes_accusations_once(self):
        self.assertTrue(await database.trigger_finale_once())
        self.assertFalse(await database.trigger_finale_once())
        self.assertEqual(await database.get_game_state("deductions_closed"), "1")
        result = await database.record_team_accusation(1, "نادر وثوق", 101)
        self.assertEqual(result["status"], "closed")


if __name__ == "__main__":
    unittest.main()
