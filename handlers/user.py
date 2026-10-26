from pathlib import Path
import re
from typing import List
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, WebAppInfo
)

import config
import database
import keyboards
import texts
import guest_list
from guest_list import GUEST_ROSTER, find_matching_guests
from states import RegistrationStates
from card_generator import generate_invitation_card

router = Router()

def parse_companion_names(text: str) -> List[str]:
    """
    Splits input text by commas, newlines, or Persian/English 'and' conjunctions
    to extract companion first names.
    """
    if not text:
        return []
    t = text.replace("،", ",").replace("\n", ",")
    t = re.sub(r"\s+و\s+", ",", t)
    t = re.sub(r"\s+and\s+", ",", t, flags=re.IGNORECASE)
    parts = [p.strip() for p in t.split(",") if p.strip()]
    return parts

async def send_existing_card(message_or_callback, guest: dict):
    """Sends the saved invitation card to an already registered guest and enables persistent menu."""
    car_str = "دارای خودروی شخصی (ظرفیت همراه)" if guest.get("has_car") == 1 else "بدون خودرو (همسفر کاروان)"
    serial = guest.get("serial_number", 1)
    name = guest.get("full_name", "")
    role = guest.get("role", "role_player")
    pin = guest.get("soul_pin") or f"{(serial * 73 + 137) % 900 + 100}"
    is_hunter = guest.get("is_hunter", 0)

    if role == "role_player":
        caption = texts.CARD_CAPTION_PLAYER.format(name=name, serial=serial, pin=pin, car_status=car_str)
    else:
        caption = texts.CARD_CAPTION_BLONDE.format(name=name, serial=serial, car_status=car_str)

    card_buf = generate_invitation_card(name, role, serial, soul_pin=pin)
    photo_file = BufferedInputFile(card_buf.getvalue(), filename=f"invitation_soul_{serial}.png")

    card_buttons = [
        [
            InlineKeyboardButton(
                text="🔄 تغییر نقش (مهلت: تا ۱۸:۰۰ روز ۲۹ اکتبر)",
                callback_data="req_change_role"
            )
        ]
    ]
    if config.WEBAPP_URL:
        card_buttons.append([
            InlineKeyboardButton(
                text="🎴 چرخاندن کارت دعوت ۳ بعدی (مینی‌اپ)",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        ])

    card_inline_kb = InlineKeyboardMarkup(inline_keyboard=card_buttons)
    reply_kb = keyboards.main_menu_reply_kb(role=role, is_hunter=is_hunter)
    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback
    await target.answer_photo(photo=photo_file, caption=caption, reply_markup=card_inline_kb)
    await target.answer("🎛 از دکمه‌های پایین صفحه جهت دسترسی سریع به امکانات مهمانی استفاده کنید:", reply_markup=reply_kb)

    # Send Carpool & Driver Telegram ID summary
    car_num = guest.get("car_number")
    if car_num and 1 <= car_num <= 13:
        driver_info = await database.get_driver_info_for_car(car_num)
        driver_contact = database.format_driver_contact(driver_info)
        manifest = await database.get_carpool_manifest()
        car_info = manifest.get(car_num, {})
        other_passengers = [p for p in car_info.get("passengers", []) if p != guest.get("full_name")]
        pass_str = "، ".join(other_passengers) if other_passengers else "در حال تکمیل ظرفیت ۴ نفره"
        car_type = "🚗 کاپیتان و راننده خودرو" if guest.get("has_car") == 1 else "🚶 مسافر و سرنشین خودرو"

        car_summary = (
            f"🚗 **مشخصات ترابری خودروی شما در کاروان صدرا:**\n\n"
            f"🔢 **شماره خودرو:** خودروی شماره {car_num}\n"
            f"🚘 **راننده خودرو:** {driver_contact}\n"
            f"👥 **همسفران:** {pass_str}\n"
            f"👤 **وضعیت شما:** {car_type}\n"
            f"📍 **زمان و مکان تجمع:** پنجشنبه ۷ آبان — ساعت ۱۷:۳۰ رأس ورودی صدرا\n\n"
            f"💡 جهت دسترسی مجدد به اطلاعات خودرو می‌توانید دستور /carpool یا دکمه‌ی «🚗 کاروان صدرا» را لمس کنید."
        )
        await target.answer(car_summary)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Entry point for /start with dramatic voice narration."""
    user_id = message.from_user.id
    existing_guest = await database.get_guest_by_telegram_id(user_id)

    # If user already registered and has role, send card directly with menu
    if existing_guest and existing_guest.get("role"):
        await message.answer(texts.ALREADY_REGISTERED_CARD)
        await send_existing_card(message, existing_guest)
        return

    await state.clear()
    await state.set_state(RegistrationStates.waiting_for_name)

    voice_path = Path("assets/audio/welcome_narration.mp3")
    if voice_path.exists():
        try:
            voice_file = FSInputFile(str(voice_path), filename="colonel_garden_narration.mp3")
            await message.answer_voice(
                voice=voice_file,
                caption=texts.START_WELCOME_TEXT,
                reply_markup=keyboards.enter_dossier_kb()
            )
            return
        except Exception as e:
            print(f"Fallback to text message due to: {e}")

    await message.answer(
        texts.START_WELCOME_TEXT,
        reply_markup=keyboards.enter_dossier_kb()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Shows all interactive party game commands."""
    help_text = (
        "🏰 **راهنمای مهمانی و بازی باغ سرهنگ (شب ۲۹ اکتبر):**\n\n"
        "📜 `/mission` — مشاهده طومار و ماموریت مخفی شما جهت کسب مصونیت\n"
        "🚗 `/carpool` — مشاهده شماره خودرو و همسفران شما در کاروان صدرا\n"
        "🔦 `/team` — مشاهده وضعیت تیم شما در حیاط تاریک عمارت\n"
        "🔴 `/lantern` — دریافت تصویر فانوس سرخ تمام‌صفحه جهت حرکت در تاریکی حیاط\n"
        "🧩 `/solve <پاسخ>` — رمزگشایی پاکت‌های طلسم روی درختان باغ\n"
        "💡 `/rescue` — روشن کردن نور حیات باغ به مدت ۱۰ ثانیه (مخصوص بلوندها در سالن)\n"
        "⚰️ `/graveyard` — آمار زنده تسخیرشدگان و بازماندگان\n"
        "🎙 `/tape` — استماع نوار کاست ضبط‌شده سال ۱۳۵۶\n"
        "🎴 `/card` — دریافت مجدد کارت دعوت رسمی\n"
        "🔄 `/change_role` — تغییر نقش بین بازیکن طلسم و بلوند بی‌گناه (مهلت: تا ساعت ۱۸:۰۰ روز ۲۹ اکتبر)\n\n"
        "💡 برای دسترسی سریع‌تر، می‌توانید از دکمه‌های پایین صفحه نیز استفاده کنید!"
    )
    await message.answer(help_text)

@router.message(Command("card"))
@router.message(F.text == "🎴 کارت دعوت من")
async def cmd_card(message: Message):
    """Resend user's card if already registered."""
    guest = await database.get_guest_by_telegram_id(message.from_user.id)
    if guest and guest.get("role"):
        await send_existing_card(message, guest)
    else:
        await message.answer("⚠️ شما هنوز ثبت‌نام خود را در مهمانی تکمیل نکرده‌اید. با ارسال /start شروع کنید.")

@router.callback_query(F.data == "enter_dossier")
async def cb_enter_dossier(callback: CallbackQuery, state: FSMContext):
    """User clicks enter dossier button."""
    await callback.answer()
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.answer(texts.CHOOSE_NAME_PROMPT)

@router.message(RegistrationStates.waiting_for_name)
async def handle_typed_name(message: Message, state: FSMContext):
    """Handles free text typed by the user to match guest name without exposing the full list."""
    user_input = message.text.strip() if message.text else ""
    matches = find_matching_guests(user_input)

    if not matches:
        await message.answer(texts.NAME_NOT_FOUND)
        return

    if len(matches) == 1:
        matched_guest = matches[0]
        taken = await database.get_guest_by_name(matched_guest["name"])
        if taken and taken.get("telegram_id") != message.from_user.id and taken.get("role"):
            await message.answer(texts.NAME_ALREADY_TAKEN)
            return

        await state.update_data(candidate_name=matched_guest["name"])
        await state.set_state(RegistrationStates.confirming_name)
        await message.answer(
            texts.CONFIRM_NAME_PROMPT.format(name=matched_guest["name"]),
            reply_markup=keyboards.confirm_name_kb(matched_guest["name"])
        )
    else:
        # Show only close variants
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=g["name"], callback_data=f"pick_variant_{g['id']}")]
                for g in matches[:5]
            ]
        )
        await message.answer("کدام مورد مد نظر شماست؟", reply_markup=kb)

