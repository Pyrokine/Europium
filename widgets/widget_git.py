from collections import deque
from typing import List, Dict, Deque, Optional, cast

import git
from PySide6.QtCore import QSize, QPoint, QRect
from PySide6.QtGui import Qt, QBrush, QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem, QHeaderView

from common import common, widget_base
from config import Config
from widgets import widget_shortcut

node_hollow_rad = Config.Git.CSS().node_hollow_rad
node_solid_rad = Config.Git.CSS().node_solid_rad


class Commit:
    def __init__(self, idx: int, ori_commit: git.objects.commit.Commit):
        self.idx = idx
        self.ori_commit = ori_commit
        self.branch: Optional[Branch] = None


class Branch:
    def __init__(self, branch: git.refs.head.Head):
        self.name = branch.name
        self.branch = branch
        self.commits: List[Commit] = []  # commits of the branch
        self.num_commits = None


class OccupiedMap:
    def __init__(self, row_cnt: int):
        self.map: List[List[bool]] = [[] for _ in range(row_cnt)]

    def is_cell_occupied(self, row_idx: int, col_idx: int):
        col_num = len(self.map[row_idx])
        if col_idx >= col_num:
            for _ in range(col_idx - col_num + 1):
                self.map[row_idx].append(False)

        return self.map[row_idx][col_idx]

    def get_first_available_column(self, row_idx_start: int, row_idx_end: int):
        col_idx = 0
        while True:
            is_occupied = False
            for row_idx in range(min(row_idx_start, row_idx_end), max(row_idx_start, row_idx_end) + 1):
                if self.is_cell_occupied(row_idx, col_idx):
                    is_occupied = True
                    break

            if is_occupied:
                col_idx += 1
            else:
                return col_idx

    def occupy(self, row_idx_start: int, row_idx_end: int, col_idx: int):
        for row_idx in range(row_idx_start, row_idx_end + 1):
            self.is_cell_occupied(row_idx, col_idx)
            self.map[row_idx][col_idx] = True


class GitTable(widget_base.EmbeddedTable):
    def __init__(self, obj: widget_base.Object):
        super().__init__(obj=obj)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.enable_checkbox = False
        self.setColumnCount(4)
        self.setShowGrid(False)
        self.setStyleSheet('border: none;')


class Repo:
    def __init__(self, name: str, is_local: bool, git_tab: 'GitTab'):
        self.name = name
        self.is_local = is_local
        self.git_tab = git_tab

        self.branches: Dict[str, Branch] = {}
        self.commits: List[Commit] = []  # all commits
        self.occupied_map: Optional[OccupiedMap] = None

        self.map_sha_commit: Dict[str, Commit] = {}
        self.map_sha_idx: Dict[str, int] = {}
        self.map_sha_node: Dict[str, Node] = {}
        self.map_sha_branch_tag: Dict[str, List[str]] = {}

        self.table = GitTable(git_tab.obj)
        self.graph = widget_base.GraphicsView(git_tab.obj, QPoint(), QSize())
        self.graph.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.page: widget_base.Page = widget_base.Page(
            title=self.name,
            frontend=self.table
        )
        if self.is_local:
            self.page.func_list = [
                widget_base.Func(name='load_folder', dclick_func=lambda x: git_tab.load_git_repo(x), args=[
                    widget_base.FuncArg('path', check=True, parse_type=widget_base.FuncArgParseType.dclick)
                ]),
                widget_base.Func(name='log', dclick_func=lambda x: git_tab.log())
            ]

    def init_occupied_map(self):
        self.occupied_map = OccupiedMap(len(self.commits))


class Node(widget_base.GraphicsEllipseItem):
    def __init__(self, commit: Commit, row_idx: int, col_idx: int, pos: QPoint):
        self.commit = commit

        self.row_idx = row_idx
        self.col_idx = col_idx

        is_merge = True if len(commit.ori_commit.parents) == 2 else False
        if is_merge:
            rad = node_solid_rad
        else:
            rad = node_hollow_rad

        super().__init__(QRect(-rad, -rad, 2 * rad, 2 * rad), pos)

        if is_merge:
            self.setBrush(QBrush(Qt.GlobalColor.black))

        self.pos_center = self.pos()
        self.pos_top = self.pos_center + QPoint(0, -rad)
        self.pos_bottom = self.pos_center + QPoint(0, rad)
        self.pos_left = self.pos_center + QPoint(-rad, 0)
        self.pos_right = self.pos_center + QPoint(rad, 0)


