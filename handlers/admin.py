import io
import csv
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile, FSInputFile
from aiogram.exceptions import TelegramAPIError

import config
import database
import texts
import keyboards
import game

router = Router()

TESTER_IDS = {102725917}
TESTER_USERNAMES = {"hamixon", "hamixn"}

def is_admin(user_id: int, username: str | None = None) -> bool:
    """Checks if the user ID matches the configured admin ID or authorized tester (Hamixon)."""
    if user_id in TESTER_IDS:
        return True
    if username and username.lower().lstrip("@") in TESTER_USERNAMES:
        return True
    if config.ADMIN_USER_ID != 0 and user_id == config.ADMIN_USER_ID:
        return True
    return False

@router.message(Command("admin"))
async def cmd_admin_help(message: Message):
    """Admin command panel overview."""
    if not is_admin(message.from_user.id):
        if config.ADMIN_USER_ID == 0:
            await message.answer(
                f"⚠️ شناسه ادمین هنوز در فایل .env تعریف نشده است!\n"
                f"آیدی عددی تلگرام شما: `{message.from_user.id}`\n\n"
                f"لطفاً مقدار `ADMIN_USER_ID={message.from_user.id}` را در فایل `.env` قرار دهید."
            )
        else:
            await message.answer("⛔️ دسترسی غیرمجاز. این بخش مخصوص مدیر عمارت است.")
        return

    help_text = (
        "👑 **پنل مدیریت مهمانی هالووین (باغ سرهنگ)**\n\n"
        "دستورات موجود:\n"
        "📊 `/stats` — مشاهده آمار زنده ثبت‌نام، ظرفیت‌ها و تسخیرشدگان\n"
        "📋 `/list` — دریافت لیست متنی مهمانان + فایل کامل اکسل/CSV\n"
        "🎭 `/start_social_game` — کلید زدن بازی ۱۹:۳۰ (تعیین ۳ تسخیرشده و ارسال ماموریت‌ها با استیکر)\n"
        "🌑 `/start_midnight_game` — کلید زدن بازی حیاط (ساعت ۲۴:۰۰ نیمه‌شب، ارسال فانوس سرخ، تیم‌ها، خائنین و معماها)\n"
        "🗝 `/reveal_traitors` — اعلام عمومی و افشای ۳ تسخیرشده و خائنین\n"
        "🚗 `/assign_carpool` — نمایش وضعیت کاروان خودروها\n"
        "📢 `/broadcast <متن>` — ارسال پیام همگانی به تمام مهمانان\n"
        "⚠️ `/broadcast_crisis` (یا `/crisis_broadcast`) — ارسال پیام بحران پیش از نیمه‌شب (ساعت ۲۳:۵۰)\n"
        "🕯 `/trigger_finale` (یا `/trigger_darkroom`) — کلید زدن سکانس نهایی تاریکخانه (ساعت ۰۱:۱۰ بامداد)\n"
        "🕯 `/broadcast_players <متن>` — ارسال پیام اختصاصی به گروه بازیکنان\n"
        "👱‍♀️ `/broadcast_blondes <متن>` — ارسال پیام اختصاصی به گروه بلوندهای بی‌گناه\n"
        "🔓 `/unlock_missions` — باز کردن دستی ماموریت‌های مخفی\n"
        "🔒 `/lock_missions` — قفل کردن مجدد ماموریت‌های مخفی"
    )
    await message.answer(help_text)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Shows party registration statistics."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    stats = await database.get_stats()
    total = stats["total"]
    players = stats["players"]
    blondes = stats["blondes"]
    cars = stats["cars"]
    hunters = stats["hunters"]
    immune = stats["immune"]
    stickered = stats.get("stickered", 0)

    stats_msg = (
        "📊 **آمار زنده مهمانی باغ سرهنگ:**\n\n"
        f"👥 **کل مهمانان ثبت‌شده:** {total} از ۵۲ نفر\n"
        f"🕯 **بازیکنان طلسم:** {players} از {config.PLAYER_CAP} نفر\n"
        f"👱‍♀️ **بلوندهای بی‌گناه:** {blondes} نفر\n"
        f"🚗 **تعداد خودروهای حاضر:** {cars} خودرو (هدف: ۱۳ خودرو)\n"
        f"🩸 **تسخیرشدگان با استیکر (شکارچی):** {hunters} نفر از ۵ نفر\n"
        f"🛡 **دارندگان طلسم مصونیت:** {immune} نفر\n"
        f"💀 **افرادی که استیکر خورده‌اند:** {stickered} نفر\n"
    )
    await message.answer(stats_msg)