@router.callback_query(F.data.startswith("pick_variant_"))
async def cb_pick_variant(callback: CallbackQuery, state: FSMContext):
    """User clicks one of the close variants of their typed name."""
    await callback.answer()
    try:
        guest_id = int(callback.data.split("_")[2])
        selected = next((g for g in GUEST_ROSTER if g["id"] == guest_id), None)
    except (IndexError, ValueError):
        selected = None

    if not selected:
        await callback.message.answer(texts.NAME_NOT_FOUND)
        return

    taken = await database.get_guest_by_name(selected["name"])
    if taken and taken.get("telegram_id") != callback.from_user.id and taken.get("role"):
        await callback.message.answer(texts.NAME_ALREADY_TAKEN)
        return

    await state.update_data(candidate_name=selected["name"])
    await state.set_state(RegistrationStates.confirming_name)
    await callback.message.answer(
        texts.CONFIRM_NAME_PROMPT.format(name=selected["name"]),
        reply_markup=keyboards.confirm_name_kb(selected["name"])
    )

@router.callback_query(RegistrationStates.confirming_name, F.data == "name_confirmed")
async def cb_name_confirmed(callback: CallbackQuery, state: FSMContext):
    """User confirms their name. Check pre-assigned car groups & psychology."""
    await callback.answer()
    data = await state.get_data()
    full_name = data.get("candidate_name")

    if not full_name:
        await callback.message.answer(texts.NAME_NOT_FOUND)
        await state.set_state(RegistrationStates.waiting_for_name)
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_car)

    # Check pre-assigned car group in roster
    matched = guest_list.find_matching_guests(full_name)
    p = matched[0] if matched else None

    if p and p.get("is_driver"):
        # Designated driver
        cg = p.get("car_group", 1)
        members = [m["name"] for m in guest_list.get_car_group_members(cg) if m["name"] != p["name"]]
        members_str = "، ".join(members)

        driver_msg = (
            f"🚗 **تبریک {p['name']}! شما به عنوان کاپیتان خودروی شماره {cg} ثبت شده‌اید.**\n\n"
            f"👥 **همسفران گروه شما برای حرکت ۱۷:۳۰ از ورودی صدرا:**\n"
            f"• {members_str}\n\n"
            f"⛔️ **قانون خروج از عمارت (بسیار مهم):**\n"
            f"دروازه‌ی باغ پس از بسته شدن در ساعت ۱۸:۱۵، **تا ساعت ۲۴:۰۰ نیمه‌شب تحت هیچ شرایطی باز نخواهد شد!** خروج زودهنگام قبل از ساعت ۱۲ امکان‌پذیر نیست.\n\n"
            f"ساعت ۱۷:۳۰ در ورودی صدرا منتظر شما و همسفرانتان هستیم!"
        )
        await database.register_or_update_guest(
            telegram_id=callback.from_user.id,
            telegram_username=callback.from_user.username,
            full_name=full_name,
            has_car=1,
            car_number=cg
        )
        await state.update_data(has_car=1, car_number=cg)
        await state.set_state(RegistrationStates.waiting_for_role)

        await callback.message.answer(driver_msg)
        # Proceed to story
        await callback.message.answer(
            f"📜 **فیلم‌نامه و سناریوی شب ۲۹ اکتبر — باغ سرهنگ**\n\n"
            f"{texts.ACT_1_TEXT}\n\n"
            f"*(برای مرور پرده‌های بعدی یا رفتن به انتخاب نقش، از دکمه‌های زیر استفاده کنید)*",
            reply_markup=keyboards.story_navigator_kb(act=1)
        )
        return

    elif p and p.get("car_group") is not None:
        # Pre-assigned passenger / squad
        cg = p.get("car_group")
        members = [m["name"] for m in guest_list.get_car_group_members(cg) if m["name"] != p["name"]]
        members_str = "، ".join(members) if members else "دوستان گروه شما"

        car_label = f"خودروی شماره {cg}" if cg > 0 else "گروه همسفران صمیمی شما"
        preassigned_msg = (
            f"🚘 **همسفران شما از پیش هماهنگ شده است!**\n\n"
            f"شما به صورت هوشمند با گروه دوستانتان ست شده‌اید:\n"
            f"🔹 **{car_label}**\n"
            f"👥 همسفران شما: **{members_str}**\n\n"
            f"⛔️ **قانون خروج از عمارت (بسیار مهم):**\n"
            f"دروازه‌های عمارت پس از بسته شدن در ساعت ۱۸:۱۵، **تا ساعت ۲۴:۰۰ نیمه‌شب تحت هیچ شرایطی باز نخواهد شد!**\n"
            f"خروج زودهنگام قبل از ساعت ۱۲ شب امکان‌پذیر نیست؛ بنابراین آوردن خودروی شخصی **هیچ انعطافی در زمان رفت‌وآمد به همراه ندارد.**\n\n"
            f"⚠️ کوچه‌باغ عمارت فوق‌العاده باریک است و جای پارک فقط برای ۱۳ خودرو در نظر گرفته شده است."
        )
        await callback.message.answer(
            preassigned_msg,
            reply_markup=keyboards.car_status_kb(is_preassigned=True)
        )
        return

    # General guest without pre-assigned car
    await callback.message.answer(
        texts.CAR_STATUS_PROMPT,
        reply_markup=keyboards.car_status_kb(is_preassigned=False)
    )

