from multiprocessing import Process, Queue

from PySide6.QtCore import QSize, QUrl

from common import common, widget_base, net_tools
from third_party.pyxtermjs import app
from widgets import widget_shortcut


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)
        self.setObjectName('widget_terminal')
        self.is_auto_start = True

        self.terminal_port = 5000

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='generate terminal widget',
                                                 shortcut_key=['Ctrl', 'T'],
                                                 callback=self.generate_terminal_widget)
        self.widget_shortcut.add_shortcut(self.shortcut)

        self.reset()

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def generate_terminal_widget(self) -> None:
        obj: widget_base.Object = self.frame.widget_object_manager.generate_object()

        tab = obj.add_object(widget_base.Tab(obj, obj.global_pos, QSize(800, 550)))

        self.new_terminal(tab)

    @staticmethod
    def io_read_callback(data):
        pass
        # print('callback', data)

    def new_terminal(self, tab: widget_base.Tab) -> widget_base.Page:
        while True:
            if net_tools.is_port_in_use(port=self.terminal_port):
                self.terminal_port += 1
            else:
                break

        terminal = widget_base.Page(
            title=str(self.terminal_port),
            frontend=self.frame.generate_webview()
        )
        terminal.io = {
            'io_write': Queue(),
            'io_read': self.io_read_callback
        }
        terminal.backend = Process(target=app.start, args=(self.terminal_port, terminal.io,))
        terminal.port = self.terminal_port
        terminal.backend.start()

        terminal.frontend.load(QUrl('http://127.0.0.1:{0}/'.format(self.terminal_port)))
        self.terminal_port += 1

        terminal.func_list = self.generate_func_list(tab, terminal)

        def deleteLater():  # noqa
            terminal.frontend.deleteLater()
            terminal.backend.kill()

        terminal.deleteLater = deleteLater

        tab.add_page(page=terminal)
        tab.on_page_change(0)

        return terminal

    def generate_func_list(self, tab: widget_base.Tab, terminal):
        args_parser = (lambda args: ''.join([arg.parse() for arg in args]))

        return [
            widget_base.Func(name='base', children=[
                widget_base.Func(name='gain_focus', dclick_func=lambda x: None, args_parser=args_parser),
                widget_base.Func(name='new_term', dclick_func=lambda x: self.new_terminal(tab), args_parser=args_parser)
            ]),
            widget_base.Func(name='file', children=[
                widget_base.Func(name='pwd', dclick_func=lambda x: terminal.io['io_write'].put('pwd'), args_parser=args_parser),
                widget_base.Func(
                    name='du', dclick_func=lambda x: terminal.io['io_write'].put('du' + x),
                    args=[
                        widget_base.FuncArg('-h', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-d', '0', True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<path>', '*', True, False, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                )
            ]),
            widget_base.Func(name='network', children=[
                widget_base.Func(
                    name='netstat', dclick_func=lambda x: terminal.io['io_write'].put('sudo netstat' + x),
                    args=[
                        widget_base.FuncArg('-l', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-n', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-p', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-t', None, False, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-u', None, False, True, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='ifconfig', dclick_func=lambda x: terminal.io['io_write'].put('ifconfig' + x),
                    args=[
                        widget_base.FuncArg('-a', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<interface>', '', False, False, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='tcpdump', dclick_func=lambda x: terminal.io['io_write'].put('sudo tcpdump' + x),
                    args=[
                        widget_base.FuncArg('-n', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-i', '', False, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('port', '', False, True, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                )
            ]),
            widget_base.Func(name='git', children=[
                widget_base.Func(name='status', dclick_func=lambda x: terminal.io['io_write'].put('git status'), args_parser=args_parser),
                widget_base.Func(
                    name='log', dclick_func=lambda x: terminal.io['io_write'].put('git log' + x),
                    args=[
                        widget_base.FuncArg('<adog>', '--all --decorate --oneline --graph', True, False,
                                            parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-n', '', False, True, comment='number of log', parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='add', dclick_func=lambda x: terminal.io['io_write'].put('git add' + x),
                    args=[
                        widget_base.FuncArg('.', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<path>', '', False, False, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='commit', dclick_func=lambda x: terminal.io['io_write'].put('git commit' + x),
                    args=[
                        widget_base.FuncArg('-m', '', True, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('--amend', '--no-edit', False, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<path>', '', False, False, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(name='branch', children=[
                    widget_base.Func(
                        name='list branch', dclick_func=lambda x: terminal.io['io_write'].put('git branch' + x),
                        args=[
                            widget_base.FuncArg('-v', None, True, True, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('-a', None, False, True, parse_type=widget_base.FuncArgParseType.dclick)
                        ],
                        args_parser=args_parser
                    ),
                    widget_base.Func(
                        name='push branch', dclick_func=lambda x: terminal.io['io_write'].put('git push' + x),
                        args=[
                            widget_base.FuncArg('-f', None, False, True, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('<remote repo>', 'origin', True, False, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('<local_b:remote_b>', 'master:master', False, False,
                                                parse_type=widget_base.FuncArgParseType.dclick)
                        ],
                        args_parser=args_parser
                    ),
                    widget_base.Func(
                        name='pull branch', dclick_func=lambda x: terminal.io['io_write'].put('git pull' + x),
                        args=[
                            widget_base.FuncArg('-f', None, False, True, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('<remote repo>', 'origin', True, False, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('<remote_b:local_b>', 'master:master', False, False,
                                                parse_type=widget_base.FuncArgParseType.dclick)
                        ],
                        args_parser=args_parser
                    )
                ]),
                widget_base.Func(
                    name='fetch', dclick_func=lambda x: terminal.io['io_write'].put('git fetch' + x),
                    args=[
                        widget_base.FuncArg('-all', None, True, True, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='reset', dclick_func=lambda x: terminal.io['io_write'].put('git reset' + x),
                    args=[
                        widget_base.FuncArg('--soft', None, False, True,
                                            comment='Keep diff in Workspace',
                                            parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('--mixed', None, True, True,
                                            comment='Make Workspace identical to Local Repo and keep diff in Staged Files',
                                            parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('--hard', None, False, True,
                                            comment='Make Workspace identical to Local Repo and clean Staged Files',
                                            parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<branch/commit>', '', False, False, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<path>', '', False, False, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='checkout', dclick_func=lambda x: terminal.io['io_write'].put('git checkout' + x),
                    args=[
                        widget_base.FuncArg('-f', None, False, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('-m', None, False, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('--', None, False, True, parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<branch/commit>', '', True, False, parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='diff', dclick_func=lambda x: terminal.io['io_write'].put('git diff' + x),
                    args=[
                        widget_base.FuncArg('head', None, False, True, comment='Workspace VS Local Repo',
                                            parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('--cached', None, False, True, comment='Staged Files VS Local Repo',
                                            parse_type=widget_base.FuncArgParseType.dclick),
                        widget_base.FuncArg('<path>', '', True, False, comment='(Default)Workspace VS Staged Files',
                                            parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                widget_base.Func(
                    name='merge', dclick_func=lambda x: terminal.io['io_write'].put('git merge' + x),
                    args=[
                        widget_base.FuncArg('<branch>', '', True, False, comment='merge specified branch to current branch',
                                            parse_type=widget_base.FuncArgParseType.dclick)
                    ],
                    args_parser=args_parser
                ),
                # 'rebase': None,
                widget_base.Func(name='tag', children=[
                    widget_base.Func(name='list local tags',
                                     dclick_func=lambda x: terminal.io['io_write'].put('git tag'),
                                     args_parser=args_parser),
                    widget_base.Func(
                        name='push tag', dclick_func=lambda x: terminal.io['io_write'].put('git push' + x),
                        args=[
                            widget_base.FuncArg('<remote repo>', 'origin', True, False, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('<tag>', '', True, False, parse_type=widget_base.FuncArgParseType.dclick)
                        ],
                        args_parser=args_parser
                    ),
                    widget_base.Func(
                        name='push all tags', dclick_func=lambda x: terminal.io['io_write'].put('git push' + x),
                        args=[
                            widget_base.FuncArg('<remote repo>', 'origin', True, False, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('--tags', None, True, False, parse_type=widget_base.FuncArgParseType.dclick)
                        ],
                        args_parser=args_parser
                    ),
                    widget_base.Func(
                        name='delete tag', dclick_func=lambda x: terminal.io['io_write'].put('git push' + x),
                        args=[
                            widget_base.FuncArg('<remote repo>', 'origin', True, False, parse_type=widget_base.FuncArgParseType.dclick),
                            widget_base.FuncArg('<tag>', '', True, False, parse_value=(lambda x: ' :{0}'.format(x)),
                                                parse_type=widget_base.FuncArgParseType.dclick)
                        ],
                        args_parser=args_parser
                    )
                ])
            ])
        ]
