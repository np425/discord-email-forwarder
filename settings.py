import os

from dotenv import load_dotenv
import logging


def load_setting(name: str):
    value = os.environ.get(name, None)
    return value


def load_settings(required_settings):
    if not load_dotenv():
        logging.warning("No .env file found, resorting to environment variables")

    for setting, setting_type in required_settings.items():
        settings[setting] = setting_type(load_setting(setting))


settings = {}
