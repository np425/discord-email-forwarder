import base64
import email.message
import io
from collections import namedtuple

Message = namedtuple('Message', 'text_content files')


class EmailFormatter:
    @staticmethod
    def _collect_message_content(message: email.message.Message):
        files = []
        text_content = ""

        if message.is_multipart():
            for part in message.get_payload():
                content = EmailFormatter._collect_message_content(part)

                text_content += content[0] + '\n'
                files.extend(content[1])
        else:
            content = message.get_payload()
            content_type = message.get_content_type()

            if content_type == 'image/png':
                files.append((content, message['Content-Id'], content_type))
            else:
                text_content += content + '\n'

        return text_content, files

    @staticmethod
    def format_message(message: email.message.Message):
        content = f"""New email!
        From: {message['From']}
        To: {message['To']}
        Subject: {message['Subject']}
        Date: {message['Date']}

        Content:
        ---"""

        html, files = EmailFormatter._collect_message_content(message)
        ready_files = []

        for data, content_id, content_type in files:
            if content_type == 'image/png':
                img_id = content_id[1:-1]

                file = io.BytesIO(base64.b64decode(data))
                file.name = f'{img_id}.png'

                ready_files.append(file)

                # replace email local image references with actual images
                html = html.replace(f'cid:{img_id}', f'data:image/png;base64,{data}')

        content += html
        return Message(content, ready_files)
