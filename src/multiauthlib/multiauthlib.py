#!/usr/bin/python

from aiohttp import web, ClientSession
import asyncio
from pathlib import Path
import json
import logging
from time import time

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

session: ClientSession = None
routes = web.RouteTableDef()
server_cache = dict()
parsed_config = dict()
extra_headers = dict()

async def _check_name_from_server(player_name: str, server: dict) -> dict:
    try:
        headers = {**extra_headers}
        server_name, server_url = server.get("name"), server.get("url")
        if server_url:
            headers = {**headers, "Content-Type": "application/json; charset=utf-8"}
            async with session.post(f"{server_url}/api/profiles/minecraft", headers=headers, json=[player_name]) as resp:
                resp.raise_for_status()
                user_profile: list = await resp.json()
        else:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}", headers=headers) as resp:
                if resp.status == 204:
                    user_profile = list()
                else:
                    resp.raise_for_status()
                    user_profile: list = [await resp.json()]
        assert isinstance(user_profile, list) and len(user_profile) <= 1
        if user_profile:
            player_name = user_profile[0]["name"]
            player_uuid = user_profile[0]["id"]
            logger.info(f"found {player_name=} {player_uuid=} from {server_name=}")
            return {"uuid": player_uuid, "server": server}
        else:
            logger.info(f"found NO {player_name=} from {server_name=}")
    except Exception:
        logger.exception(f"error checking uuid for {player_name=} at {server_name=}")
    return None

async def _check_servers(player_name: str) -> dict:
    assert isinstance(player_name, str) and player_name
    now = time()
    cached_server_info = server_cache.setdefault(player_name, {"time": 0.0})
    if now - cached_server_info.get("time", 0.0) > parsed_config.get("max_cache_time"):
        for servers in parsed_config.get("servers", list()):
            results = list(filter(None, await asyncio.gather(*[_check_name_from_server(player_name, server) for server in servers])))
            if results:
                cached_server_info["servers"] = [i["server"] for i in results]
                break
        cached_server_info["time"] = now
    return cached_server_info.get("servers", list())

async def _check_login(query: dict, server: dict) -> dict:
    try:
        headers = {**extra_headers}
        player_name = query['username']
        server_name = server.get("name")
        server_url = server.get("url")
        server_url = server_url + "/sessionserver" if server_url else "https://sessionserver.mojang.com"
        async with session.get(f"{server_url}/session/minecraft/hasJoined", params=query, headers=headers) as resp:
            if resp.status == 204:
                logger.info(f"found {player_name=} NOT logged in at {server_name=}")
                return None
            else:
                resp.raise_for_status()
                logger.info(f"found {player_name=} logged in at {server_name=}")
                return {"body": await resp.read(), "status": resp.status, "content_type": resp.content_type, "charset": resp.charset}
    except Exception:
        logger.exception(f"error checking login for {player_name=} at {server_name=}")
    return None
@routes.get('/')
async def on_proxy_info_get(request: web.Request) -> web.Response:
    ret = {
        "meta":{
            "serverName": "multi-authlib",
            "implementationName": "multi-authlib"
        },
        "skinDomains":[
        ]
    }
    return web.Response(body=json.dumps(ret), content_type='application/json', charset='utf-8')
@routes.get('/sessionserver/session/minecraft/hasJoined')
async def on_server_check_join(request: web.Request) -> web.Response:
    query = {k: v for k, v in request.query.items() if k in {"username", "serverId", "ip"}}
    assert query["username"] and query["serverId"]
    servers = await _check_servers(query["username"])
    result = list(filter(None, await asyncio.gather(*[_check_login(query, server) for server in servers])))
    if result:
        resp: dict = result[0]
        return web.Response(**resp)
    else:
        return web.Response(status=204)

async def create_session(*_):
    globals()['session'] = ClientSession()
async def cleanup(*_):
    logger.info("closing session")
    await session.close()

def main():
    default_config = {
        "max_cache_time": 3600.0,
        "useragent": "Mozilla/5.0 (compatible; multi-authlib/0.0.1; +https://github.com/isjerryxiao/multi-authlib)",
        "servers": [
            [
                {"name": "mojang", "url": ""},
                {"name": "jerry", "url": "https://bs.meson.cc/api/yggdrasil"}
            ]
        ]
    }
    import argparse
    parser = argparse.ArgumentParser(description='smart yggdrasil proxy')
    parser.add_argument('-c', '--config', type=str, default="config.json")
    parser.add_argument('-H', '--host', type=str, default="::")
    parser.add_argument('-p', '--port', type=str, default="8080")
    args = parser.parse_args()

    config_file = Path(args.config)
    if not config_file.exists():
        config_file.write_text(json.dumps(default_config, indent=2))
    globals()["parsed_config"] = json.loads(config_file.read_text())
    globals()["extra_headers"] = {"User-Agent": parsed_config.get("useragent")}

    app = web.Application()
    app.add_routes(routes)
    app.on_startup.append(create_session)
    app.on_cleanup.append(cleanup)
    web.run_app(app, host=args.host, port=args.port)

if __name__ == '__main__':
    main()
