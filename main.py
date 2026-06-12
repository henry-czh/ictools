import sys
import os
import json
import glob
from datetime import datetime
from traceback import print_tb
from jinja2 import Environment, FileSystemLoader
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QTreeWidget, QTreeWidgetItem, QTextEdit, QMenuBar, 
                             QAction, QFileDialog, QMessageBox, QGraphicsView, QPushButton, 
                             QDialog, QLineEdit, QLabel, QMenu, QSplitter) 
from PyQt5.QtCore import Qt, QMimeData, QEvent, QObject, pyqtSignal
from PyQt5.QtGui import QDrag, QIcon
from src.ipxact_parser import IPXactParser
from src.ipxact_writer import IPXactWriter
from NodeGraphQt import BaseNode, NodeGraph
from src.nodegraph_tools import (get_all_connections, make_template_node, 
                                 CircleNodeIn, CircleNodeOut)
from src.portInfoDialog import PortInfoDialog 
from src.newBusDefDialog import NewBusDefDialog
from src.newComponentDialog import NewComponentDialog
from src.terminal_widget import TerminalWidget

# 自定义输出流类，用于将print重定向到details_panel
class PanelOutputStream(QObject):
    """自定义输出流，将输出发送到QTextEdit"""
    new_output = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buffer = []
    
    def write(self, text):
        # 忽略空行
        if text.strip():
            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.buffer.append(f"[{timestamp}] {text}")
            # 发送信号
            self.new_output.emit(f"[{timestamp}] {text}")
    
    def flush(self):
        pass
    
    def get_buffer(self):
        return self.buffer
    
    def clear_buffer(self):
        self.buffer = []

def get_config_path():
    """获取配置文件路径"""
    config_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer")
    return os.path.join(config_dir, "config.json")

def save_config(config):
    """保存配置到文件"""
    config_path = get_config_path()
    config_dir = os.path.dirname(config_path)
    
    # 创建配置目录
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

def load_config():
    """从文件加载配置"""
    config_path = get_config_path()
    
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return {}

