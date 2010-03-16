#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name = "kibot",
    version = "0.0.12",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "http://wiki.github.com/pteichman/kibot/",
    description = "A simple IRC bot extensible with plugins.",
    packages = ["kibot"],
    classifiers = [
    ],
    entry_points = {
        "console_scripts" : [
            "kibot = kibot.cmd_kibot:main",
            "kibot-control = kibot.cmd_control:main"
        ],
        "kibot.modules" : [
            "module = kibot.modules.auth:auth",
            "module = kibot.modules.base:base",
            "module = kibot.modules.irc:irc"
        ]
    }
)
