import logging
from pathlib import Path

import aiosqlite
from sanic import Sanic
from sanic.response import json
from sanic_compress import Compress
from sanic_jinja2 import SanicJinja2

database = 'app.sqlite3'
app = Sanic()
Compress(app)
jinja = SanicJinja2(app)
app.static('/favicon.ico', str(Path(Path.cwd(), 'favico.ico')))

log = logging.getLogger(__name__)


@app.listener("before_server_start")
async def before_server_start(*_):
    log.debug('before_server_start')
    async with aiosqlite.connect(database) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                '''
                CREATE TABLE
                IF NOT EXISTS
                data(
                    secret TEXT,
                    who    TEXT,
                    url    TEXT,
                    mark   INTEGER,
                    cats   TEXT,
                    desc   TEXT
                );
                '''
            )
        await conn.commit()


@app.route('/<secret:[A-z0-9]+>')
@jinja.template('index.html')
async def show_data(request, secret):
    order_by = request.args.get('order_by', 'mark')

    # TODO: prevent sql injection
    sql = (
        "SELECT * FROM data "
        "WHERE secret=? "
        "ORDER BY %s;" % order_by)
    log.debug('%r %r %r', secret, order_by, sql)
    async with aiosqlite.connect(database) as conn:
        cursor = await conn.execute(sql, [secret])
        rows = await cursor.fetchall()
        return {'rows': rows}


@app.route('/<secret:[A-z0-9]+>', methods={'POST'})
async def post_data(request, secret):
    log.debug('%r %r', secret, request.json)
    # TODO: validate schema
    # TODO: prevent spam, anyone can post
    async with aiosqlite.connect(database) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                'INSERT INTO data (secret, who, url, mark, cats, desc) VALUES (?, ?, ?, ?, ?, ?);',
                [
                    secret,
                    request.json['who'],
                    request.json['url'],
                    request.json['mark'],
                    request.json['cats'],
                    request.json['desc'],
                ]
            )
        await conn.commit()
    return json({'success': True, 'data': request.json})


def setup_logging(level):
    log = logging.getLogger('aiosqlite')
    log.setLevel(logging._nameToLevel[level])
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)8.8s - %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(formatter)
    log.addHandler(ch)


if __name__ == '__main__':
    setup_logging('DEBUG')
    app.run(host='0.0.0.0', port=8000)