class CustomNodeGraph(NodeGraph):
    """自定义NodeGraph类，重写鼠标事件处理函数"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化拖拽状态
        self._panning = False
        self._last_mouse_pos = None
        self._pan_button = None
        
        # 节点双击回调函数
        self._node_double_click_callback = None
        
        # 创建fitscreen按钮
        self._create_fitscreen_button()
        
        # 获取QGraphicsView并设置事件处理
        view = self.widget.findChild(QGraphicsView)
        if view:
            # 保存原始的事件处理函数
            self._original_mouse_double_click = view.mouseDoubleClickEvent
            
            # 设置自定义事件处理函数
            view.mouseDoubleClickEvent = self._custom_mouse_double_click
    
    def _create_fitscreen_button(self):
        """创建fitscreen按钮"""
        # 获取主视图
        main_view = self.widget.findChild(QGraphicsView)
        if not main_view:
            return
        
        # 创建fitscreen按钮
        self._fitscreen_button = QPushButton(main_view)
        # 设置按钮大小
        self._fitscreen_button.setFixedSize(30, 30)
        # 设置按钮样式
        self._fitscreen_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border: 1px solid #999;
            }
        """)
        # 设置按钮图标
        # 使用自定义图标
        fitview_icon = QIcon("src/fit_view.svg")
        self._fitscreen_button.setIcon(fitview_icon)
        # 设置按钮只显示图标
        self._fitscreen_button.setText("")
        # 设置按钮提示
        self._fitscreen_button.setToolTip("Fit Screen")
        
        # 连接按钮点击事件
        self._fitscreen_button.clicked.connect(self._fitscreen)
        
        # 安装事件过滤器，监听主视图的大小改变事件
        main_view.installEventFilter(self)
        
        # 初始更新按钮位置
        self._update_fitscreen_button_position()
    
    def _update_fitscreen_button_position(self):
        """更新fitscreen按钮的位置"""
        if not hasattr(self, '_fitscreen_button'):
            return
        
        # 获取主视图
        main_view = self.widget.findChild(QGraphicsView)
        if not main_view:
            return
        
        # 将按钮放置在右下角
        self._fitscreen_button.move(main_view.width() - 40, main_view.height() - 40)
        self._fitscreen_button.show()
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于更新按钮位置"""
        if event.type() == QEvent.Resize:
            self._update_fitscreen_button_position()
        return super().eventFilter(obj, event)
    
    def _fitscreen(self):
        """显示全景"""
        # 获取NodeGraphQt库内部的viewer对象
        viewer = self.viewer()
        if viewer:
            # 获取所有节点
            nodes = viewer.all_nodes()
            if nodes:
                # 调用zoom_to_nodes方法显示所有节点
                viewer.zoom_to_nodes(nodes)
        
        # 更新按钮位置
        self._update_fitscreen_button_position()
    
    def set_node_double_click_callback(self, callback):
        """设置节点双击回调函数"""
        self._node_double_click_callback = callback
    
    def _custom_mouse_double_click(self, event):
        """自定义鼠标双击事件处理"""
        # 处理节点双击事件
        # 直接使用当前选中的节点
        selected_nodes = self.selected_nodes()
        if selected_nodes and self._node_double_click_callback:
            clicked_node = selected_nodes[0]
            self._node_double_click_callback(clicked_node)
            event.accept()
        else:
            # 调用原始的双击处理函数
            self._original_mouse_double_click(event)
    
class LibraryConfigDialog(QDialog):
    """Library库配置对话框 - 支持多个Library目录"""
    def __init__(self, parent=None, library_dirs=None):
        super().__init__(parent)
        self.setWindowTitle("Library库配置")
        self.setGeometry(100, 100, 500, 300)
        
        # 确保 library_dirs 是列表
        if library_dirs is None:
            library_dirs = []
        elif isinstance(library_dirs, str):
            # 兼容旧格式（单个目录）
            library_dirs = [library_dirs] if library_dirs else []
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 目录列表区域
        list_layout = QVBoxLayout()
        
        # 标签
        list_label = QLabel("Library目录列表:")
        list_layout.addWidget(list_label)
        
        # 列表控件
        self.dir_list = QListWidget()
        self.dir_list.addItems(library_dirs)
        list_layout.addWidget(self.dir_list)
        
        layout.addLayout(list_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 添加按钮
        add_button = QPushButton("添加")
        add_button.clicked.connect(self.add_directory)
        button_layout.addWidget(add_button)
        
        # 删除按钮
        remove_button = QPushButton("删除")
        remove_button.clicked.connect(self.remove_directory)
        button_layout.addWidget(remove_button)
        
        layout.addLayout(button_layout)
        
        # 确定和取消按钮
        ok_cancel_layout = QHBoxLayout()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        ok_cancel_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        ok_cancel_layout.addWidget(cancel_button)
        
        layout.addLayout(ok_cancel_layout)
        
        # 存储选定的目录列表
        self.selected_directories = library_dirs
    
    def add_directory(self):
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(self, "选择Library库目录")
        if directory and directory not in self.selected_directories:
            self.selected_directories.append(directory)
            self.dir_list.addItem(directory)
    
    def remove_directory(self):
        # 删除选中的目录
        selected_items = self.dir_list.selectedItems()
        for item in selected_items:
            directory = item.text()
            if directory in self.selected_directories:
                self.selected_directories.remove(directory)
            self.dir_list.takeItem(self.dir_list.row(item))
    
    def get_selected_directories(self):
        return self.selected_directories

class ComponentListWidget(QTreeWidget):
    """自定义的Component树状列表，支持拖拽功能"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.setHeaderHidden(True)
        self.main_window = None
        # 设置右键菜单策略
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
    
    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window
    
    def startDrag(self, supportedActions):
        # 启动拖拽
        item = self.currentItem()
        if item:
            # 检查是否是第三层节点（component项）
            if item.parent() and item.parent().parent():
                # 从item中获取component索引
                index = item.data(0, Qt.UserRole)
                if index is not None:
                    # 创建拖拽对象
                    mime_data = QMimeData()
                    mime_data.setText(str(index))
                    
                    drag = QDrag(self)
                    drag.setMimeData(mime_data)
                    drag.exec_(Qt.CopyAction)
    
    def mousePressEvent(self, event):
        # 获取点击的项
        item = self.itemAt(event.pos())
        if item:
            # 检查是否是第三层节点（component项）
            if item.parent() and item.parent().parent():
                # 第三层正常处理
                super().mousePressEvent(event)
            else:
                # 前两层不接受任何操作
                event.ignore()
        else:
            super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        # 获取双击的项
        item = self.itemAt(event.pos())
        if item:
            # 检查是否是第三层节点（component项）
            if item.parent() and item.parent().parent():
                # 从双击的项中获取组件信息
                component_index = item.data(0, Qt.UserRole)
                # 弹出NewComponentDialog窗口
                dialog = NewComponentDialog(self, component_index)
                # 修改窗口标题为"编辑IP组件"
                dialog.setWindowTitle("编辑IP组件")
                # 从双击的项中获取组件信息
                if component_index is not None and self.main_window:
                    # 从components列表中获取组件信息
                    if 0 <= component_index < len(self.main_window.components):
                        component = self.main_window.components[component_index]
                        # 填充基本信息
                        dialog.vendor_input.setText(component.get('vendor', ''))
                        dialog.library_input.setText(component.get('library', ''))
                        dialog.name_input.setText(component.get('name', ''))
                        dialog.version_input.setText(component.get('version', ''))
                        dialog.sv_file_input.setText(component.get('sv_file', ''))
                        
                        # 填充Port信息
                        ports = component.get('ports', [])
                        dialog.fill_port_table(ports)

                        # 填充Define信息
                        defines = component.get('defines', [])
                        dialog.fill_define_table(defines)
                        
                        # 填充Parameter信息
                        parameters = component.get('parameters', [])
                        dialog.fill_parameter_table(parameters)
                        
                        # 填充BusInterface信息
                        bus_interfaces = component.get('bus_interfaces', [])
                        dialog.fill_bus_interface_table(bus_interfaces)
                        
                        # 填充PortMap信息
                        port_maps = component.get('port_maps', [])
                        dialog.fill_port_map_table(port_maps)

                if dialog.exec_() == QDialog.Accepted and dialog.edited_component_data:
                    # 更新组件数据
                    if self.main_window and 0 <= component_index < len(self.main_window.components):
                        self.main_window.components[component_index] = dialog.edited_component_data
                        # 更新节点类型
                        self.main_window.update_component_node(component_index, dialog.edited_component_data)
            else:
                # 前两层不接受任何操作
                event.ignore()
    
    def on_context_menu(self, pos):
        """右键菜单处理"""
        # 获取右键点击的项
        item = self.itemAt(pos)
        if item:
            # 检查是否是第三层节点（component项）
            if item.parent() and item.parent().parent():
                # 创建右键菜单
                menu = QMenu(self)
                
                # 编辑菜单项
                edit_action = menu.addAction("编辑")
                edit_action.triggered.connect(lambda: self.edit_component(item))
                
                # 删除菜单项
                delete_action = menu.addAction("删除")
                delete_action.triggered.connect(lambda: self.delete_component(item))
                
                # 显示菜单
                menu.exec_(self.viewport().mapToGlobal(pos))
    
    def edit_component(self, item):
        """编辑组件"""
        # 从item中获取component索引
        component_index = item.data(0, Qt.UserRole)
        if component_index is not None and self.main_window:
            # 弹出NewComponentDialog窗口
            dialog = NewComponentDialog(self, component_index)
            # 修改窗口标题为"编辑IP组件"
            dialog.setWindowTitle("编辑IP组件")
            # 从components列表中获取组件信息
            if 0 <= component_index < len(self.main_window.components):
                component = self.main_window.components[component_index]
                # 填充基本信息
                dialog.vendor_input.setText(component.get('vendor', ''))
                dialog.library_input.setText(component.get('library', ''))
                dialog.name_input.setText(component.get('name', ''))
                dialog.version_input.setText(component.get('version', ''))
                dialog.sv_file_input.setText(component.get('sv_file', ''))
                
                # 填充Port信息
                ports = component.get('ports', [])
                dialog.fill_port_table(ports)

                # 填充Define信息
                defines = component.get('defines', [])
                dialog.fill_define_table(defines)
                
                # 填充Parameter信息
                parameters = component.get('parameters', [])
                dialog.fill_parameter_table(parameters)
                
                # 填充BusInterface信息
                bus_interfaces = component.get('bus_interfaces', [])
                dialog.fill_bus_interface_table(bus_interfaces)
                
                # 填充PortMap信息
                port_maps = component.get('port_maps', [])
                dialog.fill_port_map_table(port_maps)
                
                if dialog.exec_() == QDialog.Accepted and dialog.edited_component_data:
                    # 更新组件数据
                    if 0 <= component_index < len(self.main_window.components):
                        self.main_window.components[component_index] = dialog.edited_component_data
                        # 更新节点类型
                        self.main_window.update_component_node(component_index, dialog.edited_component_data)
    
    def delete_component(self, item):
        """删除组件"""
        # 从item中获取component索引
        component_index = item.data(0, Qt.UserRole)
        if component_index is not None and self.main_window:
            # 从components列表中获取组件信息
            if 0 <= component_index < len(self.main_window.components):
                component = self.main_window.components[component_index]
                component_name = component.get('name', '未知组件')
                component_version = component.get('version', '1.0')
                
                # 确认删除
                reply = QMessageBox.question(self, "确认", f"确定要删除组件 {component_name} 吗？", 
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    # 先从components列表中删除
                    self.main_window.components.pop(component_index)
                    
                    # 从component中获取XML文件路径并删除
                    xml_file_path = component.get('xml_file_path')
                    if xml_file_path and os.path.exists(xml_file_path):
                        try:
                            os.remove(xml_file_path)
                            print(f"已删除文件: {xml_file_path}")
                        except Exception as e:
                            print(f"删除文件失败: {e}")
                    else:
                        print(f"未找到对应的XML文件路径")
                    
                    # 更新component_list（只更新UI，不重新扫描文件）
                    self.main_window.update_component_list()
                    
                    QMessageBox.information(self, "成功", f"成功删除组件: {component_name}")


class IPXactVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IP-XACT Visualizer")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建解析器和写入器实例
        self.parser = IPXactParser()
        self.writer = IPXactWriter()
        self.components = []
        
        # 日志管理
        self.log_max_lines = 500
        self.log_file_path = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "app.log")
        # 确保日志目录存在
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        
        # 创建自定义输出流，重定向print
        self.panel_output_stream = PanelOutputStream()
        self.panel_output_stream.new_output.connect(self.append_to_details_panel)
        # 保存原始stdout
        self.original_stdout = sys.stdout
        sys.stdout = self.panel_output_stream
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧component列表
        self.component_list = ComponentListWidget()
        self.component_list.set_main_window(self)
        self.component_list.setHeaderLabel("IP Library")
        self.component_list.setHeaderHidden(False)
        self.component_list.itemClicked.connect(self.on_component_selected)
        
        # 左侧project列表
        self.project_panel = QTreeWidget()
        self.project_panel.setHeaderLabel("Project ")
        self.project_panel.setHeaderHidden(False)
        self.project_panel.itemClicked.connect(self.on_project_selected)
        # 添加右键菜单
        self.project_panel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_panel.customContextMenuRequested.connect(self.on_project_context_menu)
        
        # 左侧区域
        left_layout = QVBoxLayout()
        
        # 添加创建和保存按钮
        button_layout = QHBoxLayout()
        
        # 创建Graph按钮
        self.create_graph_button = QPushButton("创建Project")
        self.create_graph_button.clicked.connect(self.create_new_graph)
        button_layout.addWidget(self.create_graph_button)
        
        # 保存Graph按钮
        self.save_graph_button = QPushButton("保存Project")
        self.save_graph_button.clicked.connect(self.save_current_graph)
        button_layout.addWidget(self.save_graph_button)
        
        left_layout.addLayout(button_layout)
        
        # 中间和右侧区域
        right_layout = QVBoxLayout()
        
        # 右侧工作区 -  创建节点图
        self.graph = CustomNodeGraph()
        # 设置节点双击回调函数
        self.graph.set_node_double_click_callback(self.on_node_double_clicked)
        # 这里通过修改连线的样式设置来提高其层级
        self.graph.set_pipe_style(1)  # 1表示ANGLE样式，同时会影响连线层级
        
        # 注册圆形节点
        self.graph.register_node(CircleNodeOut)
        self.graph.register_node(CircleNodeIn)
        
        # 设置右键菜单
        self.graph.set_context_menu_from_file('./src/hotkeys.json')
        
        # 监听连接信号
        self.graph.port_connected.connect(self.update_connections)

        # 启用连线形状的微调功能
        # 允许用户通过拖拽来调整连线的形状
        self.graph.set_pipe_slicing(True)
        
        # 为工作区添加拖拽接收功能
        # 获取NodeGraph的QGraphicsView
        view = self.graph.widget.findChild(QGraphicsView)
        if view:
            view.setAcceptDrops(True)
            # 覆盖视图的拖拽事件处理
            view.dragEnterEvent = self.on_workspace_drag_enter
            view.dropEvent = self.on_workspace_drop
        
        # 终端窗口
        self.terminal = TerminalWidget(working_dir=os.getcwd())
        self.terminal.setMinimumHeight(100)
        self.terminal.setMaximumHeight(500)
        
        # 创建QSplitter用于调整graph和terminal的大小
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.graph.widget)
        self.splitter.addWidget(self.terminal)
        # 设置初始比例（graph占大部分空间）
        self.splitter.setSizes([600, 200])
        # 设置拉伸因子
        self.splitter.setStretchFactor(0, 1)  # graph可以拉伸
        self.splitter.setStretchFactor(1, 0)  # terminal保持固定大小
        
        # 组装左侧布局
        left_layout.addWidget(self.project_panel, 0)
        left_layout.addWidget(self.component_list, 1)
        
        # 创建左侧区域容器
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(200)  # 设置最小宽度（不再限制最大宽度）
        
        # 创建主QSplitter用于调整左侧区域和右侧工作区的大小
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(left_widget)
        self.main_splitter.addWidget(self.splitter)
        # 设置初始比例
        self.main_splitter.setSizes([250, 950])
        # 设置拉伸因子 - 两侧都可以拉伸
        self.main_splitter.setStretchFactor(0, 1)  # 左侧可以拉伸
        self.main_splitter.setStretchFactor(1, 1)  # 右侧可以拉伸
        
        # 组装主布局
        main_layout.addWidget(self.main_splitter, 1)
        
        # 存储连线关系
        self.connections = []
        # 存储工作区中的component项
        self.component_items = []
        # 存储每个component的拖拽计数
        self.component_drag_count = {}
        # 存储保存的graph状态
        self.saved_graphs = []
        # 存储当前选中的project item索引
        self.current_project_index = -1
        # 存储Library库目录位置
        self.library_directory = ""
        
        # 加载配置文件
        self.load_library_config()
    
    def on_node_double_clicked(self, node):
        """处理节点双击事件，显示端口信息"""
        node_name = node.name()

        if node.name() == "Output Ports":
            return None

        # 获取节点的端口信息
        ports_info = self.get_node_ports_info(node)

        # 获取节点的parameters
        parameters = []
        if hasattr(node, 'component_data') and node.component_data:
            parameters = node.component_data.get('parameters', [])

        # 打开端口信息对话框
        dialog = PortInfoDialog(node_name, ports_info, self, self.graph, parameters)
        dialog.exec_()
    
    def get_node_ports_info(self, node):
        """获取节点的端口信息和连接关系"""
        ports_info = []
        
        # 获取所有输入端口
        for port_name, port in node.inputs().items():
            port_info = {
                'name': port_name,
                'direction': 'in',
                'type': 'input',
                'connections': []
            }
            
            # 获取连接到该输入端口的输出端口
            for connected_port in port.connected_ports():
                connected_node = connected_port.node()
                connection_text = f"{connected_node.name()}.{connected_port.name()}"
                port_info['connections'].append(connection_text)
            
            ports_info.append(port_info)
        
        # 获取所有输出端口
        for port_name, port in node.outputs().items():
            port_info = {
                'name': port_name,
                'direction': 'out',
                'type': 'output',
                'connections': []
            }
            
            # 获取连接到该输出端口的输入端口
            for connected_port in port.connected_ports():
                connected_node = connected_port.node()
                connection_text = f"{connected_node.name()}.{connected_port.name()}"
                port_info['connections'].append(connection_text)
            
            ports_info.append(port_info)
        
        return ports_info
        
    def delete_selected_nodes(self):
        """删除选中的节点"""
        selected_nodes = self.graph.selected_nodes()
        if selected_nodes:
            for node in selected_nodes:
                self.graph.delete_node(node)
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的节点")
    
    def load_library_config(self):
        """加载Library库配置"""
        try:
            config = load_config()
            if config:
                # 支持多个Library目录（新格式）
                if "library_directories" in config:
                    library_dirs = config["library_directories"]
                    if isinstance(library_dirs, list) and library_dirs:
                        self.library_directories = library_dirs
                        # 自动加载所有Library库
                        self.load_library_from_directories(library_dirs)
                # 兼容旧格式（单个目录）
                elif "library_directory" in config:
                    library_dir = config["library_directory"]
                    if os.path.exists(library_dir):
                        self.library_directories = [library_dir]
                        # 自动加载Library库
                        self.load_library_from_directories([library_dir])
                    else:
                        print(f"配置文件中的Library库目录不存在: {library_dir}")
        except Exception as e:
            print(f"加载Library库配置失败: {e}")
        
        # 加载保存的graphs
        self.load_graphs_from_files()
    
    def load_library_from_directories(self, library_dirs):
        """从多个目录加载Library库（去重）"""
        try:
            import glob
            
            # 清空现有的components列表
            self.components = []
            
            # 用于记录已加载的component（避免重复）
            loaded_components = set()
            
            # 用于记录已处理的目录（避免重复扫描）
            processed_dirs = set()
            
            # 遍历所有目录
            for library_dir in library_dirs:
                # 获取绝对路径
                abs_library_dir = os.path.abspath(library_dir)
                
                # 跳过空目录和重复目录
                if not abs_library_dir or abs_library_dir in processed_dirs:
                    continue
                
                processed_dirs.add(abs_library_dir)
                
                # 从IP子目录读取XML文件
                ip_dir = os.path.join(library_dir, "IP")
                if os.path.exists(ip_dir):
                    xml_files = glob.glob(os.path.join(ip_dir, "*.xml"))
                else:
                    # 如果IP子目录不存在，尝试从根目录读取（兼容旧版本）
                    xml_files = glob.glob(os.path.join(library_dir, "*.xml"))
                
                # 解析每个XML文件
                for xml_file in xml_files:
                    try:
                        components = self.parser.parse_file(xml_file)
                        for component in components:
                            # 记录XML文件路径（用于后续删除）
                            component['xml_file_path'] = xml_file
                            
                            # 生成唯一标识（vendor_library_name_version）
                            comp_vendor = component.get('vendor', '')
                            comp_library = component.get('library', '')
                            comp_name = component.get('name', '')
                            comp_version = component.get('version', '')
                            comp_key = f"{comp_vendor}_{comp_library}_{comp_name}_{comp_version}"
                            
                            # 检查是否已加载
                            if comp_key not in loaded_components:
                                self.components.append(component)
                                loaded_components.add(comp_key)
                            else:
                                print(f"跳过重复component: {comp_vendor}/{comp_library}/{comp_name} v{comp_version}")
                    except Exception as e:
                        print(f"解析文件 {xml_file} 时出错: {e}")
            
            # 更新component_list
            self.update_component_list()
            
        except Exception as e:
            print(f"加载Library库失败: {e}")
    
    def load_library_from_directory(self, library_dir):
        """从指定目录加载Library库（兼容旧接口）"""
        self.load_library_from_directories([library_dir])

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        # 打开文件动作
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # 保存文件动作
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 配置菜单
        config_menu = menu_bar.addMenu("配置")
        
        # Library库配置动作
        library_config_action = QAction("Library库配置", self)
        library_config_action.triggered.connect(self.open_library_config)
        config_menu.addAction(library_config_action)
        
        # 创建IP菜单
        create_ip_menu = menu_bar.addMenu("创建IP")
        
        # 新建Component动作
        new_component_action = QAction("新建Component", self)
        new_component_action.triggered.connect(self.new_component)
        create_ip_menu.addAction(new_component_action)
        
        # 新建busdef动作
        new_busdef_action = QAction("新建busdef", self)
        new_busdef_action.triggered.connect(self.new_busdef)
        create_ip_menu.addAction(new_busdef_action)
    
    def new_busdef(self):
        """新建busdef"""
        # 检查library_directory是否已经设置
        if not hasattr(self, 'library_directory') or not self.library_directory:
            QMessageBox.warning(self, "警告", "请先在Library配置中选择IP library目录")
            return
        
        # 创建新建busdef对话框，传递library目录
        dialog = NewBusDefDialog(self, library_dir=self.library_directory)
        
        # 显示对话框，保存逻辑在对话框中完成
        dialog.exec_()
    
    def new_component(self):
        """新建Component"""
        # 创建新建Component对话框
        dialog = NewComponentDialog(self)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取输入值
        component_data = dialog.get_values()
        vendor = component_data["vendor"]
        library = component_data["library"]
        name = component_data["name"]
        version = component_data["version"]
        
        # 验证输入
        if not vendor:
            QMessageBox.warning(self, "警告", "Vendor不能为空")
            return
        if not library:
            QMessageBox.warning(self, "警告", "Library不能为空")
            return
        if not name:
            QMessageBox.warning(self, "警告", "Name不能为空")
            return
        if not version:
            QMessageBox.warning(self, "警告", "Version不能为空")
            return
        
        # 生成XML文件路径，使用name_version.xml格式，保存到IP子目录
        xml_filename = f"{name}_{version}.xml"
        ip_dir = os.path.join(self.library_directory, "IP")
        os.makedirs(ip_dir, exist_ok=True)
        xml_file_path = os.path.join(ip_dir, xml_filename)
        
        # 检查文件是否已存在
        if os.path.exists(xml_file_path):
            reply = QMessageBox.question(self, "确认", f"文件 {xml_filename} 已存在，是否覆盖？", 
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        # 创建component数据
        component = component_data
        # 记录XML文件路径（用于后续删除）
        component['xml_file_path'] = xml_file_path
        
        # 添加到components列表
        self.components.append(component)
        
        # 写入到XML文件
        if self.writer.create_component_file(xml_file_path, component):
            # 更新component_list
            self.update_component_list()
            
            QMessageBox.information(self, "成功", f"成功创建Component: {name}\n文件已保存到: {xml_file_path}")
        else:
            # 如果写入失败，从components列表中移除
            self.components.remove(component)
            QMessageBox.critical(self, "错误", f"创建Component失败，无法写入文件")
    
    def update_component_list(self):
        """更新component_list"""
        # 清空component_list
        self.component_list.clear()
        
        # 构建三层结构：vendor -> library -> component
        vendor_dict = {}
        
        for i, component in enumerate(self.components):
            component_name = component.get('name', '未知组件')
            vendor = component.get('vendor', 'UnknownVendor')
            library = component.get('library', 'UnknownLibrary')
            version = component.get('version', '1.0').replace('.', '_')
            
            # 构建name_version格式的节点名称
            node_name = f"{component_name}_{version}"
            
            # 确保 vendor 和 library 键存在（提前初始化）
            if vendor not in vendor_dict:
                vendor_dict[vendor] = {}
            if library not in vendor_dict[vendor]:
                vendor_dict[vendor][library] = []
            
            try:
                # 使用type创建动态类
                node_class_name = f'{node_name}_node'
                
                # 检查节点类型是否已经注册过
                node_identifier = f"user.{node_class_name}"
                if node_identifier in self.graph.registered_nodes():
                    # 已注册，跳过
                    vendor_dict[vendor][library].append((i, component))
                    continue
                
                # 使用统一的make_template_node函数创建节点类
                DynamicComponentNode = make_template_node(None, node_name, component)
                
                # 注册节点类型
                self.graph.register_node(DynamicComponentNode)
            except Exception as e:
                print(f"注册节点类型 {component_name} 失败: {e}")
            
            # 添加到vendor_dict结构
            vendor_dict[vendor][library].append((i, component))
        
        # 添加到component_list
        for vendor_name, libraries in vendor_dict.items():
            vendor_item = QTreeWidgetItem(self.component_list)
            vendor_item.setText(0, vendor_name)
            
            for library_name, components in libraries.items():
                library_item = QTreeWidgetItem(vendor_item)
                library_item.setText(0, library_name)
                
                for i, component in components:
                    component_name = component.get('name', '未知组件')
                    version = component.get('version', '1.0')
                    component_item = QTreeWidgetItem(library_item)
                    component_item.setText(0, f"{component_name}_{version}")
                    component_item.setData(0, Qt.UserRole, i)
        
        # 默认展开所有层级
        self.component_list.expandAll()
    
    def open_file(self):
        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开IP-XACT文件", "", "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            # 检查文件是否在 library/IP 目录下
            if hasattr(self, 'library_directory') and self.library_directory:
                ip_dir = os.path.join(self.library_directory, "IP")
                # 获取文件的绝对路径
                abs_file_path = os.path.abspath(file_path)
                abs_ip_dir = os.path.abspath(ip_dir)
                
                # 检查文件是否在 IP 目录下
                if not abs_file_path.startswith(abs_ip_dir + os.sep) and abs_file_path != abs_ip_dir:
                    QMessageBox.warning(self, "警告", f"只能打开 {ip_dir} 目录下的XML文件")
                    return
            
            try:
                #print(f"打开文件: {file_path}")
                # 解析IP-XACT文件
                self.components = self.parser.parse_file(file_path)
                
                # 清空列表并添加component
                self.component_list.clear()
                
                # 构建三层结构：vendor -> library -> component
                vendor_dict = {}
                
                for i, component in enumerate(self.components):
                    component_name = component.get('name', '未知组件')
                    vendor = component.get('vendor', 'UnknownVendor')
                    library = component.get('library', 'UnknownLibrary')
                    version = component.get('version', '1.0').replace('.', '_')
                    
                    # 构建vendor -> library -> component结构
                    if vendor not in vendor_dict:
                        vendor_dict[vendor] = {}
                    
                    if library not in vendor_dict[vendor]:
                        vendor_dict[vendor][library] = []
                    
                    vendor_dict[vendor][library].append((i, component))
                    
                    try:
                        # 检查节点类型是否已经注册过
                        node_identifier = f"user.{component_name}_{version}_node"
                        if node_identifier not in self.graph.registered_nodes():
                            TemplateClass = make_template_node(None, f"{component_name}_{version}", node_data=component)
                            # 注册节点类型
                            self.graph.register_node(TemplateClass)
                    except Exception as e:
                        print(f"注册节点失败: {e}")
                
                # 添加到component_list
                for vendor_name, libraries in vendor_dict.items():
                    vendor_item = QTreeWidgetItem(self.component_list)
                    vendor_item.setText(0, vendor_name)
                    
                    for library_name, components in libraries.items():
                        library_item = QTreeWidgetItem(vendor_item)
                        library_item.setText(0, library_name)
                        
                        for i, component in components:
                            component_name = component.get('name', '未知组件')
                            version = component.get('version', '1.0')
                            component_item = QTreeWidgetItem(library_item)
                            component_item.setText(0, f"{component_name}_{version}")
                            component_item.setData(0, Qt.UserRole, i)
                
                # 默认展开所有层级
                self.component_list.expandAll()
                
            except Exception as e:
                # 显示错误消息
                QMessageBox.critical(self, "错误", f"解析文件时出错: {str(e)}")
    
    def on_component_selected(self, item, column):
        # 获取选中的项索引
        index = item.data(0, Qt.UserRole)
        
        # 检查是component项还是保存的graph项
        # 通过检查index是否在components范围内来判断
        if 0 <= index < len(self.components):
            # 是component项 - 不再显示详细信息到details_panel
            # 保持选中状态供后续拖拽使用
            pass
    
    def on_project_selected(self, item, column):
        # 获取选中的项索引
        index = item.data(0, Qt.UserRole)
        
        # 检查是否是第三层节点（module项）
        if not (item.parent() and item.parent().parent()):
            # 前两层不响应点击
            return
        
        # 检查索引是否有效
        if index is None or index < 0 or index >= len(self.saved_graphs):
            return
        
        # 更新当前选中的project索引
        self.current_project_index = index
        
        # 加载对应的graph数据
        graph_name, graph_data = self.saved_graphs[index]
        try:
            # 清除当前graph内容
            self.graph.clear_session()
            
            # 清空component_drag_count
            self.component_drag_count = {}
            
            # 反序列化并加载保存的graph状态
            if graph_data:
                # 从graph_data中提取component_drag_count
                if 'component_drag_count' in graph_data:
                    self.component_drag_count = graph_data['component_drag_count']

                self.graph.deserialize_session(graph_data)

            # 恢复节点的component_data
            nodes_component_data = graph_data.get('nodes_component_data', {})
            for node in self.graph.all_nodes():
                node_name = node.name()
                if node_name in nodes_component_data:
                    node.component_data = nodes_component_data[node_name].get('component_data')
            
            # 恢复节点位置信息
            node_positions = graph_data.get('node_positions', {})
            if not self.graph.all_nodes():
                QMessageBox.information(self, "提示", f"加载空graph: {graph_name}")
            else:
                for node in self.graph.all_nodes():
                    node_name = node.name()
                    if node_name in node_positions and hasattr(node, 'set_pos'):
                        pos = node_positions[node_name]
                        node.set_pos(pos['x'], pos['y'])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载graph时出错: {str(e)}")
    
    def on_project_context_menu(self, position):
        """处理project_panel的右键菜单"""
        # 获取当前选中的项
        item = self.project_panel.itemAt(position)
        if not item:
            return
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 检查是否是第三层节点（module项）
        if item.parent() and item.parent().parent():
            # 第三层节点：编辑和删除
            edit_action = menu.addAction("编辑")
            delete_action = menu.addAction("删除")
            
            # 连接信号
            edit_action.triggered.connect(lambda: self.edit_project_item(item))
            delete_action.triggered.connect(lambda: self.delete_project_item(item))
        # 检查是否是第二层节点（project项）
        elif item.parent() and not item.parent().parent():
            # 第二层节点：删除（会删除所有子项）
            delete_action = menu.addAction("删除")
            delete_action.triggered.connect(lambda: self.delete_project_item(item))
        
        # 显示菜单
        menu.exec_(self.project_panel.mapToGlobal(position))
    
    def edit_project_item(self, item):
        """编辑project项"""
        # 检查是否是第三层节点（module项）
        if not (item.parent() and item.parent().parent()):
            return
        
        # 获取索引
        index = item.data(0, Qt.UserRole)
        if index is None or index < 0 or index >= len(self.saved_graphs):
            return
        
        # 获取当前graph数据
        graph_name, graph_data = self.saved_graphs[index]
        
        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑Project")
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # 项目名称
        project_name_layout = QHBoxLayout()
        project_name_label = QLabel("项目名称:")
        project_name_input = QLineEdit()
        project_name_input.setText(graph_data.get('project_name', 'UnknownProject') if graph_data else 'UnknownProject')
        project_name_layout.addWidget(project_name_label)
        project_name_layout.addWidget(project_name_input)
        layout.addLayout(project_name_layout)
        
        # 模块名称
        module_name_layout = QHBoxLayout()
        module_name_label = QLabel("模块名称:")
        module_name_input = QLineEdit()
        module_name_input.setText(graph_data.get('module_name', 'UnknownModule') if graph_data else 'UnknownModule')
        module_name_layout.addWidget(module_name_label)
        module_name_layout.addWidget(module_name_input)
        layout.addLayout(module_name_layout)
        
        # 版本号
        version_layout = QHBoxLayout()
        version_label = QLabel("版本号:")
        version_input = QLineEdit()
        version_input.setText(graph_data.get('version', '1.0') if graph_data else '1.0')
        version_layout.addWidget(version_label)
        version_layout.addWidget(version_input)
        layout.addLayout(version_layout)
        
        # Verilog文件路径
        verilog_layout = QHBoxLayout()
        verilog_label = QLabel("Verilog文件:")
        verilog_input = QLineEdit()
        verilog_input.setText(graph_data.get('verilog_file', '') if graph_data else '')
        verilog_input.setPlaceholderText("选择或新建Verilog文件")
        verilog_button = QPushButton("浏览...")
        verilog_layout.addWidget(verilog_label)
        verilog_layout.addWidget(verilog_input)
        verilog_layout.addWidget(verilog_button)
        layout.addLayout(verilog_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        verilog_button.clicked.connect(lambda: self.browse_verilog_file(verilog_input))
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取输入值
        new_project_name = project_name_input.text().strip()
        new_module_name = module_name_input.text().strip()
        new_version = version_input.text().strip()
        new_verilog_file = verilog_input.text().strip()
        
        # 验证输入
        if not new_project_name:
            QMessageBox.warning(self, "警告", "项目名称不能为空")
            return
        if not new_module_name:
            QMessageBox.warning(self, "警告", "模块名称不能为空")
            return
        if not new_version:
            QMessageBox.warning(self, "警告", "版本号不能为空")
            return
        
        # 构建新的模块名称
        new_full_module_name = f"{new_module_name}_{new_version}"
        
        # 更新graph_data
        if not graph_data:
            graph_data = {}
        
        graph_data['project_name'] = new_project_name
        graph_data['module_name'] = new_module_name
        graph_data['version'] = new_version
        graph_data['verilog_file'] = new_verilog_file
        
        # 更新saved_graphs
        self.saved_graphs[index] = (new_full_module_name, graph_data)
        
        # 更新project_panel
        # 找到旧的project项
        old_project_item = item.parent()
        old_project_name = old_project_item.text(0)
        
        # 如果项目名称改变，需要重新组织层次结构
        if new_project_name != old_project_name:
            # 查找或创建新的project项
            vendor_item = old_project_item.parent()
            new_project_item = None
            
            for i in range(vendor_item.childCount()):
                child_item = vendor_item.child(i)
                if child_item.text(0) == new_project_name:
                    new_project_item = child_item
                    break
            
            if not new_project_item:
                new_project_item = QTreeWidgetItem(vendor_item)
                new_project_item.setText(0, new_project_name)
            
            # 移动item到新的project项
            new_project_item.addChild(item)
            old_project_item.removeChild(item)
            
            # 如果old_project_item为空，删除它
            if old_project_item.childCount() == 0:
                vendor_item.removeChild(old_project_item)
        
        # 更新item的文本
        item.setText(0, new_full_module_name)
        
        # 保存到文件
        self.save_graph_to_file(new_full_module_name, graph_data)
        
        # 展开所有层级
        self.project_panel.expandAll()
        
        QMessageBox.information(self, "成功", f"成功编辑project: {new_full_module_name}")
    
    def delete_project_item(self, item):
        """删除project项"""
        # 检查是否是第三层节点（module项）
        if item.parent() and item.parent().parent():
            # 第三层节点：单个module
            index = item.data(0, Qt.UserRole)
            if index is None or index < 0 or index >= len(self.saved_graphs):
                return
            
            # 确认删除
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                f"确定要删除 {item.text(0)} 吗？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 从saved_graphs中删除
            graph_name, graph_data = self.saved_graphs[index]
            self.saved_graphs.pop(index)
            
            # 删除对应的文件
            projects_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "projects")
            safe_name = graph_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            file_path = os.path.join(projects_dir, f"{safe_name}.json")
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"删除文件失败: {e}")
            
            # 从project_panel中删除
            project_item = item.parent()
            project_item.removeChild(item)
            
            # 如果project_item为空，删除它
            if project_item.childCount() == 0:
                vendor_item = project_item.parent()
                vendor_item.removeChild(project_item)
            
            # 更新其他项的索引
            for i in range(len(self.saved_graphs)):
                # 找到对应的item
                for j in range(self.project_panel.topLevelItemCount()):
                    vendor_item = self.project_panel.topLevelItem(j)
                    for k in range(vendor_item.childCount()):
                        proj_item = vendor_item.child(k)
                        for l in range(proj_item.childCount()):
                            mod_item = proj_item.child(l)
                            item_index = mod_item.data(0, Qt.UserRole)
                            if item_index is not None and item_index > index:
                                mod_item.setData(0, Qt.UserRole, item_index - 1)
            
            # 重置当前选中的索引
            if self.current_project_index >= index:
                self.current_project_index = min(self.current_project_index - 1, len(self.saved_graphs) - 1)
                if self.current_project_index < 0:
                    self.current_project_index = -1
            
            QMessageBox.information(self, "成功", f"成功删除project: {graph_name}")
        # 检查是否是第二层节点（project项）
        elif item.parent() and not item.parent().parent():
            # 第二层节点：整个project，包括所有子项
            project_name = item.text(0)
            child_count = item.childCount()
            
            # 确认删除
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                f"确定要删除项目 {project_name} 及其所有 {child_count} 个子项吗？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 收集所有要删除的项的索引
            indices_to_delete = []
            for i in range(item.childCount()):
                child_item = item.child(i)
                index = child_item.data(0, Qt.UserRole)
                if index is not None and 0 <= index < len(self.saved_graphs):
                    indices_to_delete.append(index)
            
            # 按降序删除，避免索引偏移
            for index in sorted(indices_to_delete, reverse=True):
                # 从saved_graphs中删除
                graph_name, graph_data = self.saved_graphs[index]
                self.saved_graphs.pop(index)
                
                # 删除对应的文件
                projects_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "projects")
                safe_name = graph_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                file_path = os.path.join(projects_dir, f"{safe_name}.json")
                
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"删除文件失败: {e}")
            
            # 从project_panel中删除
            vendor_item = item.parent()
            vendor_item.removeChild(item)
            
            # 更新其他项的索引
            for i in range(len(self.saved_graphs)):
                # 找到对应的item
                for j in range(self.project_panel.topLevelItemCount()):
                    vendor_item = self.project_panel.topLevelItem(j)
                    for k in range(vendor_item.childCount()):
                        proj_item = vendor_item.child(k)
                        for l in range(proj_item.childCount()):
                            mod_item = proj_item.child(l)
                            item_index = mod_item.data(0, Qt.UserRole)
                            if item_index is not None:
                                # 调整索引
                                new_index = item_index
                                for index in indices_to_delete:
                                    if item_index > index:
                                        new_index -= 1
                                mod_item.setData(0, Qt.UserRole, new_index)
            
            # 重置当前选中的索引
            if self.current_project_index >= 0:
                # 检查当前索引是否在删除的范围内
                for index in indices_to_delete:
                    if self.current_project_index == index:
                        self.current_project_index = -1
                        break
                else:
                    # 调整索引
                    new_index = self.current_project_index
                    for index in indices_to_delete:
                        if new_index > index:
                            new_index -= 1
                    self.current_project_index = new_index
            
            QMessageBox.information(self, "成功", f"成功删除项目: {project_name} 及其所有子项")
    
    def add_component_to_workspace(self, component_index, pos):
        # 检查是否有选中的project
        if self.current_project_index == -1:
            QMessageBox.warning(self, "警告", "请先在Project面板中选择一个Project")
            return
        
        # 将component添加到工作区
        if 0 <= component_index < len(self.components):
            component = self.components[component_index]
            component_name = component.get('name', 'Unknown Component')
            version = component.get('version', '1.0').replace('.', '_')
            
            # 构建name_version格式的节点名称
            node_name = f"{component_name}_{version}"
            node_class_name = f"{node_name}_node"
            
            try:
                node_identifier = f"user.{node_class_name}"
                if node_identifier not in self.graph.registered_nodes():
                    DynamicComponentNode = make_template_node(None, node_name, component)
                    self.graph.register_node(DynamicComponentNode)
            except Exception as e:
                print(f"注册节点类型 {component_name} 失败: {e}")
            
            # 更新拖拽计数
            if node_name not in self.component_drag_count:
                self.component_drag_count[node_name] = 0
            
            # 生成唯一的节点名称
            unique_name = f"u_{component_name}_v{version}_{self.component_drag_count[node_name]}"
            
            # 显示添加消息（使用print，会自动追加到details_panel）
            print(f"添加component: {unique_name} 到工作区")
            
            # 从0开始计数
            self.component_drag_count[node_name] += 1

            # 使用正确的节点类型标识符创建节点
            # 格式：{__identifier__}.{NODE_NAME}
            
            node = self.graph.create_node(
                f'user.{node_name}_node',
                name=unique_name,
                pos=pos
            )
            self.component_items.append(node)
    
    def update_component_node(self, component_index, component_data):
        """更新工作区中指定component的节点"""
        if 0 <= component_index < len(self.components):
            component_name = component_data.get('name', 'Unknown Component')
            version = component_data.get('version', '1.0').replace('.', '_')
            node_name = f"{component_name}_{version}"
            node_class_name = f"{node_name}_node"

            try:
                node_identifier = f"user.{node_class_name}"
                if node_identifier not in self.graph.registered_nodes():
                    DynamicComponentNode = make_template_node(None, node_name, component_data)
                    self.graph.register_node(DynamicComponentNode)
            except Exception as e:
                print(f"注册节点类型 {component_name} 失败: {e}")

            # 更新工作区中的节点（遍历self.graph.all_nodes()以包含加载的节点）
            for node in self.graph.all_nodes():
                if hasattr(node, 'component_data'):
                    node_component_name = node.component_data.get('name', '')
                    node_component_version = node.component_data.get('version', '1.0')
                    if node_component_name == component_name and node_component_version == component_data.get('version', '1.0'):
                        node.component_data = component_data

            # 检查所有saved_graphs中是否有使用该组件且数据不一致的情况
            self._check_and_warn_outdated_graphs(component_name, component_data.get('version', '1.0'), component_data)
        else:
            print(f"无效的component索引: {component_index}")

    def _check_and_warn_outdated_graphs(self, component_name, component_version, latest_component_data):
        """检查所有saved_graphs中是否有使用该组件且数据不一致的graph"""
        outdated_graphs = []

        for graph_name, graph_data in self.saved_graphs:
            nodes_component_data = graph_data.get('nodes_component_data', {})

            # 检查是否有使用该组件的节点
            for node_name, node_info in nodes_component_data.items():
                node_component = node_info.get('component_data', {})
                if node_component.get('name') == component_name and node_component.get('version') == component_version:
                    # 比较 bus_interfaces 数据
                    if not self._compare_bus_interfaces(node_component.get('bus_interfaces', []), latest_component_data.get('bus_interfaces', [])):
                        outdated_graphs.append(graph_name)
                        break
                    # 比较 port_maps 数据
                    if not self._compare_port_maps(node_component.get('port_maps', []), latest_component_data.get('port_maps', [])):
                        if graph_name not in outdated_graphs:
                            outdated_graphs.append(graph_name)
                        break

        if outdated_graphs:
            outdated_list = "\n".join(f"- {name}" for name in outdated_graphs)
            QMessageBox.warning(
                self,
                "警告",
                f"组件 '{component_name}' 的数据已更新，以下保存的graph使用了旧数据：\n{outdated_list}\n\n"
                f"请重新打开这些graph以加载最新数据，或手动更新。"
            )

    def _compare_bus_interfaces(self, old_bus_if, new_bus_if):
        """比较bus_interfaces数据是否一致"""
        if len(old_bus_if) != len(new_bus_if):
            return False

        for old, new in zip(old_bus_if, new_bus_if):
            if old.get('name') != new.get('name'):
                return False
            if old.get('bus_type') != new.get('bus_type'):
                return False
            if old.get('mode') != new.get('mode'):
                return False
            # 比较 port_maps
            if not self._compare_port_maps(old.get('port_maps', []), new.get('port_maps', [])):
                return False

        return True

    def _compare_port_maps(self, old_pm, new_pm):
        """比较port_maps数据是否一致"""
        if len(old_pm) != len(new_pm):
            return False

        for old, new in zip(old_pm, new_pm):
            if old.get('logical_port') != new.get('logical_port'):
                return False
            if old.get('physical_port') != new.get('physical_port'):
                return False

        return True
    
    def on_workspace_drag_enter(self, event):
        if self.project_panel.currentItem() is None:
            return
        # 处理拖拽进入事件
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def on_workspace_drop(self, event):
        # 处理拖拽放置事件
        if event.mimeData().hasText():
            try:
                # 获取拖拽的component索引
                component_index = int(event.mimeData().text())
                # 获取鼠标在工作区中的位置（视图坐标）
                view_pos = event.pos()
                # 将视图坐标转换为场景坐标
                scene_pos = self.graph.widget.findChild(QGraphicsView).mapToScene(view_pos)
                # 添加component到工作区
                self.add_component_to_workspace(component_index, (scene_pos.x(), scene_pos.y()))
            except ValueError:
                pass
    
    def update_connections(self, input_port, output_port):
        # 更新连线关系列表
        src_node = output_port.node().name()
        dst_node = input_port.node().name()
        src_port_name = output_port.name()
        dst_port_name = input_port.name()

        # 进行位宽验证
        src_node_obj = None
        dst_node_obj = None
        for node in self.graph.all_nodes():
            if node.name() == src_node:
                src_node_obj = node
            if node.name() == dst_node:
                dst_node_obj = node

        if src_node_obj and dst_node_obj:
            # 调用验证方法（source是output_port，target是input_port）
            valid, error_msg = self.validate_port_connection(
                src_node_obj, src_port_name,
                dst_node_obj, dst_port_name
            )

            if not valid:
                # 验证失败，断开连接
                output_port.disconnect_from(input_port)
                QMessageBox.warning(self, "位宽验证失败", error_msg)

    def get_node_component_data(self, node):
        """获取节点的 component_data"""
        if hasattr(node, 'component_data') and node.component_data:
            return node.component_data
        elif hasattr(node, 'node_data') and node.node_data:
            return node.node_data
        return {}

    def get_port_width(self, node, port_name):
        """获取端口的位宽"""
        component_data = self.get_node_component_data(node)
        ports = component_data.get('ports', [])

        for port in ports:
            if port.get('name') == port_name:
                width = port.get('width', 1)
                if isinstance(width, str):
                    try:
                        return eval(width) if width else 1
                    except:
                        return 1
                return int(width) if width else 1
        return 1

    def is_bus_interface_port(self, node, port_name):
        """判断端口是否是 bus interface 端口"""
        component_data = self.get_node_component_data(node)
        bus_interfaces = component_data.get('bus_interfaces', [])

        if not bus_interfaces:
            return (False, None)

        for bus_if in bus_interfaces:
            bus_if_name = bus_if.get('name', '')
            if bus_if_name == port_name or f"bus_{bus_if_name}" == port_name:
                return (True, bus_if_name)

        return (False, None)

    def get_bus_interface_signals(self, node, bus_if_name):
        """获取 bus interface 内部的信号及其位宽映射"""
        component_data = self.get_node_component_data(node)
        bus_interfaces = component_data.get('bus_interfaces', [])
        ports = component_data.get('ports', [])

        port_width_map = {}
        for port in ports:
            port_name = port.get('name', '')
            width = port.get('width', 1)
            if isinstance(width, str):
                try:
                    width = eval(width) if width else 1
                except:
                    width = 1
            port_width_map[port_name] = int(width) if width else 1

        signal_widths = {}
        for bus_if in bus_interfaces:
            if bus_if.get('name') == bus_if_name:
                port_maps = bus_if.get('port_maps', [])
                for pm in port_maps:
                    logical_port = pm.get('logical_port', '')
                    physical_port = pm.get('physical_port', '')
                    if logical_port and physical_port and physical_port in port_width_map:
                        signal_widths[logical_port] = port_width_map[physical_port]
                    elif logical_port:
                        signal_widths[logical_port] = 1
        return signal_widths

    def get_bus_interface_type(self, node, bus_if_name):
        """获取 bus interface 的 bus_type"""
        component_data = self.get_node_component_data(node)
        bus_interfaces = component_data.get('bus_interfaces', [])

        for bus_if in bus_interfaces:
            if bus_if.get('name') == bus_if_name:
                return bus_if.get('bus_type', '')

        return ''

    def validate_port_connection(self, source_node, source_port_name, target_node, target_port_name):
        """
        验证两个端口的位宽是否匹配
        Returns: (bool, str) - (是否有效, 错误信息)
        """
        source_is_bus, source_bus_name = self.is_bus_interface_port(source_node, source_port_name)
        target_is_bus, target_bus_name = self.is_bus_interface_port(target_node, target_port_name)

        if source_is_bus and target_is_bus:
            source_bus_type = self.get_bus_interface_type(source_node, source_bus_name)
            target_bus_type = self.get_bus_interface_type(target_node, target_bus_name)

            if source_bus_type != target_bus_type:
                return (False, f"bus type 不匹配: {source_bus_type} vs {target_bus_type}")

            source_signals = self.get_bus_interface_signals(source_node, source_bus_name)
            target_signals = self.get_bus_interface_signals(target_node, target_bus_name)

            if set(source_signals.keys()) != set(target_signals.keys()):
                missing_in_source = set(target_signals.keys()) - set(source_signals.keys())
                missing_in_target = set(source_signals.keys()) - set(target_signals.keys())
                error_msg = "bus interface 内部信号名称不匹配"
                if missing_in_source:
                    error_msg += f"\n目标有但源缺少的信号: {missing_in_source}"
                if missing_in_target:
                    error_msg += f"\n源有但目标缺少的信号: {missing_in_target}"
                return (False, error_msg)

            for signalName in source_signals:
                src_width = source_signals.get(signalName, 0)
                tgt_width = target_signals.get(signalName, 0)
                if src_width != tgt_width:
                    return (False, f"信号 '{signalName}' 位宽不匹配: 源 {src_width} 位 vs 目标 {tgt_width} 位")

            return (True, "")

        elif source_is_bus or target_is_bus:
            bus_node = source_node if source_is_bus else target_node
            bus_port_name = source_port_name if source_is_bus else target_port_name
            normal_node = target_node if source_is_bus else source_node
            normal_port_name = target_port_name if source_is_bus else source_port_name

            bus_if_name = bus_port_name
            if bus_if_name.startswith('bus_'):
                bus_if_name = bus_if_name[4:]

            bus_signals = self.get_bus_interface_signals(bus_node, bus_if_name)

            if not bus_signals:
                return (True, "")

            if len(bus_signals) > 1:
                return (False, f"bus interface 包含多个信号 ({list(bus_signals.keys())})，无法直接连接到单个端口")

            signal_name = list(bus_signals.keys())[0]
            bus_width = bus_signals[signal_name]
            normal_width = self.get_port_width(normal_node, normal_port_name)

            if bus_width != normal_width:
                return (False, f"位宽不匹配: bus interface 信号 '{signal_name}' 宽度 {bus_width} 位 vs 端口 '{normal_port_name}' 宽度 {normal_width} 位")

            return (True, "")

        else:
            source_width = self.get_port_width(source_node, source_port_name)
            target_width = self.get_port_width(target_node, target_port_name)

            if source_width != target_width:
                return (False, f"位宽不匹配: 源端口 '{source_port_name}' 宽度 {source_width} 位 vs 目标端口 '{target_port_name}' 宽度 {target_width} 位")

            return (True, "")
    
    def open_library_config(self):
        # 打开Library库配置对话框
        # 获取当前的library目录列表（兼容旧格式）
        current_dirs = getattr(self, 'library_directories', [])
        if not current_dirs and hasattr(self, 'library_directory') and self.library_directory:
            current_dirs = [self.library_directory]
        
        dialog = LibraryConfigDialog(self, current_dirs)
        if dialog.exec_() == QDialog.Accepted:
            # 获取选定的目录列表
            library_dirs = dialog.get_selected_directories()
            if library_dirs:
                # 存储选定的库目录位置
                self.library_directories = library_dirs
                
                # 保存配置到文件（使用新格式）
                config = {"library_directories": library_dirs}
                if save_config(config):
                    print(f"配置已保存到: {get_config_path()}")
                else:
                    print("保存配置失败")
                
                # 加载所有Library库
                self.load_library_from_directories(library_dirs)

    def save_file(self):
        graph_name, graph_data = self.saved_graphs[self.current_project_index]
        # 保存文件对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存IP-XACT文件", graph_name, "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            try:
                
                # 获取当前graph上的所有连接关系
                connections = get_all_connections(self.graph)
                
                # 写回IP-XACT文件
                success = self.writer.write_file(file_path, graph_name, connections)
                if success:
                    QMessageBox.information(self, "成功", f"成功保存文件: {file_path}")
                else:
                    QMessageBox.warning(self, "警告", "保存文件失败，请检查日志")
            except Exception as e:
                # 显示错误消息
                QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")
    
    def browse_verilog_file(self, line_edit):
        """浏览并选择Verilog文件"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        
        # 打开文件对话框，允许选择或新建文件
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "选择或新建Verilog文件",
            "",
            "Verilog Files (*.v);;All Files (*)",
            options=options
        )
        
        if file_path:
            line_edit.setText(file_path)
    
    def create_new_graph(self):
        # 在project_panel中创建一个新的Graph item
        try:
            # 创建自定义对话框让用户输入项目信息
            dialog = QDialog(self)
            dialog.setWindowTitle("创建Project")
            dialog.resize(400, 200)
            
            layout = QVBoxLayout(dialog)
            
            # 项目名称
            project_name_layout = QHBoxLayout()
            project_name_label = QLabel("项目名称:")
            project_name_input = QLineEdit()
            project_name_input.setText(f"Project {len(self.saved_graphs) + 1}")
            project_name_layout.addWidget(project_name_label)
            project_name_layout.addWidget(project_name_input)
            layout.addLayout(project_name_layout)
            
            # 模块名称
            module_name_layout = QHBoxLayout()
            module_name_label = QLabel("模块名称:")
            module_name_input = QLineEdit()
            module_name_input.setText(f"Module {len(self.saved_graphs) + 1}")
            module_name_layout.addWidget(module_name_label)
            module_name_layout.addWidget(module_name_input)
            layout.addLayout(module_name_layout)
            
            # 版本号
            version_layout = QHBoxLayout()
            version_label = QLabel("版本号:")
            version_input = QLineEdit()
            version_input.setText("1.0")
            version_layout.addWidget(version_label)
            version_layout.addWidget(version_input)
            layout.addLayout(version_layout)
            
            # Verilog文件路径
            verilog_layout = QHBoxLayout()
            verilog_label = QLabel("Verilog文件:")
            verilog_input = QLineEdit()
            verilog_input.setPlaceholderText("选择或新建Verilog文件")
            verilog_button = QPushButton("浏览...")
            verilog_layout.addWidget(verilog_label)
            verilog_layout.addWidget(verilog_input)
            verilog_layout.addWidget(verilog_button)
            layout.addLayout(verilog_layout)
            
            # 按钮
            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # 连接信号
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            verilog_button.clicked.connect(lambda: self.browse_verilog_file(verilog_input))
            
            if dialog.exec_() != QDialog.Accepted:
                return
            
            # 获取输入值
            project_name = project_name_input.text().strip()
            module_name = module_name_input.text().strip()
            version = version_input.text().strip()
            verilog_file = verilog_input.text().strip()
            
            # 验证输入
            if not project_name:
                QMessageBox.warning(self, "警告", "项目名称不能为空")
                return
            if not module_name:
                QMessageBox.warning(self, "警告", "模块名称不能为空")
                return
            if not version:
                QMessageBox.warning(self, "警告", "版本号不能为空")
                return
            
            # 构建完整的模块名称
            full_module_name = f"{module_name}_{version}"
            
            # 检查是否已存在相同的三层结构
            existing_paths = []
            for i in range(self.project_panel.topLevelItemCount()):
                vendor_item = self.project_panel.topLevelItem(i)
                vendor_name = vendor_item.text(0)
                
                for j in range(vendor_item.childCount()):
                    project_item = vendor_item.child(j)
                    project_item_name = project_item.text(0)
                    
                    for k in range(project_item.childCount()):
                        module_item = project_item.child(k)
                        module_item_name = module_item.text(0)
                        existing_paths.append(f"{vendor_name}/{project_item_name}/{module_item_name}")
            
            new_path = f"Phytium/{project_name}/{full_module_name}"
            if new_path in existing_paths:
                QMessageBox.warning(self, "警告", f"相同的项目结构已存在: {new_path}")
                return
            
            # 存储graph状态
            graph_data = {
                'project_name': project_name,
                'module_name': module_name,
                'version': version,
                'verilog_file': verilog_file,
                'components': [],
                'connections': []
            }
            self.saved_graphs.append((full_module_name, graph_data))
            
            # 按照三层结构添加到project_panel
            # 查找或创建vendor项 (Phytium)
            vendor_item = None
            for i in range(self.project_panel.topLevelItemCount()):
                item = self.project_panel.topLevelItem(i)
                if item.text(0) == "Phytium":
                    vendor_item = item
                    break
            
            if not vendor_item:
                vendor_item = QTreeWidgetItem(self.project_panel)
                vendor_item.setText(0, "Phytium")
            
            # 查找或创建project项
            project_item = None
            for i in range(vendor_item.childCount()):
                item = vendor_item.child(i)
                if item.text(0) == project_name:
                    project_item = item
                    break
            
            if not project_item:
                project_item = QTreeWidgetItem(vendor_item)
                project_item.setText(0, project_name)
            
            # 创建module项
            module_item = QTreeWidgetItem(project_item)
            module_item.setText(0, full_module_name)
            module_item.setData(0, Qt.UserRole, len(self.saved_graphs) - 1)  # 存储索引
            
            # 展开所有层级
            self.project_panel.expandAll()
            
            # 选中新创建的项
            self.project_panel.setCurrentItem(module_item)
            self.current_project_index = len(self.saved_graphs) - 1
            
            QMessageBox.information(self, "成功", f"成功创建graph: {full_module_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建graph时出错: {str(e)}")
    
    def save_current_graph(self):
        # 保存当前graph的内容到选中的item中
        try:
            if self.current_project_index == -1:
                QMessageBox.warning(self, "警告", "请先在Project面板中选择一个Graph项")
                return
            
            # 序列化当前graph状态
            graph_data = self.graph.serialize_session()

            # 将component_drag_count添加到graph_data中
            graph_data['component_drag_count'] = self.component_drag_count

            # 收集所有节点的component_data
            nodes_component_data = {}
            for node in self.graph.all_nodes():
                if hasattr(node, 'component_data') and node.component_data:
                    node_name = node.name()
                    node_type = node.__class__.__name__
                    component_data = node.component_data

                    # 如果节点的component_data缺少bus_interfaces或port_maps，从self.components获取最新数据
                    if not component_data.get('bus_interfaces'):
                        node_type_base = node_type[5:-5] if node_type.startswith('user.') and node_type.endswith('_node') else ''
                        if node_type_base:
                            parts = node_type_base.rsplit('_', 1)
                            if len(parts) == 2:
                                comp_name = parts[0]
                                version = parts[1].replace('_', '.')
                                for comp in self.components:
                                    if comp.get('name') == comp_name and comp.get('version') == version:
                                        component_data = comp
                                        break

                    nodes_component_data[node_name] = {
                        'component_data': component_data,
                        'node_type': node_type
                    }
            graph_data['nodes_component_data'] = nodes_component_data
            
            # 更新存储的graph状态
            graph_name = self.saved_graphs[self.current_project_index][0]
            original_graph_data = self.saved_graphs[self.current_project_index][1]
            
            # 保留原始的项目信息
            if original_graph_data:
                graph_data['project_name'] = original_graph_data.get('project_name', 'UnknownProject')
                graph_data['module_name'] = original_graph_data.get('module_name', 'UnknownModule')
                graph_data['version'] = original_graph_data.get('version', '1.0')
                graph_data['verilog_file'] = original_graph_data.get('verilog_file', '')
            else:
                # 如果原始数据为None，尝试从项目面板获取信息
                current_item = self.project_panel.currentItem()
                if current_item and current_item.parent() and current_item.parent().parent():
                    # 从项目面板的层次结构中获取信息
                    project_item = current_item.parent()
                    vendor_item = project_item.parent()
                    
                    graph_data['project_name'] = project_item.text(0)
                    graph_data['module_name'] = current_item.text(0).split('_')[0]  # 从模块名称中提取
                    graph_data['version'] = current_item.text(0).split('_')[1] if len(current_item.text(0).split('_')) > 1 else '1.0'
                    graph_data['verilog_file'] = ''
                else:
                    # 使用默认值
                    graph_data['project_name'] = 'UnknownProject'
                    graph_data['module_name'] = 'UnknownModule'
                    graph_data['version'] = '1.0'
                    graph_data['verilog_file'] = ''
            
            self.saved_graphs[self.current_project_index] = (graph_name, graph_data)
            
            # 获取verilog_file路径
            verilog_file = graph_data.get('verilog_file', '')
            
            # 保存graph数据到本地文件（IP-XACT XML格式）
            # 如果指定了verilog_file，会同时在Verilog目录生成一份XML
            self.save_graph_to_file(graph_name, graph_data, verilog_file=verilog_file)
            
            # 生成Verilog代码到指定文件（如果指定了verilog_file）
            if verilog_file:
                self.generate_verilog_code(verilog_file, graph_data)
            
            QMessageBox.information(self, "成功", f"成功保存graph: {graph_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存graph时出错: {str(e)}")
    
    def save_graph_to_file(self, graph_name, graph_data, custom_path=None, verilog_file=None):
        """将graph数据保存到本地XML文件（IP-XACT格式）
        
        Args:
            graph_name: graph名称（用于生成默认文件名）
            graph_data: 完整的graph数据
            custom_path: 可选的自定义输出路径，如果提供则使用该路径
            verilog_file: 可选的Verilog文件路径，如果提供则同时在该目录生成XML文件
        """
        try:
            # 确定输出文件路径
            if custom_path:
                # 使用自定义路径（用于与Verilog文件同目录）
                file_path = custom_path
            else:
                # 默认路径：~/.config/ipxact_visualizer/projects/
                projects_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "projects")
                if not os.path.exists(projects_dir):
                    os.makedirs(projects_dir)
                safe_name = graph_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                file_path = os.path.join(projects_dir, f"{safe_name}.xml")
            
            # 如果指定了verilog_file，还需要在Verilog目录生成一份XML
            verilog_xml_path = None
            if verilog_file:
                verilog_xml_path = os.path.splitext(verilog_file)[0] + '.xml'
            
            # 收集节点位置信息
            node_positions = {}
            try:
                if hasattr(self.graph, 'all_nodes'):
                    for node in self.graph.all_nodes():
                        try:
                            # 尝试使用 scenePos() 获取节点位置（NodeGraphQt中推荐的方式）
                            scene_pos = node.scenePos()
                            node_positions[node.name()] = {'x': scene_pos.x(), 'y': scene_pos.y()}
                        except Exception:
                            # 如果 scenePos() 失败，尝试 pos()
                            try:
                                pos = node.pos()
                                if isinstance(pos, list) or isinstance(pos, tuple):
                                    node_positions[node.name()] = {'x': pos[0], 'y': pos[1]}
                                elif hasattr(pos, 'x') and hasattr(pos, 'y'):
                                    node_positions[node.name()] = {'x': pos.x(), 'y': pos.y()}
                            except Exception:
                                pass
            except Exception as e:
                print(f"收集节点位置信息时出错: {e}")
            
            # 准备项目数据
            project_data = {
                'vendor': 'Phytium',
                'library': 'interegrated',
                'module_name': graph_data.get('module_name', 'UnknownModule'),
                'version': graph_data.get('version', '1.0'),
                'description': graph_data.get('description', ''),
                'component_drag_count': graph_data.get('component_drag_count', 0),
                'input_ports': [],
                'output_ports': []
            }
            
            # 获取nodes_component_data
            nodes_component_data = graph_data.get('nodes_component_data', {})
            
            # 准备连接数据（转换为IP-XACT格式）
            ipxact_connections = []
            
            # 从graph_data中获取连接信息
            session_data = graph_data.get('session', {})
            node_data = session_data.get('node_data', {})
            
            # 遍历节点数据，收集连接信息
            for node_name, node_info in node_data.items():
                outputs = node_info.get('outputs', {})
                for output_name, connections in outputs.items():
                    for conn in connections:
                        target_node = conn.get('node')
                        target_port = conn.get('port')
                        
                        if target_node and target_port:
                            ipxact_connections.append({
                                'source_instance': node_name,
                                'source_port': output_name,
                                'target_instance': target_node,
                                'target_port': target_port
                            })
            
            # 调用writer生成IP-XACT XML文件（传递完整的graph_data）
            if self.writer.create_top_component_file(file_path, project_data, nodes_component_data, ipxact_connections, node_positions, graph_data):
                print(f"Graph已保存为IP-XACT XML文件: {file_path}")
            else:
                print(f"保存Graph XML文件失败")
            
            # 如果指定了verilog_file，同时在Verilog目录生成一份XML文件
            if verilog_xml_path and verilog_xml_path != file_path:
                if self.writer.create_top_component_file(verilog_xml_path, project_data, nodes_component_data, ipxact_connections, node_positions, graph_data):
                    print(f"IP-XACT XML文件已生成（与Verilog同目录）: {verilog_xml_path}")
                else:
                    print(f"生成Verilog同目录的XML文件失败")
                
        except Exception as e:
            print(f"保存graph到文件时出错: {e}")
            import traceback
            traceback.print_exc()

    def generate_verilog_code(self, verilog_file, graph_data):
        """生成Verilog代码到指定文件"""
        try:
            # 从graph_data中获取项目信息
            project_name = graph_data.get('project_name', 'UnknownProject')
            module_name = graph_data.get('module_name', 'UnknownModule')
            version = graph_data.get('version', '1.0')
            
            # 从graph_data中获取节点和连接信息
            nodes = graph_data.get('nodes', {})
            connections = []
            
            # 从graph_data的connections字段或session字段中提取连接关系
            if 'connections' in graph_data:
                # 使用我之前添加的connections字段
                connections = graph_data['connections']
            elif 'session' in graph_data:
                # 从session字段中提取连接关系
                session = graph_data['session']
                if 'connections' in session:
                    connections = session['connections']
            
            # 准备模板数据
            template_data = {
                'project_name': project_name,
                'module_name': module_name,
                'version': version,
                'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parameters': [],
                'input_ports': [],
                'output_ports': [],
                'internal_wires': [],
                'instances': [],
                'connections': []
            }
            
            # 提取所有输入和输出端口
            input_ports = []
            output_ports = []
            
            # 遍历节点，收集端口信息
            for node_id, node_data in nodes.items():
                node_type = node_data.get('type_', '')

                # 处理CircleNodeIn（输入端口）
                if node_type == 'user.circle.CircleNodeIn':
                    node_name = node_data.get('name', f'input_{node_id}')
                    input_ports.append({
                        'name': node_name,
                        'direction': 'input',
                        'width': 1
                    })
                
                # 处理CircleNodeOut（输出端口）
                elif node_type == 'user.circle.CircleNodeOut':
                    node_name = node_data.get('name', f'output_{node_id}')
                    output_ports.append({
                        'name': node_name,
                        'direction': 'output',
                        'width': 1
                    })
            
            # 合并端口列表
            template_data['input_ports'] = input_ports
            template_data['output_ports'] = output_ports
            
            # 从graph_data中获取保存的节点组件数据
            nodes_component_data = graph_data.get('nodes_component_data', {})

            # 提取组件实例信息
            instance_id_map = {}
            for node_id, node_data in nodes.items():
                node_type = node_data.get('type_', '')

                # 跳过CircleNodeIn和CircleNodeOut 和 BackdropNode
                if node_type in ['user.circle.CircleNodeIn', 'user.circle.CircleNodeOut', 'nodeGraphQt.nodes.BackdropNode']:
                    continue

                # 从节点类型中提取组件名称
                # 节点类型格式是"user.{component_name}_node"
                if node_type.startswith('user.') and node_type.endswith('_node'):
                    component_name = node_type[5:-5]  # 去掉"user."和"_node"
                else:
                    component_name = 'UnknownComponent'

                instance_name = node_data.get('name', f'inst_{node_id}')

                # 记录实例ID映射
                instance_id_map[node_id] = instance_name

                # 从nodes_component_data中查找组件信息
                component_data = None
                for node_name, node_info in nodes_component_data.items():
                    if node_name == instance_name:
                        component_data = node_info.get('component_data')
                        break

                if not component_data:
                    print(f"警告: 找不到组件 {component_name} 的信息, instance_name:{instance_name},node name:{node_name}")
                    continue
                
                # 提取组件的参数
                instance_params = []
                for param in component_data.get('parameters', []):
                    instance_params.append({
                        'name': param.get('name', 'UnknownParam'),
                        'value': param.get('value', param.get('default_value', '0'))
                    })
                
                # 提取组件的端口连接
                port_connections = []
                for port in component_data.get('ports', []):
                    port_name = port.get('name', 'UnknownPort')
                    port_connections.append({
                        'port_name': port_name,
                        'signal_name': f'{instance_name}_{port_name}'
                    })
                
                # 添加实例信息
                template_data['instances'].append({
                    'module_name': component_name,
                    'instance_name': instance_name,
                    'parameters': instance_params,
                    'port_connections': port_connections
                })
                
                # 添加内部连线
                for port in component_data.get('ports', []):
                    port_name = port.get('name', 'UnknownPort')
                    port_width = port.get('width', 1)
                    if isinstance(port_width, str):
                        try:
                            port_width = eval(port_width) if port_width else 1
                        except:
                            port_width = 1
                    port_width = int(port_width) if port_width else 1
                    template_data['internal_wires'].append({
                        'name': f'{instance_name}_{port_name}',
                        'width': port_width
                    })
            
            # 处理连接关系
            for conn in connections:
                src_node_id = None
                src_port = None
                dst_node_id = None
                dst_port = None

                # 检查连接关系的格式
                if 'source' in conn and 'target' in conn:
                    # 从session字段中提取的连接关系格式
                    src_node_id = conn.get('source', {}).get('node', '')
                    src_port = conn.get('source', {}).get('port', '')
                    dst_node_id = conn.get('target', {}).get('node', '')
                    dst_port = conn.get('target', {}).get('port', '')
                elif 'source_node' in conn and 'target_node' in conn:
                    # 从我之前添加的connections字段中提取的连接关系格式
                    src_node_name = conn.get('source_node', '')
                    src_port = conn.get('source_port', '')
                    dst_node_name = conn.get('target_node', '')
                    dst_port = conn.get('target_port', '')

                    # 查找源节点和目标节点的ID
                    for node_id, node_data in nodes.items():
                        if node_data.get('name') == src_node_name:
                            src_node_id = node_id
                        if node_data.get('name') == dst_node_name:
                            dst_node_id = node_id

                    if not src_node_id or not dst_node_id:
                        print(f"警告: 找不到节点 {src_node_name} 或 {dst_node_name}")
                        continue
                elif 'in' in conn and 'out' in conn:
                    # NodeGraphQt的连接格式: {'in': [node_id, port_name], 'out': [node_id, port_name]}
                    # 'out' 是源，'in' 是目标
                    out_info = conn.get('out', [])
                    in_info = conn.get('in', [])
                    if len(out_info) >= 2 and len(in_info) >= 2:
                        src_node_id = out_info[0]
                        src_port = out_info[1]
                        dst_node_id = in_info[0]
                        dst_port = in_info[1]
                else:
                    # 不支持的连接关系格式
                    print(f"警告: 不支持的连接关系格式: {conn}")
                    continue

                if not src_node_id or not dst_node_id:
                    continue

                # 获取源节点和目标节点的数据
                src_node_data = nodes.get(src_node_id, {})
                dst_node_data = nodes.get(dst_node_id, {})

                src_node_name = src_node_data.get('name', f'node_{src_node_id}')
                dst_node_name = dst_node_data.get('name', f'node_{dst_node_id}')
                src_node_type = src_node_data.get('type_', '')
                dst_node_type = dst_node_data.get('type_', '')

                # 检查是否是bus interface连接
                src_component_data = nodes_component_data.get(src_node_name, {}).get('component_data', {})
                dst_component_data = nodes_component_data.get(dst_node_name, {}).get('component_data', {})

                src_bus_interfaces = src_component_data.get('bus_interfaces', [])
                dst_bus_interfaces = dst_component_data.get('bus_interfaces', [])

                # 查找源端口是否属于bus interface
                src_bus_info = None
                for bus_if in src_bus_interfaces:
                    if bus_if.get('name') == src_port:
                        src_bus_info = bus_if
                        break

                # 查找目标端口是否属于bus interface
                dst_bus_info = None
                for bus_if in dst_bus_interfaces:
                    if bus_if.get('name') == dst_port:
                        dst_bus_info = bus_if
                        break

                # 如果是bus interface连接，展开physical signal
                if src_bus_info and dst_bus_info:
                    src_port_maps = src_bus_info.get('port_maps', [])
                    dst_port_maps = dst_bus_info.get('port_maps', [])

                    # 建立logical port到physical port的映射
                    src_logical_to_physical = {}
                    for pm in src_port_maps:
                        logical = pm.get('logical_port', '')
                        physical = pm.get('physical_port', '')
                        if logical and physical:
                            src_logical_to_physical[logical] = physical

                    dst_logical_to_physical = {}
                    for pm in dst_port_maps:
                        logical = pm.get('logical_port', '')
                        physical = pm.get('physical_port', '')
                        if logical and physical:
                            dst_logical_to_physical[logical] = physical

                    # 按logical port匹配连接
                    for logical_port in src_logical_to_physical:
                        if logical_port in dst_logical_to_physical:
                            src_physical = src_logical_to_physical[logical_port]
                            dst_physical = dst_logical_to_physical[logical_port]

                            # 确定源信号名称
                            if src_node_type == 'user.circle.CircleNodeIn':
                                src_signal = src_node_name
                            else:
                                src_signal = f'{src_node_name}_{src_physical}'

                            # 确定目标信号名称
                            if dst_node_type == 'user.circle.CircleNodeOut':
                                dst_signal = dst_node_name
                            else:
                                dst_signal = f'{dst_node_name}_{dst_physical}'

                            # 添加连接
                            template_data['connections'].append({
                                'source': src_signal,
                                'target': dst_signal
                            })
                            print(f"添加连接: {src_signal} -> {dst_signal}")
                else:
                    print(f"处理普通端口连接: {src_node_name} -> {dst_node_name}")
                    # 普通端口连接
                    # 确定源信号名称
                    if src_node_type == 'user.circle.CircleNodeIn':
                        # 输入端口连接到实例
                        src_signal = src_node_name
                    else:
                        # 实例输出连接到其他
                        src_signal = f'{src_node_name}_{src_port}'

                    # 确定目标信号名称
                    if dst_node_type == 'user.circle.CircleNodeOut':
                        # 实例输出连接到输出端口
                        dst_signal = dst_node_name
                    else:
                        # 实例输出连接到实例输入
                        dst_signal = f'{dst_node_name}_{dst_port}'

                    # 添加连接
                    template_data['connections'].append({
                        'source': src_signal,
                        'target': dst_signal
                    })
            
            # 加载模板
            template_dir = os.path.dirname(__file__)
            env = Environment(loader=FileSystemLoader(os.path.join(template_dir, 'templates')))
            template = env.get_template('verilog_template.v.jinja2')
            
            # 渲染模板
            verilog_code = template.render(**template_data)
            
            # 写入到文件
            with open(verilog_file, 'w', encoding='utf-8') as f:
                f.write(verilog_code)
            
        except Exception as e:
            import traceback
            traceback.print_exc()

    def load_graph_from_xml(self, xml_file_path):
        """从IP-XACT XML文件加载graph数据"""
        try:
            # 首先尝试从XML中解析session JSON数据（新格式）
            session_data = self.parser.parse_session_data_from_xml(xml_file_path)
            if session_data:
                print("从XML中加载到完整的session数据")
                return session_data
            
            # 如果没有session数据，则使用原有的解析逻辑（兼容旧格式）
            import xml.etree.ElementTree as ET
            
            # 定义命名空间
            ns = {
                'ipxact': 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014',
                'viz': 'http://www.phytium.com/XMLSchema/visualizer/1.0'
            }
            
            # 解析XML文件
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # 提取基本信息
            vendor = root.find('.//ipxact:vendor', ns)
            library = root.find('.//ipxact:library', ns)
            name = root.find('.//ipxact:name', ns)
            version = root.find('.//ipxact:version', ns)
            description = root.find('.//ipxact:description', ns)
            
            # 提取可视化扩展信息
            component_drag_count = {}
            node_positions = {}
            
            viz_extension = root.find('.//ipxact:vendorExtensions/viz:visualizer', ns)
            if viz_extension is not None:
                drag_count_elem = viz_extension.find('.//viz:componentDragCount', ns)
                if drag_count_elem is not None and drag_count_elem.text:
                    try:
                        # component_drag_count是字典，需要从JSON反序列化
                        component_drag_count = json.loads(drag_count_elem.text)
                    except (json.JSONDecodeError, ValueError):
                        # 如果解析失败，尝试作为整数处理（兼容旧格式）
                        try:
                            component_drag_count = int(drag_count_elem.text)
                        except ValueError:
                            component_drag_count = {}
                
                # 提取节点位置信息
                node_positions_elem = viz_extension.find('.//viz:nodePositions', ns)
                if node_positions_elem is not None:
                    for node_pos_elem in node_positions_elem.findall('.//viz:nodePosition', ns):
                        node_name_elem = node_pos_elem.find('.//viz:nodeName', ns)
                        x_elem = node_pos_elem.find('.//viz:x', ns)
                        y_elem = node_pos_elem.find('.//viz:y', ns)
                        
                        if node_name_elem is not None and x_elem is not None and y_elem is not None:
                            node_positions[node_name_elem.text] = {
                                'x': float(x_elem.text),
                                'y': float(y_elem.text)
                            }
            
            # 提取端口信息
            input_ports = []
            output_ports = []
            
            ports = root.find('.//ipxact:ports', ns)
            if ports is not None:
                for port_elem in ports.findall('.//ipxact:port', ns):
                    port_name_elem = port_elem.find('.//ipxact:name', ns)
                    direction_elem = port_elem.find('.//ipxact:direction', ns)
                    width_elem = port_elem.find('.//ipxact:wire/ipxact:width', ns)
                    
                    if port_name_elem is not None and direction_elem is not None:
                        port_info = {
                            'name': port_name_elem.text,
                            'direction': direction_elem.text,
                            'width': int(width_elem.text) if width_elem is not None else 1
                        }
                        
                        if direction_elem.text == 'in':
                            input_ports.append(port_info)
                        elif direction_elem.text == 'out':
                            output_ports.append(port_info)
            
            # 提取组件实例信息
            nodes_component_data = {}
            component_instances = root.find('.//ipxact:componentInstances', ns)
            if component_instances is not None:
                for instance_elem in component_instances.findall('.//ipxact:componentInstance', ns):
                    instance_name_elem = instance_elem.find('.//ipxact:instanceName', ns)
                    component_ref = instance_elem.find('.//ipxact:componentRef', ns)
                    
                    if instance_name_elem is not None and component_ref is not None:
                        instance_name = instance_name_elem.text
                        
                        # 从componentRef获取component信息
                        comp_vendor = component_ref.find('.//ipxact:vendor', ns)
                        comp_library = component_ref.find('.//ipxact:library', ns)
                        comp_name = component_ref.find('.//ipxact:name', ns)
                        comp_version = component_ref.find('.//ipxact:version', ns)
                        
                        # 从self.components中查找完整的component数据
                        component_data = {
                            'vendor': comp_vendor.text if comp_vendor is not None else 'Phytium',
                            'library': comp_library.text if comp_library is not None else 'interegrated',
                            'name': comp_name.text if comp_name is not None else 'UnknownComponent',
                            'version': comp_version.text if comp_version is not None else '1.0'
                        }
                        
                        # 尝试从self.components获取完整数据
                        if comp_name is not None and comp_version is not None:
                            for comp in self.components:
                                if comp.get('name') == comp_name.text and comp.get('version') == comp_version.text:
                                    component_data = comp
                                    break
                        
                        # 构建节点类型
                        node_type = f"user.{component_data['name']}_{component_data['version'].replace('.', '_')}_node"
                        
                        nodes_component_data[instance_name] = {
                            'component_data': component_data,
                            'node_type': node_type
                        }
            
            # 提取连接信息
            connections = []
            interconnections = root.find('.//ipxact:interconnections', ns)
            if interconnections is not None:
                for interconn_elem in interconnections.findall('.//ipxact:interconnection', ns):
                    source = interconn_elem.find('.//ipxact:source', ns)
                    destination = interconn_elem.find('.//ipxact:destination', ns)
                    
                    if source is not None and destination is not None:
                        src_instance = source.find('.//ipxact:instanceName', ns)
                        src_port = source.find('.//ipxact:portName', ns)
                        dst_instance = destination.find('.//ipxact:instanceName', ns)
                        dst_port = destination.find('.//ipxact:portName', ns)
                        
                        if src_instance is not None and src_port is not None and dst_instance is not None and dst_port is not None:
                            connections.append({
                                'source_instance': src_instance.text,
                                'source_port': src_port.text,
                                'target_instance': dst_instance.text,
                                'target_port': dst_port.text
                            })
            
            # 构建graph_data
            graph_data = {
                'vendor': vendor.text if vendor is not None else 'Phytium',
                'library': library.text if library is not None else 'interegrated',
                'module_name': name.text if name is not None else 'UnknownModule',
                'version': version.text if version is not None else '1.0',
                'description': description.text if description is not None else '',
                'component_drag_count': component_drag_count,
                'node_positions': node_positions,
                'input_ports': input_ports,
                'output_ports': output_ports,
                'nodes_component_data': nodes_component_data,
                'connections': connections,
                # 为了兼容现有代码，添加session结构
                'session': {
                    'node_data': {}
                }
            }
            
            # 构建session.node_data结构（用于deserialize_session）
            node_data = {}
            for conn in connections:
                src_instance = conn['source_instance']
                src_port = conn['source_port']
                dst_instance = conn['target_instance']
                dst_port = conn['target_port']
                
                if src_instance not in node_data:
                    node_data[src_instance] = {'outputs': {}}
                
                if src_port not in node_data[src_instance]['outputs']:
                    node_data[src_instance]['outputs'][src_port] = []
                
                node_data[src_instance]['outputs'][src_port].append({
                    'node': dst_instance,
                    'port': dst_port
                })
            
            graph_data['session']['node_data'] = node_data
            
            return graph_data
            
        except Exception as e:
            print(f"从XML文件加载graph数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_graphs_from_files(self):
        """从本地XML文件加载graph数据并还原project_panel"""
        try:
            # 获取projects目录路径
            projects_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "projects")
            
            if not os.path.exists(projects_dir):
                print("Projects目录不存在，跳过加载")
                return
            
            # 获取所有xml文件（优先）和json文件（兼容旧格式）
            xml_files = glob.glob(os.path.join(projects_dir, "*.xml"))
            json_files = glob.glob(os.path.join(projects_dir, "*.json"))
            
            # 清空现有的saved_graphs和project_panel
            self.saved_graphs = []
            self.project_panel.clear()
            
            # 加载每个graph文件
            for file_path in xml_files + json_files:
                try:
                    graph_name = os.path.basename(file_path)
                    graph_name = os.path.splitext(graph_name)[0]
                    
                    if file_path.endswith('.xml'):
                        # 从IP-XACT XML文件加载
                        graph_data = self.load_graph_from_xml(file_path)
                    else:
                        # 从JSON文件加载（兼容旧格式）
                        with open(file_path, 'r', encoding='utf-8') as f:
                            graph_info = json.load(f)
                            graph_name = graph_info.get("name", graph_name)
                            graph_data = graph_info.get("data")
                    
                    # 从graph_data中获取项目信息
                    project_name = 'UnknownProject'
                    module_name = 'UnknownModule'
                    version = '1.0'
                    verilog_file = ''
                    
                    if graph_data:
                        project_name = graph_data.get('project_name', 'UnknownProject')
                        module_name = graph_data.get('module_name', 'UnknownModule')
                        version = graph_data.get('version', '1.0')
                        verilog_file = graph_data.get('verilog_file', '')
                    else:
                        # 如果graph_data为None，尝试从文件路径或graph_name中推断信息
                        # 从graph_name中提取模块名称和版本号
                        if graph_name:
                            parts = graph_name.split('_')
                            if len(parts) >= 2:
                                module_name = '_'.join(parts[:-1])
                                version = parts[-1]
                            else:
                                module_name = graph_name
                                version = '1.0'
                    
                    # 添加到saved_graphs
                    self.saved_graphs.append((graph_name, graph_data))
                    
                    # 按照三层结构添加到project_panel
                    # 查找或创建vendor项 (Phytium)
                    vendor_item = None
                    for i in range(self.project_panel.topLevelItemCount()):
                        item = self.project_panel.topLevelItem(i)
                        if item.text(0) == "Phytium":
                            vendor_item = item
                            break
                    
                    if not vendor_item:
                        vendor_item = QTreeWidgetItem(self.project_panel)
                        vendor_item.setText(0, "Phytium")
                    
                    # 查找或创建project项
                    project_item = None
                    for i in range(vendor_item.childCount()):
                        item = vendor_item.child(i)
                        if item.text(0) == project_name:
                            project_item = item
                            break
                    
                    if not project_item:
                        project_item = QTreeWidgetItem(vendor_item)
                        project_item.setText(0, project_name)
                    
                    # 创建module项
                        module_item = QTreeWidgetItem(project_item)
                        module_item.setText(0, graph_name)
                        module_item.setData(0, Qt.UserRole, len(self.saved_graphs) - 1)  # 存储索引
                        
                except Exception as e:
                    print(f"加载graph文件 {json_file} 失败: {e}")
            
            # 展开所有层级
            self.project_panel.expandAll()
            
        except Exception as e:
            print(f"加载graphs失败: {e}")
    
    def append_to_details_panel(self, text):
        """将文本追加到terminal（保留所有内容）"""
        self.terminal.write_output(text)
    
    def save_log_to_file(self, content):
        """将日志内容追加到日志文件"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                # 添加分隔线和时间戳
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n{'='*60}\n")
                f.write(f"日志保存时间: {timestamp}\n")
                f.write(f"{'='*60}\n")
                f.write(content)
                f.write("\n")
            print(f"日志已保存到: {self.log_file_path}")
        except Exception as e:
            # 恢复原始stdout打印错误
            original = sys.stdout
            sys.stdout = self.original_stdout
            print(f"保存日志失败: {e}")
            sys.stdout = original
    
    def closeEvent(self, event):
        """关闭窗口时保存剩余日志"""
        # 恢复原始stdout
        sys.stdout = self.original_stdout
        
        # 调用父类的closeEvent
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IPXactVisualizer()
    window.show()
    sys.exit(app.exec_())