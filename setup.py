#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name = "kibot",
    version = "0.0.13",
    author = "Peter Teichman",
    author_email = "peter@teichman.org",
    url = "http://wiki.github.com/pteichman/kibot/",
    description = "A simple IRC bot extensible with plugins.",
    packages = find_packages(),
    namespace_packages = ["kibot", "kibot.modules"],
    classifiers = [
    ],
    entry_points = {
        "console_scripts" : [
            "kibot = kibot.scripts:kibot",
            "kibot-control = kibot.scripts:kibot_control"
        ],
        "kibot.modules" : [
            "acro = kibot.modules.acro",
            "auth = kibot.modules.auth",
            "base = kibot.modules.base",
            "bugzilla = kibot.modules.bugzilla",
            "debug = kibot.modules.debug",
            "irc = kibot.modules.irc",
            "log = kibot.modules.log",
            "messaging = kibot.modules.messaging",
            "rand = kibot.modules.rand",
            "slashdot = kibot.modules.slashdot",
            "test = kibot.modules.test",
            "units = kibot.modules.units",
            "whereis = kibot.modules.whereis"
        ]
    }
)