@router.callback_query(RegistrationStates.confirming_name, F.data == "name_rejected")
async def cb_name_rejected(callback: CallbackQuery, state: FSMContext):
    """User rejects name, re-prompt to type."""
    await callback.answer()
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.answer("لطفاً نام کوچک خود را ارسال فرمایید:")

@router.callback_query(RegistrationStates.waiting_for_car, F.data.in_(["car_yes", "car_no", "car_preassigned"]))
async def cb_car_status(callback: CallbackQuery, state: FSMContext):
    """User chooses car status."""
    await callback.answer()
    data = await state.get_data()
    full_name = data.get("full_name", "مهمان عمارت")

    if callback.data == "car_yes":
        has_car = 1
        car_num = await database.find_or_create_car_for_driver(callback.from_user.id, full_name)
        await database.register_or_update_guest(
            telegram_id=callback.from_user.id,
            telegram_username=callback.from_user.username,
            full_name=full_name,
            has_car=1,
            car_number=car_num
        )
        await state.update_data(has_car=1, car_number=car_num)
        await state.set_state(RegistrationStates.waiting_for_car_passengers)
        await callback.message.answer(
            texts.CAR_PASSENGERS_PROMPT.format(car_num=car_num),
            reply_markup=keyboards.skip_car_passengers_kb()
        )
        return
    else:
        # car_no or car_preassigned
        has_car = 0
        car_num = await database.find_best_carpool_match(full_name)
        await database.register_or_update_guest(
            telegram_id=callback.from_user.id,
            telegram_username=callback.from_user.username,
            full_name=full_name,
            has_car=0,
            car_number=car_num
        )
        await state.update_data(has_car=0, car_number=car_num)
        await state.set_state(RegistrationStates.waiting_for_role)

        # Retrieve driver Telegram contact and carpool status
        driver_info = await database.get_driver_info_for_car(car_num)
        driver_contact = database.format_driver_contact(driver_info)

        manifest = await database.get_carpool_manifest()
        car_info = manifest.get(car_num, {})
        other_passengers = [p for p in car_info.get("passengers", []) if p != full_name]
        pass_str = "، ".join(other_passengers) if other_passengers else "در حال تکمیل ظرفیت ۴ نفره"

        confirm_text = (
            f"🎉 **هماهنگی همسفری شما در کاروان صدرا انجام شد!**\n\n"
            f"🔢 **شماره خودرو:** خودروی شماره {car_num}\n"
            f"🚘 **راننده خودرو:** {driver_contact}\n"
            f"👥 **سایر همسفران:** {pass_str}\n"
            f"📍 **زمان و مکان تجمع:** پنجشنبه ۷ آبان — ساعت ۱۷:۳۰ رأس ورودی صدرا\n\n"
            f"💡 شما به عنوان سرنشین در این خودرو قرار گرفتید تا ظرفیت ۴ نفره خودرو تکمیل شود."
        )

        await callback.message.answer(confirm_text)

        # Launch interactive story explorer (Act 1)
        await callback.message.answer(
            f"📜 **فیلم‌نامه و سناریوی شب ۲۹ اکتبر — باغ سرهنگ**\n\n"
            f"{texts.ACT_1_TEXT}\n\n"
            f"*(برای مرور پرده‌های بعدی یا رفتن به انتخاب نقش، از دکمه‌های زیر استفاده کنید)*",
            reply_markup=keyboards.story_navigator_kb(act=1)
        )

