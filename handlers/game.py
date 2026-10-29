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

AUDIO_TAPE_PATH = Path("assets/audio/colonel_tape.ogg")
if not AUDIO_TAPE_PATH.exists():
    AUDIO_TAPE_PATH = Path("assets/audio/colonel_tape.wav")
RED_LANTERN_PATH = Path("assets/images/red_lantern.jpg")

TAPE_VOICE_FILE_ID = "AwACAgEAAxkDAAPDat86rJlyDDgFkfZVQRQhnPOnQxoAAn0IAALxQwABR1JeOJYDRyIwPQQ"
LANTERN_PHOTO_FILE_ID = "AgACAgEAAxkDAAOVat7mnZbQOE2oLNWQTFy0mWEbNVIAAhANaxvxQ_hGMirKbWdvIo4BAAMCAAN5AAM9BA"

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))
MISSION_UNLOCK_TIME = datetime(2026, 10, 29, 19, 30, 0, tzinfo=TEHRAN_TZ)

TESTER_IDS = {102725917}
TESTER_USERNAMES = {"hamixon", "hamixn"}

def is_tester(user_id: int, username: str | None = None) -> bool:
    if user_id in TESTER_IDS:
        return True
    if config.ADMIN_USER_ID != 0 and user_id == config.ADMIN_USER_ID:
        return True
    if username and username.lower().lstrip("@") in TESTER_USERNAMES:
        return True
    return False

async def is_mission_unlocked(user_id: int | None = None, username: str | None = None) -> bool:
    """Checks if missions are unlocked (past 29 Oct 19:30 Tehran or forced by admin or tester)."""
    if user_id and is_tester(user_id, username):
        return True
    forced = await database.get_game_state("force_unlock_missions", "0")
    if forced == "1":
        return True
    now = datetime.now(TEHRAN_TZ)
    return now >= MISSION_UNLOCK_TIME

