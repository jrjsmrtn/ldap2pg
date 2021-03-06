from __future__ import unicode_literals

from io import StringIO

import pytest


RC_SAMPLE = """
# Comment
URI   ldap://host ldaps://host

base  ou=IT staff,o="Example, Inc",c=US
"""


def test_str2dn():
    from ldap2pg.ldap import str2dn

    value = str2dn('cn=toto,dc=with space,dc=pouet')
    assert 3 == len(value)

    with pytest.raises(ValueError):
        str2dn('not a dn')


def test_connect_from_env(mocker):
    go = mocker.patch('ldap2pg.ldap.gather_options', autospec=True)
    li = mocker.patch('ldap2pg.ldap.ldap.initialize', autospec=True)

    from ldap2pg.ldap import connect

    go.return_value = dict(
        URI='ldap://host:389',
        BINDDN='dc=local',
        PASSWORD='filepass',
    )

    connexion = connect(password='argpass')

    assert connexion
    assert go.called is True
    assert li.called is True


def test_connect_sasl(mocker):
    go = mocker.patch('ldap2pg.ldap.gather_options', autospec=True)
    li = mocker.patch('ldap2pg.ldap.ldap.initialize', autospec=True)

    from ldap2pg.ldap import connect

    go.return_value = dict(URI='ldaps://host', USER='toto', PASSWORD='pw')

    connect()

    ldap = li.return_value
    assert ldap.sasl_interactive_bind_s.called is True


def test_options_dict():
    from ldap2pg.ldap import Options

    options = Options(PASSWORD='initpass')

    assert 'initpass' == options['PASSWORD']

    assert options.set_raw('PASSWORD', 'setpass')
    assert options.set_raw('URI', 'ldap://host:636')
    assert options.set_raw('BINDDN', 'cn=admin')
    assert not options.set_raw('UNKNOWN OPTION', 'raw')


def test_gather_options_noinit(mocker):
    from ldap2pg.ldap import gather_options

    options = gather_options(
        password='password',
        environ=dict(LDAPNOINIT=b'', LDAPBASEDN=b'dc=base'),
    )
    assert 'BASE' not in options


def test_gather_options(mocker):
    rf = mocker.patch('ldap2pg.ldap.read_files', autospec=True)

    from ldap2pg.ldap import gather_options, RCEntry

    rf.side_effect = [
        [RCEntry(filename='a', lineno=1, option='URI', value='ldap:///')],
        [RCEntry(filename='b', lineno=1, option='BINDDN', value='cn=binddn')],
    ]

    options = gather_options(
        password=None,
        environ=dict(LDAPBASE=b'dc=local', LDAPPASSWORD=b'envpass'),
    )

    assert 'envpass' == options['PASSWORD']
    assert 'ldap:///' == options['URI']
    assert 'cn=binddn' == options['BINDDN']


def test_read_files(mocker):
    o = mocker.patch('ldap2pg.ldap.open', create=True)
    p = mocker.patch('ldap2pg.ldap.parserc', autospec=True)

    from ldap2pg.ldap import read_files

    o.side_effect = [
        OSError(),
        OSError(),
        mocker.MagicMock(name='open'),
        OSError(),
    ]
    p.return_value = [None]

    items = list(read_files(conf='/etc/ldap/ldap.conf', rc='ldaprc'))

    assert p.called is True
    assert 1 == len(items)


def test_parse_rc():
    from ldap2pg.ldap import parserc

    fo = StringIO(RC_SAMPLE)
    items = list(parserc(fo))

    assert 2 == len(items)

    assert 'URI' == items[0].option
    assert 'ldap://host ldaps://host' == items[0].value
    assert '<stdin>' == items[0].filename
    assert 3 == items[0].lineno


def test_lower_attrs():
    from ldap2pg.manager import lower_attributes

    entry = lower_attributes(('dn', {'sAMAccountName': 'alice'}))

    assert 'samaccountname' in entry[1]


def test_expand_attributes():
    from ldap2pg.ldap import expand_attributes

    entry = ('dn', {
        'cn': ['cn=pouet,ou=POU ET,dc=org'], 'uid': ['toto', 'titi']
    })

    names = list(expand_attributes(entry, ['static', '{uid}', '{cn.dc}']))
    assert 'toto' in names
    assert 'static' in names
    assert 'titi' in names
    assert 'org' in names


def test_get_attribute():
    from ldap2pg.ldap import get_attribute

    with pytest.raises(ValueError):
        list(get_attribute(entry=('dn', {}), attribute='pouet'))

    with pytest.raises(ValueError):
        list(get_attribute(
            entry=('dn', {'cn': ['cn=pouet']}),
            attribute='cn.pouet',
        ))

    with pytest.raises(ValueError):
        list(get_attribute(
            entry=('dn', {'cn': 'not a dn'}),
            attribute='cn.pouet',
        ))


def test_logger(mocker):
    from ldap2pg.ldap import LDAPLogger
    from ldap import SCOPE_SUBTREE

    ldap = LDAPLogger(mocker.Mock(name='toto', pouet='toto'))

    assert 'toto' == ldap.pouet

    ldap.search_s('base', scope=SCOPE_SUBTREE, filter='', attributes='cn')