@router.message(RegistrationStates.waiting_for_car_passengers)
async def handle_car_passengers(message: Message, state: FSMContext):
    """Handles text input when a driver enters their companions' first names."""
    data = await state.get_data()
    car_num = data.get("car_number", 1)
    raw_names = parse_companion_names(message.text or "")
    if not raw_names:
        await message.answer(
            "لطفاً نام کوچک همسفران خود را بنویسید (مثلاً: کیانا، سایه) یا دکمه‌ی زیر را لمس کنید:",
            reply_markup=keyboards.skip_car_passengers_kb()
        )
        return

    confirmed = await database.assign_named_passengers_to_car(car_num, raw_names)
    confirmed_str = "، ".join(confirmed)
    seats_left = max(0, 4 - (1 + len(confirmed)))

    if seats_left > 0:
        seats_msg = f"ظرفیت هر ماشین ۴ نفر است ({seats_left} صندلی باقی‌مانده به صورت خودکار با سایر مهمانان کاروان تکمیل خواهد شد)."
    else:
        seats_msg = "ظرفیت ۴ نفره خودروی شما تکمیل شد."

    await state.set_state(RegistrationStates.waiting_for_role)
    await message.answer(
        f"✅ **همسفران شما در خودروی شماره {car_num} ثبت شدند:**\n"
        f"• {confirmed_str}\n\n"
        f"💡 {seats_msg}"
    )

    # Launch interactive story explorer (Act 1)
    await message.answer(
        f"📜 **فیلم‌نامه و سناریوی شب ۲۹ اکتبر — باغ سرهنگ**\n\n"
        f"{texts.ACT_1_TEXT}\n\n"
        f"*(برای مرور پرده‌های بعدی یا رفتن به انتخاب نقش، از دکمه‌های زیر استفاده کنید)*",
        reply_markup=keyboards.story_navigator_kb(act=1)
    )

