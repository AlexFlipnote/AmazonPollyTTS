import json
import asyncio
import sys
import time
import os

from functools import wraps
from utils import amazon, postgresql
from quart import Quart, request, abort, send_from_directory, jsonify

with open("config.json", "r") as f:
    config = json.load(f)

try:
    loop = asyncio.get_event_loop()
    pool = loop.run_until_complete(
        postgresql.create_pool(config["postgresql"], command_timeout=60)
    )

    print("Connected to postgresql successfully")

    data_create = loop.run_until_complete(
        postgresql.execute_sql_file(pool, "database_create")
    )

    print(f"Database: {data_create}")
except Exception as e:
    print(f"Failed to load postgresql, exiting.\n\nError: {e}")
    sys.exit(0)

app = Quart(__name__)

polly = amazon.AmazonPolly(
    config["access_key"],
    config["secret_access_key"],
    config["aws_region"]
)


def json_response(name: str, desc: str, code: int = 200):
    """ Returns a default JSON output for all API/error endpoints """
    return jsonify({"code": code, "name": name, "description": desc}), code


def authenticate(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", None)
        if not auth:
            abort(401, "Missing Authorization in headers")
        if auth != config["token"]:
            abort(403, "Invalid token for Authorization")
        return await func(*args, **kwargs)
    return wrapper


def ratelimit_manager(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = request.headers.get("user_id")
        if not user_id:
            abort(400, "Missing 'user_id' in headers")
        if not user_id.isdigit():
            abort(400, "'user_id' must be int value")

        data = await pool.fetch(
            "SELECT * FROM discord_user WHERE user_id=$1 AND created_at>$2",
            int(user_id), int(time.time()) - config["ratelimit_expire_seconds"]
        )

        can_bypass = int(user_id) in config["ratelimit_bypass_ids"]

        if not can_bypass and data:
            total_text_length = sum([g["text_length"] for g in data])
            max_length = config["ratelimit_text_length"]
            if total_text_length >= max_length:
                abort(429, f"You've used up all your characters for today ({total_text_length}/{max_length})")
        return await func(*args, **kwargs)
    return wrapper


@app.route("/")
async def index():
    return json_response("Success", "API is online, have some tea.", code=418)


@app.route("/audios/<filename>")
async def rendered_audios(filename: str):
    try:
        return await send_from_directory(config["file_location"], filename)
    except FileNotFoundError:
        return abort(404, "File not found")


@app.route("/reset_db")
@authenticate
async def reset_db():
    location = config["file_location"]
    all_files = [g for g in os.listdir(location) if g.endswith(".mp3")]
    for entry in all_files:
        os.remove(f"{location}/{entry}")

    sql_commands = ["DROP TABLE discord_user", "DROP TABLE files"]
    for command in sql_commands:
        try:
            show_res = await pool.execute(command)
            print(show_res)
        except Exception as e:
            print(f"{command}: {e}")
            pass  # Might already be dropped, idk

    try:
        await postgresql.execute_sql_file(pool, "database_create")
    except Exception as e:
        abort(500, str(e))

    return json_response("Success", "Dropped all data and recreated structure successfully")


@app.route("/users/<user_id>")
@authenticate
async def get_user_data(user_id: int):
    if not user_id.isdigit():
        abort(400, "UserID must be int")
    user_id = int(user_id)

    data = await pool.fetch(
        "SELECT * FROM discord_user WHERE user_id=$1 ORDER BY created_at",
        user_id
    )

    if not data:
        abort(404, "User was not found...")

    today_used = [
        g["text_length"] for g in data
        if data["created_at"] > int(time.time()) - config["ratelimit_expire_seconds"]
    ]

    return {
        "user_id": user_id,
        "char_used_today": sum(today_used),
        "char_used_total": sum([g["text_length"] for g in data]),
        "last_audio": data[-1]["audio_id"]
    }


@app.route("/create")
@authenticate
@ratelimit_manager
async def make_tts():
    text = request.headers.get("text")
    user_id = request.headers.get("user_id")
    if not text or not user_id:
        return abort(400, "Missing 'text' headers")

    get_cache = await pool.fetchrow(
        "SELECT * FROM files WHERE LOWER(text_input)=$1",
        text.lower()
    )

    if not get_cache:
        try:
            make_voice = polly.create_voice(text)
        except Exception as e:
            return {
                "code": 404,
                "response": "Unable to generate voice, AWS Polly failed...",
                "error": str(e)
            }

        results = polly.create_audio_file(
            make_voice, config["file_location"]
        )

        await pool.execute(
            "INSERT INTO files (text_input, audio_id, created_at, user_id) "
            "VALUES ($1, $2, $3, $4)",
            text.lower(), results.id, int(time.time()), int(user_id)
        )

        await pool.execute(
            "INSERT INTO discord_user (text_length, audio_id, created_at, user_id) "
            "VALUES ($1, $2, $3, $4)",
            len(text), results.id, int(time.time()), int(user_id)
        )
    else:
        results = amazon.AudioFile(
            config["file_location"],
            get_cache["audio_id"]
        )

    return {
        "code": 200,
        "response": results.id,
        "cache": bool(get_cache)
    }


@app.errorhandler(Exception)
async def handle_exception(e):
    return json_response(e.name, e.description, e.status_code)


app.run(port=config["port"], loop=loop)
