import os
import json
import hmac
import hashlib
import logging
from pathlib import Path
from urllib.parse import parse_qsl
from aiohttp import web
from aiogram import Bot

import config
import database

logger = logging.getLogger("ColonelWebServer")

DIST_DIR = Path(__file__).resolve().parent / "webapp" / "dist"

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validates Telegram WebApp initData against HMAC-SHA256 signature.
    Returns user dict extracted from parsed initData.
    """
    if not init_data:
        raise ValueError("No initData provided")

    vals = dict(parse_qsl(init_data, keep_blank_values=True))
    if "hash" not in vals:
        raise ValueError("Missing hash parameter")

    received_hash = vals.pop("hash")
    data_check_string = "\n".join(f"{k}={vals[k]}" for k in sorted(vals.keys()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash != received_hash:
        raise ValueError("Invalid hash signature")

    user_raw = vals.get("user", "{}")
    return json.loads(user_raw)

def get_current_user_id(request: web.Request) -> int:
    """Extracts authenticated user ID from header or falls back to admin ID for local dev."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data:
        try:
            user_info = validate_telegram_init_data(init_data, config.BOT_TOKEN)
            if "id" in user_info:
                return int(user_info["id"])
        except Exception as e:
            logger.debug(f"InitData validation failed: {e}")

    # Fallback for browser preview / local dev
    return config.ADMIN_USER_ID or 102725917

async def api_me(request: web.Request) -> web.Response:
    """Returns guest profile, carpool, team, and game state."""
    user_id = get_current_user_id(request)
    guest = await database.get_guest_by_telegram_id(user_id)

    if not guest:
        # Return default guest skeleton
        return web.json_response({
            "telegram_id": user_id,
            "full_name": "مهمان عمارت",
            "role": "role_player",
            "has_car": 0,
            "car_number": 1,
            "driver_name": "تعیین نشده",
            "driver_contact": "",
            "serial_number": 1,
            "soul_pin": "100",
            "team_number": 1,
            "team_name": "تیم ۱ (خون)",
            "teammates": [],
            "riddle_1_solved": 0,
            "riddle_2_solved": 0,
            "is_immune": 0,
            "is_traitor": 0
        })

    car_num = guest.get("car_number", 1) or 1
    driver_info = await database.get_driver_info_for_car(car_num)
    driver_contact = database.format_driver_contact(driver_info)

    team_num = guest.get("team_number")
    teammates = []
    if team_num:
        t_members = await database.get_team_members(team_num)
        teammates = [m["full_name"] for m in t_members]

    res = {
        "id": guest["id"],
        "telegram_id": guest["telegram_id"],
        "telegram_username": guest.get("telegram_username"),
        "full_name": guest["full_name"],
        "role": guest.get("role", "role_player"),
        "has_car": guest.get("has_car", 0),
        "car_number": car_num,
        "driver_name": driver_info.get("name"),
        "driver_contact": driver_contact,
        "serial_number": guest.get("serial_number", 1),
        "soul_pin": guest.get("soul_pin", "100"),
        "team_number": team_num,
        "team_name": guest.get("team_name", f"تیم {team_num}" if team_num else "نامشخص"),
        "teammates": teammates,
        "riddle_1_solved": guest.get("riddle_1_solved", 0),
        "riddle_2_solved": guest.get("riddle_2_solved", 0),
        "is_immune": guest.get("is_immune", 0),
        "is_traitor": guest.get("is_traitor", 0),
        "got_stickered": guest.get("got_stickered", 0)
    }
    return web.json_response(res)