@router.message(Command("list"))
async def cmd_list(message: Message):
    """Exports all guests as text and a downloadable CSV file."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    guests = await database.get_all_guests()
    if not guests:
        await message.answer("هنوز هیچ مهمانی در سیستم ثبت‌نام نکرده است.")
        return

    # 1. Text Summary
    lines = ["📋 **لیست مهمانان ثبت‌شده مهمانی:**\n"]
    for g in guests:
        role_fa = "🕯 بازیکن" if g.get("role") == "role_player" else ("👱‍♀️ بلوند" if g.get("role") == "role_blonde" else "⏳ در انتظار")
        car_fa = "🚗 ماشین‌دار" if g.get("has_car") == 1 else "🚶 بدون ماشین"
        hunter_fa = " 🩸[تسخیرشده]" if g.get("is_hunter") == 1 else ""
        immune_fa = " 🛡[مصون]" if g.get("is_immune") == 1 else ""
        uname = f"@{g['telegram_username']}" if g.get("telegram_username") else "بدون یوزرنیم"
        lines.append(
            f"• #{g.get('serial_number', 0):02d} | **{g.get('full_name')}** ({uname}) — {role_fa} | {car_fa}{hunter_fa}{immune_fa}"
        )

    full_text = "\n".join(lines)
    if len(full_text) > 4000:
        chunks = [full_text[i:i + 3800] for i in range(0, len(full_text), 3800)]
        for chunk in chunks:
            await message.answer(chunk)
    else:
        await message.answer(full_text)

    # 2. CSV File Export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Serial", "Full Name", "Telegram ID", "Username", "Role", "Has Car", "Car Group",
        "Is Infected", "Is Immune", "Got Stickered", "Registered At"
    ])
    for g in guests:
        writer.writerow([
            f"SOUL-#{g.get('serial_number', 0):02d}",
            g.get("full_name"),
            g.get("telegram_id"),
            g.get("telegram_username") or "",
            g.get("role") or "",
            "Yes" if g.get("has_car") == 1 else "No",
            g.get("car_number") or "",
            "Yes" if g.get("is_hunter") == 1 else "No",
            "Yes" if g.get("is_immune") == 1 else "No",
            "Yes" if g.get("got_stickered") == 1 else "No",
            g.get("registered_at") or ""
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    csv_file = BufferedInputFile(csv_bytes, filename="guests_colonel_garden.csv")
    await message.answer_document(
        document=csv_file,
        caption="📁 فایل اکسل/CSV اطلاعات ۵۲ مهمان"
    )

@router.message(Command("start_social_game"))
async def cmd_start_social_game(message: Message, bot: Bot):
    """
    Phase 2 (19:15 Social Game):
    1. Picks 5 secret infected guests (is_hunter=1) and sends physical sticker DMs.
    2. Sends social missions to all remaining players with immunity & stickered buttons.
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    players = await database.get_players()
    if len(players) < 3:
        await message.answer(
            f"⚠️ تعداد بازیکنان ثبت‌شده ({len(players)} نفر) کمتر از ۳ نفر است!\n"
            f"حداقل ۳ نفر بازیکن برای شروع بازی نیاز است."
        )
        return

    res = await database.start_social_game(count=3)
    hunters = res["hunters"]
    regular = res["regular_players"]

    # 1. Notify the 3 infected
    hunter_success = 0
    for h in hunters:
        tid = h.get("telegram_id")
        if tid:
            try:
                await bot.send_message(chat_id=tid, text=texts.INFECTED_SECRET_DM)
                hunter_success += 1
            except Exception as e:
                print(f"Error DMing infected {h['full_name']}: {e}")

    # 2. Notify remaining players with social missions & action buttons
    regular_success = 0
    for p in regular:
        tid = p.get("telegram_id")
        if tid:
            mission_id = p.get("social_mission_id", 1)
            mission_text = game.SOCIAL_MISSIONS.get(mission_id, game.SOCIAL_MISSIONS[1])
            text = (
                "🩸 **[آغاز بازی اجتماعی سالن — ساعت ۱۹:۳۰]**\n\n"
                "۳ تسخیرشده‌ی پنهان با بسته‌های استیکر در سالن رها شده‌اند!\n\n"
                f"🎯 **ماموریت اجتماعی شما برای فعال‌سازی طلسم مصونیت:**\n"
                f"||{mission_text}||\n\n"
                "💡 به محض انجام این ماموریت در سالن، دکمه‌ی «✅ ماموریتم رو انجام دادم!» را لمس کنید تا کارت طلسم مصونیت سبز دریافت کنید.\n"
                "⚠️ اگر کسی استیکر به پشت لباستان چسباند، دکمه‌ی «💀 استیکر خوردم!» را بزنید."
            )
            kb = keyboards.social_mission_player_kb(
                is_immune=bool(p.get("is_immune")),
                got_stickered=bool(p.get("got_stickered"))
            )
            try:
                await bot.send_message(chat_id=tid, text=text, reply_markup=kb)
                regular_success += 1
            except Exception as e:
                print(f"Error DMing player {p['full_name']}: {e}")

    # 3. Notify blondes
    blondes = await database.get_all_telegram_ids(role_filter="role_blonde")
    for b_tid in blondes:
        try:
            await bot.send_message(
                chat_id=b_tid,
                text=(
                    "🥂 **[آغاز پرده‌ی سوم: بازی اجتماعی در سالن رقص]**\n\n"
                    "بازی استیکر و ماموریت‌های بازیکنان در سالن آغاز شد!\n"
                    "شما در حاشیه امن مطلق قرار دارید؛ از نوشیدنی، موسیقی و تماشای تکاپوی دیگران لذت ببرید."
                )
            )
        except Exception:
            pass

    hunters_names = "، ".join([h["full_name"] for h in hunters])
    await message.answer(
        f"✅ **بازی اجتماعی ساعت ۱۹:۳۰ آغاز شد!**\n\n"
        f"🩸 **۳ تسخیرشده‌ی منتخب:** {hunters_names}\n"
        f"📨 پیام برای {hunter_success} تسخیرشده و {regular_success} بازیکن ارسال گردید."
    )

