# set EXTRA_DIST and CLEANFILES so we can use += below
EXTRA_DIST =
CLEANFILES =

dist_bin_SCRIPTS = \
	bin/kibot \
	bin/kibot-control

EXTRA_DIST += bin/kibot_devel.py

nodist_pkgpython_PYTHON = \
	kibot/Options.py

pkgpython_PYTHON = \
	kibot/BaseModule.py \
	kibot/Bot.py \
	kibot/CommandHandler.py \
	kibot/Flood.py \
	kibot/ModuleManager.py \
	kibot/OptionParser.py \
	kibot/PermObjects.py \
	kibot/Settings.py \
	kibot/Stasher.py \
	kibot/__init__.py \
	kibot/daemon.py \
	kibot/ircDB.py \
	kibot/irclib.py \
	kibot/logger.py \
	kibot/m_irclib.py \
	kibot/permDB.py \
	kibot/timeoutsocket.py

modulesdir = $(pkgdatadir)/modules

modules_PYTHON = \
	modules/acro.py \
	modules/auth.py \
	modules/base.py \
	modules/bugzilla.py \
	modules/debug.py \
	modules/google.py \
	modules/irc.py \
	modules/log.py \
	modules/magic.py \
	modules/messaging.py \
	modules/rand.py \
	modules/slashdot.py \
	modules/test.py \
	modules/units.py \
	modules/whereis.py

pymoddir = $(pkgdatadir)/pymod

pymod_PYTHON = \
	pymod/AccessTree.py \
	pymod/GibberSpeak.py \
	pymod/SOAP.py \
	pymod/TextFilter.py \
	pymod/gibberbase.py \
	pymod/magicdata.py \
	pymod/pygoogle.py \
	pymod/shellfilters.py

dist_man1_MANS = \
	doc/kibot.1 \
	doc/kibot-control.1

EXTRA_DIST += \
	doc/Magic3PiBall/MagicTree.txt \
	doc/Magic3PiBall/README.shellfilters \
	doc/Magic3PiBall/formats.txt \
	doc/defaults.conf \
	doc/help.css \
	doc/module-tutorial.html \
	doc/modulehelp.css \
	doc/perms \
	doc/simple.conf \
	tools/ircdb-convert.py \
	tools/ircdb-dump.py \
	tools/kibot.init \
	tools/make_module_docs.py \
	tools/stash_convert.py
