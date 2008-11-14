Summary: Python-based IRC Bot
Name: kibot
Version: 0.0.12
Release: 1
Packager: Michael Stenner <mstenner@phy.duke.edu>
License: GPL
Group: Messaging and Web Tools
Source: %{name}-%{version}.tar.gz
URL: http://linux.duke.edu/projects/kibot/
BuildRoot: %{_tmppath}/%{name}-%{version}root
BuildArchitectures: noarch
BuildRequires: python2 >= 2.2
Requires: python2
#Prereq:

%description
Kibot is a python-based IRC bot written to be cleanly and robustly
modular, powerful and flexible. It has a rich permissions framework,
and writing modules/commands for it is ridiculously simple.

%prep
%setup -q

%build
%configure --with-python=/usr/bin/python2
make


%install
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT
make DESTDIR=$RPM_BUILD_ROOT install
/usr/bin/install -D tools/kibot.init \
                    %{buildroot}%{_sysconfdir}/rc.d/init.d/kibot

%clean
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT

%post

%preun

%files 
%defattr(-, root, root)
%doc README AUTHORS COPYING TODO INSTALL ReleaseNotes ChangeLog
%doc -P tools/ircdb-dump.py tools/make_module_docs.py tools/ircdb-convert.py
%doc doc/kibot doc/Magic3PiBall
%doc doc/help.css doc/module-tutorial.html doc/perms
%doc doc/modulehelp.css doc/modulehelp.html
%doc doc/simple.conf doc/defaults.conf
%{_libdir}/python2.2/site-packages/kibot
%{_bindir}/kibot
%{_bindir}/kibot-control
%{_datadir}/kibot/modules
%{_datadir}/kibot/pymod
%{_mandir}/man*/*
%config %attr(0755,root,root)%{_sysconfdir}/rc.d/init.d/kibot

%changelog
* Tue Apr 29 2003 Michael Stenner <mstenner@phy.duke.edu>
- fixed init script install command

* Thu Apr 17 2003 Michael Stenner <mstenner@phy.duke.edu>
- fixed incorrect url, added sample conf files

* Mon Apr 14 2003 Michael Stenner <mstenner@phy.duke.edu> - 0.0.7-1
- changed mbot->kibot

* Fri Apr 11 2003 Michael Stenner <mstenner@phy.duke.edu> - 0.0.7-1
- added mbot.init

* Tue Apr  8 2003 Michael Stenner <mstenner@phy.duke.edu> - 0.0.7-1
- added man pages

* Sun Mar  2 2003 Michael Stenner <mstenner@phy.duke.edu>
- Added some new doc files

* Sat Feb 22 2003 Michael Stenner <mstenner@phy.duke.edu>
- Added Packager, updated URL, some new files

* Sun Feb 16 2003 Michael Stenner <mstenner@phy.duke.edu>
- First packaging