async def can_change_role(user_id: int | None = None, username: str | None = None) -> bool:
    """Checks if guests can still change their role (before 29 Oct 19:30 Tehran)."""
    if user_id and is_tester(user_id, username):
        return True
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
@router.message(F.text.in_(["📜 طومار و ماموریت مخفی", "📜 ماموریت مخفی", "📜 ثبت آلیبای و ماموریت"]))
async def cmd_mission(message: Message):
    """Displays the player's secret social mission for party alibi/evidence logging (19:30 to 23:50)."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return

    # Auto-assign tester to Team 1 if not yet configured
    if is_tester(message.from_user.id, message.from_user.username):
        if guest.get("role") != "role_player" or not guest.get("team_number"):
            await database.assign_tester_team(message.from_user.id, guest.get("team_number") or 1)
            guest = await database.get_guest_by_telegram_id(message.from_user.id)

    if guest.get("role") != "role_player":
        await message.answer(
            "🥂 **مخصوص همراهان مهمانی (بلوندهای بی‌گناه):**\n\n"
            "حضور در پرونده و ماموریت‌های تحقیق کاملاً اختیاری است.\n"
            "شما آزادی کامل دارید تا از موسیقی، رقص، پذیرایی و فضای هالووین لذت ببرید."
        )
        return

    # Check if missions are unlocked (19:30 to 23:50 or tester)
    if not await is_mission_unlocked(message.from_user.id, message.from_user.username):
        now = datetime.now(TEHRAN_TZ)
        diff = MISSION_UNLOCK_TIME - now
        total_seconds = max(0, int(diff.total_seconds()))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        countdown_str = f"{hours} ساعت و {minutes} دقیقه" if hours > 0 else f"{minutes} دقیقه"

        await message.answer(
            f"⏳ **پرونده‌ی بازی اجتماعی هنوز بازگشایی نشده است!**\n\n"
            f"🔒 بازی اجتماعی و ثبت آلیبای (۱۹:۳۰ تا ۲۳:۵۰)، رأس ساعت **۱۹:۳۰** "
            f"به صورت خودکار در همین بخش فعال خواهد شد.\n\n"
            f"⏱ **زمان باقی‌مانده:** {countdown_str}\n\n"
            f"💡 *این ماموریت‌ها فعالیتی پس‌زمینه و کاملاً اختیاری برای ثبت مدارک هستند.*"
        )
        return

    mission_id = guest.get("social_mission_id", 1)
    mission_text = game.SOCIAL_MISSIONS.get(mission_id, game.SOCIAL_MISSIONS[1])
    is_immune = guest.get("is_immune", 0)
    has_shield = (guest.get("alibi_shields") or 0) > 0

    if has_shield:
        status_str = "🛡 **وضعیت شما:** ۱ سپر آلیبای فعال دارید (خنثی‌کننده ۱ استیکر فیزیکی)."
    elif is_immune:
        status_str = texts.ALIBI_LOGGED_BADGE
    else:
        status_str = "⏳ **وضعیت شما:** آلیبای شما هنوز در پرونده ثبت نشده است."

    text = (
        "📜 **بازی اجتماعی و ثبت آلیبای (فعالیت پس‌زمینه و کاملاً اختیاری — ۱۹:۳۰ تا ۲۳:۵۰):**\n\n"
        f"🎯 **روایت ماموریت شما جهت ثبت حضور:**\n"
        f"||{mission_text}||\n\n"
        f"{status_str}\n\n"
        "💡 پس از انجام این گفت‌وگو در سالن، دکمه‌ی «✅ ماموریتم رو انجام دادم!» را بزنید تا ۱ سپر آلیبای دریافت کنید.\n"
        "*(این سپر برای خنثی‌کردن یک استیکر فیزیکی است و مصونیت دائمی ایجاد نمی‌کند)*"
    )

    kb = keyboards.social_mission_player_kb(
        is_immune=bool(is_immune),
        got_stickered=bool(guest.get("got_stickered", 0)),
        has_shield=has_shield
    )
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
    """Awards alibi / evidence badge and at most one alibi shield to player."""
    guest = await database.get_guest_by_telegram_id(callback.from_user.id)
    if not guest:
        await callback.answer("اطلاعات شما یافت نشد!", show_alert=True)
        return

    res = await database.grant_alibi_shield(callback.from_user.id)
    if res.get("status") == "already_has_shield":
        await callback.answer("شما در حال حاضر یک سپر آلیبای فعال دارید!", show_alert=True)
        await callback.message.answer(
            "🛡 **سپر آلیبای شما فعال است:**\n"
            "شما هم‌اکنون یک سپر آلیبای آماده‌ی مصرف دارید. در صورت چسبانده‌شدن استیکر، با فشردن دکمه‌ی مصرف سپر یا دستور `/use_alibi` آن را باطل کنید."
        )
        return

    await callback.answer("📋 آلیبای شما ثبت شد!", show_alert=True)
    await callback.message.answer(
        f"{texts.ALIBI_LOGGED_BADGE}\n\n"
        "🛡 **یک سپر آلیبای تک‌بار مصرف به شما اعطا شد.**\n"
        "این سپر مصونیت دائمی ایجاد نمی‌کند، بلکه تنها برای خنثی کردن ۱ عدد استیکر فیزیکی است.\n"
        "در صورتی که استیکری به شما زده شد، می‌توانید با زدن دکمه‌ی «🛡 مصرف سپر آلیبای» یا دستور `/use_alibi` آن را خنثی نمایید."
    )

@router.message(Command("use_alibi"))
@router.callback_query(F.data == "use_alibi")
async def handle_use_alibi(event: Message | CallbackQuery):
    """Consumes the player's single one-use alibi shield to cancel a physical sticker."""
    message = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await event.answer()

    res = await database.use_alibi_shield(event.from_user.id)
    if res.get("status") == "consumed":
        await message.answer(
            "🛡 **[سپر آلیبای شما مصرف گردید]**\n\n"
            "یک استیکر فیزیکی با موفقیت باطل شد و وضعیت استیکر شما پاکسازی گردید.\n"
            "*(این سپر یک‌بار مصرف بود و اکنون منقضی شده است)*"
        )
    elif res.get("status") == "no_shield":
        await message.answer(
            "⚠️ **شما سپر آلیبای فعالی برای مصرف ندارید!**\n"
            "برای کسب سپر، ابتدا ماموریت اجتماعی خود را از طریق دستور /mission انجام دهید."
        )
    else:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")