@router.message(Command("start_midnight_game"))
async def cmd_start_midnight_game(message: Message, bot: Bot):
    """
    Phase 3 (24:00 Midnight Horror Game):
    1. Splits players into 4 teams.
    2. Appoints 1 secret traitor per team.
    3. Sends Red Lantern image + rules to all players.
    4. Secretly DMs each traitor their sabotage mission.
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    teams = await database.start_midnight_game()
    if not teams:
        await message.answer("⚠️ بازیکن ثبت‌شده‌ای برای شروع بازی نیمه‌شب وجود ندارد.")
        return

    red_lantern_path = Path("assets/images/red_lantern.jpg")

    for team_num, t_info in teams.items():
        team_name = t_info["name"]
        members = t_info["members"]
        traitor = t_info["traitor"]
        all_member_names = [m["full_name"] for m in members]

        for m in members:
            tid = m.get("telegram_id")
            if not tid:
                continue

            lantern_caption = (
                "🔴 **[فانوس سرخ دیجیتال — تنها نور مجاز در عمارت]** 🕯\n\n"
                "📱 تصویر را لمس کنید و به صورت **تمام‌صفحه (Full-Screen)** روی سیستم یا گوشی خود باز نگه دارید.\n\n"
                "⚠️ **تنها نوری که می‌توانید استفاده کنید و سرهنگ به آن حساس نیست همین است!**\n"
                "سرهنگ به نور سرخ تاریک‌خانه‌اش الفت داشته و به آن کاملاً نابیناست. "
                "روشن کردن هرگونه چراغ‌قوه سفید یا صفحه عادی گوشی = حمله و شکار فوری توسط روح سرهنگ!"
            )

            rules_msg = (
                f"{texts.MIDNIGHT_RULES_BRIEFING}\n\n"
                f"🏷 **تیم شما:** {team_name}\n"
                f"👥 **هم‌تیمی‌های شما:** {'، '.join(all_member_names)}\n\n"
                f"🔍 دو پاکت معمای تیم خود را در باغ پیدا کنید و پاسخ هر معما را با دستور زیر در بات وارد نمایید:\n"
                f"`/solve <پاسخ معما>`"
            )

            try:
                if red_lantern_path.exists():
                    photo_file = FSInputFile(str(red_lantern_path), filename="red_lantern.jpg")
                    await bot.send_photo(chat_id=tid, photo=photo_file, caption=lantern_caption)
                await bot.send_message(chat_id=tid, text=rules_msg, reply_markup=keyboards.midnight_action_kb())
            except Exception as e:
                print(f"Error briefing {m['full_name']}: {e}")

            # Send secret traitor DM if this player is the appointed traitor
            if traitor and m["id"] == traitor["id"]:
                try:
                    await bot.send_message(chat_id=tid, text=texts.TRAITOR_SECRET_DM)
                except Exception as e:
                    print(f"Error sending traitor DM to {m['full_name']}: {e}")

    # Notify blondes about movie & safety in salon
    blondes = await database.get_all_telegram_ids(role_filter="role_blonde")
    for b_tid in blondes:
        try:
            await bot.send_message(
                chat_id=b_tid,
                text=(
                    "🍿 **[ساعت ۲۴:۰۰ — زنگ خاموشی عمارت و آغاز بازی حیاط نواخته شد!]**\n\n"
                    "چراغ‌های حیاط خاموش شد و بازیکنان با فانوس سرخ وارد تاریکی باغ شدند!\n"
                    "پخش فیلم سینمایی ترسناک در سالن گرم با نوشیدنی و پاپ‌کورن آغاز گردید.\n\n"
                    "💡 یادآوری: در صورت بحرانی شدن اوضاع حیاط، می‌توانید با دکمه‌ی «💡 روشن کردن نور حیات باغ» موقتاً ارواح را کور کنید."
                )
            )
        except Exception:
            pass

    summary = ["🔦 **بازی ساعت ۲۴:۰۰ حیاط با موفقیت آغاز گردید!**\n"]
    for t_num, t_info in teams.items():
        tr_name = t_info["traitor"]["full_name"] if t_info.get("traitor") else "نامشخص"
        m_count = len(t_info["members"])
        summary.append(f"• **{t_info['name']}** ({m_count} نفر) — خائن مخفی: {tr_name}")

    await message.answer("\n".join(summary))

@router.message(Command("reveal_traitors"))
async def cmd_reveal_traitors(message: Message, bot: Bot):
    """
    Phase 4 (02:00 Reveal):
    Broadcasts the 5 Infected and 4 Traitors to all guests.
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    data = await database.get_reveal_manifest()
    hunters = data.get("hunters", [])
    traitors = data.get("traitors", [])

    h_lines = []
    for idx, h in enumerate(hunters, 1):
        uname = f"(@{h['telegram_username']})" if h.get("telegram_username") else ""
        h_lines.append(f"{idx}. {h['full_name']} {uname}")
    h_str = "\n".join(h_lines) if h_lines else "اطلاعاتی ثبت نشده است."

    t_lines = []
    for idx, t in enumerate(traitors, 1):
        uname = f"(@{t['telegram_username']})" if t.get("telegram_username") else ""
        t_label = t.get("team_name") or f"تیم {t.get('team_number', '')}"
        t_lines.append(f"{idx}. {t['full_name']} ({t_label}) {uname}")
    t_str = "\n".join(t_lines) if t_lines else "اطلاعاتی ثبت نشده است."

    reveal_text = texts.REVEAL_ANNOUNCEMENT.format(
        hunters_list=h_str,
        traitors_list=t_str
    )

    success, failed = await send_broadcast(bot, reveal_text)
    await message.answer(f"✅ پیام افشای نهایی به {success} مهمان مخابره شد. (خطا: {failed})")

