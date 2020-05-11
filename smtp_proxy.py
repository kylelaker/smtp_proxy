#!/usr/bin/env python3

import asyncio
import os
import smtplib

import aiosmtpd
import click
import ruamel.yaml as yaml

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message


class ConfigurationError(Exception):
    pass


def parse_config(path):
    try:
        config = yaml.safe_load(path)
    except yaml.YAMLError as err:
        raise ConfigurationError(str(err))

    if not config:
        raise ConfigurationError("configuration is empty")

    if 'server' not in config:
        raise ConfigurationError("'server' is missing from config")
    if 'listen' not in config['server']:
        raise ConfigurationError("'server.listen' is missing from config")
    for section in ('addr', 'port'):
        if section not in config['server']['listen']:
            raise ConfigurationError(f"'server.listen.{section}' is missing from config")
    if 'proxy' not in config:
        raise ConfigurationError("'proxy' is missing from config")
    for section in ('hostname', 'port', 'username', 'password', 'tls'):
        if section not in config['proxy']:
            raise ConfigurationError(f"'proxy.{section}' is missing from config")
    if config['proxy']['tls'] not in (True, False, 'STARTTLS'):
        raise ConfigurationError("'proxy.tls' must be one of [True, False, 'STARTTLS']")
    return config


class MessageProxy(Message):
    def __init__(self, proxy_config, message_class=None):
        super().__init__(message_class)
        self.proxy_config = proxy_config

    def _initialize_client(self, hostname, port, username, password, tls, **kwargs):
        if tls is True:
            smtp_init = smtplib.SMTP_SSL
        else:
            smtp_init = smtplib.SMTP
        client = smtp_init(hostname, port)
        if tls.lower() == 'starttls':
            client.starttls()
        client.login(username, password)
        return client

    def handle_message(self, message):
        client = self._initialize_client(**self.proxy_config)
        client.send_message(message)
        client.quit()


@click.command('smtp-proxy')
@click.option(
    '--config-file',
    '-f',
    type=click.File(),
    help="The path to the configuration file",
    required=True,
)
def main(config_file):

    try:
        config = parse_config(config_file)
    except ConfigurationError as e:
        print(e)
        return

    server = config['server']
    proxy = config['proxy']
    controller = Controller(
        MessageProxy(proxy),
        hostname=server['listen']['addr'],
        port=server['listen']['port'],
    )
    controller.start()
    input("Press enter to stop the server")
    controller.stop()

if __name__ == '__main__':
    main()
