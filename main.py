import datetime
import hashlib
import sqlite3
import uuid
import ssl
import os
from flask import Flask, jsonify, request
from attrdict import AttrDefault

from settings import DB_PATH, CERTS_PATH, SALT, DEFAULT_SESSION_DURATION, MAX_SESSION_DURATION, MAX_SQLITE_INTEGER


class ClientError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


app = Flask(__name__)
app.connection = sqlite3.connect(DB_PATH)
app.connection.row_factory = sqlite3.Row
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
context.load_cert_chain(os.path.join(CERTS_PATH, 'demo.crt'), os.path.join(CERTS_PATH, 'demo.key'))


def get_user_id(cursor, session_id):
    sql = "SELECT user_id from sessions WHERE sid = ? AND expires > ?"
    res = cursor.execute(sql, (session_id, datetime.datetime.now())).fetchone()
    if not res:
        raise ClientError('Unauthorized', status_code=401)
    return res['user_id']


def validate_and_convert_user_input(user_args, parameters):
    errors = []
    converted_args = {}
    for parameter_name, required in parameters.iteritems():
        value = user_args.get(parameter_name)
        if (value is None or value == '') and required:
            errors.append("Parameter '%s' is missing" % parameter_name)
        else:
            if parameter_name == 'resolution':
                if value not in ['D', 'M']:
                    errors.append("Parameter '%s' accepts only values D or M" % parameter_name)
                else:
                    converted_args[parameter_name] = value
            elif (parameter_name == 'count' or parameter_name == 'duration') and value:
                try:
                    converted_args[parameter_name] = int(value)
                    assert converted_args[parameter_name] >= 0
                except (ValueError, AssertionError):
                    errors.append("Parameter '%s' must be positive integer" % parameter_name)
            elif parameter_name == 'start':
                try:
                    converted_args[parameter_name] = datetime.datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    errors.append("Parameter '%s' must match format 'YYYY-mm-dd'" % parameter_name)
            else:
                converted_args[parameter_name] = value
    if errors:
        raise ClientError('Invalid query', payload={'errors': errors})
    return converted_args


def fill_limits(month_data, day_data):
    limits = AttrDefault(dict)
    limits.months.timestamp.maximum = max(month_data, key=lambda x: x['timestamp'])['timestamp'].split()[0]
    limits.months.timestamp.minimum = min(month_data, key=lambda x: x['timestamp'])['timestamp'].split()[0]
    limits.months.consumption.maximum = max(month_data, key=lambda x: x['consumption'])['consumption']
    limits.months.consumption.minimum = min(month_data, key=lambda x: x['consumption'])['consumption']
    limits.months.temperature.maximum = max(month_data, key=lambda x: x['temperature'])['temperature']
    limits.months.temperature.minimum = min(month_data, key=lambda x: x['temperature'])['temperature']

    limits.days.timestamp.maximum = max(day_data, key=lambda x: x['timestamp'])['timestamp'].split()[0]
    limits.days.timestamp.minimum = min(day_data, key=lambda x: x['timestamp'])['timestamp'].split()[0]
    limits.days.consumption.maximum = max(day_data, key=lambda x: x['consumption'])['consumption']
    limits.days.consumption.minimum = min(day_data, key=lambda x: x['consumption'])['consumption']
    limits.days.temperature.maximum = max(day_data, key=lambda x: x['temperature'])['temperature']
    limits.days.temperature.minimum = min(day_data, key=lambda x: x['temperature'])['temperature']
    return limits


@app.route('/login', methods=['POST'])
def login():
    cursor = app.connection.cursor()
    user_args = validate_and_convert_user_input(request.get_json(),
                                                {'login': True, 'password': True, 'duration': False})
    user_row = cursor.execute('SELECT * FROM users WHERE username=?', (user_args['login'],)).fetchone()
    if (user_row and not user_row['blocked'] and
            hashlib.sha256(SALT + user_args['password']).hexdigest() == user_row['password']):
        session_id = uuid.uuid4().hex
        session_duration = user_args.get('duration', DEFAULT_SESSION_DURATION)
        if session_duration > MAX_SESSION_DURATION:
            session_duration = MAX_SESSION_DURATION
        expires = datetime.datetime.now() + datetime.timedelta(hours=session_duration)
        p = (session_id, user_row['id'], expires)
        cursor.execute("INSERT INTO sessions VALUES (?, ?, ?)", p)
        app.connection.commit()
        return jsonify({'session_id': session_id, 'expires': expires.strftime('%Y-%m-%d %H:%M:%S')})
    else:
        raise ClientError('Unauthorized', status_code=401)


@app.route('/logout', methods=['POST'])
def logout():
    cursor = app.connection.cursor()
    user_args = validate_and_convert_user_input(request.get_json(), {'session_id': True})
    expires = datetime.datetime.now()
    cursor.execute("UPDATE sessions SET expires = ? WHERE sid = ?", (expires, user_args['session_id']))
    app.connection.commit()
    return jsonify({})


@app.route('/limits')
def limits():
    cursor = app.connection.cursor()
    user_args = validate_and_convert_user_input(request.args, {'session_id': True})
    user_id = get_user_id(cursor, user_args['session_id'])

    p = (user_id,)
    month_data = cursor.execute('SELECT * FROM months WHERE user_id=?', p).fetchall()
    day_data = cursor.execute('SELECT * FROM days WHERE user_id=?', p).fetchall()

    limits = fill_limits(month_data, day_data)

    return jsonify(
        {
            "limits": {
                "months": {
                    "timestamp": {
                        "minimum": limits.months.timestamp.minimum,
                        "maximum": limits.months.timestamp.maximum
                    },
                    "consumption": {
                        "minimum": limits.months.consumption.minimum,
                        "maximum": limits.months.consumption.maximum
                    },
                    "temperature": {
                        "minimum": limits.months.temperature.minimum,
                        "maximum": limits.months.temperature.maximum
                    }
                },
                "days": {
                    "timestamp": {
                        "minimum": limits.days.timestamp.minimum,
                        "maximum": limits.days.timestamp.maximum
                    },
                    "consumption": {
                        "minimum": limits.days.consumption.minimum,
                        "maximum": limits.days.consumption.maximum
                    },
                    "temperature": {
                        "minimum": limits.days.temperature.minimum,
                        "maximum": limits.days.temperature.maximum
                    }
                }
            }
        }
    )


@app.route('/data')
def data():
    cursor = app.connection.cursor()
    user_args = validate_and_convert_user_input(request.args, {'session_id': True, 'start': True,
                                                               'count': True, 'resolution': True})
    user_id = get_user_id(cursor, user_args['session_id'])
    count = user_args['count']
    if count > MAX_SQLITE_INTEGER:
        count = MAX_SQLITE_INTEGER
    p = (user_id, user_args['start'], count)
    tablename = 'months' if user_args['resolution'] == 'M' else 'days'
    sql = 'SELECT * FROM %s WHERE user_id=? AND timestamp>=? ORDER BY timestamp ASC LIMIT ? ' % tablename
    data = cursor.execute(sql, p).fetchall()
    return jsonify({"data": [[d['timestamp'].split()[0], d['consumption'], d['temperature']] for d in data]})


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    try:
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
    except:
        response = jsonify({"message": "Server error"})
        response.status_code = 500
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, ssl_context=context)