@router.callback_query(RegistrationStates.waiting_for_car_passengers, F.data == "skip_car_passengers")
async def cb_skip_car_passengers(callback: CallbackQuery, state: FSMContext):
    """Driver chooses to skip companion input and let system auto-draft remaining seats."""
    await callback.answer()
    data = await state.get_data()
    car_num = data.get("car_number", 1)
    await state.set_state(RegistrationStates.waiting_for_role)

    await callback.message.answer(
        f"✅ **خودروی شماره {car_num} ثبت شد.**\n"
        f"صندلی‌های خودرو به صورت خودکار با سایر مهمانان بدون خودرو تکمیل خواهد شد (تا سقف ۴ نفر)."
    )

    # Launch interactive story explorer (Act 1)
    await callback.message.answer(
        f"📜 **فیلم‌نامه و سناریوی شب ۲۹ اکتبر — باغ سرهنگ**\n\n"
        f"{texts.ACT_1_TEXT}\n\n"
        f"*(برای مرور پرده‌های بعدی یا رفتن به انتخاب نقش، از دکمه‌های زیر استفاده کنید)*",
        reply_markup=keyboards.story_navigator_kb(act=1)
    )

@router.callback_query(F.data.startswith("show_act_"))
async def cb_show_act(callback: CallbackQuery):
    """Interactive navigation across the 4 acts of the party."""
    await callback.answer()
    try:
        act_num = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        act_num = 1

    act_texts = {
        1: texts.ACT_1_TEXT,
        2: texts.ACT_2_TEXT,
        3: texts.ACT_3_TEXT,
        4: texts.ACT_4_TEXT
    }
    current_act_text = act_texts.get(act_num, texts.ACT_1_TEXT)

    await callback.message.edit_text(
        f"📜 **فیلم‌نامه و سناریوی شب ۲۹ اکتبر — باغ سرهنگ**\n\n"
        f"{current_act_text}\n\n"
        f"*(برای مرور سایر پرده‌ها یا ورود به انتخاب نقش، دکمه‌های زیر را لمس کنید)*",
        reply_markup=keyboards.story_navigator_kb(act=act_num)
    )

