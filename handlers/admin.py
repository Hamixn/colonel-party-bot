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
        "🔒 `/lock_missions` — قفل کردن مجدد ماموریت‌های مخفی\n"
        "🧹 `/clean_guests` (یا `/reset_guests`) — پاکسازی کامل لیست مهمانان جهت ثبت‌نام مجدد\n"
        "👤 `/reset_guest <نام یا آیدی>` — حذف یک مهمان خاص جهت ثبت‌نام مجدد\n"
        "🧪 `/test` — راهنما و پنل تست جریان بازی (برای تستر)"
    )
    await message.answer(help_text)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Shows party registration and game statistics (Admin only, role-safe)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    stats = await database.get_stats()
    total = stats.get("total", 0)
    players = stats.get("players", 0)
    blondes = stats.get("blondes", 0)
    cars = stats.get("cars", 0)
    immune = stats.get("immune", 0)
    stickered = stats.get("stickered", 0)
    alibi_avail = stats.get("alibi_shields_available", 0)
    alibi_used = stats.get("alibi_shields_used", 0)
    acc_count = stats.get("accusations_count", 0)
    rescue_alerts = stats.get("rescue_alerts", 0)
    phase = stats.get("phase", "registration")
    teams = stats.get("teams", {})

    t_lines = []
    for t_num in (1, 2, 3):
        t_data = teams.get(t_num, {})
        size = t_data.get("size", 0)
        r1 = "✅" if t_data.get("riddle_1_solved") else "⏳"
        r2 = "✅" if t_data.get("riddle_2_solved") else "⏳"
        acc = "ثبت شد" if t_data.get("accusation_submitted") else "در انتظار"
        t_name = {1: "خون", 2: "سایه", 3: "سکوت"}.get(t_num, str(t_num))
        t_lines.append(f"• **تیم {t_num} ({t_name}):** {size} نفر | پاکت ۱: {r1} | پاکت ۲: {r2} | نظریه میز: {acc}")

    teams_str = "\n".join(t_lines) if t_lines else "تیم‌ها هنوز مشخص نشده‌اند."

    stats_msg = (
        "📊 **داشبورد وضعیت رویداد باغ سرهنگ:**\n\n"
        f"🏷 **فاز جاری رویداد:** `{phase}`\n"
        f"👥 **کل ثبت‌نام‌شدگان:** {total} نفر\n"
        f"🕵️‍♂️ **بازرسان فعال (پرونده):** {players} نفر\n"
        f"👱‍♀️ **همراهان مهمانی (بلوندها):** {blondes} نفر\n"
        f"🚗 **خودروهای حاضر در کاروان:** {cars} خودرو\n\n"
        "🔦 **وضعیت تیم‌های سه‌گانه نیمه‌شب:**\n"
        f"{teams_str}\n\n"
        "📜 **وضعیت بازی اجتماعی و آلیبای:**\n"
        f"• سپرهای آلیبای فعال (آماده مصرف): {alibi_avail} نفر\n"
        f"• سپرهای آلیبای مصرف‌شده: {alibi_used} نفر\n"
        f"• افراد نشان‌دار شده با استیکر: {stickered} نفر\n"
        f"• نظریه‌های ثبت‌شده روی میز مرکزی: {acc_count} از ۳ تیم"
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

@router.message(Command("assign_characters"))
async def cmd_assign_characters(message: Message, bot: Bot):
    """Admin command to assign and privately deliver the 4 special character roles."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    assigned = await database.assign_special_character_roles(force_reassign=True)
    if not assigned:
        await message.answer("⚠️ بازیکنی برای انتساب نقش‌های ویژه یافت نشد.")
        return

    success_count = 0
    fail_count = 0
    role_labels = {
        "shirin": "شیرین نوری (شاهد صحنه — تیم ۱)",
        "keyvan": "کیوان رستگار (عکاس مهمانی — تیم ۲)",
        "fereydoun": "دکتر فریدون مهر (پزشک معالج — تیم ۳)",
        "nader": "نادر وثوق (مقصر اصلی و مخفی)"
    }

    report_lines = ["🎭 **نتیجه انتساب نقش‌های ویژه پرونده سال ۵۶:**\n"]
    for role_key, guest in assigned.items():
        card_text = game.CHARACTER_ROLE_CARDS.get(role_key)
        tid = guest.get("telegram_id")
        delivered = False
        if tid and card_text:
            try:
                await bot.send_message(chat_id=tid, text=card_text)
                delivered = True
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"Failed delivering role card to {guest.get('full_name')}: {e}")

        status_icon = "📨 ارسال شد" if delivered else "⚠️ عدم ارسال به تلگرام"
        report_lines.append(f"• **{role_labels.get(role_key, role_key)}:** {guest.get('full_name')} — {status_icon}")

    await message.answer("\n".join(report_lines))

@router.message(Command("start_social_game"))
async def cmd_start_social_game(message: Message, bot: Bot):
    """
    Phase 2 (19:30 Social Sticker Game):
    1. Assigns 3 witness sticker carriers (Shirin, Keyvan, Dr. Fereydoun) + Nader Vosough.
    2. Sends private role cards explaining their 2 physical suspect stickers.
    3. Sends social missions to all remaining players with 1-use alibi shield button.
    4. Reassures casual blondes about VIP safe zone.
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    players = await database.get_players()
    if len(players) < 4:
        await message.answer(
            f"⚠️ تعداد بازیکنان ثبت‌شده ({len(players)} نفر) کمتر از ۴ نفر است!\n"
            f"برای انتساب ۳ شاهد و ۱ مقصر حداقل ۴ بازرس نیاز است."
        )
        return

    # Assign the scripted killer outside the three scoring teams and place one witness per team.
    assigned_roles = await database.assign_special_character_roles()
    if not assigned_roles or not all(k in assigned_roles for k in ("shirin", "keyvan", "fereydoun", "nader")):
        await message.answer("⚠️ انتساب نقش‌ها انجام نشد. حداقل ۴ بازرس فعال لازم است؛ ابتدا ثبت‌نام‌ها را بررسی کنید.")
        return
    await database.set_game_state("social_game_started", "1")
    await database.set_game_state("force_unlock_missions", "1")
    await database.set_game_state("game_phase", "social_game")

    # 1. Deliver private character cards to the 4 special roles
    role_success = 0
    role_failed = 0
    for role_key, guest in assigned_roles.items():
        tid = guest.get("telegram_id")
        card_text = game.CHARACTER_ROLE_CARDS.get(role_key)
        if tid and card_text:
            try:
                await bot.send_message(chat_id=tid, text=card_text)
                role_success += 1
            except Exception as e:
                role_failed += 1
                print(f"Error sending special role card to {guest['full_name']}: {e}")

    # 2. Notify remaining players with social missions & action buttons
    regular_success = 0
    witness_ids = {g["id"] for g in assigned_roles.values()}
    all_players = await database.get_players()
    for p in all_players:
        if p["id"] not in witness_ids:
            tid = p.get("telegram_id")
            if tid:
                mission_id = p.get("social_mission_id", 1)
                mission_text = game.SOCIAL_MISSIONS.get(mission_id, game.SOCIAL_MISSIONS[1])
                text = (
                    "📜 **[آغاز بازی اجتماعی سالن — ساعت ۱۹:۳۰ تا ۲۳:۵۰]**\n\n"
                    "پرونده‌ی باغ سرهنگ به جریان افتاد! ۳ شاهد کلیدی با استیکرهای نشان‌دار در سالن حضور دارند.\n\n"
                    f"🎯 **ماموریت اجتماعی شما جهت ثبت آلیبای و دریافت سپر:**\n"
                    f"||{mission_text}||\n\n"
                    "💡 پس از انجام گفت‌وگو، دکمه‌ی «✅ ماموریتم رو انجام دادم!» را بزنید تا یک سپر آلیبای (برای باطل کردن ۱ استیکر) دریافت نمایید.\n"
                    "⚠️ اگر استیکری به شما زده شد، دکمه‌ی «💀 استیکر خوردم!» یا «🛡 مصرف سپر» را لمس کنید."
                )
                kb = keyboards.social_mission_player_kb(
                    is_immune=bool(p.get("is_immune")),
                    got_stickered=bool(p.get("got_stickered")),
                    has_shield=bool((p.get("alibi_shields") or 0) > 0)
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
                    "بازی اجتماعی بازرسان در سالن آغاز شد!\n"
                    "شما در حاشیه امن مطلق قرار دارید؛ از نوشیدنی، موسیقی و تماشای تکاپوی دیگران لذت ببرید."
                )
            )
        except Exception:
            pass

    await message.answer(
        f"✅ **بازی اجتماعی ساعت ۱۹:۳۰ با موفقیت آغاز شد!**\n\n"
        f"🎭 کارت‌های محرمانه ۴ شخصیت اصلی (۳ شاهد + نادر): {role_success} ارسال موفق (خطا: {role_failed})\n"
        f"📜 ماموریت‌های اجتماعی برای {regular_success} بازرس دیگر ارسال گردید."
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

    phase = await database.get_game_state("game_phase", "registration")
    if phase != "social_game":
        await message.answer("⚠️ ابتدا /start_social_game را اجرا کنید؛ نقش‌ها باید پیش از آغاز تحقیقات تثبیت شوند.")
        return

    teams = await database.start_midnight_game()
    if not teams or not all(teams.get(t, {}).get("members") for t in (1, 2, 3)):
        await message.answer("⚠️ سه تیم کامل برای شروع تحقیقات موجود نیست. ثبت‌نام‌ها و نقش‌ها را بررسی کنید.")
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
                "🔴 **فانوس سرخ دیجیتال — وسیله‌ی نمایشی اختیاری** 🕯\n\n"
                "این تصویر جایگزین نور واقعی نیست. مسیرها، پله‌ها، اطراف استخر و خروجی‌ها باید روشن بمانند. "
                "برای ایمنی از چراغ‌قوه یا نور گوشی استفاده کنید؛ هیچ نور سفیدی موجب حذف یا جریمه‌ی بازی نمی‌شود."
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
                    "🍿 **[آغاز بازی نیمه‌شب]**\n\n"
                    "نورپردازی تزئینی و موسیقی ممکن است برای فضاسازی کاهش یابد؛ اما روشنایی ایمنی مسیرها، پله‌ها، اطراف استخر و خروجی‌ها همیشه برقرار می‌ماند.\n"
                    "پخش فیلم و پذیرایی در سالن ادامه دارد.\n\n"
                    "💡 در هر وضعیت ناایمن، بازی را متوقف کنید و از مسئول حاضر کمک بخواهید."
                )
            )
        except Exception:
            pass

    summary = ["🔦 **بازی ساعت ۲۴:۰۰ حیاط با موفقیت آغاز گردید!**\n"]
    for t_num, t_info in teams.items():
        m_count = len(t_info["members"])
        summary.append(f"• **{t_info['name']}** ({m_count} بازرس) — نقش‌های محرمانه برای بازیکنان ارسال شده‌اند.")

    await message.answer("\n".join(summary))

