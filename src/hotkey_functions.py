#!/usr/bin/python

# ------------------------------------------------------------------------------
# menu command functions
# ------------------------------------------------------------------------------

from curses import pair_content
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import (QInputDialog, QMessageBox, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QSpinBox, QComboBox, 
                             QPushButton, QGroupBox)
from PyQt5.QtCore import Qt

# 导入自定义 BackdropNode
from src.nodegraph_tools import BackdropNode

def get_bus_definitions(busdef_dir=None):
    """
    从 busdef 目录获取所有 bus 定义
    
    Args:
        busdef_dir: busdef 目录路径，如果为 None 则使用默认路径
    
    Returns:
        list: 包含 bus 定义信息的列表，每个元素是 {'name': 'xxx', 'version': '1.0', 'file': 'xxx.xml'}
    """
    if not busdef_dir:
        busdef_dir = os.path.join(os.path.dirname(__file__), '..', 'library', 'busdef')
    
    bus_defs = []
    
    try:
        if os.path.exists(busdef_dir):
            for filename in os.listdir(busdef_dir):
                if filename.endswith('.xml') and not filename.startswith('.'):
                    basename = os.path.splitext(filename)[0]
                    parts = basename.split('_')
                    
                    if 'abstract' in parts:
                        continue
                    
                    if len(parts) >= 2:
                        version = parts[-1]
                        name = '_'.join(parts[:-1])
                    else:
                        name = basename
                        version = '1.0'
                    
                    bus_defs.append({
                        'name': name,
                        'version': version,
                        'file': filename,
                        'full_path': os.path.join(busdef_dir, filename)
                    })
    except Exception as e:
        print(f"读取 busdef 目录失败: {e}")
    
    return bus_defs

