import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile

import config
import database
import game
import texts
import keyboards
import card_generator

router = Router()

AUDIO_TAPE_PATH = Path("assets/audio/colonel_tape.wav")
RED_LANTERN_PATH = Path("assets/images/red_lantern.jpg")

TAPE_VOICE_FILE_ID = "AwACAgEAAxkDAAOUat7mnLOvrLtH8g2qn5xA5Vga2iEAAkEKAALxQ_hGBnT2Ao2vHjg9BA"
LANTERN_PHOTO_FILE_ID = "AgACAgEAAxkDAAOVat7mnZbQOE2oLNWQTFy0mWEbNVIAAhANaxvxQ_hGMirKbWdvIo4BAAMCAAN5AAM9BA"

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))
MISSION_UNLOCK_TIME = datetime(2026, 10, 29, 18, 0, 0, tzinfo=TEHRAN_TZ)

async def is_mission_unlocked() -> bool:
    """Checks if missions are unlocked (past 29 Oct 18:00 Tehran or forced by admin)."""
    forced = await database.get_game_state("force_unlock_missions", "0")
    if forced == "1":
        return True
    now = datetime.now(TEHRAN_TZ)
    return now >= MISSION_UNLOCK_TIME

async def can_change_role() -> bool:
    """Checks if guests can still change their role (before 29 Oct 18:00 Tehran)."""
    forced_lock = await database.get_game_state("force_lock_roles", "0")
    if forced_lock == "1":
        return False
    now = datetime.now(TEHRAN_TZ)
    return now < MISSION_UNLOCK_TIME

@router.message(Command("tape"))
@router.message(F.text == "🎙 نوار کاست سرهنگ")
async def cmd_tape(message: Message):
    """Eerie cassette tape transcript & real audio soundscape from 1356."""
    if TAPE_VOICE_FILE_ID:
        try:
            await message.answer_voice(
                voice=TAPE_VOICE_FILE_ID,
                caption="🎙 نوار کاست صوتی شماره ۷ سرهنگ — آبان ۱۳۵۶"
            )
        except Exception:
            pass
    elif AUDIO_TAPE_PATH.exists():
        try:
            audio_file = FSInputFile(str(AUDIO_TAPE_PATH), filename="colonel_tape_1356.wav")
            await message.answer_voice(
                voice=audio_file,
                caption="🎙 نوار کاست صوتی شماره ۷ سرهنگ — آبان ۱۳۵۶"
            )
        except Exception:
            pass

    await message.answer(game.COLONEL_CASSETTE_TRANSCRIPT)