@router.callback_query(F.data == "got_stickered")
async def cb_got_stickered(callback: CallbackQuery):
    """Player marks that they received a sticker from a witness/suspect carrier."""
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

    # Auto-assign tester to Team 1 if not yet configured
    if is_tester(message.from_user.id, message.from_user.username):
        if guest.get("role") != "role_player" or not guest.get("team_number"):
            await database.assign_tester_team(message.from_user.id, guest.get("team_number") or 1)
            guest = await database.get_guest_by_telegram_id(message.from_user.id)

    if guest.get("role") != "role_player":
        await message.answer("🍿 شما همراه مهمانی (بلوند بی‌گناه) هستید و نیازی به ورود به معمای تاریکی حیاط ندارید!")
        return

    phase = await database.get_game_state("game_phase", "registration")
    if phase != "midnight_investigation":
        await message.answer("⏳ ثبت پاسخ معما فقط پس از اعلام رسمی آغاز تحقیقات نیمه‌شب فعال می‌شود.")
        return

    team_num = guest.get("team_number")
    if not team_num or team_num < 1 or team_num > 4:
        await message.answer("⚠️ شما هنوز در تیمی دسته‌بندی نشده‌اید یا فاز کشف مدارک هنوز کلید نخورده است.")
        return

    if not user_answer:
        t_info = game.TEAM_RIDDLES.get(team_num, {})
        t_name = t_info.get("name", f"تیم {team_num}")
        r1_solved = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
        r2_solved = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"

        status_lines = [
            f"🔍 **وضعیت مدارک {t_name}:**\n",
            f"• پاکت اول: {'✅ مدرک ثبت شده' if r1_solved else '⏳ هنوز ثبت نشده'}",
            f"• پاکت دوم: {'✅ مدرک ثبت شده' if r2_solved else '⏳ هنوز ثبت نشده'}",
            "\nبرای ثبت پاسخ معما بنویسید:",
            "`/solve <پاسخ شما>`"
        ]
        await message.answer("\n".join(status_lines))
        return

    res = await database.check_team_riddle(message.from_user.id, user_answer)
    status = res.get("status")

    if status == "already_both_solved":
        await message.answer(
            "🔓 **تیم شما قبلاً هر دو مدرک را ثبت کرده است!**\n\n"
            "مدارک را با دقت بررسی کنید و نظریه نهایی خود را با دستور `/accuse` ثبت نمایید."
        )
        return

    if status == "already_solved":
        r_num = res.get("riddle_num", 1)
        await message.answer(
            res.get("response_text", f"⚠️ مدرک پاکت شماره {r_num} قبلاً توسط تیم شما ثبت شده است!")
        )
        return

    if status == "riddle_solved":
        r_num = res.get("riddle_num", 1)
        resp_text = res.get("response_text", "✅ مدرک با موفقیت ثبت شد.")
        # Deliver clue privately to sender
        await message.answer(resp_text)

        # Broadcast completion to teammates ONLY (excluding sender)
        teammates = await database.get_team_members(team_num)
        for tm in teammates:
            if tm.get("telegram_id") and tm["telegram_id"] != message.from_user.id:
                try:
                    await bot.send_message(
                        chat_id=tm["telegram_id"],
                        text=f"⚡️ یکی از هم‌تیمی‌های شما مدرک پاکت شماره {r_num} را ثبت کرد:\n\n{resp_text}"
                    )
                except Exception:
                    pass
        return

    if status == "both_solved":
        r_num = res.get("just_solved", 2)
        resp_text = res.get("response_text", "✅ مدرک با موفقیت ثبت شد.")
        # Deliver clue privately to sender
        await message.answer(resp_text)

        # Broadcast completion to teammates ONLY (excluding sender)
        teammates = await database.get_team_members(team_num)
        for tm in teammates:
            if tm.get("telegram_id") and tm["telegram_id"] != message.from_user.id:
                try:
                    await bot.send_message(
                        chat_id=tm["telegram_id"],
                        text=f"⚡️ یکی از هم‌تیمی‌های شما مدرک پاکت شماره {r_num} را ثبت کرد:\n\n{resp_text}"
                    )
                except Exception:
                    pass

        # Exact-once completion notification when both envelopes are solved
        if res.get("just_completed"):
            completion_msg = (
                "📁 **هر دو مدرک تیم شما با موفقیت ثبت شد!**\n\n"
                "شواهد کاغذی را بررسی کنید و با دستور `/accuse` نظریه اتهام خود را ثبت نمایید."
            )
            for tm in teammates:
                if tm.get("telegram_id"):
                    try:
                        await bot.send_message(
                            chat_id=tm["telegram_id"],
                            text=completion_msg
                        )
                    except Exception:
                        pass
        return

    if status == "other_team_riddle":
        resp_text = res.get("response_text", texts.OTHER_TEAM_CODE_ALERT)
        await message.answer(resp_text)
        return

    if status == "wrong":
        resp_text = res.get("response_text", texts.WRONG_ANSWER_TRAP)
        await message.answer(resp_text)