class Arc(QGraphicsPathItem):
    def __init__(self, rad: int, start_angle: int, span_angle: int, pos: QPoint):
        super().__init__()

        # 0 degree is at 3 o'clock
        # positive degree is counter clock
        painter_path = QPainterPath()
        painter_path.arcMoveTo(-rad, -rad, 2 * rad, 2 * rad, start_angle)
        painter_path.arcTo(-rad, -rad, 2 * rad, 2 * rad, start_angle, span_angle)

        self.setPath(painter_path)
        self.setPos(pos)


class GitTab:
    def __init__(self, frame: widget_base.Frame):
        self.frame = frame
        self.obj: widget_base.Object = frame.widget_object_manager.generate_object()
        self.tab_local: widget_base.Tab = self.obj.add_object(widget_base.Tab(obj=self.obj, pos=self.obj.global_pos, size=QSize(800, 600)))
        self.tab_remote: widget_base.Tab = self.obj.add_object(
            widget_base.Tab(obj=self.obj, pos=self.obj.global_pos + QPoint(1100, 0), size=QSize(800, 600)))

        self.git_repo: Optional[git.Repo] = None
        self.repos = {'local': Repo('local', True, self), 'remote': {}}

        self.node_rad = Config.Git.CSS().node_hollow_rad
        self.node_interval = Config.Git.CSS().node_interval
        self.arc_rad = Config.Git.CSS().arc_rad

        self.reset_tab()

    def reset(self) -> None:
        self.repos = {'local': Repo('local', True, self), 'remote': {}}
        self.reset_tab()

    def reset_tab(self):
        self.tab_local.delete_all_pages()
        self.tab_local.add_page(self.repos['local'].page)
        self.tab_local.on_page_change(0)

    def map_row_col_to_pos(self, row: int, col: int) -> QPoint:
        return QPoint((col + 0.5) * self.node_interval, (row + 0.5) * self.node_interval)

    def connect_nodes(self, repo: Repo, node_a: Node, node_b: Node, new_branch: bool = False, merge_branch: bool = False):
        if node_a.row_idx > node_b.row_idx:
            node_lower, node_upper = node_a, node_b
        else:
            node_lower, node_upper = node_b, node_a

        if new_branch:
            connect_point = QPoint(node_upper.pos_center.x(), node_lower.pos_center.y())

            if node_lower.col_idx < node_upper.col_idx:
                widget_base.GraphicsLineItem(
                    frame=self.frame,
                    scene=repo.graph.scene(),
                    pos_start=node_lower.pos_right,
                    pos_end=QPoint(connect_point.x() - self.arc_rad, connect_point.y()))
                arc = Arc(self.arc_rad, 0, -90, connect_point + QPoint(-self.arc_rad, -self.arc_rad))

            else:
                widget_base.GraphicsLineItem(
                    frame=self.frame,
                    scene=repo.graph.scene(),
                    pos_start=node_lower.pos_left,
                    pos_end=QPoint(connect_point.x() + self.arc_rad, connect_point.y()))
                arc = Arc(self.arc_rad, 270, -90, connect_point + QPoint(self.arc_rad, -self.arc_rad))
            repo.graph.scene().addItem(arc)

            widget_base.GraphicsLineItem(
                frame=self.frame,
                scene=repo.graph.scene(),
                pos_start=node_upper.pos_bottom,
                pos_end=QPoint(connect_point.x(), connect_point.y() - self.arc_rad))
        elif merge_branch:
            connect_point = QPoint(node_lower.pos_center.x(), node_upper.pos_center.y())

            widget_base.GraphicsLineItem(
                frame=self.frame,
                scene=repo.graph.scene(),
                pos_start=node_lower.pos_top,
                pos_end=QPoint(connect_point.x(), connect_point.y() + self.arc_rad))

            if node_lower.col_idx < node_upper.col_idx:
                widget_base.GraphicsLineItem(
                    frame=self.frame,
                    scene=repo.graph.scene(),
                    pos_start=node_upper.pos_left,
                    pos_end=QPoint(connect_point.x() + self.arc_rad, connect_point.y()))
                arc = Arc(self.arc_rad, 180, -90, connect_point + QPoint(self.arc_rad, self.arc_rad))
            else:
                widget_base.GraphicsLineItem(
                    frame=self.frame,
                    scene=repo.graph.scene(),
                    pos_start=node_upper.pos_right,
                    pos_end=QPoint(connect_point.x() - self.arc_rad, connect_point.y()))
                arc = Arc(self.arc_rad, 90, -90, connect_point + QPoint(-self.arc_rad, self.arc_rad))
            repo.graph.scene().addItem(arc)
        else:
            widget_base.GraphicsLineItem(
                frame=self.frame,
                scene=repo.graph.scene(),
                pos_start=node_lower.pos_top,
                pos_end=QPoint(node_upper.pos_bottom.x(), node_upper.pos_bottom.y()))

    def fetch_branches(self) -> None:
        for branch in cast(List[git.Head], self.git_repo.refs):
            if branch.is_remote():
                repo_name = branch.remote_name
                if repo_name not in self.repos['remote']:
                    repo = Repo(repo_name, False, self)
                    self.repos['remote'].update({repo_name: repo})
                    self.tab_remote.add_page(repo.page)

                self.repos['remote'][repo_name].branches.update({branch.remote_head: Branch(branch)})
            else:
                self.repos['local'].branches.update({branch.name: Branch(branch)})

        self.fetch_commits(self.repos['local'])

        for repo in self.repos['remote'].values():
            self.fetch_commits(repo)

    def fetch_commits(self, repo: Repo) -> None:
        commit_history = {self.git_repo.head.commit.hexsha: self.git_repo.head.commit}

        for branch in repo.branches.values():
            commit_history.update({ori_commit.hexsha: ori_commit for ori_commit in list(self.git_repo.iter_commits(rev=branch.branch))})

            sha = branch.branch.commit.hexsha
            if sha not in repo.map_sha_branch_tag:
                repo.map_sha_branch_tag.update({sha: [branch.branch.name]})
            else:
                repo.map_sha_branch_tag[sha].append(branch.branch.name)

        repo.commits = [Commit(idx, ori_commit) for idx, ori_commit in enumerate(
            sorted(list(commit_history.values()), key=lambda x: -x.committed_date))]
        repo.map_sha_commit = {commit.ori_commit.hexsha: commit for commit in repo.commits}
        repo.map_sha_idx = {commit.ori_commit.hexsha: idx for idx, commit in enumerate(repo.commits)}
        repo.init_occupied_map()

        # to be verified
        for commit in repo.commits:
            hexsha = commit.ori_commit.hexsha
            if hexsha not in repo.map_sha_node:
                row_idx = repo.map_sha_idx[hexsha]
                col_idx = repo.occupied_map.get_first_available_column(row_idx, row_idx)

                node = Node(
                    commit=commit,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    pos=self.map_row_col_to_pos(row_idx, col_idx)
                )
                repo.graph.scene().addItem(node)
                repo.map_sha_node.update({hexsha: node})

                repo.occupied_map.occupy(row_idx, row_idx, col_idx)

                self.fetch_commits_helper(repo, deque([hexsha]))

        self.render_nodes_details(repo)

    def fetch_commits_helper(self, repo: Repo, process_list: Deque[str]) -> None:
        while process_list:
            process_list = deque(sorted(process_list, key=lambda x: repo.map_sha_idx[x]))  # efficiency?
            latter_commit = repo.map_sha_commit[process_list[0]].ori_commit
            latter_node = repo.map_sha_node[latter_commit.hexsha]

            parents = latter_commit.parents
            if parents:
                prev_hexsha: str = parents[0].hexsha
                prev_commit: Commit = repo.map_sha_commit[prev_hexsha]

                if prev_hexsha not in repo.map_sha_node:
                    row_idx = repo.map_sha_idx[prev_hexsha]
                    col_idx = latter_node.col_idx

                    prev_node = Node(
                        commit=prev_commit,
                        row_idx=row_idx,
                        col_idx=col_idx,
                        pos=self.map_row_col_to_pos(row_idx, col_idx)
                    )
                    repo.graph.scene().addItem(prev_node)
                    repo.map_sha_node.update({prev_hexsha: prev_node})

                    self.connect_nodes(repo, latter_node, prev_node)
                    repo.occupied_map.occupy(latter_node.row_idx, prev_node.row_idx, prev_node.col_idx)

                    process_list.append(prev_hexsha)
                else:
                    prev_node = repo.map_sha_node[prev_hexsha]
                    self.connect_nodes(repo, latter_node, prev_node, new_branch=True)
                    repo.occupied_map.occupy(latter_node.row_idx, prev_node.row_idx, latter_node.col_idx)

                if len(parents) == 2:
                    prev_hexsha = parents[1].hexsha
                    prev_commit = repo.map_sha_commit[prev_hexsha]

                    if prev_hexsha not in repo.map_sha_node:
                        row_idx = repo.map_sha_idx[prev_hexsha]
                        col_idx = repo.occupied_map.get_first_available_column(latter_node.row_idx + 1, row_idx)

                        prev_node = Node(
                            commit=prev_commit,
                            row_idx=row_idx,
                            col_idx=col_idx,
                            pos=self.map_row_col_to_pos(row_idx, col_idx)
                        )
                        repo.graph.scene().addItem(prev_node)
                        repo.map_sha_node.update({prev_hexsha: prev_node})

                        self.connect_nodes(repo, latter_node, prev_node, merge_branch=True)
                        repo.occupied_map.occupy(latter_node.row_idx, prev_node.row_idx, prev_node.col_idx)

                        process_list.append(prev_hexsha)
                    else:
                        prev_node = repo.map_sha_node[prev_hexsha]
                        self.connect_nodes(repo, latter_node, prev_node, merge_branch=True)
                        repo.occupied_map.occupy(latter_node.row_idx, prev_node.row_idx, prev_node.col_idx)

            process_list.popleft()

    def render_nodes_details(self, repo: Repo) -> None:
        num_col = max([i.col_idx for i in repo.map_sha_node.values()])

        repo.table.setRowCount(len(repo.commits))

        table_header = ['branch/tag', 'graph', 'message', 'hexsha']
        table_data = []
        for row_cnt, commit in enumerate(repo.commits):
            row_data = {
                'branch/tag': widget_base.TableCell('branch/tag', repo.map_sha_branch_tag[commit.ori_commit.hexsha][0],  # TODO
                                                    widget_base.TableCellType.LINEEDIT_READONLY, QSize(100, self.node_interval))
            } if commit.ori_commit.hexsha in repo.map_sha_branch_tag else {}
            row_data.update({
                'message': widget_base.TableCell('message', commit.ori_commit.message, widget_base.TableCellType.LINEEDIT_READONLY,
                                                 QSize(400, self.node_interval)),
                'hexsha': widget_base.TableCell('hexsha', commit.ori_commit.hexsha[:7], widget_base.TableCellType.LINEEDIT_READONLY,
                                                QSize(60, self.node_interval))
            })
            table_row = widget_base.TableRow(data=row_data)
            table_data.append(table_row)

        repo.table.render_list(table_header, table_data)
        repo.table.update_height()
        repo.table.update_width()

        repo.graph.set_scene_size((num_col + 1.5) * self.node_interval, len(repo.commits) * self.node_interval, update_view_size=False)
        repo.table.setSpan(0, 1, len(repo.commits), 1)
        repo.table.setCellWidget(0, 1, repo.graph)
        repo.table.setColumnWidth(1, (num_col + 2) * self.node_interval)

        pass

    def load_git_repo(self, args: List[widget_base.FuncArg]) -> None:
        try:
            self.git_repo = git.Repo(args[0].value, search_parent_directories=True)
            self.obj.frame.logger.success('git repo loaded')
        except git.InvalidGitRepositoryError:
            self.obj.frame.logger.error('cannot find git repo in input path')

    def log(self):
        self.reset()

        if self.git_repo:
            self.fetch_branches()
        else:
            self.obj.frame.logger.error('git repo is not loaded')


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_git')
        self.is_auto_start = True

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='generate git widget',
                                                 shortcut_key=['Ctrl', 'G'],
                                                 callback=self.generate_git_widget)
        self.widget_shortcut.add_shortcut(self.shortcut)

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def generate_git_widget(self):
        GitTab(self.frame)