class PortSettingsDialog(QDialog):
    """端口设置对话框"""
    def __init__(self, port_type='output', parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"设置{'Output' if port_type == 'output' else 'Input'} Port")
        self.setGeometry(100, 100, 400, 300)
        
        self.port_type = port_type
        
        layout = QVBoxLayout(self)
        
        name_group = QGroupBox("端口名称")
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入端口名称")
        name_layout.addWidget(QLabel("名称:"))
        name_layout.addWidget(self.name_edit)
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)
        
        self.width_group = QGroupBox("端口位宽")
        width_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 1024)
        self.width_spin.setValue(1)
        width_layout.addWidget(QLabel("位宽:"))
        width_layout.addWidget(self.width_spin)
        width_layout.addWidget(QLabel("bit"))
        self.width_group.setLayout(width_layout)
        layout.addWidget(self.width_group)
        
        type_group = QGroupBox("端口类型")
        type_layout = QVBoxLayout()
        
        signal_bus_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["signal", "bus"])
        self.type_combo.currentTextChanged.connect(self.on_port_type_changed)
        signal_bus_layout.addWidget(QLabel("类型:"))
        signal_bus_layout.addWidget(self.type_combo)
        type_layout.addLayout(signal_bus_layout)
        
        self.bus_group = QGroupBox("Bus 定义")
        bus_layout = QVBoxLayout()
        
        # Bus 选择和 Mode 选择并行布局
        bus_mode_layout = QHBoxLayout()
        
        # Bus 选择
        bus_select_layout = QHBoxLayout()
        bus_select_layout.addWidget(QLabel("Bus:"))
        bus_defs = get_bus_definitions()
        self.bus_combo = QComboBox()
        if bus_defs:
            for bus in bus_defs:
                self.bus_combo.addItem(f"{bus['name']} v{bus['version']}", bus)
            # 当切换 bus 选择时，重新加载 bus map
            self.bus_combo.currentIndexChanged.connect(self.load_bus_map)
        else:
            self.bus_combo.addItem("未找到 bus 定义")
            self.bus_combo.setEnabled(False)
        bus_select_layout.addWidget(self.bus_combo)
        bus_mode_layout.addLayout(bus_select_layout)
        
        # Mode 选择
        mode_select_layout = QHBoxLayout()
        mode_select_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["master", "slave"])
        mode_select_layout.addWidget(self.mode_combo)
        bus_mode_layout.addLayout(mode_select_layout)
        
        bus_layout.addLayout(bus_mode_layout)
        self.bus_group.setLayout(bus_layout)
        self.bus_group.setVisible(False)
        
        self.bus_map_group = QGroupBox("Bus Map 定义")
        self.bus_map_layout = QVBoxLayout()
        self.bus_map_table = None
        self.bus_map_group.setLayout(self.bus_map_layout)
        self.bus_map_group.setVisible(False)
        
        type_layout.addWidget(self.bus_group)
        type_layout.addWidget(self.bus_map_group)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def on_port_type_changed(self, text):
        """当端口类型改变时显示/隐藏相应的设置栏"""
        if text == "signal":
            # signal 类型：显示位宽栏，隐藏 bus 相关
            self.width_group.setVisible(True)
            self.bus_group.setVisible(False)
            self.bus_map_group.setVisible(False)
        else:
            # bus 类型：隐藏位宽栏，显示 bus 相关
            self.width_group.setVisible(False)
            self.bus_group.setVisible(True)
            self.bus_map_group.setVisible(True)
            self.load_bus_map()
    
    def load_bus_map(self):
        """加载 bus 定义文件并显示逻辑信号名列表"""
        # 清空现有表格
        if self.bus_map_table:
            self.bus_map_layout.removeWidget(self.bus_map_table)
            self.bus_map_table.deleteLater()
        
        # 获取选中的 bus 定义
        bus_data = self.bus_combo.currentData()
        if not bus_data:
            return
        
        # 解析 bus 定义文件，提取逻辑信号名
        logical_signals = self.parse_bus_definition(bus_data['full_path'])
        
        # 创建表格
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.bus_map_table = QTableWidget()
        self.bus_map_table.setColumnCount(2)
        self.bus_map_table.setHorizontalHeaderLabels(["逻辑信号名", "物理信号名"])
        self.bus_map_table.setRowCount(len(logical_signals))
        
        for i, signal_name in enumerate(logical_signals):
            # 逻辑信号名（只读）
            logical_item = QTableWidgetItem(signal_name)
            logical_item.setFlags(logical_item.flags() & ~Qt.ItemIsEditable)
            self.bus_map_table.setItem(i, 0, logical_item)
            
            # 物理信号名（可编辑，默认为逻辑信号名）
            physical_item = QTableWidgetItem(signal_name)
            self.bus_map_table.setItem(i, 1, physical_item)
        
        self.bus_map_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bus_map_layout.addWidget(self.bus_map_table)
    
    def parse_bus_definition(self, file_path):
        """解析 bus 定义 XML 文件，提取逻辑信号名"""
        import xml.etree.ElementTree as ET
        
        logical_signals = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # IP-XACT 命名空间
            namespace = 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
            
            # 查找 signalDefinitions 元素
            signal_defs_elem = root.find(f".//{{{namespace}}}signalDefinitions")
            
            if signal_defs_elem is not None:
                # 查找所有 signalDefinition 元素
                signal_elems = signal_defs_elem.findall(f".//{{{namespace}}}signalDefinition")
                for signal_elem in signal_elems:
                    # 查找 name 子元素
                    name_elem = signal_elem.find(f".//{{{namespace}}}name")
                    if name_elem is not None and name_elem.text:
                        logical_signals.append(name_elem.text)
        except Exception as e:
            print(f"解析 bus 定义文件失败: {e}")
        
        return logical_signals
    
    def get_settings(self):
        """获取用户设置的端口信息"""
        port_type = self.type_combo.currentText()
        settings = {
            'name': self.name_edit.text().strip(),
            'width': self.width_spin.value(),
            'port_type': port_type,
            'bus_def': None,
            'bus_mode': None,
            'bus_map': []
        }
        
        if port_type == 'bus' and self.bus_combo.count() > 0:
            bus_data = self.bus_combo.currentData()
            if bus_data:
                settings['bus_def'] = bus_data
            settings['bus_mode'] = self.mode_combo.currentText()
            
            # 收集 bus map 数据
            if self.bus_map_table:
                bus_map = []
                for row in range(self.bus_map_table.rowCount()):
                    logical_name = self.bus_map_table.item(row, 0).text()
                    physical_name = self.bus_map_table.item(row, 1).text() if self.bus_map_table.item(row, 1) else ''
                    bus_map.append({
                        'logical': logical_name,
                        'physical': physical_name
                    })
                settings['bus_map'] = bus_map
        
        return settings

def _as_xy(pos):
    """兼容 NodeGraphQt 返回 list/tuple 或 QPointF 的坐标。"""
    if isinstance(pos, (list, tuple)):
        return float(pos[0]), float(pos[1])
    return float(pos.x()), float(pos.y())


