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
from aiogram.fsm.context import FSMContext
from states import AccusationStates

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
    """Validate a team's own envelope answer and notify only that team."""
    user_answer = (message.text or "").partition(" ")[2].strip()
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return
    if is_tester(message.from_user.id, message.from_user.username):
        if guest.get("role") != "role_player" or not guest.get("team_number"):
            await database.assign_tester_team(message.from_user.id, guest.get("team_number") or 1)
            guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if guest.get("role") != "role_player":
        await message.answer("🍿 شما مهمان بخش آزاد هستید و نیازی به ورود به معماهای رقابتی ندارید.")
        return
    team_num = guest.get("team_number")
    if team_num not in (1, 2, 3) or guest.get("character_role") == "nader":
        await message.answer("⚠️ شما عضو یکی از سه تیم رقابتی نیستید یا تیم‌بندی نیمه‌شب هنوز آغاز نشده است.")
        return

    if not user_answer:
        t_info = game.TEAM_RIDDLES.get(team_num, {})
        r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
        r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
        await message.answer(
            f"🔍 **وضعیت پرونده‌ی مستقل {t_info.get('name', 'تیم شما')}:**\n\n"
            f"• پاکت اول: {'✅ ثبت شده' if r1 else '⏳ در انتظار بررسی'}\n"
            f"• پاکت دوم: {'✅ ثبت شده' if r2 else '⏳ در انتظار بررسی'}\n\n"
            "برای ثبت پاسخ بنویسید:\n/solve <پاسخ>"
        )
        return

    result = await database.check_team_riddle(message.from_user.id, user_answer)
    status = result.get("status")
    if status == "not_registered":
        await message.answer("⚠️ ابتدا با /start ثبت‌نام کنید.")
        return
    if status == "no_team":
        await message.answer("⚠️ شما عضو یکی از سه تیم رقابتی نیستید.")
        return
    if status == "wrong":
        await message.answer(result.get("response_text", game.WRONG_ANSWER_TEXT))
        return
    if status == "other_team_riddle":
        await message.answer(result.get("response_text", game.OTHER_TEAM_CODE_ALERT))
        return
    if status == "already_solved":
        await message.answer(result.get("response_text", "این پاکت قبلاً ثبت شده است."))
        return
    if status == "already_both_solved":
        await message.answer("📁 هر دو پاکت تیم شما ثبت شده‌اند. نظریه‌ی مستقل خود را با /accuse آماده یا اصلاح کنید.")
        return

    response_text = result.get("response_text", "✅ مدرک ثبت شد.")
    teammates = await database.get_team_members(team_num)
    if status == "riddle_solved":
        await message.answer(response_text)
        notify = (
            f"⚡️ یکی از هم‌تیمی‌های شما پاکت {result.get('riddle_num')} را ثبت کرد. "
            "فقط اطلاعات پرونده‌ی تیم خودتان را بررسی کنید؛ سرنخ‌های تیم‌های دیگر محرمانه‌اند."
        )
        for member in teammates:
            if member.get("telegram_id") and member["telegram_id"] != message.from_user.id:
                try:
                    await bot.send_message(chat_id=member["telegram_id"], text=notify)
                except Exception:
                    pass
        return

    if status == "both_solved":
        notify = (
            "📁 **مدارک هر دو پاکت تیم شما ثبت شد.**\n\n"
            "دو پاکت و اسناد پشتیبان خودتان را کنار هم بگذارید. برای برنده‌شدن باید نادر وثوق را "
            "با دو مدرک متمایز و توضیح انگیزه یا فرصت معرفی کنید.\n"
            "اتهام را با /accuse ثبت کنید. نتیجه محرمانه می‌ماند؛ تبادل اطلاعات با تیم‌های دیگر لازم نیست."
        )
        await message.answer(response_text + "\n\n" + notify)
        for member in teammates:
            if member.get("telegram_id") and member["telegram_id"] != message.from_user.id:
                try:
                    await bot.send_message(chat_id=member["telegram_id"], text=notify)
                except Exception:
                    pass