async def send_broadcast(bot: Bot, text: str, role_filter: str | None = None) -> tuple[int, int]:
    """Helper to broadcast messages to guests."""
    target_ids = await database.get_all_telegram_ids(role_filter=role_filter)
    success = 0
    failed = 0
    for tid in target_ids:
        try:
            await bot.send_message(chat_id=tid, text=text)
            success += 1
        except Exception:
            failed += 1
    return success, failed

@router.message(Command("broadcast"))
async def cmd_broadcast_all(message: Message, bot: Bot):
    """Broadcasts a message to all registered guests."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("⚠️ لطفاً متن پیام را بعد از دستور وارد کنید:\n`/broadcast متن پیام شما`")
        return

    broadcast_text = f"📢 **[اعلامیه رسمی عمارت باغ سرهنگ]**\n\n{text}"
    success, failed = await send_broadcast(bot, broadcast_text, role_filter=None)
    await message.answer(f"✅ پیام به {success} مهمان ارسال شد. (خطا: {failed})")

@router.message(Command("broadcast_players"))
async def cmd_broadcast_players(message: Message, bot: Bot):
    """Broadcasts a message specifically to the player group."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("⚠️ لطفاً متن پیام را وارد کنید:\n`/broadcast_players متن پیام شما`")
        return

    broadcast_text = f"🕯 **[پیام اختصاصی به بازیکنان]**\n\n{text}"
    success, failed = await send_broadcast(bot, broadcast_text, role_filter="role_player")
    await message.answer(f"✅ پیام به {success} بازیکن ارسال شد. (خطا: {failed})")

