import asyncio
import sys
from pathlib import Path

import discord
import imapclient.exceptions
from httpx_oauth.clients.google import GoogleOAuth2

from settings import settings, load_settings
import bot_client
import logging
from email_client import email_client
from auth import oauth

REQUIRED_SETTINGS = {
    'IMAP_HOST': str,
    'IMAP_PORT': int,
    'GOOGLE_CLIENT_ID': str,
    'GOOGLE_CLIENT_SECRET': str,
    'GOOGLE_CLIENT_TOKEN_FILE': Path,
    'DISCORD_TOKEN': str,
    'EMAIL_ADDRESS': str,
    'EMAIL_FOLDER': str,
    'EMAIL_REFRESH_RATE': int,
    'DISCORD_CHANNEL_ID': int,
    'OAUTH_HTTP_PORT': int
}


class Setup:
    @staticmethod
    async def basic_setup():
        Setup.setup_loging()
        Setup.setup_settings()

        try:
            await Setup.setup_auth()
            await Setup.setup_email()
        except imapclient.exceptions.LoginError:
            await oauth.refresh_token()
            await Setup.setup_email()

        Setup.setup_bot()

        loop = asyncio.get_event_loop()
        loop.create_task(Setup.start_bot())
        loop.create_task(await email_client.wait_for_new_emails(bot_client.bot.on_new_email))
        loop.run_forever()

    @staticmethod
    def setup_settings():
        load_settings(REQUIRED_SETTINGS)

    @staticmethod
    def setup_loging():
        logger = logging.getLogger()

        logger.setLevel(logging.INFO)

        ch = logging.StreamHandler(sys.stdout)
        fh = logging.FileHandler('bot.log')

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(ch)
        logger.addHandler(fh)


    @staticmethod
    async def setup_auth():
        google_creds = GoogleOAuth2(
            settings['GOOGLE_CLIENT_ID'],
            settings['GOOGLE_CLIENT_SECRET']
        )

        token_file = settings['GOOGLE_CLIENT_TOKEN_FILE']
        auth_http_port = settings['OAUTH_HTTP_PORT']

        await oauth.login(token_file, google_creds, auth_http_port)

    @staticmethod
    async def setup_email():
        await email_client.login_imap_token(
            settings['IMAP_HOST'],
            settings['EMAIL_ADDRESS'],
            oauth.token['access_token']
        )
        await email_client.select_email_folder(settings['EMAIL_FOLDER'])

    @staticmethod
    def setup_bot():
        intents = discord.Intents.default()
        intents.message_content = True

        bot_client.bot = bot_client.EmailBot(intents=intents)

    @staticmethod
    async def start_bot():
        token = settings['DISCORD_TOKEN']
        await bot_client.bot.start(token)