@router.message(Command("mission"))
@router.message(F.text.in_(["📜 طومار و ماموریت مخفی", "📜 ماموریت مخفی"]))
async def cmd_mission(message: Message):
    """Displays the player's secret social mission for party immunity, unlocked at 29 Oct 18:00 Tehran."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return

    if guest.get("role") != "role_player":
        await message.answer(
            "🥂 **مخصوص بلوندهای بی‌گناه:**\n\n"
            "شما وارد بازی خطرناک نخواهید شد و نیازی به ماموریت ندارید!\n"
            "وظیفه شما لذت بردن از رقص، نوشیدنی، تماشای فیلم در سالن گرم، و تماشای فرار دیگران است."
        )
        return

    # Check if missions are unlocked (29 October at 18:00 Tehran)
    if not await is_mission_unlocked():
        now = datetime.now(TEHRAN_TZ)
        diff = MISSION_UNLOCK_TIME - now
        total_seconds = max(0, int(diff.total_seconds()))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        countdown_str = f"{hours} ساعت و {minutes} دقیقه" if hours > 0 else f"{minutes} دقیقه"

        await message.answer(
            f"⏳ **طومار مخفی هنوز مُهر و موم است!**\n\n"
            f"🔒 ماموریت‌های مخفی نفوذ و مصونیت در عمارت، رأس ساعت **۱۸:۰۰ روز پنجشنبه ۲۹ اکتبر (۷ آبان)** "
            f"به وقت شیراز، به صورت خودکار در همین صفحه رمزگشایی و گشوده خواهند شد.\n\n"
            f"⏱ **زمان باقی‌مانده تا گشایش طومارها:** {countdown_str}\n\n"
            f"💡 *تا آن ساعت هویت و نقش خود را از دیگران مخفی نگه دارید...*"
        )
        return

    mission_id = guest.get("social_mission_id", 1)
    mission_text = game.SOCIAL_MISSIONS.get(mission_id, game.SOCIAL_MISSIONS[1])
    is_immune = guest.get("is_immune", 0)
    got_stickered = guest.get("got_stickered", 0)

    status_str = "🛡 **وضعیت شما:** مصونیت فعال است (غیرقابل تسخیر)" if is_immune else (
        "💀 **وضعیت شما:** استیکر خورده و تسخیر شده!" if got_stickered else "⚠️ **وضعیت شما:** آسیب‌پذیر در برابر ۵ تسخیرشده!"
    )

    text = (
        f"📜 **ماموریت اجتماعی شما برای فعال‌سازی طلسم مصونیت:**\n\n"
        f"🎯 **ماموریت مخفی شما (لمس کنید تا نمایان شود):**\n"
        f"||{mission_text}||\n\n"
        f"{status_str}\n\n"
        f"💡 به محض انجام این ماموریت در سالن مهمانی، دکمه‌ی زیر را لمس کنید تا کارت سبز طلسم مصونیت صادر شود."
    )

    kb = keyboards.social_mission_player_kb(is_immune=bool(is_immune), got_stickered=bool(got_stickered))
    await message.answer(text, reply_markup=kb)

@router.message(Command("change_role"))
@router.callback_query(F.data == "req_change_role")
async def handle_change_role_request(event: Message | CallbackQuery):
    """Allows players and blondes to change their roles before 29 Oct 18:00 Tehran."""
    message = event if isinstance(event, Message) else event.message
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    if not await can_change_role():
        await message.answer(
            "⛔️ **مهلت تغییر نقش به پایان رسیده است!**\n\n"
            "ساعت ۱۸:۰۰ روز ۲۹ اکتبر فرا رسیده و سرنوشت تمامی مهمانان عمارت قفل شده است."
        )
        return

    guest = await database.get_guest_by_telegram_id(user_id)
    if not guest or not guest.get("role"):
        await message.answer("⚠️ شما هنوز ثبت‌نام خود را در مهمانی تکمیل نکرده‌اید.")
        return

    current_role = guest["role"]
    if current_role == "role_player":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👱‍♀️ تغییر نقش به: بلوند بی‌گناه (حاشیه امن سالن)",
                        callback_data="switch_role_blonde"
                    )
                ]
            ]
        )
        await message.answer(
            "⚖️ **تغییر سرنوشت و نقش در مهمانی:**\n\n"
            "نقش فعلی شما: **🕯 بازیکن**\n\n"
            "آیا مایلید به گروه «بلوندهای بی‌گناه» (حاشیه امن سالن، نوشیدنی، فیلم و رقص) جابجا شوید؟\n"
            "*(مهلت تغییر: تا ساعت ۱۸:۰۰ روز ۲۹ اکتبر)*",
            reply_markup=kb
        )
    else:
        # currently blonde
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🕯 تغییر نقش به: بازیکن (ورود به بازی)",
                        callback_data="switch_role_player"
                    )
                ]
            ]
        )
        await message.answer(
            "⚖️ **تغییر سرنوشت و نقش در مهمانی:**\n\n"
            "نقش فعلی شما: **👱‍♀️ بلوند بی‌گناه**\n\n"
            "آیا مایلید وارد بازی شوید و به گروه «بازیکنان» بپیوندید؟\n"
            "*(مهلت تغییر: تا ساعت ۱۸:۰۰ روز ۲۹ اکتبر)*",
            reply_markup=kb
        )

@router.callback_query(F.data == "switch_role_blonde")
async def cb_switch_to_blonde(callback: CallbackQuery):
    """Switches user to innocent blonde."""
    if not await can_change_role():
        await callback.answer("مهلت تغییر نقش به پایان رسیده است!", show_alert=True)
        return

    await callback.answer("نقش شما با موفقیت تغییر کرد!")
    guest = await database.set_guest_role(callback.from_user.id, "role_blonde")
    from handlers.user import send_existing_card
    await callback.message.answer("🎉 **نقش شما با موفقیت به «بلوند بی‌گناه» تغییر یافت!**\nکارت دعوت جدید شما صادر گردید:")
    await send_existing_card(callback, guest)

@router.callback_query(F.data == "switch_role_player")
async def cb_switch_to_player(callback: CallbackQuery):
    """Switches user to player (if cap not exceeded)."""
    if not await can_change_role():
        await callback.answer("مهلت تغییر نقش به پایان رسیده است!", show_alert=True)
        return

    player_count = await database.count_role("role_player")
    if player_count >= config.PLAYER_CAP:
        await callback.answer("ظرفیت گروه بازیکنان (۲۰ نفر) پر است!", show_alert=True)
        return

    await callback.answer("نقش شما با موفقیت تغییر کرد!")
    guest = await database.set_guest_role(callback.from_user.id, "role_player")
    from handlers.user import send_existing_card
    await callback.message.answer("🎉 **نقش شما با موفقیت به «بازیکن» تغییر یافت!**\nکارت دعوت جدید شما صادر گردید:")
    await send_existing_card(callback, guest)

@router.callback_query(F.data == "claim_immunity")
async def cb_claim_immunity(callback: CallbackQuery):
    """Awards immunity to player upon mission completion and sends green immunity shield image."""
    guest = await database.get_guest_by_telegram_id(callback.from_user.id)
    if not guest:
        await callback.answer("اطلاعات شما یافت نشد!", show_alert=True)
        return

    if guest.get("is_immune") == 1:
        await callback.answer("مصونیت شما قبلاً ثبت و صادر شده است!", show_alert=True)
        return

    await database.set_mission_completed(callback.from_user.id)
    await callback.answer("🎉 طلسم مصونیت شما فعال شد!", show_alert=True)

    # Generate bright green immunity screen
    pin = guest.get("soul_pin") or f"{(guest.get('serial_number', 1) * 73 + 137) % 900 + 100}"
    card_buf = card_generator.generate_immunity_card(guest["full_name"], pin)
    photo_file = BufferedInputFile(card_buf.getvalue(), filename="immunity_shield.png")

    caption = (
        "🛡 **[طلسم مصونیت شما صادر و فعال شد!]**\n\n"
        "تبریک! شما ماموریت اجتماعی خود را به انجام رساندید.\n"
        "این تصویر سبز را به صورت تمام‌صفحه به افراد تسخیرشده نشان دهید.\n"
        "هیچ تسخیرشده‌ای حق چسباندن استیکر به شما را ندارد!"
    )
    await callback.message.answer_photo(photo=photo_file, caption=caption)

@router.callback_query(F.data == "got_stickered")
async def cb_got_stickered(callback: CallbackQuery):
    """Player marks that they received a sticker from an infected guest."""
    await database.mark_stickered(callback.from_user.id)
    await callback.answer("💀 وضعیت شما به عنوان استیکر خورده ثبت شد!", show_alert=True)
    await callback.message.answer(texts.STICKERED_ALERT)

@router.message(Command("solve"))
async def cmd_solve(message: Message, bot: Bot):
    """
    Submits and verifies an answer for the team's garden envelope riddles.
    Triggered via /solve <پاسخ>.
    """
    user_answer = message.text.partition(" ")[2].strip()
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return

    if guest.get("role") != "role_player":
        await message.answer("🍿 شما بلوند بی‌گناه هستید و نیازی به ورود به معمای تاریکی حیاط ندارید!")
        return

    team_num = guest.get("team_number")
    if not team_num or team_num < 1 or team_num > 4:
        await message.answer("⚠️ شما هنوز در تیمی دسته‌بندی نشده‌اید یا بازی نیمه‌شب هنوز کلید نخورده است.")
        return

    if not user_answer:
        t_info = game.TEAM_RIDDLES.get(team_num, {})
        t_name = t_info.get("name", f"تیم {team_num}")
        r1_solved = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
        r2_solved = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"

        status_lines = [
            f"🔍 **وضعیت معماهای {t_name}:**\n",
            f"• پاکت اول: {'✅ حل شده' if r1_solved else '⏳ هنوز حل نشده'}",
            f"• پاکت دوم: {'✅ حل شده' if r2_solved else '⏳ هنوز حل نشده'}",
            "\nبرای ارسال پاسخ معما بنویسید:",
            "`/solve <پاسخ شما>`"
        ]
        await message.answer("\n".join(status_lines))
        return

    res = await database.check_team_riddle(message.from_user.id, user_answer)
    status = res.get("status")

    if status == "already_both_solved":
        await message.answer(
            "🔓 **تیم شما قبلاً هر دو معما را حل کرده است!**\n\n"
            + game.CLIMAX_INSTRUCTIONS
        )
        return

    if status == "already_solved":
        r_num = res.get("riddle_num", 1)
        await message.answer(
            f"⚠️ **معمای شماره {r_num} قبلاً توسط تیم شما حل شده است!**\n"
            f"لطفاً پاکت دیگر را در باغ پیدا کنید و پاسخ آن را ارسال نمایید."
        )
        return

    if status == "riddle_solved":
        r_num = res.get("riddle_num", 1)
        await message.answer(
            f"🎉 **معمای شماره {r_num} با موفقیت حل شد!**\n\n"
            f"عالی بود! حالا پاکت دوم را در باغ پیدا کنید و پاسخ آن را با `/solve <پاسخ>` ارسال نمایید."
        )
        # Notify other teammates
        teammates = await database.get_team_members(team_num)
        for tm in teammates:
            if tm["telegram_id"] and tm["telegram_id"] != message.from_user.id:
                try:
                    await bot.send_message(
                        chat_id=tm["telegram_id"],
                        text=f"⚡️ یکی از هم‌تیمی‌های شما معمای شماره {r_num} را با موفقیت حل کرد! پاکت بعدی را پیدا کنید."
                    )
                except Exception:
                    pass
        return

    if status == "both_solved":
        # Climax unlocked for the whole team!
        teammates = await database.get_team_members(team_num)
        for tm in teammates:
            if tm.get("telegram_id"):
                try:
                    await bot.send_message(
                        chat_id=tm["telegram_id"],
                        text=game.CLIMAX_INSTRUCTIONS
                    )
                except Exception:
                    pass
        return

    if status == "wrong":
        # Wrong answer warning + audio trap
        if AUDIO_TAPE_PATH.exists():
            try:
                audio_file = FSInputFile(str(AUDIO_TAPE_PATH), filename="colonel_warning.wav")
                await message.answer_voice(
                    voice=audio_file,
                    caption=texts.WRONG_ANSWER_TRAP
                )
                return
            except Exception:
                pass
        await message.answer(texts.WRONG_ANSWER_TRAP)

@router.message(Command("team"))
@router.message(F.text == "🔦 تیم من در حیاط")
async def cmd_team(message: Message):
    """Shows player's midnight team, teammates, and secret traitor brief."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با /start در سیستم ثبت‌نام کنید.")
        return

    if guest.get("role") != "role_player":
        await message.answer(
            "🍿 شما در گروه بلوندهای بی‌گناه هستید و شب را در سالن گرم همراه با فیلم و تنقلات سپری خواهید کرد."
        )
        return

    team_num = guest.get("team_number")
    if not team_num:
        await message.answer(
            "⏳ **تیم‌های حیاط هنوز نهایی نشده‌اند.**\n"
            "تیم‌بندی‌های حیاط در ساعت ۰۰:۳۰ بامداد هم‌زمان با خاموشی و آغاز بازی اعلام خواهد شد."
        )
        return

    teammates = await database.get_team_members(team_num)
    names = [m["full_name"] for m in teammates]
    team_name = guest.get("team_name") or f"تیم {team_num}"

    r1_solved = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2_solved = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"

    traitor_text = ""
    if guest.get("is_traitor") == 1:
        traitor_text = (
            "\n\n🐍 **[پیام فوق‌محرمانه: تو خائن تیمت هستی!]**\n"
            "هدف تو این است که تیمت در طبقه دوم کلمات رمز را اشتباه در گوش جنازه سرهنگ بگوید! "
            "سعی کن در تاریکی صدای تله‌ها را دربیاوری یا تیمت را قانع کنی که کلمه دوم رمز «مرگ» است نه «سایه»!"
        )

    msg = (
        f"🔦 **اطلاعات تیم شما در بازی نیمه‌شب حیاط:**\n\n"
        f"🏷 **نام تیم:** {team_name}\n"
        f"👥 **هم‌تیمی‌های شما:** {'، '.join(names)}\n\n"
        f"📊 **وضعیت معماها:**\n"
        f"• پاکت اول: {'✅ حل شد' if r1_solved else '⏳ در حال جستجو'}\n"
        f"• پاکت دوم: {'✅ حل شد' if r2_solved else '⏳ در حال جستجو'}\n\n"
        f"💡 پاسخ هر پاکت را با دستور `/solve <پاسخ>` ارسال کنید."
        f"{traitor_text}"
    )
    await message.answer(msg)

