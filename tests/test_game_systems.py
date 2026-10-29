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

    async def test_riddle_answers_success_team_1(self):
        """Verifies Team 1 riddle keys: خون (1-A) and 1356/۱۳۵۶ (1-B)."""
        # 1-A: خون
        res_1a = await database.check_team_riddle(101, "خون")
        self.assertEqual(res_1a["status"], "riddle_solved")
        self.assertEqual(res_1a["riddle_num"], 1)
        self.assertEqual(
            res_1a["response_text"],
            "✅ مدرک جسمانی ثبت شد. این گزارش و دکمه‌ی سردست نقره‌ای، روایت سقوط ساده را زیر سؤال می‌برد؛ اما برای اثبات مسئولیت یک فرد کافی نیست."
        )

        # 1-B: Persian digits ۱۳۵۶
        res_1b = await database.check_team_riddle(101, "۱۳۵۶")
        self.assertEqual(res_1b["status"], "both_solved")
        self.assertEqual(res_1b["riddle_num"], 2)
        self.assertEqual(
            res_1b["response_text"],
            "✅ صفحه‌ی حساب‌ها ثبت شد. این مدرک به وجود انگیزه‌ی مالی اشاره دارد، اما هنوز به‌تنهایی قاتل را مشخص نمی‌کند."
        )

    async def test_riddle_answers_success_team_2(self):
        """Verifies Team 2 riddle keys: سایه (2-A) and 2910/۲۹۱۰ (2-B)."""
        # 2-A: سایه (with arabic yeh normalization)
        res_2a = await database.check_team_riddle(102, "سايه")
        self.assertEqual(res_2a["status"], "riddle_solved")
        self.assertEqual(res_2a["riddle_num"], 1)
        self.assertEqual(
            res_2a["response_text"],
            "✅ تصویر ثبت شد. بازتاب در شیشه، حضور یک نفر را مطرح می‌کند؛ اما هویت او باید با مدرک دیگری تأیید شود."
        )

        # 2-B: Persian digits ۲۹۱۰
        res_2b = await database.check_team_riddle(102, "۲۹۱۰")
        self.assertEqual(res_2b["status"], "both_solved")
        self.assertEqual(res_2b["riddle_num"], 2)
        self.assertEqual(
            res_2b["response_text"],
            "✅ زمان عکس (۲۲:۱۹) ثبت شد. نادر ادعا کرده بود پیش از ساعت ۲۲:۰۰ باغ را ترک کرده است. این تصویر، ادعای او را زیر سؤال می‌برد."
        )

    async def test_riddle_answers_success_team_3(self):
        """Verifies Team 3 riddle keys: سکوت (3-A) and 5/۵/پنج (3-B)."""
        # 3-A: سکوت
        res_3a = await database.check_team_riddle(103, "سکوت")
        self.assertEqual(res_3a["status"], "riddle_solved")
        self.assertEqual(res_3a["riddle_num"], 1)
        self.assertEqual(
            res_3a["response_text"],
            "✅ شهادت ثبت شد. سکوت شاهدان، حقیقت را پنهان کرده بود؛ اما سکوت آنها به‌تنهایی اثبات گناهشان نیست."
        )

        # 3-B: Persian digit ۵
        res_3b = await database.check_team_riddle(103, "۵")
        self.assertEqual(res_3b["status"], "both_solved")
        self.assertEqual(res_3b["riddle_num"], 2)
        self.assertEqual(
            res_3b["response_text"],
            "✅ فهرست افراد مرتبط کامل شد. اکنون باید مشخص کنید کدام فرد در عکس دیده می‌شود، انگیزه‌ی مالی دارد و ادعای غیبتش با زمان ثبت تصویر سازگار نیست."
        )

    async def test_riddle_3b_rejection_of_3(self):
        """
        CRITICAL TEST: Verifies that '3' and '۳' are strictly REJECTED for Riddle 3-B
        and DO NOT alter answer key '5'.
        """
        res_fail_latin = await database.check_team_riddle(103, "3")
        self.assertEqual(res_fail_latin["status"], "wrong")
        self.assertEqual(
            res_fail_latin["response_text"],
            "❌ پاسخ ثبت‌شده با مستندات پرونده همخوانی ندارد. شواهد داخل پاکت (واژه کلیدی گزارش، سال چهاررقمی، کد روز و ماه، یا مجموع ۵ فرد مرتبط با پرونده) را دوباره بررسی کنید."
        )

        res_fail_persian = await database.check_team_riddle(103, "۳")
        self.assertEqual(res_fail_persian["status"], "wrong")
        self.assertEqual(
            res_fail_persian["response_text"],
            "❌ پاسخ ثبت‌شده با مستندات پرونده همخوانی ندارد. شواهد داخل پاکت (واژه کلیدی گزارش، سال چهاررقمی، کد روز و ماه، یا مجموع ۵ فرد مرتبط با پرونده) را دوباره بررسی کنید."
        )

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
        """Verifies exact narrative texts for Step 2 Part A, C, and E."""
        # Part A: Grounded True-Crime text
        self.assertIn("پرونده‌ی جنایی شماره‌ی ۵۶/۱۰/۲۹ — باغ سرهنگ (حوالی خان‌زنیان)", texts.START_WELCOME_TEXT)
        self.assertIn("سرهنگ بهرام فرهمند", texts.START_WELCOME_TEXT)
        self.assertIn("آرش", texts.START_WELCOME_TEXT)
        self.assertIn("بازرسان پرونده (۱۲ تا ۱۵ داوطلب در ۳ تیم ۴ تا ۵ نفره)", texts.START_WELCOME_TEXT)
        self.assertIn("همراهان مهمانی (بلوندهای بی‌گناه)", texts.START_WELCOME_TEXT)

        # Part C: Pre-Midnight Crisis Broadcast (23:50)
        expected_crisis = (
            "⚠️ آخرین نسخه‌ی پرونده‌ی سرهنگ از تاریکخانه دریافت شد.\n"
            "یک فایل ناقص است.\n"
            "و یک نفر در باغ، به هر قیمتی نمی‌خواهد این فایل پیدا شود."
        )
        self.assertEqual(texts.CRISIS_BROADCAST_TEXT, expected_crisis)
        self.assertEqual(game.CRISIS_BROADCAST_TEXT, expected_crisis)

        # Part E: Final Darkroom Sequence (01:10 AM)
        expected_darkroom = (
            "🕯 آخرین مدرک در تاریکخانه است.\n"
            "نادر فهمیده که عکس پیدا شده است.\n"
            "او برای آخرین بار به باغ برگشته تا مدرک را پس بگیرد."
        )
        self.assertEqual(texts.DARKROOM_FINAL_PROMPT, expected_darkroom)
        self.assertEqual(game.DARKROOM_FINAL_PROMPT, expected_darkroom)

    def test_invitation_card_generation(self):
        """Verifies that invitation and immunity cards generate successfully without font or bidi crash."""
        import card_generator
        card_buf = card_generator.generate_invitation_card("سمیرا (Samira)", "role_player", 1, soul_pin="310")
        self.assertGreater(len(card_buf.getvalue()), 50000)

        imm_buf = card_generator.generate_immunity_card("سمیرا (Samira)", "310")
        self.assertGreater(len(imm_buf.getvalue()), 10000)


if __name__ == "__main__":
    unittest.main()
