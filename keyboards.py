from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
import texts

def enter_dossier_kb() -> InlineKeyboardMarkup:
    """Button to enter the mansion party."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.ENTER_DOSSIER_BTN,
                    callback_data="enter_dossier"
                )
            ]
        ]
    )

def confirm_name_kb(guest_name: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard for matched name."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.CONFIRM_YES,
                    callback_data="name_confirmed"
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts.CONFIRM_NO,
                    callback_data="name_rejected"
                )
            ]
        ]
    )

def car_status_kb(is_preassigned: bool = False) -> InlineKeyboardMarkup:
    """Car options keyboard with preassigned friendly matching."""
    if is_preassigned:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.CAR_CONFIRM_PREASSIGNED_BTN,
                        callback_data="car_preassigned"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=texts.CAR_YES_BTN,
                        callback_data="car_yes"
                    )
                ]
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.CAR_NO_BTN,
                    callback_data="car_no"
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts.CAR_YES_BTN,
                    callback_data="car_yes"
                )
            ]
        ]
    )

def skip_car_passengers_kb() -> InlineKeyboardMarkup:
    """Button to skip entering specific car companions and allow auto-drafting."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.SKIP_CAR_PASSENGERS_BTN,
                    callback_data="skip_car_passengers"
                )
            ]
        ]
    )

def story_navigator_kb(act: int = 1) -> InlineKeyboardMarkup:
    """Interactive 4-act screenplay viewer."""
    tabs = []
    for i in range(1, 5):
        label = f"🔹 پرده {i} 🔹" if i == act else f"پرده {i}"
        tabs.append(InlineKeyboardButton(text=label, callback_data=f"show_act_{i}"))

    nav_row = []
    if act > 1:
        nav_row.append(InlineKeyboardButton(text="➡️ پرده قبلی", callback_data=f"show_act_{act - 1}"))
    if act < 4:
        nav_row.append(InlineKeyboardButton(text="پرده بعدی ⬅️", callback_data=f"show_act_{act + 1}"))

    keyboard = [
        tabs,
        nav_row if nav_row else [],
        [
            InlineKeyboardButton(
                text="⚖️ ادامه: انتخاب نقش من در مهمانی",
                callback_data="proceed_to_role"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=[r for r in keyboard if r])

def role_selection_detailed_kb() -> InlineKeyboardMarkup:
    """Role selection confirmation buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.ROLE_PLAYER_BTN,
                    callback_data="role_player"
                )
            ],
            [
                InlineKeyboardButton(
                    text=texts.ROLE_BLONDE_BTN,
                    callback_data="role_blonde"
                )
            ]
        ]
    )

def main_menu_reply_kb(role: str = "role_player", is_hunter: int = 0) -> ReplyKeyboardMarkup:
    """
    Persistent bottom menu providing instant 1-tap access to all party features.
    """
    kb_rows = []

    if role == "role_player":
        kb_rows.append([
            KeyboardButton(text="🔴 فانوس سرخ دیجیتال"),
            KeyboardButton(text="🔦 تیم من در حیاط")
        ])
        kb_rows.append([
            KeyboardButton(text="🎴 کارت دعوت من"),
            KeyboardButton(text="📜 طومار و ماموریت مخفی")
        ])
        if is_hunter == 1:
            kb_rows.append([
                KeyboardButton(text="🩸 تسخیر قربانی (شکار)")
            ])
        kb_rows.append([
            KeyboardButton(text="🚗 کاروان"),
            KeyboardButton(text="🎙 نوار کاست سرهنگ")
        ])
        kb_rows.append([
            KeyboardButton(text="⚰️ وضعیت زنده عمارت")
        ])
    else:
        # Blonde
        kb_rows.append([
            KeyboardButton(text="🎴 کارت دعوت من"),
            KeyboardButton(text="💡 روشن کردن نور حیات باغ")
        ])
        kb_rows.append([
            KeyboardButton(text="🚗 کاروان"),
            KeyboardButton(text="🎙 نوار کاست سرهنگ")
        ])
        kb_rows.append([
            KeyboardButton(text="⚰️ وضعیت زنده عمارت")
        ])

    return ReplyKeyboardMarkup(
        keyboard=kb_rows,
        resize_keyboard=True,
        is_persistent=True
    )

def midnight_action_kb() -> InlineKeyboardMarkup:
    """Action buttons for players during the final midnight game."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔴 دریافت تمام‌صفحه فانوس سرخ",
                    callback_data="dl_lantern"
                ),
                InlineKeyboardButton(
                    text="🔦 وضعیت تیم و معماها",
                    callback_data="chk_team"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧩 راهنمای ثبت پاسخ (/solve)",
                    callback_data="help_solve"
                ),
                InlineKeyboardButton(
                    text="📜 مرور کل قوانین بازی",
                    callback_data="rules_midnight"
                )
            ]
        ]
    )

def social_mission_player_kb(is_immune: bool = False, got_stickered: bool = False) -> InlineKeyboardMarkup:
    """Inline keyboard for social mission in Phase 2."""
    buttons = []
    if not is_immune:
        buttons.append([
            InlineKeyboardButton(
                text="✅ ماموریتم رو انجام دادم!",
                callback_data="claim_immunity"
            )
        ])
    if not got_stickered:
        buttons.append([
            InlineKeyboardButton(
                text="💀 استیکر خوردم!",
                callback_data="got_stickered"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_confirm_hunters_kb() -> InlineKeyboardMarkup:
    """Confirm hunter assignment."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🩸 ارسال پیام محرمانه به ۵ شکارچی",
                    callback_data="admin_notify_hunters"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 انتخاب مجدد",
                    callback_data="admin_reshuffle_hunters"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="admin_cancel_hunters"
                )
            ]
        ]
    )