@router.message(Command("team"))
@router.message(F.text == "🔦 تیم من در حیاط")
async def cmd_team(message: Message):
    """Shows only the caller's own competitive team and envelope status."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با /start در سیستم ثبت‌نام کنید.")
        return
    if guest.get("role") != "role_player":
        await message.answer("🍿 شما مهمان بخش آزاد هستید و نیازی به تیم تحقیقاتی ندارید.")
        return
    team_num = guest.get("team_number")
    if is_tester(message.from_user.id, message.from_user.username) and team_num not in (1, 2, 3):
        await database.assign_tester_team(message.from_user.id, 1)
        guest = await database.get_guest_by_telegram_id(message.from_user.id)
        team_num = guest.get("team_number")
    if team_num not in (1, 2, 3) or guest.get("character_role") == "nader":
        await message.answer(
            "⏳ تیم‌های رقابتی در ساعت ۰۰:۰۰ به‌صورت خصوصی اعلام می‌شوند. "
            "نادرِ نقش‌آفرین عضو هیچ تیم امتیازگیری نیست."
        )
        return
    members = await database.get_team_members(team_num)
    labels = {1: "تیم خون", 2: "تیم سایه", 3: "تیم سکوت"}
    r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
    await message.answer(
        f"🔎 **پرونده‌ی محرمانه‌ی {labels[team_num]}**\n\n"
        f"👥 هم‌تیمی‌ها: {'، '.join(p['full_name'] for p in members)}\n\n"
        f"📄 پاکت اول: {'✅ ثبت شده' if r1 else '⏳ بررسی نشده'}\n"
        f"📄 پاکت دوم: {'✅ ثبت شده' if r2 else '⏳ بررسی نشده'}\n\n"
        "این تیم مستقل رقابت می‌کند. وضعیت، سرنخ‌ها و اتهام تیم‌های دیگر محرمانه است.\n"
        "پاسخ: /solve <پاسخ> | اتهام: /accuse"
    )


@router.message(Command("rescue"))
@router.message(F.text.in_(["💡 روشن کردن نور حیات باغ", "💡 روشن کردن نور حیاط باغ", "💡 روشن کردن نورافکن باغ"]))
async def cmd_rescue(message: Message, bot: Bot):
    """Always accepts a safety request and alerts the event lead."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    guest_name = guest.get("full_name") if guest else (message.from_user.full_name or "مهمان ناشناس")
    count = await database.record_rescue_alert(message.from_user.id, guest_name)
    admin_id = config.ADMIN_USER_ID if config.ADMIN_USER_ID > 0 else next(iter(TESTER_IDS), None)
    alerted = False
    if admin_id:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    "🚨 **درخواست کمک/ایمنی در باغ سرهنگ**\n\n"
                    f"مهمان: {guest_name}\nTelegram ID: {message.from_user.id}\n"
                    f"شماره‌ی ثبت درخواست: {count}\n"
                    "لطفاً فوراً حضوری وضعیت مهمان را بررسی کنید و در صورت نیاز نور ایمنی را روشن کنید."
                )
            )
            alerted = True
        except Exception:
            pass
    if alerted:
        await message.answer(
            "🚨 درخواست ایمنی شما ثبت شد و به مسئول اجرا اطلاع داده شد. این دستور هیچ محدودیتی ندارد. "
            "حرکت را متوقف کنید و در صورت نیاز مستقیم با مسئول حاضر تماس بگیرید."
        )
    else:
        await message.answer(
            "🚨 درخواست ایمنی شما ثبت شد، اما ارسال خودکار به مسئول اجرا تأیید نشد. "
            "همین حالا حضوری مسئول اجرا را صدا بزنید و مسیر خروج را آزاد نگه دارید."
        )


