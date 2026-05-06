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
                             QDialog, QLineEdit, QLabel, QInputDialog, QMenu, QGroupBox, 
                             QGridLayout, QComboBox, QTableWidget, QTableWidgetItem, QGraphicsRectItem, QStyle)
from PyQt5.QtCore import Qt, QMimeData, QPoint, QEvent
from PyQt5.QtGui import QDrag, QPen, QBrush, QColor, QPainter, QIcon
from src.ipxact_parser import IPXactParser
from src.ipxact_writer import IPXactWriter
from NodeGraphQt import BaseNode, NodeGraph
from src.nodegraph_tools import (get_all_connections, make_template_node, 
                                 CircleNodeIn, CircleNodeOut)
from src.portInfoDialog import PortInfoDialog 
from src.newBusDefDialog import NewBusDefDialog
from src.newComponentDialog import NewComponentDialog

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
            print(f"双击事件触发，使用选中的节点: {clicked_node.name()}")
            self._node_double_click_callback(clicked_node)
            event.accept()
        else:
            # 调用原始的双击处理函数
            self._original_mouse_double_click(event)
    
class LibraryConfigDialog(QDialog):
    """Library库配置对话框"""
    def __init__(self, parent=None, library_dir=""):
        super().__init__(parent)
        self.setWindowTitle("Library库配置")
        self.setGeometry(100, 100, 400, 150)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 目录选择区域
        dir_layout = QHBoxLayout()
        
        # 标签
        dir_label = QLabel("库目录:")
        dir_layout.addWidget(dir_label)
        
        # 文本框显示选定的目录
        self.dir_line_edit = QLineEdit()
        self.dir_line_edit.setReadOnly(True)
        dir_layout.addWidget(self.dir_line_edit)
        
        # 浏览按钮
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(browse_button)
        
        layout.addLayout(dir_layout)
        
        # 确定和取消按钮
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # 存储选定的目录
        self.selected_directory = library_dir
        # 设置初始目录
        self.dir_line_edit.setText(library_dir)
    
    def browse_directory(self):
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(self, "选择Library库目录")
        if directory:
            self.selected_directory = directory
            self.dir_line_edit.setText(directory)
    
    def get_selected_directory(self):
        return self.selected_directory

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
                    # 删除对应的XML文件
                    xml_filename = f"{component_name}_{component_version}.xml"
                    xml_file_path = os.path.join(self.main_window.library_directory, xml_filename)
                    if os.path.exists(xml_file_path):
                        try:
                            os.remove(xml_file_path)
                            print(f"删除文件: {xml_file_path}")
                        except Exception as e:
                            print(f"删除文件失败: {e}")
                    
                    # 从components列表中删除
                    self.main_window.components.pop(component_index)
                    
                    # 更新component_list
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
        self.component_list.setMaximumWidth(250)
        self.component_list.itemClicked.connect(self.on_component_selected)
        
        # 左侧project列表
        self.project_panel = QTreeWidget()
        self.project_panel.setHeaderLabel("Project ")
        self.project_panel.setHeaderHidden(False)
        self.project_panel.setMaximumWidth(250)
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
        
        # 详细信息窗口
        self.details_panel = QTextEdit()
        self.details_panel.setMaximumHeight(200)
        
        # 组装布局
        right_layout.addWidget(self.graph.widget, 1)
        right_layout.addWidget(self.details_panel, 0)
        
        left_layout.addWidget(self.project_panel, 0)
        left_layout.addWidget(self.component_list, 1)
        main_layout.addLayout(left_layout, 0)
        main_layout.addLayout(right_layout, 1)
        
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
        print(f"双击节点: {node_name}")
        
        # 获取节点的端口信息
        ports_info = self.get_node_ports_info(node)
        
        # 打开端口信息对话框
        dialog = PortInfoDialog(node_name, ports_info, self, self.graph)
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
            print(f"已删除 {len(selected_nodes)} 个节点")
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的节点")
    
    def load_library_config(self):
        """加载Library库配置"""
        try:
            config = load_config()
            if config and "library_directory" in config:
                library_dir = config["library_directory"]
                if os.path.exists(library_dir):
                    self.library_directory = library_dir
                    print(f"从配置文件加载Library库目录: {library_dir}")
                    # 自动加载Library库
                    self.load_library_from_directory(library_dir)
                else:
                    print(f"配置文件中的Library库目录不存在: {library_dir}")
        except Exception as e:
            print(f"加载Library库配置失败: {e}")
        
        # 加载保存的graphs
        self.load_graphs_from_files()
    
    def load_library_from_directory(self, library_dir):
        """从指定目录加载Library库"""
        try:
            import glob
            # 从IP子目录读取XML文件
            ip_dir = os.path.join(library_dir, "IP")
            if os.path.exists(ip_dir):
                xml_files = glob.glob(os.path.join(ip_dir, "*.xml"))
            else:
                # 如果IP子目录不存在，尝试从根目录读取（兼容旧版本）
                xml_files = glob.glob(os.path.join(library_dir, "*.xml"))
            print(f"找到 {len(xml_files)} 个XML文件")
            
            # 清空现有的components列表
            self.components = []
            
            # 解析每个XML文件
            for xml_file in xml_files:
                try:
                    components = self.parser.parse_file(xml_file)
                    self.components.extend(components)
                    print(f"解析文件: {xml_file}, 找到 {len(components)} 个components")
                except Exception as e:
                    print(f"解析文件 {xml_file} 时出错: {e}")
            
            # 清空component_list并添加解析结果
            self.component_list.clear()
            
            # 构建三层结构：vendor -> library -> component
            vendor_dict = {}
            
            for i, component in enumerate(self.components):
                component_name = component.get('name', '未知组件')
                vendor = component.get('vendor', 'UnknownVendor')
                library = component.get('library', 'UnknownLibrary')
                version = component.get('version', '1.0').replace('.', '_')
                
                # 检查节点类型是否已经注册过
                node_identifier = f"user.{component_name}_{version}_node"
                if node_identifier in self.graph.registered_nodes():
                    print(f"节点类型 '{node_identifier}' 已经注册过，跳过")
                    continue
                
                # 构建vendor -> library -> component结构
                if vendor not in vendor_dict:
                    vendor_dict[vendor] = {}
                
                if library not in vendor_dict[vendor]:
                    vendor_dict[vendor][library] = []
                
                vendor_dict[vendor][library].append((i, component))
                
                try:
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
            
            print(f"成功加载Library库，共解析 {len(self.components)} 个components")
        except Exception as e:
            print(f"加载Library库失败: {e}")
    
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
        
        # 检查library_directory是否已经设置
        if not hasattr(self, 'library_directory') or not self.library_directory:
            QMessageBox.warning(self, "警告", "请先在Library配置中选择IP library目录")
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
            
            # 注册节点类型
            # 使用闭包捕获当前的component和node_name值
            def create_node_init(component, node_name):
                def node_init(self):
                    super(type(self), self).__init__()
                    
                    # 设置节点名称
                    self.set_name(node_name)
                    
                    # 存储component数据
                    self.component_data = component
                    
                    # 打印component数据，看看是否包含inout端口
                    print(f"Component数据: {component}")
                    print(f"Component端口: {component.get('ports', [])}")
                    
                    # 根据component的ports创建输入和输出端口
                    for port in component.get('ports', []):
                        port_name = port.get('name', 'Unknown')
                        direction = port.get('direction', 'input')
                        print(f"端口: {port_name}, 方向: {direction}")
                        
                        if direction == 'input' or direction == 'inout':
                            # input和inout端口都添加为输入
                            print(f"添加输入端口: {port_name}")
                            self.add_input(port_name)
                        if direction == 'output' or direction == 'inout':
                            # output和inout端口都添加为输出
                            print(f"添加输出端口: {port_name}")
                            self.add_output(port_name)
                return node_init
            
            try:
                # 使用type创建动态类
                node_class_name = f'{node_name}_node'
                DynamicComponentNode = type(
                    node_class_name,
                    (BaseNode,),
                    {
                        '__identifier__': 'user',
                        'NODE_NAME': node_class_name,  # 使用完整的类名作为NODE_NAME
                        '__init__': create_node_init(component, node_name)
                    }
                )
                
                # 注册节点类型，覆盖已有的注册
                self.graph.register_node(DynamicComponentNode)
                print(f"注册节点类型: {node_class_name}, 标识符: user.{node_class_name}")
                print(f"当前注册的节点类型: {self.graph.registered_nodes()}")
            except Exception as e:
                print(f"注册节点类型 {component_name} 失败: {e}")
            
            # 构建vendor -> library -> component结构
            if vendor not in vendor_dict:
                vendor_dict[vendor] = {}
            
            if library not in vendor_dict[vendor]:
                vendor_dict[vendor][library] = []
            
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
                        TemplateClass = make_template_node(None, f"{component_name}_{version}", node_data=component)
                        ## 注册节点类型
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
                
                # 清空详细信息
                self.details_panel.clear()
                
                # 显示成功消息
                #QMessageBox.information(self, "成功", f"成功解析文件: {file_path}")
            except Exception as e:
                # 显示错误消息
                QMessageBox.critical(self, "错误", f"解析文件时出错: {str(e)}")
    
    def on_component_selected(self, item, column):
        # 获取选中的项索引
        index = item.data(0, Qt.UserRole)
        
        # 检查是component项还是保存的graph项
        # 通过检查index是否在components范围内来判断
        if 0 <= index < len(self.components):
            # 是component项
            component = self.components[index]
            # 显示详细信息
            details = self.parser.get_component_details(component)
            self.details_panel.setText(details)
    
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
                print(f"加载graph: {graph_name}")
                QMessageBox.information(self, "成功", f"成功加载graph: {graph_name}")
            else:
                print(f"加载空graph: {graph_name}")
                QMessageBox.information(self, "提示", f"加载空graph: {graph_name}")
        except Exception as e:
            print(f"加载graph时出错: {e}")
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
                    print(f"删除文件: {file_path}")
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
                        print(f"删除文件: {file_path}")
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
            QMessageBox.warning(self, "警告", "请先在Project面板中选择一个Graph项")
            return
        
        # 将component添加到工作区
        if 0 <= component_index < len(self.components):
            component = self.components[component_index]
            component_name = component.get('name', 'Unknown Component')
            version = component.get('version', '1.0').replace('.', '_')
            
            # 构建name_version格式的节点名称
            node_name = f"{component_name}_{version}"
            node_class_name = f"{node_name}_node"
            
            # 重新注册节点类型，确保使用最新的组件信息
            class DynamicComponentNode:
                """动态组件节点"""
                __identifier__ = "user"
                __name__ = node_class_name
                
                def __init__(self):
                    super(type(self), self).__init__()
                    
                    # 设置节点名称
                    self.set_name(node_name)
                    
                    # 存储component数据
                    self.component_data = component
                    
                    # 打印component数据
                    print(f"添加Component数据: {component}")
                    print(f"添加Component端口: {component.get('ports', [])}")
                    print(f"添加Component bus interfaces: {component.get('bus_interfaces', [])}")
                    print(f"添加Component port maps: {component.get('port_maps', [])}")
                    
                    # 构建端口映射
                    port_directions = {}
                    
                    # 收集所有port map中的physical port
                    mapped_physical_ports = set()
                    for port_map in component.get('port_maps', []):
                        physical_port = port_map.get('physical_port', '')
                        if physical_port:
                            mapped_physical_ports.add(physical_port)
                    
                    print(f"已映射的physical ports: {mapped_physical_ports}")
                    
                    # 首先添加port表中的端口，但排除已经被映射的port
                    for port in component.get('ports', []):
                        port_name = port.get('name', 'Unknown')
                        # 检查这个port是否已经被映射
                        if port_name not in mapped_physical_ports:
                            direction = port.get('direction', 'input')
                            port_directions[port_name] = direction
                    
                    # 然后添加bus接口中的端口，根据master/slave映射方向
                    for bus_interface in component.get('bus_interfaces', []):
                        bus_name = bus_interface.get('name', '')
                        mode = bus_interface.get('mode', 'master')
                        # 根据mode映射方向
                        if mode == 'master':
                            port_directions[bus_name] = 'output'
                        elif mode == 'slave':
                            port_directions[bus_name] = 'input'
                    
                    print(f"端口方向映射: {port_directions}")
                    
                    # 根据端口映射创建输入和输出端口
                    for port_name, direction in port_directions.items():
                        if direction == 'input' or direction == 'inout':
                            # input和inout端口都添加为输入
                            print(f"添加输入端口: {port_name}")
                            self.add_input(port_name)
                        if direction == 'output' or direction == 'inout':
                            # output和inout端口都添加为输出
                            print(f"添加输出端口: {port_name}")
                            self.add_output(port_name)
            
            try:
                # 注册节点类型，覆盖已有的注册
                self.graph.register_node(DynamicComponentNode)
                print(f"注册节点类型: {node_class_name}, 标识符: user.{node_class_name}")
                print(f"当前注册的节点类型: {self.graph.registered_nodes()}")
            except Exception as e:
                print(f"注册节点类型 {component_name} 失败: {e}")
            
            # 更新拖拽计数
            if node_name not in self.component_drag_count:
                self.component_drag_count[node_name] = 0
            
            # 生成唯一的节点名称
            unique_name = f"u_{component_name}_v{version}_{self.component_drag_count[node_name]}"
            
            print(f"添加component: {unique_name} 到工作区")
            self.details_panel.setText(f"添加component: {unique_name} 到工作区")
            
            # 从0开始计数
            self.component_drag_count[node_name] += 1

            # 使用正确的节点类型标识符创建节点
            # 格式：{__identifier__}.{NODE_NAME}
            print(f"创建节点，类型标识符: user.{node_name}_node")
            
            node = self.graph.create_node(
                f'user.{node_name}_node',
                name=unique_name,
                pos=pos
            )
            print(f"创建节点成功: {node}")
            print(f"节点输入端口: {node.inputs()}")
            print(f"节点输出端口: {node.outputs()}")
            self.component_items.append(node)
    
    def update_component_node(self, component_index, component_data):
        """更新工作区中指定component的节点"""
        if 0 <= component_index < len(self.components):
            # 构建节点名称
            component_name = component_data.get('name', 'Unknown Component')
            version = component_data.get('version', '1.0').replace('.', '_')
            node_name = f"{component_name}_{version}"
            node_class_name = f"{node_name}_node"
            
            # 重新注册节点类型
            # 定义动态节点类
            class DynamicComponentNode:
                """动态组件节点"""
                __identifier__ = "user"
                __name__ = node_class_name
                
                def __init__(self):
                    super(type(self), self).__init__()
                    
                    # 设置节点名称
                    self.set_name(node_name)
                    
                    # 存储component数据
                    self.component_data = component_data
                    
                    # 打印component数据
                    print(f"更新Component数据: {component_data}")
                    print(f"更新Component端口: {component_data.get('ports', [])}")
                    print(f"更新Component bus interfaces: {component_data.get('bus_interfaces', [])}")
                    print(f"更新Component port maps: {component_data.get('port_maps', [])}")
                    
                    # 构建端口映射
                    port_directions = {}
                    
                    # 收集所有port map中的physical port
                    mapped_physical_ports = set()
                    for port_map in component_data.get('port_maps', []):
                        physical_port = port_map.get('physical_port', '')
                        if physical_port:
                            mapped_physical_ports.add(physical_port)
                    
                    print(f"已映射的physical ports: {mapped_physical_ports}")
                    
                    # 首先添加port表中的端口，但排除已经被映射的port
                    for port in component_data.get('ports', []):
                        port_name = port.get('name', 'Unknown')
                        # 检查这个port是否已经被映射
                        if port_name not in mapped_physical_ports:
                            direction = port.get('direction', 'input')
                            port_directions[port_name] = direction
                    
                    # 然后添加bus接口中的端口，根据master/slave映射方向
                    for bus_interface in component_data.get('bus_interfaces', []):
                        bus_name = bus_interface.get('name', '')
                        mode = bus_interface.get('mode', 'master')
                        # 根据mode映射方向
                        if mode == 'master':
                            port_directions[bus_name] = 'output'
                        elif mode == 'slave':
                            port_directions[bus_name] = 'input'
                    
                    print(f"端口方向映射: {port_directions}")
                    
                    # 根据端口映射创建输入和输出端口
                    for port_name, direction in port_directions.items():
                        if direction == 'input' or direction == 'inout':
                            # input和inout端口都添加为输入
                            print(f"添加输入端口: {port_name}")
                            self.add_input(port_name)
                        if direction == 'output' or direction == 'inout':
                            # output和inout端口都添加为输出
                            print(f"添加输出端口: {port_name}")
                            self.add_output(port_name)
            
            try:
                # 注册节点类型，覆盖已有的注册
                self.graph.register_node(DynamicComponentNode)
                print(f"更新节点类型: {node_class_name}, 标识符: user.{node_class_name}")
                print(f"当前注册的节点类型: {self.graph.registered_nodes()}")
            except Exception as e:
                print(f"注册节点类型 {component_name} 失败: {e}")
            
            # 更新工作区中的节点
            for node in self.component_items:
                # 检查节点是否是对应的component
                if hasattr(node, 'component_data'):
                    node_component_name = node.component_data.get('name', '')
                    node_component_version = node.component_data.get('version', '1.0')
                    if node_component_name == component_name and node_component_version == component_data.get('version', '1.0'):
                        # 更新节点的数据
                        node.component_data = component_data
                        print(f"更新节点: {node.name()}")
                        
                        # 这里可以添加更新节点端口的逻辑
                        # 注意：具体的端口更新方法取决于您使用的图形库
                        # 可能需要重新创建节点或调用特定的更新方法
        else:
            print(f"无效的component索引: {component_index}")
    
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
        print(f"更新连线关系: {src_node}.{output_port.name()} -> {dst_node}.{input_port.name()}")
        #connection = {"source_node": src_node, 
        #              "target_node": dst_node, 
        #              "source_port": output_port.name(), 
        #              "target_port": input_port.name()}

        #self.connections.append(connection)
        print("更新连线关系")
    
    def open_library_config(self):
        # 打开Library库配置对话框
        dialog = LibraryConfigDialog(self, self.library_directory)
        if dialog.exec_() == QDialog.Accepted:
            # 获取选定的目录
            library_dir = dialog.get_selected_directory()
            if library_dir:
                # 存储选定的库目录位置
                self.library_directory = library_dir
                print(f"选定Library库目录: {library_dir}")
                
                # 保存配置到文件
                config = {"library_directory": library_dir}
                if save_config(config):
                    print(f"配置已保存到: {get_config_path()}")
                else:
                    print("保存配置失败")
                
                # 检索目录下的XML文件
                try:
                    import glob
                    # 从IP子目录读取XML文件
                    ip_dir = os.path.join(library_dir, "IP")
                    if os.path.exists(ip_dir):
                        xml_files = glob.glob(os.path.join(ip_dir, "*.xml"))
                    else:
                        # 如果IP子目录不存在，尝试从根目录读取（兼容旧版本）
                        xml_files = glob.glob(os.path.join(library_dir, "*.xml"))
                    print(f"找到 {len(xml_files)} 个XML文件")
                    
                    # 清空现有的components列表
                    self.components = []
                    
                    # 解析每个XML文件
                    for xml_file in xml_files:
                        try:
                            components = self.parser.parse_file(xml_file)
                            self.components.extend(components)
                            print(f"解析文件: {xml_file}, 找到 {len(components)} 个components")
                        except Exception as e:
                            print(f"解析文件 {xml_file} 时出错: {e}")
                    
                    # 清空component_list并添加解析结果
                    self.component_list.clear()
                    for i, component in enumerate(self.components):
                        component_name = component.get('name', '未知组件')
                        component_version = component.get('version', '未知组件').replace('.', '_')
                        
                        # 检查节点类型是否已经注册过
                        node_identifier = f"user.{component_name}_{component_version}_node"
                        if node_identifier in self.graph.registered_nodes():
                            QMessageBox.warning(self, "警告", f"节点类型 '{component_name}' 已经注册过，跳过'{xml_file}'的解析")
                            continue
                        
                        try:
                            TemplateClass = make_template_node(None, f"{component_name}_{component_version}", node_data=component)
                            # 注册节点类型
                            self.graph.register_node(TemplateClass)
                        except Exception as e:
                            print(f"注册节点失败: {e}")
                    
                    # 更新component_list
                    self.update_component_list()
                    
                    QMessageBox.information(self, "成功", f"成功加载Library库，共解析 {len(self.components)} 个components")
                except Exception as e:
                    print(f"检索XML文件时出错: {e}")
                    QMessageBox.critical(self, "错误", f"检索XML文件时出错: {str(e)}")
    
    def save_file(self):
        graph_name, graph_data = self.saved_graphs[self.current_project_index]
        # 保存文件对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存IP-XACT文件", graph_name, "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            try:
                print(f"保存文件: {file_path}")
                
                # 获取当前graph上的所有连接关系
                connections = get_all_connections(self.graph)
                print(connections)
                
                # 写回IP-XACT文件
                success = self.writer.write_file(file_path, graph_name, connections)
                if success:
                    print("保存成功！")
                    QMessageBox.information(self, "成功", f"成功保存文件: {file_path}")
                else:
                    print("保存失败！")
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
            
            print(f"创建graph: {full_module_name}")
            QMessageBox.information(self, "成功", f"成功创建graph: {full_module_name}")
        except Exception as e:
            print(f"创建graph时出错: {e}")
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
            
            # 保存graph数据到本地文件
            self.save_graph_to_file(graph_name, graph_data)
            
            # 生成Verilog代码到指定文件
            verilog_file = graph_data.get('verilog_file', '')
            if verilog_file:
                self.generate_verilog_code(verilog_file, graph_data)
            
            print(f"保存graph: {graph_name}")
            QMessageBox.information(self, "成功", f"成功保存graph: {graph_name}")
        except Exception as e:
            print(f"保存graph时出错: {e}")
            QMessageBox.critical(self, "错误", f"保存graph时出错: {str(e)}")
    
    def save_graph_to_file(self, graph_name, graph_data):
        """将graph数据保存到本地文件"""
        try:
            # 获取projects目录路径
            projects_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "projects")
            
            # 创建projects目录
            if not os.path.exists(projects_dir):
                os.makedirs(projects_dir)
            
            # 生成安全的文件名
            safe_name = graph_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            file_path = os.path.join(projects_dir, f"{safe_name}.json")
            
            # 保存graph数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "name": graph_name,
                    "data": graph_data
                }, f, ensure_ascii=False, indent=4)
            
            print(f"Graph数据已保存到: {file_path}")
            return True
        except Exception as e:
            print(f"保存graph数据到文件失败: {e}")
            return False
    
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
                print(f"节点类型: {node_type}")

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
            
            # 提取组件实例信息
            instance_id_map = {}
            for node_id, node_data in nodes.items():
                node_type = node_data.get('type_', '')
                
                # 跳过CircleNodeIn和CircleNodeOut
                if node_type in ['user.circle.CircleNodeIn', 'user.circle.CircleNodeOut']:
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
                
                # 从self.components中查找组件信息
                component_data = None
                for comp in self.components:
                    if comp.get('name') == component_name:
                        component_data = comp
                        break
                
                if not component_data:
                    print(f"警告: 找不到组件 {component_name} 的信息")
                    continue
                
                # 提取组件的参数
                instance_params = []
                for param in component_data.get('parameters', []):
                    instance_params.append({
                        'name': param.get('name', 'UnknownParam'),
                        'value': param.get('default_value', '0')
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
                    template_data['internal_wires'].append({
                        'name': f'{instance_name}_{port_name}',
                        'width': port_width
                    })
            
            # 处理连接关系
            for conn in connections:
                # 检查连接关系的格式
                if 'source' in conn and 'target' in conn:
                    # 从session字段中提取的连接关系格式
                    src_node_id = conn.get('source', {}).get('node', '')
                    src_port = conn.get('source', {}).get('port', '')
                    dst_node_id = conn.get('target', {}).get('node', '')
                    dst_port = conn.get('target', {}).get('port', '')
                    
                    # 获取源节点和目标节点的数据
                    src_node_data = nodes.get(src_node_id, {})
                    dst_node_data = nodes.get(dst_node_id, {})
                    
                    src_node_name = src_node_data.get('name', f'node_{src_node_id}')
                    dst_node_name = dst_node_data.get('name', f'node_{dst_node_id}')
                elif 'source_node' in conn and 'target_node' in conn:
                    # 从我之前添加的connections字段中提取的连接关系格式
                    src_node_name = conn.get('source_node', '')
                    src_port = conn.get('source_port', '')
                    dst_node_name = conn.get('target_node', '')
                    dst_port = conn.get('target_port', '')
                    
                    # 查找源节点和目标节点的ID
                    src_node_id = None
                    dst_node_id = None
                    for node_id, node_data in nodes.items():
                        if node_data.get('name') == src_node_name:
                            src_node_id = node_id
                        if node_data.get('name') == dst_node_name:
                            dst_node_id = node_id
                    
                    if not src_node_id or not dst_node_id:
                        print(f"警告: 找不到节点 {src_node_name} 或 {dst_node_name}")
                        continue
                    
                    # 获取源节点和目标节点的数据
                    src_node_data = nodes.get(src_node_id, {})
                    dst_node_data = nodes.get(dst_node_id, {})
                else:
                    # 不支持的连接关系格式
                    print(f"警告: 不支持的连接关系格式: {conn}")
                    continue
                
                src_node_type = src_node_data.get('type_', '')
                dst_node_type = dst_node_data.get('type_', '')
                
                # 确定源信号名称
                if src_node_type == 'user.circle.CircleNodeIn':
                    # 输入端口连接到实例
                    src_signal = src_node_data.get('name', f'input_{src_node_id}')
                else:
                    # 实例输出连接到其他
                    src_signal = f'{src_node_name}_{src_port}'
                
                # 确定目标信号名称
                if dst_node_type == 'user.circle.CircleNodeOut':
                    # 实例输出连接到输出端口
                    dst_signal = dst_node_data.get('name', f'output_{dst_node_id}')
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
            
            print(f"Verilog代码已生成到: {verilog_file}")
        except Exception as e:
            print(f"生成Verilog代码时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def load_graphs_from_files(self):
        """从本地文件加载graph数据并还原project_panel"""
        try:
            # 获取projects目录路径
            projects_dir = os.path.join(os.path.expanduser("~"), ".config", "ipxact_visualizer", "projects")
            
            if not os.path.exists(projects_dir):
                print("Projects目录不存在，跳过加载")
                return
            
            # 获取所有json文件
            json_files = glob.glob(os.path.join(projects_dir, "*.json"))
            print(f"找到 {len(json_files)} 个graph文件")
            
            # 清空现有的saved_graphs和project_panel
            self.saved_graphs = []
            self.project_panel.clear()
            
            # 加载每个graph文件
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        graph_info = json.load(f)
                        graph_name = graph_info.get("name", "Unknown")
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
                        
                        print(f"加载graph: {graph_name}")
                except Exception as e:
                    print(f"加载graph文件 {json_file} 失败: {e}")
            
            # 展开所有层级
            self.project_panel.expandAll()
            
            print(f"成功加载 {len(self.saved_graphs)} 个graphs")
        except Exception as e:
            print(f"加载graphs失败: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IPXactVisualizer()
    window.show()
    sys.exit(app.exec_())