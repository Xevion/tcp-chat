from server.db import ClientDatabase


def test_last_connection_is_none_when_empty():
    db = ClientDatabase(':memory:')
    assert db.last_connection() is None


def test_remember_connection_stores_and_returns_latest():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.2.3.4', 5555, 'alice', 'secret')
    assert db.last_connection() == {
        'address': '1.2.3.4', 'port': 5555, 'nickname': 'alice', 'password': 'secret',
    }

    db.remember_connection('5.6.7.8', 5555, 'bob')
    assert db.last_connection()['nickname'] == 'bob'


def test_remember_connection_bumps_existing_use_count():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.2.3.4', 5555, 'alice')
    db.remember_connection('1.2.3.4', 5555, 'alice')
    cur = db.conn.cursor()
    cur.execute('SELECT connections FROM connection WHERE nickname = ?', ['alice'])
    assert cur.fetchone()[0] == 2
    cur.close()
