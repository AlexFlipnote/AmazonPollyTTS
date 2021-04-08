import json
import asyncpg


async def create_pool(uri, **kwargs):
    """ Setup and return PostgreSQL connection """
    def encode_jsonb(value):
        return json.dumps(value)

    def decode_jsonb(value):
        return json.loads(value)

    async def init(con):
        await con.set_type_codec(
            "jsonb", schema="pg_catalog",
            encoder=encode_jsonb, decoder=decode_jsonb,
            format="text"
        )

    pool = await asyncpg.create_pool(uri, init=init, **kwargs)
    return pool


async def execute_sql_file(pool, filename: str):
    """ Create the default database structure """
    with open(f"./sql_commands/{filename}.sql", "r") as f:
        data = f.read()

    results = await pool.execute(data)
    print(f"No errors | {results}")