@router.message(Command("rescue"))
@router.message(F.text.in_(["💡 روشن کردن نور حیات باغ", "💡 روشن کردن نور حیاط باغ", "💡 روشن کردن نورافکن باغ"]))
async def cmd_rescue(message: Message, bot: Bot):
    """Blondes can trigger emergency courtyard lights to temporarily blind the ghost."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در سیستم ثبت‌نام کنید.")
        return

    rescue_count = int(await database.get_game_state("rescue_count", "0"))
    if rescue_count >= 3:
        await message.answer("⚠️ انرژی ژنراتور باغ تمام شده است! حداکثر ۳ بار امکان روشن کردن نور حیات باغ وجود داشت.")
        return

    await database.set_game_state("rescue_count", str(rescue_count + 1))
    await message.answer(f"💡 نور حیات باغ به مدت ده ثانیه روشن میشود. ({rescue_count + 1}/3)")

    players = await database.get_all_telegram_ids(role_filter="role_player")
    for pid in players:
        try:
            await bot.send_message(
                chat_id=pid,
                text="💡 **[امداد از سالن — نور حیات باغ روشن شد!]**\n\nبلوندهای بی‌گناه از پشت پنجره نور حیات باغ را روشن کردند! روح سرهنگ موقتاً کور شد؛ الان زمان فرار و پیدا کردن پاکت طلسم است!"
            )
        except Exception:
            pass

@router.message(Command("lantern"))
@router.message(Command("red_lantern"))
@router.message(F.text == "🔴 فانوس سرخ دیجیتال")
async def cmd_red_lantern(message: Message):
    """Sends the Red Lantern full-screen phone image + survival instructions."""
    caption = (
        "🔴 **[فانوس سرخ دیجیتال — تنها نور مجاز در عمارت]** 🕯\n\n"
        "📱 **دستورالعمل مهم:** این تصویر را به صورت **تمام‌صفحه (Full-Screen)** روی سیستم یا گوشی خود باز کنید و نور صفحه را بالا ببرید.\n\n"
        "⚠️ **تنها نوری که سرهنگ به آن حساس نیست همین است!**\n"
        "سرهنگ در پاییز ۱۳۵۶ در تاریک‌خانه عکاسی‌اش به نور سرخ الفت داشته و به آن کاملاً نابیناست؛ "
        "اما هرگونه نور سفید، چراغ‌قوه یا صفحه عادی گوشی فوراً سرهنگ را به سمت موقعیت شما کشانده و باعث شکار تیمتان می‌شود!\n\n"
        "💡 در طول بازی نیمه‌شب در حیاط، این تصویر را باز نگه دارید و بدون هیچ صدای اضافه‌ای حرکت کنید."
    )
    kb = keyboards.midnight_action_kb()
    if LANTERN_PHOTO_FILE_ID:
        try:
            await message.answer_photo(photo=LANTERN_PHOTO_FILE_ID, caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    if RED_LANTERN_PATH.exists():
        photo_file = FSInputFile(str(RED_LANTERN_PATH), filename="red_lantern.jpg")
        await message.answer_photo(photo=photo_file, caption=caption, reply_markup=kb)
    else:
        await message.answer(caption, reply_markup=kb)

@router.callback_query(F.data == "dl_lantern")
async def cb_dl_lantern(callback: CallbackQuery):
    """Re-sends the red lantern photo for full-screen display."""
    await callback.answer("فانوس سرخ دیجیتال")
    caption = (
        "🔴 **[فانوس سرخ دیجیتال — تنها نور مجاز در عمارت]** 🕯\n\n"
        "📱 تصویر را لمس کنید و به صورت **تمام‌صفحه (Full-Screen)** روی گوشی باز نگه دارید.\n\n"
        "⚠️ **تنها نوری که سرهنگ به آن حساس نیست همین است!**\n"
        "سرهنگ به نور سرخ تاریک‌خانه الفت داشته و به آن کاملاً نابیناست؛ "
        "روشن کردن هرگونه چراغ سفید یا صفحه عادی گوشی = شکار فوری توسط روح سرهنگ!"
    )
    kb = keyboards.midnight_action_kb()
    if LANTERN_PHOTO_FILE_ID:
        try:
            await callback.message.answer_photo(photo=LANTERN_PHOTO_FILE_ID, caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    if RED_LANTERN_PATH.exists():
        photo_file = FSInputFile(str(RED_LANTERN_PATH), filename="red_lantern.jpg")
        await callback.message.answer_photo(photo=photo_file, caption=caption, reply_markup=kb)
    else:
        await callback.message.answer(caption, reply_markup=kb)

@router.callback_query(F.data == "chk_team")
async def cb_chk_team(callback: CallbackQuery):
    """Shows team status and riddle progression from inline button."""
    await callback.answer()
    guest = await database.get_guest_by_telegram_id(callback.from_user.id)
    if not guest:
        await callback.message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return

    team_num = guest.get("team_number")
    if not team_num:
        await callback.message.answer("⏳ تیم‌بندی شما در ساعت ۰۰:۳۰ اعلام خواهد شد.")
        return

    teammates = await database.get_team_members(team_num)
    names = [m["full_name"] for m in teammates]
    team_name = guest.get("team_name") or f"تیم {team_num}"
    r1_solved = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2_solved = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"

    traitor_text = ""
    if guest.get("is_traitor") == 1:
        traitor_text = (
            "\n\n🐍 **[پیام فوق‌محرمانه: تو خائن تیمت هستی!]**\n"
            "هدف تو این است که تیمت در طبقه دوم کلمات رمز را اشتباه در گوش جنازه سرهنگ بگوید!"
        )

    msg = (
        f"🔦 **اطلاعات تیم شما در بازی نیمه‌شب حیاط:**\n\n"
        f"🏷 **نام تیم:** {team_name}\n"
        f"👥 **هم‌تیمی‌های شما:** {'، '.join(names)}\n\n"
        f"📊 **وضعیت معماها:**\n"
        f"• پاکت اول: {'✅ حل شد' if r1_solved else '⏳ در حال جستجو روی درختان'}\n"
        f"• پاکت دوم: {'✅ حل شد' if r2_solved else '⏳ در حال جستجو روی درختان'}\n\n"
        f"💡 پاسخ هر پاکت را با دستور `/solve <پاسخ>` ارسال کنید."
        f"{traitor_text}"
    )
    await callback.message.answer(msg, reply_markup=keyboards.midnight_action_kb())

@router.callback_query(F.data == "help_solve")
async def cb_help_solve(callback: CallbackQuery):
    """Shows how to submit riddle solutions."""
    await callback.answer("راهنمای حل معما")
    msg = (
        "🧩 **راهنمای ثبت پاسخ معماها در حیاط:**\n\n"
        "۱. روی درختان باغ به دنبال پاکت‌های چسبانده‌شده‌ی تیم خود بگردید.\n"
        "۲. پس از خواندن شعر معما و مشورت با هم‌تیمی‌ها، جواب را با این فرمت بنویسید:\n"
        "`/solve <پاسخ شما>`\n\n"
        "📌 **مثال:** `/solve خون` یا `/solve ۱۳۵۶`\n\n"
        "⚠️ **هشدار مرگبار:** اگر جواب اشتباه ارسال کنید، صدای شکستن شاخه‌ها پخش می‌شود و سرهنگ بلافاصله به سمت تیم شما هجوم می‌آورد!"
    )
    await callback.message.answer(msg, reply_markup=keyboards.midnight_action_kb())

@router.message(Command("rules"))
@router.callback_query(F.data == "rules_midnight")
async def cb_rules_midnight(event: Message | CallbackQuery):
    """Re-sends the full midnight game rules."""
    if isinstance(event, CallbackQuery):
        await event.answer("قوانین بازی")
        target = event.message
    else:
        target = event
    await target.answer(texts.MIDNIGHT_RULES_BRIEFING, reply_markup=keyboards.midnight_action_kb())

@router.message(Command("carpool"))
@router.message(F.text == "🚗 کاروان صدرا")
async def cmd_carpool(message: Message):
    """Displays guest's assigned car in the 13-car convoy with fellow passengers and driver's Telegram contact."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start ثبت‌نام کنید.")
        return

    car_num = guest.get("car_number") or await database.find_best_carpool_match(guest["full_name"])
    driver_info = await database.get_driver_info_for_car(car_num)
    driver_contact = database.format_driver_contact(driver_info)
    manifest = await database.get_carpool_manifest()
    car_info = manifest.get(car_num, {})

    other_passengers = [p for p in car_info.get("passengers", []) if p != guest["full_name"]]
    pass_str = "، ".join(other_passengers) if other_passengers else "در حال تکمیل ظرفیت ۴ نفره"

    car_type = "🚗 کاپیتان و راننده خودرو" if guest.get("has_car") == 1 else "🚶 مسافر و سرنشین خودرو"
    seats_left = car_info.get("seats_left", max(0, 4 - car_info.get("total_count", 0)))
    seats_info = f"({seats_left} صندلی خالی تا سقف ۴ نفر)" if seats_left > 0 else "(ظرفیت ۴ نفره تکمیل است)"

    await message.answer(
        f"🚗 **اطلاعات خودروی شما در کاروان ۱۳ تایی صدرا:**\n\n"
        f"🔢 **شماره خودرو:** خودروی شماره {car_num} {seats_info}\n"
        f"🚘 **راننده خودرو:** {driver_contact}\n"
        f"👥 **همسفران شما در این خودرو:** {pass_str}\n"
        f"👤 **وضعیت شما:** {car_type}\n"
        f"📍 **زمان و مکان تجمع:** پنجشنبه ۷ آبان — ساعت ۱۷:۳۰ رأس ورودی صدرا\n\n"
        f"⛔️ **یادآوری مهم:** دروازه‌ی عمارت از ساعت ۱۸:۱۵ تا ۲۴:۰۰ قفل خواهد بود و خروج زودهنگام امکان‌پذیر نیست."
    )

@router.message(Command("graveyard"))
@router.message(F.text == "⚰️ وضعیت زنده عمارت")
async def cmd_graveyard(message: Message):
    """Shows live survival and stickered scoreboard."""
    stats = await database.get_stats()
    players = stats["players"]
    immune = stats["immune"]
    stickered = stats.get("stickered", 0)
    survivors = max(0, players - stickered)

    msg = (
        "⚰️ **جدول زنده ارواح و بقای عمارت باغ سرهنگ:**\n\n"
        f"🕯 **کل بازیکنان:** {players} نفر\n"
        f"🛡 **افراد دارای طلسم مصونیت:** {immune} نفر\n"
        f"💀 **افرادی که استیکر خورده‌اند:** {stickered} نفر\n"
        f"✨ **بازماندگان آزاد:** {survivors} نفر\n\n"
        f"*(ساعت ۲۴:۰۰ سرنوشت نهایی در تاریکی حیاط تعیین خواهد شد...)*"
    )
    await message.answer(msg)