@router.message(Command("team"))
@router.message(F.text == "🔦 تیم من در حیاط")
async def cmd_team(message: Message):
    """Reveal team assignment only after the host starts midnight."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با /start در سیستم ثبت‌نام کنید.")
        return
    if guest.get("role") != "role_player":
        await message.answer("🍿 شما در گروه بلوندهای بی‌گناه هستید و شب را در سالن گرم همراه فیلم و پذیرایی می‌گذرانید.")
        return

    phase = await database.get_game_state("game_phase", "registration")
    if phase not in ("midnight_investigation", "central_deduction", "finale", "completed"):
        await message.answer("⏳ تیم شما تا زمان اعلام رسمی شروع تحقیقات نیمه‌شب محرمانه می‌ماند.")
        return

    team_num = guest.get("team_number")
    if is_tester(message.from_user.id, message.from_user.username) and team_num not in (1, 2, 3):
        await database.assign_tester_team(message.from_user.id, 1)
        guest = await database.get_guest_by_telegram_id(message.from_user.id)
        team_num = guest.get("team_number")
    if team_num not in (1, 2, 3):
        await message.answer("⚠️ شما عضو یکی از سه تیم رقابتی نیستید.")
        return

    members = await database.get_team_members(team_num)
    names = [m["full_name"] for m in members]
    labels = {1: "تیم ۱ (خون)", 2: "تیم ۲ (سایه)", 3: "تیم ۳ (سکوت)"}
    r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
    msg = (
        f"🔦 **پرونده‌ی محرمانه‌ی {labels[team_num]}**\n\n"
        f"👥 هم‌تیمی‌ها: {'، '.join(names)}\n\n"
        f"📄 پاکت اول: {'✅ ثبت شده' if r1 else '⏳ بررسی نشده'}\n"
        f"📄 پاکت دوم: {'✅ ثبت شده' if r2 else '⏳ بررسی نشده'}\n\n"
        "سه تیم مستقل رقابت می‌کنند؛ اطلاعات تیم‌های دیگر محرمانه است."
    )
    if guest.get("is_traitor") == 1:
        msg += "\n\n🐍 نقش محرمانه: در بازی اجتماعی مأموریت گمراه‌سازی به شما داده شده؛ ایمنی کسی را به خطر نیندازید."
    await message.answer(msg)

@router.message(Command("rescue"))
@router.message(F.text.in_(["💡 روشن کردن نور حیات باغ", "💡 روشن کردن نور حیاط باغ", "💡 روشن کردن نورافکن باغ", "🆘 کمک و امداد اضطراری", "🆘 امداد"]))
async def cmd_rescue(message: Message, bot: Bot):
    """Always-available safety alert; red-light gameplay never overrides real lighting."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    caller_name = guest.get("full_name") if guest else (message.from_user.full_name or str(message.from_user.id))
    details = f"درخواست امداد از طرف {caller_name}"
    alert_num = await database.record_rescue_alert(message.from_user.id, details=details)

    alert_sent = False
    if config.ADMIN_USER_ID:
        try:
            await bot.send_message(
                chat_id=config.ADMIN_USER_ID,
                text=(
                    "🚨 **[هشدار اضطراری / درخواست کمک — باغ سرهنگ]**\n\n"
                    f"مهمان: {caller_name} ({message.from_user.id})\n"
                    f"شماره‌ی درخواست: {alert_num}\n"
                    f"جزئیات: {details}\n"
                    f"زمان: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n\n"
                    "فوراً حضوری وضعیت مهمان را بررسی کنید و روشنایی ایمن مسیرها را فعال کنید."
                )
            )
            alert_sent = True
        except Exception:
            alert_sent = False

    if alert_sent:
        await message.answer(
            "🚨 درخواست شما ثبت و به مسئول اجرا ارسال شد. پیام امداد شما به میزبان و تیم پشتیبانی عمارت مخابره شد. "
            "حرکت را متوقف کنید و نزدیک‌ترین مسئول حاضر را صدا بزنید؛ مسیرها، اطراف استخر و خروجی‌ها باید روشن بمانند. فانوس سرخ جایگزین روشنایی ایمنی نیست."
        )
    else:
        await message.answer(
            "🚨 درخواست شما ثبت شد، اما ارسال خودکار به مسئول اجرا تأیید نشد. همین حالا حضوری مسئول اجرا را صدا بزنید. "
            "حرکت را متوقف کنید و روشنایی ایمنی مسیر، پله‌ها، اطراف استخر و خروجی‌ها را برقرار کنید."
        )