def _node_size(node):
    """获取节点当前视图尺寸，取不到时使用 circle 节点的默认尺寸。"""
    view = getattr(node, 'view', None)
    width = getattr(view, 'width', None) or getattr(getattr(node, 'model', None), 'width', None) or 160
    height = getattr(view, 'height', None) or getattr(getattr(node, 'model', None), 'height', None) or 60
    return float(width), float(height)


def _find_port_backdrop(graph, backdrop_name):
    for existing_node in graph.all_nodes():
        if existing_node.name() == backdrop_name:
            return existing_node
    return None


def _create_port_backdrop(graph, backdrop_name, color):
    if BackdropNode is None:
        raise RuntimeError("当前 NodeGraphQt 环境无法创建 BackdropNode")

    cursor_x, cursor_y = _as_xy(graph.cursor_pos())
    backdrop_node = BackdropNode()
    graph.add_node(
        backdrop_node,
        pos=[cursor_x - 54, cursor_y - 54],
        selected=False
    )
    backdrop_node.set_name(backdrop_name)
    backdrop_node.set_property('color', color)
    return backdrop_node


def _get_or_create_port_backdrop(graph, backdrop_name, color):
    return _find_port_backdrop(graph, backdrop_name) or _create_port_backdrop(
        graph, backdrop_name, color
    )


def auto_arrange_nodes_in_backdrop(backdrop_node, graph, spacing=40, layout='horizontal'):
    """
    自动排列 backdrop 内的节点
    
    Args:
        backdrop_node: BackdropNode 实例
        graph: 图形实例，用于获取所有节点
        spacing: 节点之间的间距（默认 40）
        layout: 排列方式，'horizontal' 或 'vertical'（默认水平）
    """
    # 获取 backdrop 的名称，用于确定要排列的节点类型
    backdrop_name = backdrop_node.name()
    
    # 根据 backdrop 名称确定要排列的节点类型
    if backdrop_name == "Output Ports":
        node_type = 'user.circle.CircleNodeOut'
    elif backdrop_name == "Input Ports":
        node_type = 'user.circle.CircleNodeIn'
    else:
        return
    
    # 获取所有该类型的节点
    nodes = []
    for node in graph.all_nodes():
        if node.type_ == node_type:
            nodes.append(node)
    
    if not nodes:
        return
    
    backdrop_x, backdrop_y = _as_xy(backdrop_node.pos())

    # NodeGraphQt 的 backdrop 拖拽会选择“完全包含”的节点，因此留出足够边距。
    left_padding = 54
    top_padding = 54
    right_padding = 58
    bottom_padding = 48

    start_x = backdrop_x + left_padding
    start_y = backdrop_y + top_padding
    current_x = start_x
    current_y = start_y
    max_node_width = 0
    max_node_height = 0
    total_width = 0
    total_height = 0

    for node in nodes:
        node_width, node_height = _node_size(node)
        max_node_width = max(max_node_width, node_width)
        max_node_height = max(max_node_height, node_height)
        node.set_pos(current_x, current_y)

        if layout == 'horizontal':
            current_x += node_width + spacing
            total_width += node_width + spacing
            total_height = max(total_height, node_height)
        else:
            current_y += node_height + spacing
            total_height += node_height + spacing
            total_width = max(total_width, node_width)

    if layout == 'horizontal':
        total_width = max(0, total_width - spacing)
        backdrop_width = left_padding + total_width + right_padding
        backdrop_height = top_padding + max_node_height + bottom_padding
    else:
        total_height = max(0, total_height - spacing)
        backdrop_width = left_padding + max_node_width + right_padding
        backdrop_height = top_padding + total_height + bottom_padding

    # 确保最小大小
    backdrop_width = max(backdrop_width, 150)
    backdrop_height = max(backdrop_height, 120)
    
    try:
        backdrop_node.set_size(backdrop_width, backdrop_height)
    except AttributeError:
        try:
            # 尝试其他可能的方法名
            backdrop_node.resize(backdrop_width, backdrop_height)
        except AttributeError:
            # 尝试直接设置属性
            try:
                backdrop_node.width = backdrop_width
                backdrop_node.height = backdrop_height
            except AttributeError:
                print("无法设置 backdrop 大小")

