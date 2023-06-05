import asyncio
import logging

from aioimaplib import IMAP4_SSL
from typing import Callable, Coroutine
import re

import settings
import email

FETCH_MESSAGE_DATA_UID = re.compile(rb'.*UID (?P<uid>\d+).*')


class EmailClient:
    def __init__(self):
        self.imap_client: IMAP4_SSL | None = None
        self.next_email_uid = 1

    async def login_imap_token(self, host: str, email_login: str, token: str, timeout=60):
        self.imap_client = IMAP4_SSL(host, timeout=timeout)

        await self.imap_client.wait_hello_from_server()
        response = await self.imap_client.xoauth2(email_login, token)

        logging.info(response)

    async def select_email_folder(self, folder: str):
        result = await self.imap_client.select(folder)
        line = result.lines[5].decode('UTF-8')
        uid = int(re.search('UIDNEXT (?P<uid>\d*)', line).group('uid'))
        self.next_email_uid = uid

    async def fetch_new_emails(self, headers: str | None = None):
        if not headers:
            headers = 'UID BODY.PEEK[]'

        emails = []

        response = await self.imap_client.uid('fetch', '%d:*' % (self.next_email_uid + 1),
                                              f'({headers})')

        old_max_uid = self.next_email_uid

        if response.result == 'OK':
            for i in range(0, len(response.lines) - 1, 3):
                new_email = email.message_from_bytes(response.lines[i + 1])

                fetch_command_without_literal = b'%s %s' % (response.lines[i], response.lines[i + 2])

                uid = int(FETCH_MESSAGE_DATA_UID.match(fetch_command_without_literal).group('uid'))
                if uid >= old_max_uid:
                    emails.append(new_email)
                    self.next_email_uid = uid + 1
        else:
            logging.error(f"error getting new emails {response}")

        return emails

    async def wait_for_new_emails(self, receiver: Callable[[email.message.Message], Coroutine] | None):
        timeout = settings.settings['EMAIL_REFRESH_RATE']
        logging.info(f'Waiting for incoming emails...')

        while True:
            emails = await self.fetch_new_emails()
            for message in emails:
                logging.info(f"new email: {message['Subject']}")
                await receiver(message)

            idle_task = await self.imap_client.idle_start(timeout=timeout)
            self.imap_client.idle_done()
            await asyncio.wait_for(idle_task, timeout=15)


email_client: EmailClient = EmailClient()