@router.message(Command("accuse"))
async def cmd_accuse(message: Message, bot: Bot):
    """
    Central deduction submission: allows a team to submit or revise its structured suspect conclusion.
    Accepts suspect name, motive, and evidence points (multi-line or delimited).
    """
    if await database.is_deductions_closed():
        await message.answer("⛔️ مهلت ثبت اتهام توسط میزبان به پایان رسیده است.")
        return

    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return

    if guest.get("role") != "role_player":
        await message.answer("🍿 شما همراه مهمانی (بلوند بی‌گناه) هستید و ثبت نظریه نهایی بر عهده‌ی تیم‌های بازرسی است.")
        return

    team_num = guest.get("team_number")
    if team_num not in (1, 2, 3):
        await message.answer("⚠️ شما عضو یکی از سه تیم رقابتی نیستید.")
        return

    phase = await database.get_game_state("game_phase", "registration")
    if phase not in ("midnight_investigation", "central_deduction"):
        await message.answer("⏳ ثبت اتهام فقط در زمان رسمی تحقیقات نیمه‌شب فعال است.")
        return

    raw_payload = message.text.partition(" ")[2].strip()
    if not raw_payload:
        current_acc = await database.get_team_accusation(team_num)
        curr_str = f"\n\n📌 **نظریه فعلی ثبت‌شده برای تیم شما:** «{current_acc}»" if current_acc else ""
        help_text = (
            "⚖️ **[میز مرکزی تجمیع مدارک — ثبت نظریه نهایی تیم]**\n\n"
            "برای ثبت اتهام، نام متهم، انگیزه/فرصت و حداقل دو مدرک معتبر از اسناد تیم خود را ارسال کنید:\n\n"
            "📌 **فرمت پیشنهادی (ارسال در خطوط جداگانه یا با خط فاصله):**\n"
            "`/accuse نام متهم`\n"
            "`انگیزه یا فرصت: ...`\n"
            "`مدرک اول: ...`\n"
            "`مدرک دوم: ...`\n"
            f"{curr_str}"
        )
        await message.answer(help_text, reply_markup=keyboards.accuse_suspects_kb())
        return

    r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
    if not (r1 and r2):
        await message.answer("🔎 ابتدا هر دو پاکت اختصاصی تیم خود را حل کنید؛ سپس اتهام مستدل ثبت می‌شود.")
        return

    # Parse payload
    lines = [l.strip() for l in raw_payload.splitlines() if l.strip()]
    suspect_name = ""
    motive_opportunity = ""
    evidence_point_1 = ""
    evidence_point_2 = ""

    if len(lines) >= 3:
        suspect_name = lines[0]
        motive_opportunity = lines[1]
        evidence_point_1 = lines[2]
        if len(lines) >= 4:
            evidence_point_2 = lines[3]
    elif len(lines) == 2:
        suspect_name = lines[0]
        evidence_point_1 = lines[1]
        motive_opportunity = lines[1]
    else:
        line = lines[0]
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
        elif " - " in line:
            parts = [p.strip() for p in line.split(" - ") if p.strip()]
        elif "؛" in line:
            parts = [p.strip() for p in line.split("؛") if p.strip()]
        else:
            parts = [line]

        suspect_name = parts[0]
        if len(parts) > 1:
            motive_opportunity = parts[1]
        if len(parts) > 2:
            evidence_point_1 = parts[2]
        if len(parts) > 3:
            evidence_point_2 = parts[3]
        if not evidence_point_1 and motive_opportunity:
            evidence_point_1 = motive_opportunity

    eval_res = game.evaluate_structured_accusation(
        team_number=team_num,
        suspect_name=suspect_name,
        motive_opportunity=motive_opportunity,
        evidence_point_1=evidence_point_1,
        evidence_point_2=evidence_point_2
    )

    rec_res = await database.record_structured_accusation(
        team_id=team_num,
        team_number=team_num,
        telegram_id=message.from_user.id,
        suspect_name=suspect_name,
        motive_opportunity=motive_opportunity,
        evidence_point_1=evidence_point_1,
        evidence_point_2=evidence_point_2,
        is_correct=eval_res["is_correct"]
    )

    if rec_res.get("is_first_winner") and config.ADMIN_USER_ID != 0:
        admin_alert = texts.ADMIN_WINNER_ALERT.format(
            team_number=team_num,
            team_name=guest.get("team_name") or f"تیم {team_num}",
            submitter_name=guest.get("full_name") or str(message.from_user.id),
            telegram_id=message.from_user.id,
            submitted_at=datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            suspect_name=suspect_name,
            matched_points="، ".join(eval_res.get("matched_points", [])) or "مدارک منطبق پرونده"
        )
        try:
            await bot.send_message(chat_id=config.ADMIN_USER_ID, text=admin_alert)
        except Exception:
            pass

    # Always respond neutrally without disclosing culprit
    await message.answer(texts.ACCUSATION_RECORDED_NEUTRAL)


