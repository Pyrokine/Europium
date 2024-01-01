import argparse
import os
import platform
import shlex
import struct
import subprocess
from multiprocessing import Queue

import select
from flask import Flask, render_template
from flask_socketio import SocketIO

system_version = platform.system()

if system_version in ['Windows']:
    import winpty
elif system_version in ['Linux', 'Darwin']:
    import pty
    import termios
    import fcntl

__version__ = '0.5.0.2'

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = 'secret!'
app.config['fd'] = None
app.config['child_pid'] = None
socketio = SocketIO(app)

io_read = lambda x: None


def set_win_size(row, col, x_pix=0, y_pix=0):
    if system_version in ['Windows']:
        app.config['fd'].setwinsize(row, col)
    elif system_version in ['Linux', 'Darwin']:
        win_size = struct.pack('HHHH', row, col, x_pix, y_pix)
        fcntl.ioctl(app.config['fd'], termios.TIOCSWINSZ, win_size)


def read_and_forward_pty_output():
    # read from pty and write to terminal
    max_read_bytes = 1024 * 20

    if system_version in ['Windows']:
        while True:
            socketio.sleep(0.01)
            if app.config['fd']:
                buffer = app.config['fd'].read()

                if not buffer or len(buffer) == 0:
                    continue

                io_read(buffer)
                socketio.emit('pty-output', {'output': buffer}, namespace='/pty')
    elif system_version in ['Linux', 'Darwin']:
        while True:
            socketio.sleep(0.01)
            if app.config['fd']:
                timeout_sec = 0
                data_ready, _, _ = select.select([app.config['fd']], [], [], timeout_sec)

                if data_ready:
                    buffer = os.read(app.config['fd'], max_read_bytes).decode(errors='ignore')
                    io_read(buffer)
                    socketio.emit('pty-output', {'output': buffer}, namespace='/pty')


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('pty-input', namespace='/pty')
def pty_input(data):
    # read from terminal and write to pty
    if app.config['fd']:
        if system_version in ['Windows']:
            app.config['fd'].write(data['input'])
        elif system_version in ['Linux', 'Darwin']:
            os.write(app.config['fd'], data['input'].encode())


def io_write(q):
    while True:
        data = q.get()
        if system_version in ['Windows']:
            data += '\n\r'
        elif system_version in ['Linux', 'Darwin']:
            data += '\n'

        # print('io_write', data)
        pty_input({'input': data})


@socketio.on('resize', namespace='/pty')
def resize(data):
    if app.config['fd']:
        set_win_size(data['rows'], data['cols'])


@socketio.on('connect', namespace='/pty')
def connect():
    if app.config['child_pid']:
        return

    if system_version in ['Windows']:
        app.config['fd'] = winpty.PtyProcess.spawn('cmd', backend=1)
        app.config['child_pid'] = app.config['fd'].pid
        set_win_size(50, 50)

    elif system_version in ['Linux', 'Darwin']:
        child_pid, fd = pty.fork()
        if child_pid == 0:
            # this is the child process fork.
            # anything printed here will show up in the pty, including the output of this subprocess
            subprocess.run(app.config['cmd'])
        else:
            # this is the parent process fork.
            # store child fd and pid
            app.config['fd'] = fd
            app.config['child_pid'] = child_pid
            set_win_size(50, 50)
            # logging/print statements must go after this because... I have no idea why
            # but if they come before the background, task will never start
    else:
        return

    socketio.start_background_task(target=read_and_forward_pty_output)

    if system_version in ['Linux', 'Darwin']:
        pty_input({'input': 'export TERM=xterm && clear\n'})


def start(port, io, host='127.0.0.1'):
    global io_read
    io_read = io['io_read']

    parser = argparse.ArgumentParser(
        description=(
            'A fully functional terminal in your browser. '
            'https://github.com/cs01/pyxterm.js'
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-p', '--port', default=port, help='port to run server on', type=int)
    parser.add_argument('--host', default=host, help='host to run server on (use 0.0.0.0 to allow access from other hosts)')
    parser.add_argument('--debug', action='store_true', help='debug the server')
    parser.add_argument('--version', action='store_true', help='print version and exit')
    parser.add_argument('--command', default='bash', help='Command to run in the terminal')
    parser.add_argument('--cmd-args', default='', help='arguments to pass to command (i.e. --cmd-args="arg1 arg2 --flag")')
    args = parser.parse_args()
    if args.version:
        print(__version__)
        exit(0)
    app.config['cmd'] = [args.command] + shlex.split(args.cmd_args)

    socketio.start_background_task(io_write, io['io_write'])
    socketio.run(app, port=port, host=host, use_reloader=False, log_output=False, allow_unsafe_werkzeug=True)