@router.message(Command("broadcast_blondes"))
async def cmd_broadcast_blondes(message: Message, bot: Bot):
    """Broadcasts a message specifically to the innocent blonde group."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("⚠️ لطفاً متن پیام را وارد کنید:\n`/broadcast_blondes متن پیام شما`")
        return

    broadcast_text = f"🥂 **[پیام اختصاصی به بلوندهای بی‌گناه — سالن VIP]**\n\n{text}"
    success, failed = await send_broadcast(bot, broadcast_text, role_filter="role_blonde")
    await message.answer(f"✅ پیام به {success} مهمان بلوند ارسال شد. (خطا: {failed})")

@router.message(Command("assign_carpool"))
async def cmd_assign_carpool(message: Message):
    """Displays current 13-car convoy distribution."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    manifest = await database.get_carpool_manifest()
    summary = ["🚗 **وضعیت کاروان خودروها:**\n"]
    for c_num, info in manifest.items():
        driver = info.get("driver") or "بدون راننده"
        passengers = info.get("passengers", [])
        pass_str = "، ".join(passengers) if passengers else "بدون همسفر فعلاً"
        summary.append(f"🚘 **خودروی {c_num}:** راننده: {driver} | همسفران: {pass_str}")

    await message.answer("\n".join(summary))

@router.message(Command("crisis_broadcast"))
@router.message(Command("broadcast_crisis"))
async def cmd_crisis_broadcast(message: Message, bot: Bot):
    """Broadcasts the 23:50 Pre-Midnight Crisis text to all registered guests."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    text = texts.CRISIS_BROADCAST_TEXT
    success, failed = await send_broadcast(bot, text)
    await message.answer(f"📢 پیام بحران پیش از نیمه‌شب (۲۳:۵۰) برای {success} نفر ارسال شد. (خطا: {failed})")

@router.message(Command("trigger_finale"))
@router.message(Command("finale"))
@router.message(Command("trigger_darkroom"))
async def cmd_trigger_darkroom(message: Message, bot: Bot):
    """Triggers the 01:10 AM Final Darkroom Sequence to all players."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    text = texts.DARKROOM_FINAL_PROMPT
    success, failed = await send_broadcast(bot, text, role_filter="role_player")
    await message.answer(f"🕯 سکانس نهایی تاریکخانه برای {success} بازرس ارسال شد. (خطا: {failed})")

@router.message(Command("unlock_missions"))
async def cmd_unlock_missions(message: Message):
    """Force unlocks the secret missions for testing."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return
    await database.set_game_state("force_unlock_missions", "1")
    await message.answer("🔓 قفل ماموریت‌های مخفی به صورت دستی باز شد!")

@router.message(Command("lock_missions"))
async def cmd_lock_missions(message: Message):
    """Re-locks the secret missions until 29 Oct 18:00."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return
    await database.set_game_state("force_unlock_missions", "0")
    await message.answer("🔒 ماموریت‌های مخفی مجدداً قفل شدند تا ساعت ۱۸:۰۰ روز ۲۹ اکتبر.")