def add_circle_node_out(graph):
    """添加输出端口圆形节点"""
    try:
        # 弹出端口设置对话框
        dialog = PortSettingsDialog(port_type='output')
        if dialog.exec_() != QDialog.Accepted:
            return
        
        settings = dialog.get_settings()
        name = settings['name']
        width = settings['width']
        port_type = settings['port_type']
        bus_def = settings['bus_def']
        bus_mode = settings['bus_mode']
        bus_map = settings['bus_map']
        
        if not name:
            QMessageBox.warning(None, "警告", "端口名称不能为空")
            return
        
        # 创建圆形节点，随后会自动排列到 Output Ports backdrop 内。
        node = graph.create_node(
            'user.circle.CircleNodeOut',
            name=name,
            pos=graph.cursor_pos()
        )
        
        node.width = width
        node.port_type = port_type
        if bus_def:
            node.bus_def = bus_def
            node.bus_name = bus_def['name']
            node.bus_mode = bus_mode
            node.bus_map = bus_map
        
        backdrop_node = _get_or_create_port_backdrop(
            graph, "Output Ports", (50, 50, 80, 100)
        )
        auto_arrange_nodes_in_backdrop(backdrop_node, graph, spacing=30, layout='vertical')
        
        print(f"已创建输出端口节点: {name}, 位宽: {width}, 类型: {port_type}" + (f", Bus: {bus_def['name']}" if bus_def else ""))
    except Exception as e:
        print(f"创建输出端口节点失败: {e}")
        QMessageBox.critical(None, "错误", f"创建输出端口节点失败: {str(e)}")

def add_circle_node_in(graph):
    """添加输入端口圆形节点"""
    try:
        # 弹出端口设置对话框
        dialog = PortSettingsDialog(port_type='input')
        if dialog.exec_() != QDialog.Accepted:
            return
        
        settings = dialog.get_settings()
        name = settings['name']
        width = settings['width']
        port_type = settings['port_type']
        bus_def = settings['bus_def']
        bus_mode = settings['bus_mode']
        bus_map = settings['bus_map']
        
        if not name:
            QMessageBox.warning(None, "警告", "端口名称不能为空")
            return
        
        # 创建圆形节点，随后会自动排列到 Input Ports backdrop 内。
        node = graph.create_node(
            'user.circle.CircleNodeIn',
            name=name,
            pos=graph.cursor_pos()
        )
        
        node.width = width
        node.port_type = port_type
        if bus_def:
            node.bus_def = bus_def
            node.bus_name = bus_def['name']
            node.bus_mode = bus_mode
            node.bus_map = bus_map
        
        backdrop_node = _get_or_create_port_backdrop(
            graph, "Input Ports", (80, 50, 50, 100)
        )
        auto_arrange_nodes_in_backdrop(backdrop_node, graph, spacing=30, layout='vertical')
        
        print(f"已创建输入端口节点: {name}, 位宽: {width}, 类型: {port_type}" + (f", Bus: {bus_def['name']}" if bus_def else ""))
    except Exception as e:
        print(f"创建输入端口节点失败: {e}")
        QMessageBox.critical(None, "错误", f"创建输入端口节点失败: {str(e)}")


def zoom_in(graph):
    """
    Set the node graph to zoom in by 0.1
    """
    zoom = graph.get_zoom() + 0.1
    graph.set_zoom(zoom)


def zoom_out(graph):
    """
    Set the node graph to zoom in by 0.1
    """
    zoom = graph.get_zoom() - 0.2
    graph.set_zoom(zoom)


def reset_zoom(graph):
    """
    Reset zoom level.
    """
    graph.reset_zoom()


def layout_h_mode(graph):
    """
    Set node graph layout direction to horizontal.
    """
    graph.set_layout_direction(0)


def layout_v_mode(graph):
    """
    Set node graph layout direction to vertical.
    """
    graph.set_layout_direction(1)


def open_session(graph):
    """
    Prompts a file open dialog to load a session.
    """
    current = graph.current_session()
    file_path = graph.load_dialog(current)
    if file_path:
        graph.load_session(file_path)


def import_session(graph):
    """
    Prompts a file open dialog to load a session.
    """
    current = graph.current_session()
    file_path = graph.load_dialog(current)
    if file_path:
        graph.import_session(file_path)


def save_session(graph):
    """
    Prompts a file save dialog to serialize a session if required.
    """
    current = graph.current_session()
    if current:
        graph.save_session(current)
        msg = 'Session layout saved:\n{}'.format(current)
        viewer = graph.viewer()
        viewer.message_dialog(msg, title='Session Saved')
    else:
        save_session_as(graph)


def save_session_as(graph):
    """
    Prompts a file save dialog to serialize a session.
    """
    current = graph.current_session()
    file_path = graph.save_dialog(current)
    if file_path:
        graph.save_session(file_path)


def clear_session(graph):
    """
    Prompts a warning dialog to new a node graph session.
    """
    if graph.question_dialog('Clear Current Session?', 'Clear Session'):
        graph.clear_session()

