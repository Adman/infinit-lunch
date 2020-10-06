#!/usr/bin/env python3

import asyncio
import os
from datetime import datetime

import aiohttp
from aiohttp import web
from raven import Client

from restaurants import (
    FormattedMenus,
    SafeRestaurant,
    OtherRestaurant,
    DonQuijoteRestaurant,
    DreamsRestaurant,
    KantinaRestaurant,
    PlzenskaBranaRestaurant,
    MenuUJelena,
    GastrohouseRestaurant,
)
                        
from slack import Channel
from slackclient import SlackClient

# SLACK_HOOK = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
SLACK_HOOK = os.environ.get('SLACK_HOOK', None)
SLACK_LEGACY_TOKEN = os.environ.get('SLACK_LEGACY_TOKEN', None)
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', None)
SECRET_KEY = os.environ.get('SECRET_KEY', None)
DEBUG = bool(os.environ.get('DEBUG', False))


def is_work_day():
    return datetime.today().weekday() in range(0, 5)


def should_send_to_slack(secret_key):
    return SLACK_HOOK and secret_key == SECRET_KEY


async def retrieve_menus(session):
    futures = [
        SafeRestaurant(DonQuijoteRestaurant(session)).retrieve_menu(),
        SafeRestaurant(KantinaRestaurant(session)).retrieve_menu(),
        SafeRestaurant(PlzenskaBranaRestaurant(session)).retrieve_menu(),
        SafeRestaurant(DreamsRestaurant(session)).retrieve_menu(),
        SafeRestaurant(MenuUJelena(session)).retrieve_menu(),
        SafeRestaurant(GastrohouseRestaurant(session)).retrieve_menu(),
    ]

    # Add list of other restaurants first, will be in header.
    menus = [await SafeRestaurant(OtherRestaurant()).retrieve_menu()]
    for future in asyncio.as_completed(futures):
        menus.append(await future)

    return menus


def create_poll():
    candidates = [
        'avalon',
        'bezzinka',
        'bigger',
        'bistro',
        'cantina',
        'casa',
        'chefstreet',
        'freshmarket',
        'hladovka',
        'mango',
        'oliva',
        'toto',
    ]
    client = SlackClient(SLACK_LEGACY_TOKEN)
    return client.api_call(
        'chat.command',
        channel=SLACK_CHANNEL,
        command='/votemeal',
        text='new ' + ' '.join(candidates),
    )


async def index(request):
    if is_work_day():
        async with aiohttp.ClientSession() as session:
            menus = FormattedMenus(await retrieve_menus(session))
            secret_key = request.match_info.get('secret_key')
            if should_send_to_slack(secret_key):
                await Channel(SLACK_HOOK, session).send(menus)
            if SLACK_LEGACY_TOKEN and SLACK_CHANNEL and secret_key == SECRET_KEY:
                create_poll()
            return web.Response(text=str(menus))
    return web.Response(text='Come on Monday-Friday')


sentry_client = Client()            # credentials is taken from environment variable SENTRY_DSN

app = web.Application(debug=True)
app.router.add_get('/', index)
app.router.add_get('/{secret_key}', index)

if __name__ == '__main__':
    web.run_app(app, host='localhost', port=5000)
