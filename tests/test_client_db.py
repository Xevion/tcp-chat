from server.db import ClientDatabase


def test_last_connection_is_none_when_empty():
    db = ClientDatabase(':memory:')
    assert db.last_connection() is None


def test_remember_connection_stores_and_returns_latest():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.2.3.4', 5555, 'alice', 'secret')
    assert db.last_connection() == {
        'address': '1.2.3.4', 'port': 5555, 'nickname': 'alice', 'password': 'secret',
        'favorite': False,
    }

    db.remember_connection('5.6.7.8', 5555, 'bob')
    assert db.last_connection()['nickname'] == 'bob'


def test_recent_connections_orders_newest_first_and_limits():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.1.1.1', 5555, 'alice')
    db.remember_connection('2.2.2.2', 5555, 'bob')
    db.remember_connection('3.3.3.3', 5555, 'carol')

    recents = db.recent_connections(limit=2)
    assert [c['nickname'] for c in recents] == ['carol', 'bob']


def test_set_favorite_flags_and_lists_favorites():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.1.1.1', 5555, 'alice')
    db.remember_connection('2.2.2.2', 5555, 'bob')
    assert db.favorite_connections() == []

    db.set_favorite('2.2.2.2', 5555, 'bob')
    favorites = db.favorite_connections()
    assert [c['nickname'] for c in favorites] == ['bob']
    assert favorites[0]['favorite'] is True

    db.set_favorite('2.2.2.2', 5555, 'bob', favorite=False)
    assert db.favorite_connections() == []


def test_remember_connection_bumps_existing_use_count():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.2.3.4', 5555, 'alice')
    db.remember_connection('1.2.3.4', 5555, 'alice')
    cur = db.conn.cursor()
    cur.execute('SELECT connections FROM connection WHERE nickname = ?', ['alice'])
    assert cur.fetchone()[0] == 2
    cur.close()
