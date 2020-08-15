import os
from collections import deque
from stat import S_ISDIR
from typing import Dict, Optional

import paramiko
from PySide6.QtCore import QSize, QPoint

from common import common, widget_base
from config import Config
from widgets import widget_shortcut


class FileManagerSFTP:
    def __init__(self,
                 obj: widget_base.Object,
                 sftp: paramiko.sftp_client,
                 root_path: str,
                 file_attr: Optional[paramiko.sftp_attr.SFTPAttributes],
                 rel_pos: QPoint):
        self.obj = obj
        self.sftp = sftp

        self.line_height = Config.SSH.CSS().line_height

        self.process_list = deque()
        self.map_abs_path_node: Dict[str, widget_base.Func] = {}
        func_list = [self.generate_dir_tree(root_path, file_attr)]

        self.tab = obj.add_object(widget_base.Tab(self.obj, self.obj.global_pos + rel_pos, QSize(800, 550)))

        self.file_list = widget_base.Page(
            title='foo',
            frontend=widget_base.Table(obj=self.obj, pos=QPoint()),
            func_list=func_list
        )

        self.tab.add_page(page=self.file_list)
        self.tab.on_page_change(0)

    def generate_dir_tree(self, root_path: str, file_attr: paramiko.sftp_attr.SFTPAttributes) -> widget_base.Func:
        if file_attr:
            root_node = widget_base.Func(name=os.path.basename(file_attr.filename), args=[widget_base.FuncArg('abs_path', root_path)])
            root_node.click_func = lambda x: self.render_file_attr(root_node)

            self.process_list.append([root_node, root_path, file_attr])
            self.map_abs_path_node.update({root_path: root_node})
        else:
            root_node = widget_base.Func(name=root_path, args=[widget_base.FuncArg('abs_path', root_path)])
            root_node.click_func = lambda x: self.render_file_attr(root_node)

            self.map_abs_path_node.update({root_path: root_node})

            for child_file_attr in sorted(self.sftp.listdir_attr(root_path), key=lambda x: x.filename):
                file_path = common.join_path(root_path, child_file_attr.filename)
                child_node = widget_base.Func(name=child_file_attr.filename, args=[widget_base.FuncArg('abs_path', file_path)])
                child_node.click_func = lambda x: self.render_file_attr(child_node)

                root_node.children.append(child_node)
                child_node.parent = root_node

                self.process_list.append([child_node, file_path, child_file_attr])
                self.map_abs_path_node.update({file_path: child_node})

        while self.process_list:
            self.process(*self.process_list[0])
            self.process_list.popleft()

        return root_node

    def process(self, node: widget_base.Func, node_path: str, file_attr: paramiko.sftp_attr.SFTPAttributes) -> None:
        # TODO: maybe path will no longer exists during processing
        if self.is_dir(file_attr):
            node.is_leaf = False
            for child_file_attr in sorted(self.sftp.listdir_attr(node_path), key=lambda x: x.filename):
                filename, file_path = child_file_attr.filename, common.join_path(node_path, child_file_attr.filename)
                child_node = widget_base.Func(name=filename, args=[widget_base.FuncArg('abs_path', file_path)])
                child_node.click_func = lambda x: self.render_file_attr(child_node)

                node.children.append(child_node)
                child_node.parent = node

                self.process_list.append([child_node, file_path, child_file_attr])
                self.map_abs_path_node.update({file_path: child_node})
        else:
            node.is_leaf = True

    @staticmethod
    def is_dir(path):
        return True if S_ISDIR(path.st_mode) else False

    def render_file_attr(self, node: widget_base.Func):
        self.file_list.frontend.clear()
        table_header, table_data = [], []

        if node.parent:
            for func in node.parent.children:
                # TODO: improve data structure
                table_row = widget_base.TableRow()
                table_data.append(table_row)

                for arg in func.args:
                    # table_cell = widget_base.TableCell(arg.key, arg.value, widget_base.TableCellType.text_readonly)
                    table_cell = widget_base.TableCell(arg.key, arg.value, widget_base.TableCellType.PLAINTEXT_EDITABLE)
                    table_row.data.update({arg.key: table_cell})

            if node.parent.children:
                table_header = [arg.key for arg in node.parent.children[0].args]

        self.file_list.frontend.render_list(table_header, table_data)