async def api_solve(request: web.Request) -> web.Response:
    """Submits riddle answer from WebApp."""
    user_id = get_current_user_id(request)
    bot: Bot = request.app["bot"]

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"status": "invalid_json"}, status=400)

    answer = body.get("answer", "").strip()
    if not answer:
        return web.json_response({"status": "empty_answer"}, status=400)

    res = await database.check_team_riddle(user_id, answer)
    status = res.get("status")

    # If solved, notify teammates via bot
    team_num = res.get("team_number")
    if team_num and status in ["riddle_solved", "both_solved"]:
        teammates = await database.get_team_members(team_num)
        r_num = res.get("riddle_num", 1)
        for tm in teammates:
            if tm.get("telegram_id") and tm["telegram_id"] != user_id:
                try:
                    await bot.send_message(
                        chat_id=tm["telegram_id"],
                        text=f"⚡️ یکی از هم‌تیمی‌های شما در مینی‌اپ معمای شماره {r_num} را با موفقیت حل کرد!"
                    )
                except Exception:
                    pass

    return web.json_response(res)

async def api_rescue(request: web.Request) -> web.Response:
    """Triggers rescue courtyard light from WebApp."""
    user_id = get_current_user_id(request)
    bot: Bot = request.app["bot"]

    rescue_count = int(await database.get_game_state("rescue_count", "0"))
    if rescue_count >= 3:
        return web.json_response({
            "success": False,
            "error": "حداکثر سقف ۳ بار روشن کردن نور حیات باغ پر شده است."
        }, status=400)

    new_count = rescue_count + 1
    await database.set_game_state("rescue_count", str(new_count))

    # Alert players in garden
    players = await database.get_all_telegram_ids(role_filter="role_player")
    for pid in players:
        try:
            await bot.send_message(
                chat_id=pid,
                text="💡 **[امداد از سالن — نور حیات باغ روشن شد!]**\n\nبلوندهای بی‌گناه از پشت پنجره نور حیات باغ را روشن کردند! روح سرهنگ موقتاً کور شد؛ الان زمان فرار و پیدا کردن پاکت طلسم است!"
            )
        except Exception:
            pass

    return web.json_response({
        "success": True,
        "rescue_count": new_count
    })

async def api_claim_immunity(request: web.Request) -> web.Response:
    """Claims social mission immunity from WebApp."""
    user_id = get_current_user_id(request)
    await database.set_mission_completed(user_id)
    return web.json_response({"success": True})

async def api_state(request: web.Request) -> web.Response:
    """Returns general game state."""
    social_started = (await database.get_game_state("social_game_started", "0")) == "1"
    midnight_started = (await database.get_game_state("midnight_game_started", "0")) == "1"
    rescue_count = int(await database.get_game_state("rescue_count", "0"))

    return web.json_response({
        "social_game_started": social_started,
        "midnight_game_started": midnight_started,
        "rescue_count": rescue_count
    })

async def serve_index(request: web.Request) -> web.FileResponse:
    """Serves the WebApp index.html."""
    index_file = DIST_DIR / "index.html"
    if not index_file.exists():
        return web.Response(text="WebApp build not found. Run 'npm run build' inside webapp/", status=404)
    return web.FileResponse(index_file)

def create_web_app(bot: Bot) -> web.Application:
    """Builds and configures the aiohttp Web Application."""
    app = web.Application()
    app["bot"] = bot

    # API routes
    app.router.add_get("/api/me", api_me)
    app.router.add_post("/api/solve", api_solve)
    app.router.add_post("/api/rescue", api_rescue)
    app.router.add_post("/api/claim_immunity", api_claim_immunity)
    app.router.add_get("/api/state", api_state)

    # Static assets
    if DIST_DIR.exists():
        app.router.add_static("/assets", DIST_DIR / "assets")
        app.router.add_static("/audio", DIST_DIR / "audio")
        app.router.add_static("/fonts", DIST_DIR / "fonts")
        app.router.add_static("/images", DIST_DIR / "images")

    app.router.add_get("/", serve_index)
    app.router.add_get("/{tail:.*}", serve_index)

    return app

async def start_webapp_server(bot: Bot, port: int = 8080) -> web.AppRunner:
    """Starts the aiohttp WebApp web server in the background."""
    app = create_web_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 [Three.js Telegram Mini App] Running on http://0.0.0.0:{port}")
    return runner