@router.message(Command("hint"))
async def cmd_hint(message: Message, bot: Bot):
    """
    Admin command to send progressive hints to a team.
    Usage: /hint <team_number: 1-3> <level: 1-3>
    Validates admin, team, and level; delivers hint privately to all members of that team.
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer(
            "⚠️ فرمت صحیح دستور:\n"
            "`/hint <شماره تیم: 1-3> <سطح راهنمایی: 1-3>`\n\n"
            "سطوح راهنمایی:\n"
            "• سطح ۱: اشاره ظریف (Subtle pointer)\n"
            "• سطح ۲: توضیح شفاف (Explicit explanation)\n"
            "• سطح ۳: راهنمای مستقیم میزبان (Host fallback)"
        )
        return

    try:
        t_raw = parts[1].replace("۱", "1").replace("۲", "2").replace("۳", "3")
        l_raw = parts[2].replace("۱", "1").replace("۲", "2").replace("۳", "3")
        team_num = int(t_raw)
        level = int(l_raw)
    except ValueError:
        await message.answer("❌ شماره تیم و سطح باید عدد باشند (مثلاً `/hint 1 2`).")
        return

    if team_num not in (1, 2, 3):
        await message.answer("❌ شماره تیم باید ۱، ۲ یا ۳ باشد.")
        return

    if level not in (1, 2, 3):
        await message.answer("❌ سطح راهنمایی باید ۱، ۲ یا ۳ باشد.")
        return

    hint_content = game.PROGRESSIVE_HINTS.get(team_num, {}).get(level)
    if not hint_content:
        await message.answer("❌ متن راهنمایی برای این تیم و سطح یافت نشد.")
        return

    hint_msg = texts.HINT_DELIVERY_TEMPLATE.format(
        level=level,
        hint_text=hint_content
    )

    members = await database.get_team_members(team_num)
    if not members:
        await message.answer(f"⚠️ هیچ عضوی برای تیم {team_num} در سیستم یافت نشد.")
        return

    success = 0
    failed = 0
    for m in members:
        tid = m.get("telegram_id")
        if tid:
            try:
                await bot.send_message(chat_id=tid, text=hint_msg)
                success += 1
            except Exception:
                failed += 1

    await message.answer(
        f"💡 راهنمایی سطح {level} با موفقیت برای {success} عضو تیم {team_num} ارسال شد. (خطا: {failed})"
    )

@router.message(Command("reveal_traitors"))
async def cmd_reveal_traitors(message: Message, bot: Bot):
    """
    Phase 4 (02:00 Reveal):
    Broadcasts the mystery solution, distinguishing Nader as sole killer from witnesses,
    and reveals infected and traitors to all guests.
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

    winning_team = await database.get_game_state("game_winner_team", "")
    win_team_text = "هنوز مشخص نشده است"
    if winning_team:
        try:
            wt_num = int(winning_team)
            win_team_text = {1: "تیم ۱ (خون)", 2: "تیم ۲ (سایه)", 3: "تیم ۳ (سکوت)"}.get(wt_num, f"تیم {wt_num}")
        except Exception:
            win_team_text = winning_team

    try:
        reveal_text = texts.REVEAL_ANNOUNCEMENT.format(
            hunters_list=h_str,
            traitors_list=t_str,
            winning_team_text=win_team_text
        )
    except KeyError:
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
    """
    Triggers the 01:10 AM Final Darkroom Sequence to all players.
    Idempotent and safe to call multiple times without duplicating or breaking state.
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    if await database.get_game_state("finale_triggered_at", ""):
        await message.answer("ℹ️ سکانس فینال قبلاً اجرا شده است؛ پیام تکراری ارسال نشد.")
        return

    from datetime import datetime, timezone
    await database.close_deductions()
    await database.set_game_state("game_phase", "finale")
    await database.set_game_state("finale_triggered_at", datetime.now(timezone.utc).isoformat())

    text = game.DARKROOM_FINAL_PROMPT
    success, failed = await send_broadcast(bot, text, role_filter="role_player")
    await message.answer(
        f"🕯 سکانس نهایی آغاز شد و مهلت اتهام‌ها بسته شد. پیام برای {success} بازرس ارسال شد. (خطا: {failed})"
    )

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

@router.message(Command("clean_guests"))
@router.message(Command("reset_guests"))
async def cmd_clean_guests(message: Message):
    """Wipes all registered guests from database so everyone can register from scratch."""
    user_id = message.from_user.id
    username = message.from_user.username
    if not is_admin(user_id, username):
        await message.answer("⛔️ دسترسی غیرمجاز. این دستور فقط مخصوص مدیر است.")
        return

    count = await database.clean_all_guests()
    msg = (
        f"🧹 **لیست مهمانان با موفقیت کاملاً پاکسازی شد!**\n\n"
        f"👥 **تعداد مهمانان حذف‌شده:** {count} نفر\n"
        f"🔢 شمارنده شماره سریال‌ها مجدداً از **#01** تنظیم گردید.\n"
        f"🔄 وضعیت فاز بازی به `registration` ریست شد.\n\n"
        f"✨ اکنون تمامی افراد می‌توانند با ارسال دستور /start ثبت‌نام را از ابتدا آغاز کرده و کارت دعوت شیک و جدید خود را دریافت نمایند."
    )
    await message.answer(msg)

@router.message(Command("reset_guest"))
async def cmd_reset_single_guest(message: Message):
    """Deletes a single guest by username, ID, or name so they can re-register."""
    user_id = message.from_user.id
    username = message.from_user.username
    if not is_admin(user_id, username):
        await message.answer("⛔️ دسترسی غیرمجاز.")
        return

    arg = message.text.partition(" ")[2].strip()
    if not arg:
        await message.answer("⚠️ لطفاً آیدی عددی، یوزرنیم یا نام مهمان را مشخص کنید:\n`/reset_guest 102725917` یا `/reset_guest @username` یا `/reset_guest سمیرا`")
        return

    name = await database.delete_guest_by_identifier(arg)
    if name:
        await message.answer(f"✅ ثبت‌نام مهمان «**{name}**» با موفقیت پاک شد. ایشان می‌توانند دوباره با /start ثبت‌نام کنند.")
    else:
        await message.answer(f"❌ مهمانی با مشخصات «{arg}» در دیتابیس یافت نشد.")

@router.message(Command("reset_me"))
async def cmd_reset_me(message: Message):
    """Allows an admin/tester to delete their own registration to test /start from scratch."""
    user_id = message.from_user.id
    deleted = await database.delete_guest_by_telegram_id(user_id)
    if deleted:
        await message.answer("♻️ ثبت‌نام شما پاک شد. اکنون می‌توانید با ارسال /start از اول ثبت‌نام کرده و کارت دعوت را دریافت کنید.")
    else:
        await message.answer("شما در حال حاضر در دیتابیس ثبت‌نام نشده‌اید. می‌توانید مستقیماً /start را ارسال کنید.")