@router.callback_query(F.data == "proceed_to_role")
async def cb_proceed_to_role(callback: CallbackQuery, state: FSMContext):
    """Shows role selection screen with info buttons."""
    await callback.answer()
    await state.set_state(RegistrationStates.waiting_for_role)
    await callback.message.answer(
        texts.ROLE_SELECTION_PROMPT,
        reply_markup=keyboards.role_selection_detailed_kb()
    )

@router.callback_query(F.data == "info_player")
async def cb_info_player(callback: CallbackQuery):
    """Shows player role info modal."""
    await callback.answer("جزئیات نقش بازیکن طلسم", show_alert=False)
    await callback.message.answer(
        texts.ROLE_PLAYER_DESC,
        reply_markup=keyboards.role_selection_detailed_kb()
    )

@router.callback_query(F.data == "info_blonde")
async def cb_info_blonde(callback: CallbackQuery):
    """Shows blonde role info modal."""
    await callback.answer("جزئیات نقش بلوند بی‌گناه", show_alert=False)
    await callback.message.answer(
        texts.ROLE_BLONDE_DESC,
        reply_markup=keyboards.role_selection_detailed_kb()
    )

@router.callback_query(RegistrationStates.waiting_for_role, F.data.in_(["role_player", "role_blonde"]))
async def cb_select_role(callback: CallbackQuery, state: FSMContext):
    """User selects their role for the party night."""
    role = callback.data

    # Check capacity for players
    if role == "role_player":
        player_count = await database.count_role("role_player")
        if player_count >= config.PLAYER_CAP:
            await callback.answer("ظرفیت بازیکنان تکمیل است!", show_alert=True)
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            blonde_only_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=texts.ROLE_BLONDE_BTN,
                            callback_data="role_blonde"
                        )
                    ]
                ]
            )
            await callback.message.answer(
                texts.ROLE_PLAYER_CAP_REACHED,
                reply_markup=blonde_only_kb
            )
            return

    await callback.answer()

    # Save chosen role in DB
    guest = await database.set_guest_role(callback.from_user.id, role)
    await state.clear()

    if not guest:
        await callback.message.answer("⚠️ خطایی رخ داد، لطفاً مجدداً /start کنید.")
        return

    # Generate and send dynamic gothic invitation card + activate persistent menu
    await callback.message.answer("⏳ در حال صدور و ارسال کارت دعوت رسمی شما...")
    await send_existing_card(callback, guest)