class SSHProxy:
    def __init__(self, frame, obj):
        self.frame = frame
        self.obj = obj

        self.transport: Optional[paramiko.transport.Transport] = None
        self.file_manager = None
        self.sftp = None

        obj_pos = obj.global_pos
        height = 30

        self.lineedit_host_ip: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos, size=QSize(100, height), text=''))
        self.lineedit_host_port: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos + QPoint(0, 1 * height), size=QSize(100, height), text=''))
        self.lineedit_username: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos + QPoint(0, 2 * height), size=QSize(100, height), text=''))
        self.lineedit_password: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos + QPoint(0, 3 * height), size=QSize(100, height), text=''))
        self.lineedit_cwd: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos + QPoint(0, 4 * height), size=QSize(100, height), text=''))
        self.button_connect: widget_base.Text = obj.add_object(
            widget_base.Text(obj=obj, pos=obj_pos + QPoint(0, 5 * height), text='connect', is_changeable=False,
                             func_select=widget_base.Func(name='', click_func=lambda x: self.establish_connection())))
        self.lineedit_local_path: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos + QPoint(0, 6 * height), size=QSize(100, height), text=''))
        self.lineedit_remote_path: widget_base.EmbeddedLineedit = obj.add_object(
            widget_base.Lineedit(obj=obj, pos=obj_pos + QPoint(0, 7 * height), size=QSize(100, height), text=''))
        self.button_upload: widget_base.Text = obj.add_object(
            widget_base.Text(obj=obj, pos=obj_pos + QPoint(0, 8 * height), text='upload', is_changeable=False,
                             func_select=widget_base.Func(name='', click_func=lambda x: self.upload())))

        self.lineedit_password.setEchoMode(widget_base.EmbeddedLineedit.EchoMode.Password)

    def establish_connection(self) -> None:
        ip = self.lineedit_host_ip.text()
        port = int(self.lineedit_host_port.text())
        username = self.lineedit_username.text()
        password = self.lineedit_password.text()
        cwd = self.lineedit_cwd.text()

        try:
            self.transport = paramiko.Transport((ip, port))
        except paramiko.ssh_exception.SSHException:
            self.frame.logger.info('connection failed')
            return

        try:
            self.transport.connect(username=username, password=password)
        except paramiko.ssh_exception.AuthenticationException:
            self.frame.logger.info('authentication failed')
            return
        # self.transport.auth_interactive_dumb(username=self.username)

        if self.transport.active:
            self.transport.set_keepalive(60)

            # TODO: path not exist
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            self.sftp.chdir(cwd)
            self.sftp.chdir('..')
            is_root_path = True if self.sftp.getcwd() == cwd else False

            if not is_root_path:
                file_attr = [i for i in self.sftp.listdir_attr(self.sftp.getcwd()) if i.filename == os.path.basename(cwd)]
                if file_attr:
                    self.file_manager = FileManagerSFTP(self.obj, self.sftp, cwd, file_attr[0], QPoint(100, 0))
                else:
                    self.frame.logger.error('check path')
                    return
            else:
                self.file_manager = FileManagerSFTP(self.obj, self.sftp, cwd, None, QPoint(100, 0))

        # self.channel = self.transport.open_session()
        # self.channel.get_pty()
        # self.channel.invoke_shell()

    def command(self, cmd) -> str:
        # self.channel.send(cmd + '\n')
        # result = self.channel.recv(-1).decode()

        channel = self.transport.open_session()

        # client = self.transport.open_sftp_client()
        channel.exec_command(cmd)
        # channel.send(cmd + '\n')
        result = channel.recv(-1).decode()

        # ssh = paramiko.SSHClient()
        # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # ssh._transport = self.transport

        # stdin, stdout, stderr = ssh.exec_command(cmd)
        # result = stdout.read()
        print(result)
        return result

    def upload(self) -> None:
        if not self.transport:
            self.frame.logger.error('transport has not been initialized')
        if not self.sftp:
            self.frame.logger.error('sftp has not been initialized')

        if self.transport.active:
            self.sftp.put(localpath=self.lineedit_local_path.text(), remotepath=self.lineedit_remote_path.text())
        else:
            self.frame.logger.error('transport is not active')

    def close(self) -> None:
        self.sftp.close()
        self.transport.close()


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_ssh')
        self.is_auto_start = True

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='generate ssh widget',
                                                 shortcut_key=['Ctrl', 'S'],
                                                 callback=self.generate_ssh_widget)
        self.widget_shortcut.add_shortcut(self.shortcut)

        self.reset()

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def generate_ssh_widget(self):
        obj: widget_base.Object = self.frame.widget_object_manager.generate_object()
        SSHProxy(self.frame, obj)

        # print(ssh_proxy.command('pwd'))
        # ssh_proxy.upload('1.txt', '1.txt')
