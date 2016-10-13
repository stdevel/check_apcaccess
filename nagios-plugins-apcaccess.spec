Name:           nagios-plugins-apcaccess
Version:        0.5.0
Release:        1%{?dist}
Summary:        A Nagios / Icinga plugin for checking APC UPS devices using apcupsd

Group:          Applications/System
License:        GPL
URL:            https://github.com/stdevel/check_apcaccess
Source0:        nagios-plugins-apcaccess-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

#BuildRequires:
Requires:       apcupsd

%description
This package contains a Nagios / Icinga plugin for checking APC UPS devices using the apcupsd daemon.

Check out the GitHub page for further information: https://github.com/stdevel/check_apcaccess

%prep
%setup -q

%build
#change /usr/lib64 to /usr/lib if we're on i686
%ifarch i686
sed -i -e "s/usr\/lib64/usr\/lib/" check_apcaccess.cfg
%endif

%install
install -m 0755 -d %{buildroot}%{_libdir}/nagios/plugins/
install -m 0755 check_apcaccess.py %{buildroot}%{_libdir}/nagios/plugins/check_apcaccess
%if 0%{?el7}
        install -m 0755 -d %{buildroot}%{_sysconfdir}/nrpe.d/
        install -m 0755 check_apcaccess.cfg  %{buildroot}%{_sysconfdir}/nrpe.d/check_apcaccess.cfg
%else
        install -m 0755 -d %{buildroot}%{_sysconfdir}/nagios/plugins.d/
        install -m 0755 check_apcaccess.cfg  %{buildroot}%{_sysconfdir}/nagios/plugins.d/check_apcaccess.cfg
%endif



%clean
rm -rf $RPM_BUILD_ROOT

%files
%if 0%{?el7}
        %config %{_sysconfdir}/nrpe.d/check_apcaccess.cfg
%else
        %config %{_sysconfdir}/nagios/plugins.d/check_apcaccess.cfg
%endif
%{_libdir}/nagios/plugins/check_apcaccess


%changelog
* Thu Oct 13 2016 Christian Stankowic <info@stankowic-development.net> - 0.5.0-1
- Initial release
