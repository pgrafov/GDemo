import os


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'test_data_2017_02_24.db')
CERTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
SALT = '__salt__'
DEFAULT_SESSION_DURATION = 1
MAX_SESSION_DURATION = 24
MAX_SQLITE_INTEGER = 0x7FFFFFFFFFFFFFFF
