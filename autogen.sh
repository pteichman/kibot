#!/bin/sh

aclocal
automake --add-missing
autoconf
sh ./configure "$@"