@router.callback_query(F.data.startswith("accuse_"))
async def cb_accuse(callback: CallbackQuery, bot: Bot | None = None):
    """Suspect buttons never submit an incomplete accusation."""
    if await database.is_deductions_closed():
        await callback.answer("مهلت ثبت اتهام توسط میزبان به پایان رسیده است.", show_alert=True)
        return
    guest = await database.get_guest_by_telegram_id(callback.from_user.id)
    if not guest:
        await callback.answer("اطلاعات شما یافت نشد.", show_alert=True)
        return
    team_num = guest.get("team_number")
    if guest.get("role") != "role_player" or team_num not in (1, 2, 3):
        await callback.answer("ثبت اتهام فقط برای سه تیم رقابتی است.", show_alert=True)
        return

    phase = await database.get_game_state("game_phase", "registration")
    if phase not in ("midnight_investigation", "central_deduction"):
        await callback.answer("هنوز زمان ثبت اتهام نرسیده است.", show_alert=True)
        return
    r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
    if not (r1 and r2):
        await callback.answer("ابتدا هر دو پاکت تیم خود را ثبت کنید.", show_alert=True)
        return

    key = callback.data.removeprefix("accuse_")
    name_map = {
        "نادر": "نادر وثوق",
        "شیرین": "شیرین نوری",
        "کیوان": "کیوان رستگار",
        "دکتر": "دکتر فریدون مهر",
        "سرهنگ": "سرهنگ بهرام فرهمند",
    }
    suspect = name_map.get(key, key)
    await callback.answer("نام مظنون انتخاب شد.")
    await callback.message.answer(
        f"مظنون انتخاب‌شده: **{suspect}**\n\n"
        "این انتخاب هنوز اتهام ثبت‌شده نیست. برای ثبت نظریه‌ی محرمانه، دستور کامل را با انگیزه و دو مدرک متمایز ارسال کنید:\n"
        f"/accuse {suspect} | انگیزه یا فرصت | مدرک اول از پرونده‌ی تیم شما | مدرک دوم از دسته‌ای متفاوت"
    )