def quit_qt(graph):
    """
    Quit the Qt application.
    """
    from Qt import QtCore
    QtCore.QCoreApplication.quit()

def clear_undo(graph):
    """
    Prompts a warning dialog to clear undo.
    """
    viewer = graph.viewer()
    msg = 'Clear all undo history, Are you sure?'
    if viewer.question_dialog('Clear Undo History', msg):
        graph.clear_undo_stack()


def copy_nodes(graph):
    """
    Copy nodes to the clipboard.
    """
    graph.copy_nodes()


def cut_nodes(graph):
    """
    Cut nodes to the clip board.
    """
    graph.cut_nodes()


def paste_nodes(graph):
    """
    Pastes nodes copied from the clipboard.
    """
    # by default the graph will inherite the global style
    # from the graph when pasting nodes.
    # to disable this behaviour set `adjust_graph_style` to False.
    graph.paste_nodes(adjust_graph_style=False)


def delete_nodes_and_pipes(graph):
    """
    Delete selected nodes and connections.
    """
    graph.delete_nodes(graph.selected_nodes())
    for pipe in graph.selected_pipes():
        pipe[0].disconnect_from(pipe[1])


def extract_nodes(graph):
    """
    Extract selected nodes.
    """
    graph.extract_nodes(graph.selected_nodes())


def clear_node_connections(graph):
    """
    Clear port connection on selected nodes.
    """
    graph.undo_stack().beginMacro('clear selected node connections')
    for node in graph.selected_nodes():
        for port in node.input_ports() + node.output_ports():
            port.clear_connections()
    graph.undo_stack().endMacro()


def select_all_nodes(graph):
    """
    Select all nodes.
    """
    graph.select_all()


def clear_node_selection(graph):
    """
    Clear node selection.
    """
    graph.clear_selection()


def invert_node_selection(graph):
    """
    Invert node selection.
    """
    graph.invert_selection()


def disable_nodes(graph):
    """
    Toggle disable on selected nodes.
    """
    graph.disable_nodes(graph.selected_nodes())


def duplicate_nodes(graph):
    """
    Duplicated selected nodes.
    """
    graph.duplicate_nodes(graph.selected_nodes())


def expand_group_node(graph):
    """
    Expand selected group node.
    """
    selected_nodes = graph.selected_nodes()
    if not selected_nodes:
        graph.message_dialog('Please select a "GroupNode" to expand.')
        return
    graph.expand_group_node(selected_nodes[0])


def fit_to_selection(graph):
    """
    Sets the zoom level to fit selected nodes.
    """
    graph.fit_to_selection()


def show_undo_view(graph):
    """
    Show the undo list widget.
    """
    graph.undo_view.show()


def curved_pipe(graph):
    """
    Set node graph pipes layout as curved.
    """
    from NodeGraphQt.constants import PipeLayoutEnum
    graph.set_pipe_style(PipeLayoutEnum.CURVED.value)


def straight_pipe(graph):
    """
    Set node graph pipes layout as straight.
    """
    from NodeGraphQt.constants import PipeLayoutEnum
    graph.set_pipe_style(PipeLayoutEnum.STRAIGHT.value)


def angle_pipe(graph):
    """
    Set node graph pipes layout as angled.
    """
    from NodeGraphQt.constants import PipeLayoutEnum
    graph.set_pipe_style(PipeLayoutEnum.ANGLE.value)


def bg_grid_none(graph):
    """
    Turn off the background patterns.
    """
    from NodeGraphQt.constants import ViewerEnum
    graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_NONE.value)


def bg_grid_dots(graph):
    """
    Set background node graph background with grid dots.
    """
    from NodeGraphQt.constants import ViewerEnum
    graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_DOTS.value)


def bg_grid_lines(graph):
    """
    Set background node graph background with grid lines.
    """
    from NodeGraphQt.constants import ViewerEnum
    graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_LINES.value)


def layout_graph_down(graph):
    """
    Auto layout the nodes down stream.
    """
    nodes = graph.selected_nodes() or graph.all_nodes()
    graph.auto_layout_nodes(nodes=nodes, down_stream=True)


def layout_graph_up(graph):
    """
    Auto layout the nodes up stream.
    """
    nodes = graph.selected_nodes() or graph.all_nodes()
    graph.auto_layout_nodes(nodes=nodes, down_stream=False)


def toggle_node_search(graph):
    """
    show/hide the node search widget.
    """
    graph.toggle_node_search()