async def _send_accusation_result(message: Message, bot: Bot, team_num: int, result: dict) -> None:
    """Keeps team results private; only the host is notified when a winner is locked."""
    status = result.get("status")
    if status == "closed":
        await message.answer("⏳ مهلت ثبت اتهام به پایان رسیده است. نتیجه در افشای رسمی اعلام می‌شود.")
        return
    if status == "insufficient_evidence":
        await message.answer(
            "⚠️ دو مدرک باید از دو دسته‌ی متفاوت و مرتبط با پرونده‌ی تیم خودتان باشند؛ "
            "توضیح انگیزه یا فرصت نیز باید روشن باشد. با /accuse دوباره تلاش کنید."
        )
        return
    if status != "recorded":
        await message.answer("⚠️ ثبت اتهام انجام نشد. با /accuse دوباره شروع کنید.")
        return
    await message.answer(
        "🔒 اتهام و توضیح تیم شما به‌صورت محرمانه ثبت شد. زمان اولین ثبت حفظ می‌شود؛ "
        "نتیجه و پاسخ تیم‌های دیگر نمایش داده نمی‌شود."
    )
    if result.get("winner_created"):
        admin_id = config.ADMIN_USER_ID if config.ADMIN_USER_ID > 0 else next(iter(TESTER_IDS), None)
        if admin_id:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "🏁 **یک اتهام کامل و صحیح ثبت شد؛ برنده برای افشای نهایی قفل شد.**\n\n"
                        f"تیم: {team_num}\nمتهم: {result.get('suspect')}\n"
                        f"مدرک ۱: {result.get('evidence_1', '')}\n"
                        f"مدرک ۲: {result.get('evidence_2', '')}\n"
                        f"استدلال: {result.get('rationale', '')}\n"
                        "این نتیجه تا فرمان /reveal_traitors عمومی نشود."
                    )
                )
            except Exception:
                pass


async def _record_accusation_from_parts(message: Message, bot: Bot, team_num: int, parts: list[str]) -> None:
    result = await database.record_team_accusation(
        team_num, parts[0], message.from_user.id, parts[1], parts[2], parts[3]
    )
    await _send_accusation_result(message, bot, team_num, result)


