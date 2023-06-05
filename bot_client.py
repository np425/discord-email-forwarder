import email.message

import discord
import logging

import settings
import nest_asyncio

from email_formatter import EmailFormatter

MESSAGE_MAX_LENGTH = 2000


class EmailBot(discord.Client):
    async def on_ready(self):
        logging.info(f'Bot logged in on as {self.user}')
        nest_asyncio.apply(bot.loop)

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.content == 'ping':
            await message.channel.send('pong')

    async def on_new_email(self, message: email.message.Message):
        channel = self.get_channel(settings.settings['DISCORD_CHANNEL_ID'])

        email_subject = message['Subject']

        content = EmailFormatter.format_message(message)

        text_content = content.text_content

        # convert files to discord files
        files = [discord.File(file) for file in content.files]

        if len(content.text_content) > MESSAGE_MAX_LENGTH:
            text_content = content.text_content[:MESSAGE_MAX_LENGTH]
            logging.info(f'Email content exceeds max message length! ({email_subject}')

        try:
            await channel.send(text_content, files=files)
        except Exception as e:
            logging.error(f'Failed to send email ({email_subject}), reason: {e}')


bot: EmailBot | None = None