@router.message(Command("lantern"))
@router.message(Command("red_lantern"))
@router.message(F.text == "🔴 فانوس سرخ دیجیتال")
async def cmd_red_lantern(message: Message):
    """Sends the Red Lantern full-screen phone image + survival instructions."""
    caption = (
        "🔴 **فانوس سرخ دیجیتال — وسیله‌ی نمایشی اختیاری** 🕯\n\n"
        "این تصویر جایگزین روشنایی واقعی نیست. مسیرهای عبور، پله‌ها، اطراف استخر و خروجی‌ها باید روشن بمانند. "
        "برای حرکت ایمن از چراغ‌قوه یا نور گوشی استفاده کنید؛ هیچ نور سفیدی موجب جریمه یا حذف از بازی نمی‌شود."
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
        "🔴 **فانوس سرخ دیجیتال — وسیله‌ی نمایشی اختیاری** 🕯\n\n"
        "این تصویر فقط برای فضاسازی است و جایگزین نور واقعی نیست. مسیرها، پله‌ها، اطراف استخر و خروجی‌ها روشن می‌مانند. "
        "در صورت نیاز برای ایمنی از نور گوشی یا چراغ‌قوه استفاده کنید؛ هیچ جریمه‌ای برای نور سفید وجود ندارد."
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

    phase = await database.get_game_state("game_phase", "registration")
    if phase not in ("midnight_investigation", "central_deduction", "finale", "completed"):
        await callback.message.answer("⏳ اطلاعات تیم پس از آغاز مرحله‌ی تحقیقات نیمه‌شب نمایش داده می‌شود.")
        return

    team_num = guest.get("team_number")
    if not team_num and is_tester(callback.from_user.id, callback.from_user.username):
        await database.assign_tester_team(callback.from_user.id, 1)
        guest = await database.get_guest_by_telegram_id(callback.from_user.id)
        team_num = 1

    if not team_num:
        await callback.message.answer("⏳ شما عضو یکی از سه تیم تحقیقاتی نیستید.")
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
            "هدف تو این است که تیمت در اتاق عمارت کلمات رمز را اشتباه در گوش جنازه سرهنگ بگوید!"
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
@router.message(F.text == "🚗 کاروان")
@router.message(F.text == "🚗 کاروان صدرا")
async def cmd_carpool(message: Message):
    """Displays guest's assigned car in the convoy with fellow passengers and driver's Telegram contact."""
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
        f"🚗 **اطلاعات خودروی شما در کاروان:**\n\n"
        f"🔢 **شماره خودرو:** خودروی شماره {car_num} {seats_info}\n"
        f"🚘 **راننده خودرو:** {driver_contact}\n"
        f"👥 **همسفران شما در این خودرو:** {pass_str}\n"
        f"👤 **وضعیت شما:** {car_type}\n"
        f"📍 **زمان حرکت:** پنجشنبه ۲۹ اکتبر — رأس ساعت ۱۸:۰۰ به سمت خانزنیان\n"
        f"🗺 **لوکیشن محل تجمع ساعت ۱۸:۰۰ (گوگل‌مپ):**\nhttps://maps.app.goo.gl/U6Dz6SzEUdoTnNty7\n\n"
        f"⛔️ **یادآوری مهم:** دروازه‌ی عمارت از ساعت ۱۸:۴۵ تا ۲۴:۰۰ قفل خواهد بود و خروج زودهنگام امکان‌پذیر نیست."
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