@router.message(Command("accuse"))
async def cmd_accuse(message: Message, state: FSMContext, bot: Bot):
    """Guided private accusation; one-line format is /accuse suspect | evidence1 | evidence2 | rationale."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest:
        await message.answer("⚠️ ابتدا با ارسال /start در مهمانی ثبت‌نام کنید.")
        return
    if guest.get("role") != "role_player":
        await message.answer("🍿 ثبت اتهام فقط برای سه تیم رقابتی است.")
        return
    team_num = guest.get("team_number")
    if team_num not in (1, 2, 3) or guest.get("character_role") == "nader":
        await message.answer("⚠️ شما عضو تیم امتیازگیر نیستید.")
        return
    if await database.get_game_state("deductions_closed", "0") == "1":
        await message.answer("⏳ مهلت ثبت اتهام بسته شده است.")
        return
    r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
    if not (r1 and r2):
        await message.answer("🔎 ابتدا هر دو پاکت اختصاصی تیم خودتان را حل کنید؛ سپس می‌توانید اتهام مستدل ثبت کنید.")
        return
    args = (message.text or "").partition(" ")[2].strip()
    if "|" in args:
        parts = [p.strip() for p in args.split("|", 3)]
        if len(parts) != 4 or not all(parts):
            await message.answer("فرمت: /accuse نام مظنون | مدرک اول | مدرک دوم | توضیح انگیزه یا فرصت")
            return
        await _record_accusation_from_parts(message, bot, team_num, parts)
        return
    if args:
        await state.update_data(accuse_team=team_num, accuse_suspect=args)
        await state.set_state(AccusationStates.waiting_for_evidence_1)
        await message.answer("📄 مدرک اول را دقیق و کوتاه از اسناد تیم خود بنویسید.")
        return
    current = await database.get_team_accusation_details(team_num)
    current_line = f"\n\nنظریه‌ی فعلی تیم شما: «{current.get('suspect', '')}»" if current else ""
    await state.set_state(AccusationStates.waiting_for_suspect)
    await message.answer(
        "⚖️ **ثبت اتهام محرمانه‌ی تیم شما**\n\n"
        "قاتل را انتخاب کنید؛ سپس دو مدرک متمایز از پرونده‌ی خودتان و توضیح انگیزه یا فرصت را وارد می‌کنید.\n"
        "قالب مستقیم:\n/accuse نام مظنون | مدرک اول | مدرک دوم | توضیح انگیزه یا فرصت"
        f"{current_line}",
        reply_markup=keyboards.accuse_suspects_kb()
    )


@router.callback_query(F.data.startswith("accuse_"))
async def cb_accuse(callback: CallbackQuery, state: FSMContext):
    guest = await database.get_guest_by_telegram_id(callback.from_user.id)
    if not guest:
        await callback.answer("اطلاعات شما یافت نشد.", show_alert=True)
        return
    team_num = guest.get("team_number")
    if guest.get("role") != "role_player" or team_num not in (1, 2, 3) or guest.get("character_role") == "nader":
        await callback.answer("شما عضو تیم امتیازگیر نیستید.", show_alert=True)
        return
    if await database.get_game_state("deductions_closed", "0") == "1":
        await callback.answer("مهلت ثبت اتهام بسته شده است.", show_alert=True)
        return
    r1 = (await database.get_game_state(f"team_{team_num}_riddle_1", "0")) == "1"
    r2 = (await database.get_game_state(f"team_{team_num}_riddle_2", "0")) == "1"
    if not (r1 and r2):
        await callback.answer("ابتدا هر دو پاکت تیم خود را ثبت کنید.", show_alert=True)
        return
    suspect_map = {
        "accuse_nader": "نادر وثوق",
        "accuse_shirin": "شیرین نوری",
        "accuse_keyvan": "کیوان رستگار",
        "accuse_fereydoun": "دکتر فریدون مهر",
        "accuse_colonel": "سرهنگ بهرام فرهمند",
    }
    suspect = suspect_map.get(callback.data)
    if not suspect:
        await callback.answer("انتخاب نامعتبر است.", show_alert=True)
        return
    await callback.answer()
    await state.update_data(accuse_team=team_num, accuse_suspect=suspect)
    await state.set_state(AccusationStates.waiting_for_evidence_1)
    await callback.message.answer("📄 مدرک اول را دقیق و کوتاه از اسناد تیم خود بنویسید.")


@router.message(AccusationStates.waiting_for_suspect, F.text & ~F.text.startswith("/"))
async def accusation_waiting_for_suspect(message: Message):
    await message.answer("لطفاً یکی از گزینه‌های مظنون را انتخاب کنید یا دستور /accuse را دوباره اجرا کنید.")


@router.message(AccusationStates.waiting_for_evidence_1, F.text & ~F.text.startswith("/"))
async def accusation_evidence_1(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value:
        await message.answer("مدرک اول خالی است؛ آن را دوباره وارد کنید.")
        return
    await state.update_data(accuse_evidence_1=value)
    await state.set_state(AccusationStates.waiting_for_evidence_2)
    await message.answer("📄 مدرک دوم را از دسته‌ای متفاوت و مرتبط با پرونده‌ی تیم خود بنویسید.")


@router.message(AccusationStates.waiting_for_evidence_2, F.text & ~F.text.startswith("/"))
async def accusation_evidence_2(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value:
        await message.answer("مدرک دوم خالی است؛ آن را دوباره وارد کنید.")
        return
    await state.update_data(accuse_evidence_2=value)
    await state.set_state(AccusationStates.waiting_for_rationale)
    await message.answer("🧠 در چند جمله توضیح دهید این شواهد چگونه انگیزه یا فرصت مظنون را ثابت می‌کنند.")


@router.message(AccusationStates.waiting_for_rationale, F.text & ~F.text.startswith("/"))
async def accusation_rationale(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if not guest or guest.get("team_number") not in (1, 2, 3) or guest.get("character_role") == "nader":
        await state.clear()
        await message.answer("⚠️ عضویت تیمی شما تغییر کرده است؛ با /accuse دوباره شروع کنید.")
        return
    if await database.get_game_state("deductions_closed", "0") == "1":
        await state.clear()
        await message.answer("⏳ مهلت ثبت اتهام بسته شده است.")
        return
    result = await database.record_team_accusation(
        guest["team_number"], data.get("accuse_suspect", ""), message.from_user.id,
        data.get("accuse_evidence_1", ""), data.get("accuse_evidence_2", ""),
        (message.text or "").strip()
    )
    await state.clear()
    await _send_accusation_result(message, bot, guest["team_number"], result)

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
    if not team_num and is_tester(message.from_user.id, message.from_user.username):
        await database.assign_tester_team(message.from_user.id, 1)
        guest = await database.get_guest_by_telegram_id(message.from_user.id)
        team_num = 1

    if not team_num:
        await callback.message.answer("⏳ تیم‌بندی شما در ساعت ۲۴:۰۰ اعلام خواهد شد.")
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