@router.message(Command("test"))
@router.message(Command("tester"))
async def cmd_tester_panel(message: Message):
    """Interactive testing instructions and controls for Hamixon."""
    user_id = message.from_user.id
    username = message.from_user.username
    if not is_admin(user_id, username):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    guest = await database.get_guest_by_telegram_id(user_id)
    t_num = guest.get("team_number", 1) if guest else 1
    t_name = guest.get("team_name", f"تیم {t_num}") if guest else "تیم ۱ (خون)"
    r1 = await database.get_game_state(f"team_{t_num}_riddle_1", "0")
    r2 = await database.get_game_state(f"team_{t_num}_riddle_2", "0")

    panel_text = (
        f"🧪 **[پنل اختصاصی تست جریان کامل بازی برای @{username or 'hamixon'}]** 🎮\n\n"
        f"👤 **مهمان:** {guest.get('full_name') if guest else 'حامد'} | **نقش:** بازیکن پرونده\n"
        f"🏷 **تیم فعلی:** {t_name} (شماره {t_num})\n"
        f"🧩 **وضعیت پاکت‌ها:** پاکت ۱: {'✅ ثبت‌شده' if r1 == '1' else '⏳ باز'} | پاکت ۲: {'✅ ثبت‌شده' if r2 == '1' else '⏳ باز'}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 **راهنمای گام‌به‌گام تست:**\n\n"
        "۱. 📜 **تست ماموریت اجتماعی و آلیبای:**\n"
        "   دستور `/mission` — مشاهده ماموریت، زدن دکمه‌ی «ثبت آلیبای» و «استیکر خوردم».\n\n"
        "۲. 🔦 **مشاهده اطلاعات تیم:**\n"
        "   دستور `/team` — اطلاعات تیم شما و ماموریت خائن.\n\n"
        "۳. 🧩 **تست حل معما با دستور `/solve <پاسخ>`:**\n"
        "   • تیم ۱: `/solve خون` و `/solve 1356`\n"
        "   • تیم ۲: `/solve سایه` و `/solve 2910`\n"
        "   • تیم ۳: `/solve سکوت` و `/solve 5`\n"
        "   *(تست کدهای تیم دیگر هشدار تفکیک تیم‌ها را نمایش می‌دهد)*\n\n"
        "۴. 🔄 **تغییر تیم تست:**\n"
        "   • `/test_team 1` — سوئیچ به تیم ۱ (خون)\n"
        "   • `/test_team 2` — سوئیچ به تیم ۲ (سایه)\n"
        "   • `/test_team 3` — سوئیچ به تیم ۳ (سکوت)\n\n"
        "۵. ♻️ **ریست معماها جهت تست مجدد:**\n"
        "   دستور `/test_reset` — پاک کردن پاسخ‌ها و باز کردن مجدد پاکت‌ها.\n\n"
        "۶. ⚠️ **تست آلارم بحران ۲۳:۵۰:**\n"
        "   دستور `/broadcast_crisis`\n\n"
        "۷. 🕯 **تست سکانس فینال تاریکخانه ۰۱:۱۰:**\n"
        "   دستور `/trigger_finale`\n\n"
        "۸. 🎭 **تست افشای نهایی ۰۲:۰۰:**\n"
        "   دستور `/reveal_traitors`\n"
    )
    await message.answer(panel_text)

@router.message(Command("test_team"))
async def cmd_test_team(message: Message):
    """Switches tester's team to 1, 2, or 3."""
    user_id = message.from_user.id
    username = message.from_user.username
    if not is_admin(user_id, username):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    arg = message.text.partition(" ")[2].strip()
    if arg not in ["1", "2", "3"]:
        await message.answer("⚠️ لطفاً شماره تیم را وارد کنید (۱ یا ۲ یا ۳):\n`/test_team 1` یا `/test_team 2` یا `/test_team 3`")
        return

    t_num = int(arg)
    res = await database.assign_tester_team(user_id, t_num)
    await message.answer(f"✅ تیم شما با موفقیت به **{res['team_name']}** تغییر یافت!\nاکنون با دستور `/team` و `/solve` معماهای این تیم را تست کنید.")

@router.message(Command("test_reset"))
async def cmd_test_reset(message: Message):
    """Resets riddles for tester's current team."""
    user_id = message.from_user.id
    username = message.from_user.username
    if not is_admin(user_id, username):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    guest = await database.get_guest_by_telegram_id(user_id)
    t_num = guest.get("team_number", 1) if guest else 1
    await database.reset_team_riddles(t_num)
    await message.answer(f"♻️ وضعیت معماهای **تیم {t_num}** ریست شد. اکنون می‌توانید دوباره با `/solve` پاکت‌ها را حل کنید.")
