import xml.etree.ElementTree as ET
import os
import ast
import operator
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QHeaderView, QHBoxLayout, 
                    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QGroupBox, QLabel, QLineEdit, QGridLayout, QFileDialog, QMessageBox)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from .ipxact_parser import IPXactParser
from .ipxact_writer import IPXactWriter


class NewComponentDialog(QDialog):
    """新建Component对话框"""
    
    def get_parameters_dict(self):
        """获取所有parameter的名称和值的字典"""
        params = {}
        for i in range(self.parameter_table.rowCount()):
            # 跳过添加按钮行
            btn = self.parameter_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            
            # 获取parameter名称
            param_name_item = self.parameter_table.item(i, 0)
            if not param_name_item:
                continue
            param_name = param_name_item.text().strip()
            if not param_name:
                continue
            
            # 获取parameter默认值
            param_default_item = self.parameter_table.item(i, 2)
            param_value = param_default_item.text().strip() if param_default_item else ""
            
            # 如果值本身是表达式，尝试计算
            if param_value:
                try:
                    # 先尝试直接转换为数字
                    params[param_name] = int(param_value)
                except ValueError:
                    try:
                        params[param_name] = float(param_value)
                    except ValueError:
                        # 如果无法转换，保留原始字符串
                        params[param_name] = param_value
        return params
    
    # 安全的公式计算函数
    def safe_eval(self, expr, params=None):
        """安全地计算数学公式，支持parameter替换和基本运算符"""
        if not expr or not isinstance(expr, str):
            return expr
        
        # 如果没有提供params，获取当前的parameter列表
        if params is None:
            params = self.get_parameters_dict()
        
        # 替换表达式中的parameter为对应的值
        expr_with_params = expr
        for param_name, param_value in params.items():
            # 只替换独立的parameter名称（避免部分匹配）
            import re
            # 使用正则表达式匹配独立的变量名
            pattern = r'\b' + re.escape(param_name) + r'\b'
            expr_with_params = re.sub(pattern, str(param_value), expr_with_params)
        
        # 定义允许的操作符
        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        # 安全的表达式评估函数
        def eval_node(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            elif isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](eval_node(node.operand))
            elif isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
                return allowed_ops[type(node.op)](eval_node(node.left), eval_node(node.right))
            else:
                # 如果表达式无法安全计算，返回原始值
                return expr
        
        try:
            # 解析表达式
            parsed_expr = ast.parse(expr_with_params, mode='eval')
            # 计算结果
            result = eval_node(parsed_expr.body)
            return str(result)
        except Exception:
            # 如果计算失败，返回原始值
            return expr
    def __init__(self, parent=None, component_index=None):
        super().__init__(parent)
        self.setWindowTitle("新建Component")
        self.resize(800, 700)
        self.component_index = component_index
        self.edited_component_data = None
        # 存储每个bus interface的port map信息
        self.bus_interface_port_maps = {}
        # 当前选中的bus interface行索引
        self.current_bus_interface_row = None
        
        self.layout = QVBoxLayout(self)
        
        # 主布局 - 垂直布局
        main_layout = QVBoxLayout()
        
        # 第一行布局：基础信息（占2/3）和LocalParameter信息（占1/3）
        first_row_layout = QHBoxLayout()
        
        # 基本信息部分
        basic_info_group = QGroupBox("基本信息")
        basic_layout = QGridLayout()
        
        # Vendor
        self.vendor_label = QLabel("Vendor:")
        self.vendor_input = QLineEdit()
        self.vendor_input.setText("Phytium")
        basic_layout.addWidget(self.vendor_label, 0, 0)
        basic_layout.addWidget(self.vendor_input, 0, 1)
        
        # Library
        self.library_label = QLabel("Library:")
        self.library_input = QLineEdit()
        self.library_input.setText("LowSpeedDevice")
        basic_layout.addWidget(self.library_label, 1, 0)
        basic_layout.addWidget(self.library_input, 1, 1)
        
        # Name
        self.name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        self.name_input.setText("NewComponent")
        basic_layout.addWidget(self.name_label, 2, 0)
        basic_layout.addWidget(self.name_input, 2, 1)
        
        # Version
        self.version_label = QLabel("Version:")
        self.version_input = QLineEdit()
        self.version_input.setText("1.0")
        basic_layout.addWidget(self.version_label, 3, 0)
        basic_layout.addWidget(self.version_input, 3, 1)
        
        # SystemVerilog File
        self.sv_file_label = QLabel("SystemVerilog File:")
        self.sv_file_input = QLineEdit()
        self.sv_file_button = QPushButton("浏览...")
        basic_layout.addWidget(self.sv_file_label, 4, 0)
        basic_layout.addWidget(self.sv_file_input, 4, 1)
        basic_layout.addWidget(self.sv_file_button, 4, 2)
        
        basic_info_group.setLayout(basic_layout)
        first_row_layout.addWidget(basic_info_group, 2)  # 基础信息占2/3
        
        # LocalParameter信息表格
        define_group = QGroupBox("LocalParameter信息")
        define_layout = QVBoxLayout()
        
        self.localparameter_table = QTableWidget()
        self.localparameter_table.setColumnCount(4)  # 增加一列用于操作按钮
        self.localparameter_table.setHorizontalHeaderLabels(["Name", "Type", "Value", "操作"])
        self.localparameter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.add_define_lastrow()
        
        define_layout.addWidget(self.localparameter_table)
        define_group.setLayout(define_layout)
        first_row_layout.addWidget(define_group, 1)  # LocalParameter占1/3
        
        # 添加第一行布局到主布局
        main_layout.addLayout(first_row_layout)
        main_layout.setStretch(0, 2)  # 第一行占2份
        
        # 第二行布局：Parameter信息和BusInterface信息（各占一半）
        second_row_layout = QHBoxLayout()
        
        # Parameter信息表格
        parameter_group = QGroupBox("Parameter信息")
        parameter_layout = QVBoxLayout()
        
        self.parameter_table = QTableWidget()
        self.parameter_table.setColumnCount(4)  # 增加一列用于操作按钮
        self.parameter_table.setHorizontalHeaderLabels(["Name", "Type", "Default Value", "操作"])
        self.parameter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.add_parameter_lastrow()
        
        parameter_layout.addWidget(self.parameter_table)
        parameter_group.setLayout(parameter_layout)
        second_row_layout.addWidget(parameter_group, 1)  # Parameter占一半
        
        # BusInterface信息表格
        bus_interface_group = QGroupBox("BusInterface信息")
        bus_interface_layout = QVBoxLayout()
        
        self.bus_interface_table = QTableWidget()
        self.bus_interface_table.setColumnCount(4)  # 增加一列用于操作按钮
        self.bus_interface_table.setHorizontalHeaderLabels(["Name", "Bus Type", "Mode", "操作"])
        self.bus_interface_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.add_bus_interface_lastrow()
        
        bus_interface_layout.addWidget(self.bus_interface_table)
        bus_interface_group.setLayout(bus_interface_layout)
        second_row_layout.addWidget(bus_interface_group, 1)  # BusInterface占一半
        
        # 添加第二行布局到主布局
        main_layout.addLayout(second_row_layout)
        main_layout.setStretch(1, 3)  # 第二行占2份
        
        # 第三行布局：Port信息和PortMap信息（各占一半）
        third_row_layout = QHBoxLayout()
        
        # Port信息表格
        port_group = QGroupBox("Port信息")
        port_layout = QVBoxLayout()
        
        self.port_table = QTableWidget()
        self.port_table.setColumnCount(6)  # 增加一列用于操作按钮
        self.port_table.setHorizontalHeaderLabels(["Port名称", "方向", "位宽", "MSB", "LSB", "操作"])
        self.port_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.add_port_lastrow()
        
        port_layout.addWidget(self.port_table)
        port_group.setLayout(port_layout)
        third_row_layout.addWidget(port_group, 1)  # Port占一半
        
        # PortMap信息表格
        port_map_group = QGroupBox("PortMap信息")
        port_map_layout = QVBoxLayout()
        
        self.port_map_table = QTableWidget()
        self.port_map_table.setColumnCount(5)  # 5列：Logical Port, Physical Port, Port Direction, Port Width, Bus Interface
        self.port_map_table.setHorizontalHeaderLabels(["Logical Port", "Physical Port", "Port Direction", "Port Width", "Bus Interface"])
        self.port_map_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        port_map_layout.addWidget(self.port_map_table)
        port_map_group.setLayout(port_map_layout)
        third_row_layout.addWidget(port_map_group, 1)  # PortMap占一半
        
        # 添加第三行布局到主布局
        main_layout.addLayout(third_row_layout)
        main_layout.setStretch(2, 5)  # 第三行占6份
        
        # 将主布局添加到对话框布局
        self.layout.addLayout(main_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(button_layout)
        
        # 连接信号
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.sv_file_button.clicked.connect(self.browse_sv_file)
        # 添加bus_interface_table的点击事件处理
        self.bus_interface_table.cellClicked.connect(self.on_bus_interface_cell_clicked)
    
    def on_bus_interface_cell_clicked(self, row, column):
        """处理bus_interface_table的点击事件"""
        # 检查是否是添加按钮行
        btn = self.bus_interface_table.cellWidget(row, 0)
        if isinstance(btn, QPushButton):
            return  # 不处理添加按钮行的点击
        
        # 保存当前点击的bus_interface_table行索引
        bus_interface_row = row
        self.current_bus_interface_row = row
        
        # 获取该行的bus_type
        bus_type_widget = self.bus_interface_table.cellWidget(row, 1)
        if not bus_type_widget:
            return
        
        bus_type = bus_type_widget.currentText()
        if not bus_type:
            return
        
        # 获取该行的名称
        interface_name_item = self.bus_interface_table.item(row, 0)
        if not interface_name_item:
            return
        
        interface_name = interface_name_item.text().strip()
        if not interface_name:
            return
        
        # 从主窗口获取library库目录列表
        library_dirs = []
        if self.parent():
            if hasattr(self.parent(), 'library_directories'):
                library_dirs = self.parent().library_directories
            elif hasattr(self.parent(), 'library_directory'):
                library_dir = self.parent().library_directory
                if library_dir:
                    library_dirs = [library_dir]
        
        if not library_dirs:
            default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library")
            if os.path.exists(default_dir):
                library_dirs = [default_dir]
        
        # 创建IPXactParser实例
        parser = IPXactParser()
        
        # 查找对应的总线定义文件（遍历所有library目录）
        busdef_file = None
        for library_dir in library_dirs:
            busdef_dir = os.path.join(library_dir, "busdef")
            busdef_file = parser.find_bus_definition_file(bus_type, busdef_dir)
            if busdef_file:
                break
        
        if not busdef_file:
            return
        
        # 解析总线定义文件，提取port信息
        try:
            # 解析abstract文件，提取信号信息
            signals = parser.parse_abstract_file(busdef_file, None, None)
            
            if not signals:
    
                return
            
            # 从字典中获取该bus interface的port map信息（用于恢复）
            saved_port_maps = self.bus_interface_port_maps.get(bus_interface_row, {})
            
            # 清除所有portMap行（避免增量显示问题）
            self.port_map_table.setRowCount(0)
            
            # 取消隐藏port table中所有被隐藏的端口行
            for i in range(self.port_table.rowCount()):
                self.port_table.setRowHidden(i, False)
            
            # 隐藏所有bus interface行选中的端口
            for bus_row, port_map in self.bus_interface_port_maps.items():
                for physical_port in port_map.values():
                    if physical_port:
                        for i in range(self.port_table.rowCount()):
                            port_btn = self.port_table.cellWidget(i, 0)
                            if isinstance(port_btn, QPushButton):
                                continue
                            port_name_item = self.port_table.item(i, 0)
                            if port_name_item and port_name_item.text().strip() == physical_port:
                                self.port_table.setRowHidden(i, True)
                                break
            
            # 添加新的port map行，并尝试恢复之前保存的map信息
            for signal in signals:
                row = self.port_map_table.rowCount()
                self.port_map_table.insertRow(row)
                
                # 逻辑端口
                logical_port_item = QTableWidgetItem(signal)
                logical_port_item.setFlags(logical_port_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
                self.port_map_table.setItem(row, 0, logical_port_item)
                
                # Port Direction - 从abstract文件中读取
                port_direction = ""
                # Port Width - 从abstract文件中读取
                port_width = ""
                
                # 尝试从abstract文件中读取port方向和位宽信息
                try:
                    # 获取当前点击的bus_interface_table行的mode
                    mode_widget = self.bus_interface_table.cellWidget(bus_interface_row, 2)
                    mode = mode_widget.currentText() if mode_widget else ""
                    
                    # 解析abstract文件获取方向和位宽
                    port_direction, port_width = parser.parse_abstract_file(busdef_file, signal, mode)
                except Exception:
                    pass
                
                # 设置Port Direction
                direction_item = QTableWidgetItem(port_direction)
                direction_item.setFlags(direction_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
                self.port_map_table.setItem(row, 2, direction_item)
                
                # 设置Port Width
                width_item = QTableWidgetItem(port_width)
                width_item.setFlags(width_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
                self.port_map_table.setItem(row, 3, width_item)
                
                # 物理端口（下拉菜单）
                physical_port_combo = QComboBox()
                physical_port_combo.addItem("Select Port")
                
                # 获取当前要恢复的物理端口（如果有）
                current_restore_port = saved_port_maps.get(signal, None)
                
                # 获取port table中的信号列表，只添加方向一致且未被其他行选中的信号
                # 将当前要恢复的端口也传入，以便正确过滤
                port_signals = self.get_port_signals_with_direction(port_direction, row, current_restore_port)
                
                # 检查当前要恢复的端口是否在列表中（可能被其他行选中而隐藏了）
                port_names_in_list = [ps[0] for ps in port_signals]
                if current_restore_port and current_restore_port not in port_names_in_list:
                    # 当前要恢复的端口不在列表中，说明它被其他行选中了（已被隐藏）
                    # 但我们仍然需要把它添加到下拉列表中并选中
                    port_signals.insert(0, (current_restore_port, None))
                
                selected_physical_port = None
                for port_signal, port_dir in port_signals:
                    physical_port_combo.addItem(port_signal)
                    # 检查是否应该选中之前保存的端口
                    if signal in saved_port_maps and port_signal == saved_port_maps[signal]:
                        selected_physical_port = port_signal
                
                # 连接信号
                physical_port_combo.currentIndexChanged.connect(lambda index, r=row: self.on_physical_port_changed(r, index))
                self.port_map_table.setCellWidget(row, 1, physical_port_combo)
                
                # 立即恢复之前保存的端口选择（在添加下一行之前）
                if selected_physical_port:
                    index = physical_port_combo.findText(selected_physical_port)
                    if index != -1:
                        # 暂时阻塞信号以避免触发on_physical_port_changed
                        physical_port_combo.blockSignals(True)
                        physical_port_combo.setCurrentIndex(index)
                        physical_port_combo.blockSignals(False)
                        physical_port_combo.previous_port = selected_physical_port
                
                # Bus Interface
                interface_item = QTableWidgetItem(interface_name)
                interface_item.setFlags(interface_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
                self.port_map_table.setItem(row, 4, interface_item)
                
        except Exception:
            pass
    
    def browse_sv_file(self):
        """浏览并选择SystemVerilog文件"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择SystemVerilog文件",
            "",
            "SystemVerilog Files (*.sv);;All Files (*)",
            options=options
        )
        
        if file_path:
            self.sv_file_input.setText(file_path)
            # 尝试使用pyslang解析文件
            self.parse_sv_file(file_path)
    
    def parse_sv_file(self, file_path):
        """使用pyslang解析SystemVerilog文件"""
        try:
            # 检查pyslang是否安装
            import pyslang
            
            # 1. 加载并解析源文件
            tree = pyslang.SyntaxTree.fromFile(file_path)
            
            # 2. 找到真正的顶层模块声明
            top_module = None
            for member in tree.root.members:
                if hasattr(member, 'kind') and member.kind.name == 'ModuleDeclaration':
                    top_module = member
                    break
            
            if not top_module:

                return
            
            # 3. 提取define信息,现改为存储localparameter
            defines = []
            # 注意：pyslang可能需要不同的方式来获取define信息
            # 这里暂时使用默认值
            
            # 4. 提取parameter信息
            parameters = []
            # 提取参数 (parameter/localparam)
            try:
                # 首先尝试从模块声明的参数列表中提取
                if hasattr(top_module, 'header') and hasattr(top_module.header, 'parameters'):
                    params = top_module.header.parameters
                    for param in params:
                        if hasattr(param, 'kind') and param.kind.name == 'SeparatedList':
                            # 遍历SeparatedList中的元素
                            for item in param:
                                # 检查是否是参数声明
                                if hasattr(item, 'kind') and item.kind.name == 'ParameterDeclaration':
                                    if hasattr(item, 'declarators'):
                                        for declarator in item.declarators:
                                            if hasattr(declarator, 'name'):
                                                param_name = declarator.name.value if hasattr(declarator.name, 'value') else str(declarator.name)
                                                param_type = "int"  # 默认类型
                                                default_val = ""
                                                if hasattr(declarator, 'initializer') and declarator.initializer:
                                                    default_val = declarator.initializer.toString() if hasattr(declarator.initializer, 'toString') else str(declarator.initializer)
                                                    # 去除可能的等号
                                                    default_val = default_val.split('=')[1].strip()

                                                parameters.append({"name": param_name, "type": param_type, "default": default_val})
                
                # 然后尝试从模块体中提取localparam
                if hasattr(top_module, 'members'):
                    for member in top_module.members:
                        # 处理ParameterDeclarationStatement
                        if hasattr(member, 'kind') and hasattr(member.kind, 'name') and member.kind.name == 'ParameterDeclarationStatement':
                            if hasattr(member, 'parameter'):
                                param = member.parameter
                                if hasattr(param, 'declarators'):
                                    for declarator in param.declarators:
                                        if hasattr(declarator, 'name'):
                                            param_name = declarator.name.value if hasattr(declarator.name, 'value') else str(declarator.name)
                                            param_type = "logic"  # 默认类型
                                            default_val = ""
                                            if hasattr(declarator, 'initializer') and declarator.initializer:
                                                default_val = declarator.initializer.toString() if hasattr(declarator.initializer, 'toString') else str(declarator.initializer)
                                                # 去除可能的等号
                                                default_val = default_val.split('=')[1].strip()

                                            defines.append({"name": param_name, "type": param_type, "default": default_val})
            except Exception as e:
                import traceback
                traceback.print_exc()
            # 5. 提取port信息
            ports = []
            # 提取端口信息
            try:
                # 首先尝试从模块头部的ports属性提取
                if hasattr(top_module, 'header') and hasattr(top_module.header, 'ports'):
                    port_list = top_module.header.ports
                    for i, port in enumerate(port_list):
                        if hasattr(port, 'kind') and port.kind.name == 'SeparatedList':
                            # 遍历SeparatedList中的元素
                            for j, item in enumerate(port):
                                # 检查是否是端口声明（包括ImplicitAnsiPort）
                                if hasattr(item, 'kind') and item.kind.name in ['PortDeclaration', 'ImplicitAnsiPort']:
                                    # 尝试不同的方式来获取端口信息
                                    if hasattr(item, 'declarator'):
                                        # 尝试从declarator中获取信息
                                        declarator = item.declarator
                                        if hasattr(declarator, 'name'):
                                            port_name = declarator.name.value if hasattr(declarator.name, 'value') else str(declarator.name)
                                            direction = "input"  # 默认方向
                                            # 尝试从header中获取方向
                                            if hasattr(item, 'header') and hasattr(item.header, 'direction'):
                                                direction_token = item.header.direction
                                                # 尝试从Token中获取方向信息
                                                if hasattr(direction_token, 'value') and direction_token.value is not None:
                                                    direction_str = direction_token.value.strip()
                                                    if direction_str in ['input', 'output', 'inout']:
                                                        direction = direction_str
                                                elif hasattr(direction_token, 'valueText') and direction_token.valueText is not None:
                                                    direction_str = direction_token.valueText.strip()
                                                    if direction_str in ['input', 'output', 'inout']:
                                                        direction = direction_str
                                                elif hasattr(direction_token, 'rawText') and direction_token.rawText is not None:
                                                    direction_str = direction_token.rawText.strip()
                                                    if direction_str in ['input', 'output', 'inout']:
                                                        direction = direction_str
                                                else:
                                                    # 尝试直接字符串化并提取方向
                                                    dir_str = str(direction_token).strip()
                                                    # 从字符串中提取方向关键字
                                                    for keyword in ['input', 'output', 'inout']:
                                                        if keyword in dir_str:
                                                            direction = keyword
                                                            break
                                            width = "1"
                                            # 尝试从header中获取数据类型和位宽
                                            if hasattr(item, 'header') and hasattr(item.header, 'dataType'):
                                                # 尝试直接访问dataType的属性
                                                # 尝试不同的方式获取数据类型字符串
                                                data_type_str = ""
                                                if hasattr(item.header.dataType, 'toString'):
                                                    data_type_str = item.header.dataType.toString()
                                                elif hasattr(item.header.dataType, '__str__'):
                                                    data_type_str = str(item.header.dataType)
                                                if "[" in data_type_str:
                                                    # 提取位宽信息
                                                    # 找到第一个和最后一个方括号
                                                    start_idx = data_type_str.find("[")
                                                    end_idx = data_type_str.rfind("]")
                                                    if start_idx != -1 and end_idx != -1:
                                                        width_part = data_type_str[start_idx+1:end_idx].strip()
                                                        width = width_part
                                            # 尝试从declarator的dimensions获取位宽信息
                                            if width == "1" and hasattr(declarator, 'dimensions'):
                                                for i, dim in enumerate(declarator.dimensions):
                                                    # 尝试直接字符串化维度对象
                                                    dim_str = str(dim)
                                                    if "[" in dim_str and "]" in dim_str:
                                                        # 提取位宽信息
                                                        start_idx = dim_str.find("[")
                                                        end_idx = dim_str.rfind("]")
                                                        if start_idx != -1 and end_idx != -1:
                                                            width_part = dim_str[start_idx+1:end_idx].strip()
                                                            width = width_part
                                                            break
                                            ports.append({"name": port_name, "direction": direction, "width": width})
                                    elif hasattr(item, 'header') and hasattr(item.header, 'name'):
                                        # 对于PortDeclaration类型
                                        port_name = item.header.name.value if hasattr(item.header.name, 'value') else str(item.header.name)
                                        direction = "input"  # 默认方向
                                        if hasattr(item.header, 'direction') and hasattr(item.header.direction, 'name'):
                                            direction = item.header.direction.name.lower()
                                        width = "1"
                                        if hasattr(item.header, 'dataType') and hasattr(item.header.dataType, 'toString'):
                                            data_type = item.header.dataType.toString()
                                            if "[" in data_type:
                                                # 提取位宽信息
                                                width_part = data_type.split("[")[1].split("]")[0]
                                                width = width_part

                                        ports.append({"name": port_name, "direction": direction, "width": width})
                                    elif hasattr(item, 'name'):
                                        # 直接从item获取名称
                                        port_name = item.name.value if hasattr(item.name, 'value') else str(item.name)
                                        direction = "input"  # 默认方向
                                        if hasattr(item, 'direction') and hasattr(item.direction, 'name'):
                                            direction = item.direction.name.lower()
                                        width = "1"
                                        if hasattr(item, 'dataType') and hasattr(item.dataType, 'toString'):
                                            data_type = item.dataType.toString()
                                            if "[" in data_type:
                                                # 提取位宽信息
                                                width_part = data_type.split("[")[1].split("]")[0]
                                                width = width_part

                                        ports.append({"name": port_name, "direction": direction, "width": width})
                                    elif hasattr(item, 'declarators'):
                                        # 对于有declarators的类型
                                        for declarator in item.declarators:
                                            if hasattr(declarator, 'name'):
                                                port_name = declarator.name.value if hasattr(declarator.name, 'value') else str(declarator.name)
                                                direction = "input"  # 默认方向
                                                if hasattr(item, 'direction') and hasattr(item.direction, 'name'):
                                                    direction = item.direction.name.lower()
                                                width = "1"
                                                if hasattr(item, 'dataType') and hasattr(item.dataType, 'toString'):
                                                    data_type = item.dataType.toString()
                                                    if "[" in data_type:
                                                        # 提取位宽信息
                                                        width_part = data_type.split("[")[1].split("]")[0]
                                                        width = width_part
        
                                                ports.append({"name": port_name, "direction": direction, "width": width})
                
                # 然后尝试从模块体中提取（如果头部没有）
                if not ports and hasattr(top_module, 'members'):

                    for member in top_module.members:
                        if hasattr(member, 'kind') and member.kind.name == 'PortDeclaration':
                            if hasattr(member, 'header') and hasattr(member.header, 'name'):
                                port_name = member.header.name.value if hasattr(member.header.name, 'value') else str(member.header.name)
                                direction = "input"  # 默认方向
                                if hasattr(member.header, 'direction') and hasattr(member.header.direction, 'name'):
                                    direction = member.header.direction.name.lower()
                                width = "1"
                                if hasattr(member.header, 'dataType') and hasattr(member.header.dataType, 'toString'):
                                    data_type = member.header.dataType.toString()
                                    if "[" in data_type:
                                        # 提取位宽信息
                                        width_part = data_type.split("[")[1].split("]")[0]
                                        width = width_part
                                ports.append({"name": port_name, "direction": direction, "width": width})
            except Exception:
                import traceback
                traceback.print_exc()
            
            # 6. 清空表格
            self.localparameter_table.setRowCount(0)
            self.parameter_table.setRowCount(0)
            self.port_table.setRowCount(0)
            
            # 7. 添加parameter信息到表格（先添加，以便localparameter和port可以引用）
            if parameters:
                for param in parameters:
                    row = self.parameter_table.rowCount()
                    self.parameter_table.insertRow(row)
                    self.parameter_table.setItem(row, 0, QTableWidgetItem(param["name"]))
                    self.parameter_table.setItem(row, 1, QTableWidgetItem(param["type"]))
                    # 使用safe_eval计算parameter值（处理数学运算）
                    param_value = self.safe_eval(str(param["default"]))
                    self.parameter_table.setItem(row, 2, QTableWidgetItem(param_value))
            
            # 8. 添加localparameter信息到表格（现在可以引用parameter了）
            if defines:
                for define in defines:
                    row = self.localparameter_table.rowCount()
                    self.localparameter_table.insertRow(row)
                    self.localparameter_table.setItem(row, 0, QTableWidgetItem(define["name"]))
                    self.localparameter_table.setItem(row, 1, QTableWidgetItem(define["type"]))
                    # 使用safe_eval计算localparameter值（处理parameter替换和数学运算）
                    define_value = self.safe_eval(str(define["default"]))
                    self.localparameter_table.setItem(row, 2, QTableWidgetItem(define_value))
            
            # 9. 添加port信息到表格
            if ports:
                for port in ports:
                    row = self.port_table.rowCount()
                    self.port_table.insertRow(row)
                    self.port_table.setItem(row, 0, QTableWidgetItem(port["name"]))
                    
                    direction_combo = QComboBox()
                    direction_combo.addItems(["input", "output", "inout"])
                    direction_combo.setCurrentText(port["direction"])
                    self.port_table.setCellWidget(row, 1, direction_combo)
                    
                    # 计算MSB、LSB和位宽
                    msb = "0"
                    lsb = "0"
                    width = port["width"]
                    
                    # 检查是否包含冒号
                    if ":" in width:
                        # 直接从位宽字符串中提取MSB和LSB
                        # 使用rfind找到最后一个冒号，以处理多维数组的情况
                        last_colon_idx = width.rfind(":")
                        if last_colon_idx != -1:
                            msb = width[:last_colon_idx].strip().replace("[", "")
                            lsb = width[last_colon_idx+1:].strip().replace("]", "")
                            # 位宽 = MSB - LSB + 1
                            width_value = f"({msb})-({lsb})+1"
                    elif "[" in width and "]" in width:
                        # 提取位宽信息
                        # 使用rfind找到最后一个]，以处理多维数组的情况
                        start_idx = width.find("[")
                        end_idx = width.rfind("]")
                        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                            width_part = width[start_idx+1:end_idx].strip()
                            if ":" in width_part:
                                # 格式为 [MSB:LSB]
                                last_colon_idx = width_part.rfind(":")
                                if last_colon_idx != -1:
                                    msb = width_part[:last_colon_idx].strip()
                                    lsb = width_part[last_colon_idx+1:].strip()
                                    # 位宽 = MSB - LSB + 1
                                    width_value = f"({msb})-({lsb})+1"
                            else:
                                # 只有位宽数值，如 [8]
                                width_value = width_part
                        else:
                            width_value = self.safe_eval(str(port["width"]))
                    else:
                        # 普通数值位宽
                        width_value = self.safe_eval(str(port["width"]))
                    
                    # 使用safe_eval计算位宽、MSB和LSB（处理parameter替换和数学运算）
                    width_value = self.safe_eval(width_value)
                    msb_value = self.safe_eval(msb)
                    lsb_value = self.safe_eval(lsb)
                    self.port_table.setItem(row, 2, QTableWidgetItem(width_value))
                    self.port_table.setItem(row, 3, QTableWidgetItem(msb_value))
                    self.port_table.setItem(row, 4, QTableWidgetItem(lsb_value))


            
        except ImportError:
            QMessageBox.warning(self, "警告", "pyslang库未安装，无法自动解析SystemVerilog文件")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"解析SystemVerilog文件时出错: {str(e)}")
    
    def add_define_row(self):
        """添加Define行"""
        # 移除现有的添加按钮行（如果存在）
        if self.localparameter_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.localparameter_table.rowCount() - 1, -1, -1):
                btn = self.localparameter_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.localparameter_table.removeRow(i)
                    break
        
        # 在表格末尾添加新的define行
        row = self.localparameter_table.rowCount()
        self.localparameter_table.insertRow(row)
        self.localparameter_table.setItem(row, 0, QTableWidgetItem(f"define_{row + 1}"))
        self.localparameter_table.setItem(row, 1, QTableWidgetItem("logic"))
        self.localparameter_table.setItem(row, 2, QTableWidgetItem("0"))
        
        # 添加删除按钮
        delete_button = QPushButton()
        delete_icon = QIcon("src/delete.svg")
        delete_button.setIcon(delete_icon)
        delete_button.setText(" ")
        delete_button.setToolTip("删除LocalParameter行")
        delete_button.setFlat(True)
        delete_button.clicked.connect(lambda checked, idx=row: self.remove_define_row(idx))
        self.localparameter_table.setCellWidget(row, 3, delete_button)
        self.add_define_lastrow()
        
    # 在表格末尾添加添加按钮行
    def add_define_lastrow(self):
        add_icon = QIcon("src/add.svg")
        add_button = QPushButton()
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加LocalParameter行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_define_row)
        add_row = self.localparameter_table.rowCount()
        self.localparameter_table.insertRow(add_row)
        self.localparameter_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.localparameter_table.setSpan(add_row, 0, 1, 4)
        self.localparameter_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    def remove_define_row(self, row=None):
        """删除Define行"""
        if row is None:
            row = self.localparameter_table.currentRow()
        if row >= 0:
            # 检查是否是添加按钮行
            btn = self.localparameter_table.cellWidget(row, 0)
            if isinstance(btn, QPushButton):
                return  # 不删除添加按钮行
            
            # 删除指定行
            self.localparameter_table.removeRow(row)
            
            # 更新剩余行的删除按钮连接
            for i in range(self.localparameter_table.rowCount()):
                btn = self.localparameter_table.cellWidget(i, 3)
                if isinstance(btn, QPushButton):
                    btn.disconnect()
                    btn.clicked.connect(lambda checked, idx=i: self.remove_define_row(idx))
            
            # 确保添加按钮在最后一行
            # 先检查是否已经有添加按钮行
            has_add_button = False
            for i in range(self.localparameter_table.rowCount()):
                btn = self.localparameter_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    has_add_button = True
                    if i != self.localparameter_table.rowCount() - 1:
                        # 添加按钮不在最后一行，移动它
                        self.localparameter_table.removeRow(i)
                        self.add_define_lastrow()
                    break
            
            if not has_add_button:
                # 没有添加按钮，添加一个
                self.add_define_define_row()
    
    def add_parameter_row(self):
        """添加Parameter行"""
        # 移除现有的添加按钮行（如果存在）
        if self.parameter_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.parameter_table.rowCount() - 1, -1, -1):
                btn = self.parameter_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.parameter_table.removeRow(i)
                    break
        
        # 在表格末尾添加新的parameter行
        row = self.parameter_table.rowCount()
        self.parameter_table.insertRow(row)
        self.parameter_table.setItem(row, 0, QTableWidgetItem(f"PARAM_{row + 1}"))
        self.parameter_table.setItem(row, 1, QTableWidgetItem("int"))
        self.parameter_table.setItem(row, 2, QTableWidgetItem(str(row + 1)))
        
        # 添加删除按钮
        delete_button = QPushButton()
        delete_icon = QIcon("src/delete.svg")
        delete_button.setIcon(delete_icon)
        delete_button.setText(" ")
        delete_button.setToolTip("删除Parameter行")
        delete_button.setFlat(True)
        delete_button.clicked.connect(lambda checked, idx=row: self.remove_parameter_row(idx))
        self.parameter_table.setCellWidget(row, 3, delete_button)
        self.add_parameter_lastrow()
        
    # 在表格末尾添加添加按钮行
    def add_parameter_lastrow(self):
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加Parameter行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_parameter_row)
        add_row = self.parameter_table.rowCount()
        self.parameter_table.insertRow(add_row)
        self.parameter_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.parameter_table.setSpan(add_row, 0, 1, 4)
        self.parameter_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    def add_port_map_lastrow(self):
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加PortMap行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_port_map_row)
        add_row = self.port_map_table.rowCount()
        self.port_map_table.insertRow(add_row)
        self.port_map_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.port_map_table.setSpan(add_row, 0, 1, 5)
        self.port_map_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    def on_physical_port_changed(self, row, index):
        """处理物理端口选择变化"""
        # 获取当前选择的端口
        physical_port_combo = self.port_map_table.cellWidget(row, 1)
        if not physical_port_combo:
            return
        
        # 获取之前选择的端口（如果有）
        previous_port = getattr(physical_port_combo, 'previous_port', None)
        
        # 获取当前选择的端口
        current_port = physical_port_combo.currentText()
        if current_port == "Select Port":
            current_port = None
        
        # 显示之前选择的端口对应的行
        if previous_port:
            for i in range(self.port_table.rowCount()):
                # 跳过添加按钮行
                btn = self.port_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    continue
                
                # 检查端口名称是否匹配
                port_name_item = self.port_table.item(i, 0)
                if port_name_item and port_name_item.text().strip() == previous_port:
                    self.port_table.setRowHidden(i, False)
                    break
        
        # 隐藏当前选择的端口对应的行
        if current_port:
            # 标记是否允许修改
            allow_change = True
            
            for i in range(self.port_table.rowCount()):
                # 跳过添加按钮行
                btn = self.port_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    continue
                
                # 检查端口名称是否匹配
                port_name_item = self.port_table.item(i, 0)
                if port_name_item and port_name_item.text().strip() == current_port:
                    # 检查选择的信号的位宽和方向是否与表格中的位宽和方向相同
                    # 获取port table中的方向和位宽
                    direction_widget = self.port_table.cellWidget(i, 1)
                    port_direction = direction_widget.currentText() if direction_widget else ""
                    
                    width_item = self.port_table.item(i, 2)
                    port_width = width_item.text() if width_item else ""
                    
                    # 获取port_map_table中的方向和位宽
                    map_direction_item = self.port_map_table.item(row, 2)
                    map_direction = map_direction_item.text() if map_direction_item else ""
                    
                    map_width_item = self.port_map_table.item(row, 3)
                    map_width = map_width_item.text() if map_width_item else ""
                    
                    # 方向映射：in <-> input, out <-> output
                    direction_map = {
                        "in": "input",
                        "input": "input",
                        "out": "output",
                        "output": "output",
                        "inout": "inout"
                    }
                    
                    # 获取标准化的方向
                    normalized_map_direction = direction_map.get(map_direction, map_direction)
                    normalized_port_direction = direction_map.get(port_direction, port_direction)
                    
                    # 检查方向是否相同
                    if normalized_port_direction != normalized_map_direction:
                        QMessageBox.warning(self, "警告", f"选择的端口 '{current_port}' 的方向 '{port_direction}' 与表格中的方向 '{map_direction}' 不匹配！")
                        allow_change = False
                    
                    # 检查位宽是否相同
                    if port_width != map_width:
                        QMessageBox.warning(self, "警告", f"选择的端口 '{current_port}' 的位宽 '{port_width}' 与表格中的位宽 '{map_width}' 不匹配！")
                        allow_change = False
                    break
            
            if allow_change:
                # 隐藏当前选择的端口对应的行
                for i in range(self.port_table.rowCount()):
                    # 跳过添加按钮行
                    btn = self.port_table.cellWidget(i, 0)
                    if isinstance(btn, QPushButton):
                        continue
                    
                    # 检查端口名称是否匹配
                    port_name_item = self.port_table.item(i, 0)
                    if port_name_item and port_name_item.text().strip() == current_port:
                        self.port_table.setRowHidden(i, True)
                        break
                
                # 更新 bus_interface_port_maps 字典
                if self.current_bus_interface_row is not None:
                    logical_port_item = self.port_map_table.item(row, 0)
                    if logical_port_item:
                        logical_port = logical_port_item.text().strip()
                        if self.current_bus_interface_row in self.bus_interface_port_maps:
                            if current_port:
                                self.bus_interface_port_maps[self.current_bus_interface_row][logical_port] = current_port
                            elif logical_port in self.bus_interface_port_maps[self.current_bus_interface_row]:
                                del self.bus_interface_port_maps[self.current_bus_interface_row][logical_port]
                
                # 保存当前选择的端口
                physical_port_combo.previous_port = current_port
            else:
                # 恢复下拉菜单的选择到之前的值
                if previous_port:
                    index = physical_port_combo.findText(previous_port)
                    if index != -1:
                        # 暂时断开信号连接，避免递归调用
                        physical_port_combo.currentIndexChanged.disconnect()
                        physical_port_combo.setCurrentIndex(index)
                        physical_port_combo.currentIndexChanged.connect(lambda index, r=row: self.on_physical_port_changed(r, index))
                        
                        # 重新隐藏之前选择的端口对应的行
                        for i in range(self.port_table.rowCount()):
                            # 跳过添加按钮行
                            btn = self.port_table.cellWidget(i, 0)
                            if isinstance(btn, QPushButton):
                                continue
                            
                            # 检查端口名称是否匹配
                            port_name_item = self.port_table.item(i, 0)
                            if port_name_item and port_name_item.text().strip() == previous_port:
                                self.port_table.setRowHidden(i, True)
                                break
                else:
                    # 如果之前没有选择，恢复到"Select Port"
                    index = physical_port_combo.findText("Select Port")
                    if index != -1:
                        # 暂时断开信号连接，避免递归调用
                        physical_port_combo.currentIndexChanged.disconnect()
                        physical_port_combo.setCurrentIndex(index)
                        physical_port_combo.currentIndexChanged.connect(lambda index, r=row: self.on_physical_port_changed(r, index))
        else:
            # 如果取消选择端口，更新字典删除该映射
            if self.current_bus_interface_row is not None:
                logical_port_item = self.port_map_table.item(row, 0)
                if logical_port_item:
                    logical_port = logical_port_item.text().strip()
                    if self.current_bus_interface_row in self.bus_interface_port_maps:
                        if logical_port in self.bus_interface_port_maps[self.current_bus_interface_row]:
                            del self.bus_interface_port_maps[self.current_bus_interface_row][logical_port]
            physical_port_combo.previous_port = current_port
        
        # 保存当前行的选择
        current_row_selection = physical_port_combo.currentText()
        
        # 更新所有行的下拉菜单内容
        self.update_all_port_map_combos(row, current_row_selection)
    
    def get_port_signals(self):
        """获取port table中的信号列表"""
        port_signals = []
        for i in range(self.port_table.rowCount()):
            # 跳过添加按钮行
            btn = self.port_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            
            # 检查行是否隐藏
            if self.port_table.isRowHidden(i):
                continue
            
            # 获取端口名称
            port_name_item = self.port_table.item(i, 0)
            if port_name_item:
                port_signals.append(port_name_item.text().strip())
        return port_signals
    
    def get_port_signals_with_direction(self, direction, current_row=None, current_restore_port=None):
        """获取与给定方向一致且未被其他行选中的端口列表"""
        port_signals = []
        
        # 获取当前port_map_table中所有已被选中的端口
        selected_ports = []
        for i in range(self.port_map_table.rowCount()):
            # 跳过当前行
            if i == current_row:
                continue
            
            # 获取物理端口
            physical_port_combo = self.port_map_table.cellWidget(i, 1)
            if physical_port_combo:
                selected_port = physical_port_combo.currentText()
                if selected_port and selected_port != "Select Port":
                    selected_ports.append(selected_port)
        
        # 获取当前行的选择（如果有）
        current_row_selection = None
        if current_row is not None:
            current_combo = self.port_map_table.cellWidget(current_row, 1)
            if current_combo:
                current_row_selection = current_combo.currentText()
                if current_row_selection == "Select Port":
                    current_row_selection = None
        
        # 获取其他bus interface行选中的端口（从bus_interface_port_maps字典中获取）
        # 这样即使port_map_table被清空，也能检测到冲突
        if self.current_bus_interface_row is not None:
            for bus_row, port_map in self.bus_interface_port_maps.items():
                # 跳过当前bus interface行（它的映射会在下面单独处理）
                if bus_row == self.current_bus_interface_row:
                    continue
                # 添加该bus interface行选中的所有端口
                for physical_port in port_map.values():
                    if physical_port and physical_port not in selected_ports:
                        selected_ports.append(physical_port)
        
        for i in range(self.port_table.rowCount()):
            # 跳过添加按钮行
            btn = self.port_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            
            # 检查行是否隐藏
            if self.port_table.isRowHidden(i):
                continue
            
            # 获取端口名称
            port_name_item = self.port_table.item(i, 0)
            if port_name_item:
                port_name = port_name_item.text().strip()
                
                # 检查端口是否已被其他行选中，当前行的选择和要恢复的端口除外
                if port_name in selected_ports and port_name != current_row_selection and port_name != current_restore_port:
                    continue
                
                # 获取端口方向
                direction_widget = self.port_table.cellWidget(i, 1)
                port_direction = direction_widget.currentText() if direction_widget else ""
                
                # 方向映射：in <-> input, out <-> output
                direction_map = {
                    "in": "input",
                    "input": "input",
                    "out": "output",
                    "output": "output",
                    "inout": "inout"
                }
                
                # 获取标准化的方向
                normalized_direction = direction_map.get(direction, direction)
                normalized_port_direction = direction_map.get(port_direction, port_direction)
                
                # 检查方向是否一致
                if normalized_port_direction == normalized_direction:
                    port_signals.append((port_name, port_direction))
        return port_signals
    
    def update_all_port_map_combos(self, current_row=None, current_row_selection=None):
        """更新所有port map行的下拉菜单内容"""
        for row in range(self.port_map_table.rowCount()):
            # 跳过添加按钮行
            item = self.port_map_table.item(row, 0)
            if item and item.text() == "":
                continue
            
            # 获取当前行的方向
            direction_item = self.port_map_table.item(row, 2)
            if not direction_item:
                continue
            direction = direction_item.text()
            if not direction:
                continue
            
            # 获取当前下拉菜单
            physical_port_combo = self.port_map_table.cellWidget(row, 1)
            if not physical_port_combo:
                continue
            
            # 如果是当前行，跳过处理
            if row == current_row:
                continue
            
            # 检查当前行的选择是否与新选中的text相同
            if current_row_selection and current_row_selection != "Select Port":
                row_selection = physical_port_combo.currentText()
                if row_selection == current_row_selection:
                    # 报错
                    QMessageBox.warning(self, "警告", f"端口 '{current_row_selection}' 已经被其他行选中！")
                    continue
            
            # 保存当前选择
            current_selection = physical_port_combo.currentText()
            
            # 清空下拉菜单
            # 暂时断开信号连接，避免递归调用
            physical_port_combo.currentIndexChanged.disconnect()
            physical_port_combo.clear()
            
            # 添加可用的端口
            port_signals = self.get_port_signals_with_direction(direction, row)
            for port_signal, port_dir in port_signals:
                # 排除新选中的text
                if current_row_selection and port_signal == current_row_selection:
                    continue
                physical_port_combo.addItem(port_signal)
            
            physical_port_combo.addItem(current_selection)

            # 恢复之前的选择（如果仍然可用）
            if current_selection:
                index = physical_port_combo.findText(current_selection)
                # 之前选择的项必然不再可选项中，否则报错
                if index != -1:
                    physical_port_combo.setCurrentIndex(index)
                    # 保存当前选择
                    physical_port_combo.previous_port = current_selection
                else:
                    # 如果之前的选择不再可用，设置为"Select Port"
                    physical_port_combo.setCurrentIndex(0)
                    # 保存当前选择
                    physical_port_combo.previous_port = None
            
            # 重新连接信号
            physical_port_combo.currentIndexChanged.connect(lambda index, r=row: self.on_physical_port_changed(r, index))
    
    def accept(self):
        """点击确定按钮时，保存bus interface和port map两个table中的信息到xml文件中"""
        
        # 在保存前检查是否已存在同名同版本的component
        name = self.name_input.text().strip()
        version = self.version_input.text().strip()
        
        # 获取parent中的components列表
        if self.parent() and hasattr(self.parent(), 'components'):
            for existing_component in self.parent().components:
                existing_name = existing_component.get('name', '')
                existing_version = existing_component.get('version', '')
                if existing_name == name and existing_version == version:
                    QMessageBox.warning(self, "警告", f"已存在同名同版本的Component: {name} v{version}，请修改名称或版本号")
                    return  # 不关闭对话框，保留用户的工作
        
        # 收集component基本信息
        component_data = {
            'vendor': self.vendor_input.text().strip(),
            'library': self.library_input.text().strip(),
            'name': name,
            'version': version,
            'description': '',  # 使用默认值，因为没有description_input属性
            'ports': [],
            'bus_interfaces': [],
            'port_maps': [],
            'defines': [],
            'parameters': []
        }
        
        # 收集port table中的端口信息
        for i in range(self.port_table.rowCount()):
            # 跳过添加按钮行
            btn = self.port_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            
            # 获取端口名称
            port_name_item = self.port_table.item(i, 0)
            if not port_name_item:
                continue
            port_name = port_name_item.text().strip()
            if not port_name:
                continue
            
            # 获取端口方向
            direction_widget = self.port_table.cellWidget(i, 1)
            port_direction = direction_widget.currentText() if direction_widget else "input"
            
            # 获取端口位宽
            width_item = self.port_table.item(i, 2)
            port_width = width_item.text().strip() if width_item else "1"
            
            # 添加端口信息
            component_data['ports'].append({
                'name': port_name,
                'direction': port_direction,
                'width': port_width
            })
        
        # 收集bus interface table中的信息
        for i in range(self.bus_interface_table.rowCount()):
            # 跳过添加按钮行
            btn = self.bus_interface_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            
            # 获取bus interface名称
            interface_name_item = self.bus_interface_table.item(i, 0)
            if not interface_name_item:
                continue
            interface_name = interface_name_item.text().strip()
            if not interface_name:
                continue
            
            # 获取bus type（第1列是QComboBox）
            bus_type_combo = self.bus_interface_table.cellWidget(i, 1)
            bus_type = bus_type_combo.currentText() if bus_type_combo else "AXI4"
            
            # 获取mode（第2列是QComboBox）
            mode_widget = self.bus_interface_table.cellWidget(i, 2)
            mode = mode_widget.currentText() if mode_widget else "master"
            
            # 添加bus interface信息
            component_data['bus_interfaces'].append({
                'name': interface_name,
                'bus_type': bus_type,
                'mode': mode,
                'vendor': 'Phytium',
                'library': 'LowSpeedDevice',
                'version': '1.0'
            })
        
        # 收集port map table中的信息
        for i in range(self.port_map_table.rowCount()):
            # 获取逻辑端口
            logical_port_item = self.port_map_table.item(i, 0)
            if not logical_port_item:
                continue
            logical_port = logical_port_item.text().strip()
            if not logical_port:
                continue
            
            # 获取物理端口
            physical_port_combo = self.port_map_table.cellWidget(i, 1)
            if not physical_port_combo:
                continue
            physical_port = physical_port_combo.currentText()
            if physical_port == "Select Port":
                physical_port = ""
            
            # 获取bus interface
            interface_item = self.port_map_table.item(i, 4)
            if not interface_item:
                continue
            interface_name = interface_item.text().strip()
            if not interface_name:
                continue
            
            # 添加port map信息
            component_data['port_maps'].append({
                'logical_port': logical_port,
                'physical_port': physical_port,
                'bus_interface': interface_name
            })
        
        # 收集define信息
        for i in range(self.localparameter_table.rowCount()):
            # 获取define名称
            define_name_item = self.localparameter_table.item(i, 0)
            if not define_name_item:
                continue
            define_name = define_name_item.text().strip()
            if not define_name:
                continue
            
            # 获取define类型
            define_type_item = self.localparameter_table.item(i, 1)
            define_type = define_type_item.text().strip() if define_type_item else "int"
            
            # 获取define默认值
            define_default_item = self.localparameter_table.item(i, 2)
            define_default = define_default_item.text().strip() if define_default_item else ""
            
            # 添加define信息
            component_data['defines'].append({
                'name': define_name,
                'type': define_type,
                'default': define_default
            })
        
        # 收集parameter信息
        for i in range(self.parameter_table.rowCount()):
            # 获取parameter名称
            param_name_item = self.parameter_table.item(i, 0)
            if not param_name_item:
                continue
            param_name = param_name_item.text().strip()
            if not param_name:
                continue
            
            # 获取parameter类型
            param_type_item = self.parameter_table.item(i, 1)
            param_type = param_type_item.text().strip() if param_type_item else "int"
            
            # 获取parameter默认值
            param_default_item = self.parameter_table.item(i, 2)
            param_default = param_default_item.text().strip() if param_default_item else ""
            
            # 添加parameter信息
            component_data['parameters'].append({
                'name': param_name,
                'type': param_type,
                'default': param_default
            })
        
        # 选择保存文件路径
        file_path = ""
        # 检查是否已经设置了library目录
        library_dirs = []
        # 检查父窗口是否有library_directories或library_directory属性
        if self.parent():
            if hasattr(self.parent(), 'library_directories') and self.parent().library_directories:
                library_dirs = self.parent().library_directories
            elif hasattr(self.parent(), 'library_directory') and self.parent().library_directory:
                library_dirs = [self.parent().library_directory]
            # 如果父窗口是ComponentListWidget，检查它的main_window属性
            elif hasattr(self.parent(), 'main_window') and self.parent().main_window:
                if hasattr(self.parent().main_window, 'library_directories') and self.parent().main_window.library_directories:
                    library_dirs = self.parent().main_window.library_directories
                elif hasattr(self.parent().main_window, 'library_directory') and self.parent().main_window.library_directory:
                    library_dirs = [self.parent().main_window.library_directory]
        
        # 如果没有设置library目录，使用默认路径
        if not library_dirs:
            default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library")
            if os.path.exists(default_dir):
                library_dirs = [default_dir]
        
        if len(library_dirs) == 1:
            # 只有一个library目录，直接使用
            library_dir = library_dirs[0]
        elif len(library_dirs) > 1:
            # 有多个library目录，让用户选择
            items = [os.path.basename(d) for d in library_dirs]
            item, ok = QInputDialog.getItem(self, "选择保存目录", "请选择要保存的Library目录:", items, 0, False)
            if ok and item:
                # 找到用户选择的目录
                selected_name = item
                for d in library_dirs:
                    if os.path.basename(d) == selected_name:
                        library_dir = d
                        break
            else:
                return
        else:
            # 没有library目录，让用户选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存Component文件", "", "XML文件 (*.xml)"
            )
            if not file_path:
                return
            # 保存到用户选择的路径
            writer = IPXactWriter()
            success = writer.create_component_file(file_path, component_data)
            if success:
                QMessageBox.information(self, "成功", f"Component文件保存成功: {file_path}")
                self.edited_component_data = component_data
                super().accept()
            else:
                QMessageBox.warning(self, "失败", "Component文件保存失败！")
            return
        
        if library_dir:
            # 使用library_dir作为保存路径
            component_name = component_data.get('name', 'NewComponent')
            version = component_data.get('version', '1.0')
            file_name = f"{component_name}_{version.replace('.', '_')}.xml"
            file_path = os.path.join(library_dir, "IP", file_name)
            os.makedirs(os.path.join(library_dir, "IP"), exist_ok=True)
        if not file_path:
            return
        
        # 保存到XML文件
        writer = IPXactWriter()
        success = writer.create_component_file(file_path, component_data)
        
        if success:
            QMessageBox.information(self, "成功", f"Component文件保存成功: {file_path}")
            self.edited_component_data = component_data
            super().accept()
        else:
            QMessageBox.warning(self, "失败", "Component文件保存失败！")
    
    def remove_port_map_row(self, row=None):
        """删除PortMap行"""
        if row is None:
            row = self.port_map_table.currentRow()
        if row >= 0:
            # 检查是否是添加按钮行
            btn = self.port_map_table.cellWidget(row, 0)
            if isinstance(btn, QPushButton):
                return  # 不删除添加按钮行
            
            # 获取当前行的物理端口
            physical_port_combo = self.port_map_table.cellWidget(row, 1)
            if physical_port_combo:
                current_port = physical_port_combo.currentText()
                if current_port and current_port != "Select Port":
                    # 显示对应的port table行
                    for i in range(self.port_table.rowCount()):
                        # 跳过添加按钮行
                        port_btn = self.port_table.cellWidget(i, 0)
                        if isinstance(port_btn, QPushButton):
                            continue
                        
                        # 检查端口名称是否匹配
                        port_name_item = self.port_table.item(i, 0)
                        if port_name_item and port_name_item.text().strip() == current_port:
                            self.port_table.setRowHidden(i, False)
                            break
            
            # 删除指定行
            self.port_map_table.removeRow(row)
            
            # 更新剩余行的删除按钮连接
            for i in range(self.port_map_table.rowCount()):
                btn = self.port_map_table.cellWidget(i, 5)
                if isinstance(btn, QPushButton):
                    btn.disconnect()
                    btn.clicked.connect(lambda checked, idx=i: self.remove_port_map_row(idx))
            
    def add_bus_interface_row(self):
        """添加BusInterface行"""
        # 移除现有的添加按钮行（如果存在）
        if self.bus_interface_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.bus_interface_table.rowCount() - 1, -1, -1):
                btn = self.bus_interface_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.bus_interface_table.removeRow(i)
                    break
        
        # 扫描library/busdef目录下的所有总线定义
        bus_defs = []
        library_dirs = []

        if self.parent():
            if hasattr(self.parent(), 'library_directories'):
                library_dirs = self.parent().library_directories
            elif hasattr(self.parent(), 'library_directory'):
                library_dir = self.parent().library_directory
                if library_dir:
                    library_dirs = [library_dir]

        if not library_dirs:
            default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library")
            if os.path.exists(default_dir):
                library_dirs = [default_dir]

        for library_dir in library_dirs:
            busdef_dir = os.path.join(library_dir, "busdef")
            if os.path.exists(busdef_dir):
                for file_name in os.listdir(busdef_dir):
                    if file_name.endswith(".xml"):
                        file_path = os.path.join(busdef_dir, file_name)
                        try:
                            tree = ET.parse(file_path)
                            root = tree.getroot()
                            name_elem = root.find(".//{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name")
                            if name_elem is not None and name_elem.text not in bus_defs:
                                bus_defs.append(name_elem.text)
                        except Exception as e:
                            print(f"解析总线定义文件 {file_name} 时出错: {e}")
        
        # 如果没有找到总线定义，添加默认值
        if not bus_defs:
            bus_defs = ["amba4.axi4", "amba4.apb", "amba4.ahb"]
        
        # 在表格末尾添加新的bus interface行
        row = self.bus_interface_table.rowCount()
        self.bus_interface_table.insertRow(row)
        self.bus_interface_table.setItem(row, 0, QTableWidgetItem(""))  # 默认Name列为空
        
        # 初始化该bus interface的port map信息字典
        # 使用row作为唯一标识（因为Name可能为空）
        self.bus_interface_port_maps[row] = {}
        
        # 第2列：总线类型下拉菜单
        bus_type_combo = QComboBox()
        bus_type_combo.addItems(bus_defs)
        bus_type_combo.setCurrentText("amba4.axi4")
        self.bus_interface_table.setCellWidget(row, 1, bus_type_combo)
        
        # 第3列：模式下拉菜单
        mode_combo = QComboBox()
        mode_combo.addItems(["master", "slave"])
        mode_combo.setCurrentText("master")
        self.bus_interface_table.setCellWidget(row, 2, mode_combo)
        
        # 添加删除按钮
        delete_button = QPushButton()
        delete_icon = QIcon("src/delete.svg")
        delete_button.setIcon(delete_icon)
        delete_button.setText(" ")
        delete_button.setToolTip("删除BusInterface行")
        delete_button.setFlat(True)
        delete_button.clicked.connect(lambda checked, idx=row: self.remove_bus_interface_row(idx))
        self.bus_interface_table.setCellWidget(row, 3, delete_button)
        self.add_bus_interface_lastrow()
        
    # 在表格末尾添加添加按钮行
    def add_bus_interface_lastrow(self):
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加BusInterface行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_bus_interface_row)
        add_row = self.bus_interface_table.rowCount()
        self.bus_interface_table.insertRow(add_row)
        self.bus_interface_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.bus_interface_table.setSpan(add_row, 0, 1, 4)
        self.bus_interface_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    def remove_bus_interface_row(self, row=None):
        """删除BusInterface行"""
        if row is None:
            row = self.bus_interface_table.currentRow()
        if row >= 0:
            # 检查是否是添加按钮行
            btn = self.bus_interface_table.cellWidget(row, 0)
            if isinstance(btn, QPushButton):
                return  # 不删除添加按钮行
            
            # 删除指定行
            self.bus_interface_table.removeRow(row)
            
            # 更新剩余行的删除按钮连接
            for i in range(self.bus_interface_table.rowCount()):
                btn = self.bus_interface_table.cellWidget(i, 3)
                if isinstance(btn, QPushButton):
                    btn.disconnect()
                    btn.clicked.connect(lambda checked, idx=i: self.remove_bus_interface_row(idx))
            
            # 确保添加按钮在最后一行
            # 先检查是否已经有添加按钮行
            has_add_button = False
            for i in range(self.bus_interface_table.rowCount()):
                btn = self.bus_interface_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    has_add_button = True
                    if i != self.bus_interface_table.rowCount() - 1:
                        # 添加按钮不在最后一行，移动它
                        self.bus_interface_table.removeRow(i)
                        self.add_bus_interface_lastrow()
                    break
            
            if not has_add_button:
                # 没有添加按钮，添加一个
                self.add_bus_interface_lastrow()
    
    def add_port_map_row(self):
        """添加PortMap行"""
        
        # 在表格末尾添加新的port map行
        row = self.port_map_table.rowCount()
        self.port_map_table.insertRow(row)
        self.port_map_table.setItem(row, 0, QTableWidgetItem(f"logical_port_{row + 1}"))
        
        # 物理端口（下拉菜单）
        physical_port_combo = QComboBox()
        physical_port_combo.addItem("Select Port")
        # 获取port table中的信号列表
        port_signals = self.get_port_signals()
        for port_signal in port_signals:
            physical_port_combo.addItem(port_signal)
        # 连接信号
        physical_port_combo.currentIndexChanged.connect(lambda index, r=row: self.on_physical_port_changed(r, index))
        self.port_map_table.setCellWidget(row, 1, physical_port_combo)
        
        # Port Direction
        self.port_map_table.setItem(row, 2, QTableWidgetItem(""))
        
        # Port Width
        self.port_map_table.setItem(row, 3, QTableWidgetItem(""))
        
        self.port_map_table.setItem(row, 4, QTableWidgetItem("bus_interface_1"))
        
    def remove_parameter_row(self, row=None):
        """删除Parameter行"""
        if row is None:
            row = self.parameter_table.currentRow()
        if row >= 0:
            # 检查是否是添加按钮行
            btn = self.parameter_table.cellWidget(row, 0)
            if isinstance(btn, QPushButton):
                return  # 不删除添加按钮行
            
            # 删除指定行
            self.parameter_table.removeRow(row)
            
            # 更新剩余行的删除按钮连接
            for i in range(self.parameter_table.rowCount()):
                btn = self.parameter_table.cellWidget(i, 3)
                if isinstance(btn, QPushButton):
                    btn.disconnect()
                    btn.clicked.connect(lambda checked, idx=i: self.remove_parameter_row(idx))
            
            # 确保添加按钮在最后一行
            # 先检查是否已经有添加按钮行
            has_add_button = False
            for i in range(self.parameter_table.rowCount()):
                btn = self.parameter_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    has_add_button = True
                    if i != self.parameter_table.rowCount() - 1:
                        # 添加按钮不在最后一行，移动它
                        self.parameter_table.removeRow(i)
                        self.add_parameter_lastrow()
                    break
            
            if not has_add_button:
                # 没有添加按钮，添加一个
                self.add_parameter_lastrow()
    
    def add_port_row(self):
        """添加Port行"""
        # 移除现有的添加按钮行（如果存在）
        if self.port_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.port_table.rowCount() - 1, -1, -1):
                btn = self.port_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.port_table.removeRow(i)
                    break
        
        # 在表格末尾添加新的port行
        row = self.port_table.rowCount()
        self.port_table.insertRow(row)
        self.port_table.setItem(row, 0, QTableWidgetItem(f"port_{row + 1}"))
        
        direction_combo = QComboBox()
        direction_combo.addItems(["input", "output", "inout"])
        self.port_table.setCellWidget(row, 1, direction_combo)
        
        self.port_table.setItem(row, 2, QTableWidgetItem("1"))
        self.port_table.setItem(row, 3, QTableWidgetItem("0"))
        self.port_table.setItem(row, 4, QTableWidgetItem("0"))
        
        # 添加删除按钮
        delete_button = QPushButton()
        delete_icon = QIcon("src/delete.svg")
        delete_button.setIcon(delete_icon)
        delete_button.setText(" ")
        delete_button.setToolTip("删除Port行")
        delete_button.setFlat(True)
        delete_button.clicked.connect(lambda checked, idx=row: self.remove_port_row(idx))
        self.port_table.setCellWidget(row, 5, delete_button)
        self.add_port_lastrow()
        
    # 在表格末尾添加添加按钮行
    def add_port_lastrow(self):
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加Port行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_port_row)
        add_row = self.port_table.rowCount()
        self.port_table.insertRow(add_row)
        self.port_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.port_table.setSpan(add_row, 0, 1, 6)
        self.port_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    def remove_port_row(self, row=None):
        """删除Port行"""
        if row is None:
            row = self.port_table.currentRow()
        if row >= 0:
            # 检查是否是添加按钮行
            btn = self.port_table.cellWidget(row, 0)
            if isinstance(btn, QPushButton):
                return  # 不删除添加按钮行
            
            # 删除指定行
            self.port_table.removeRow(row)
            
            # 更新剩余行的删除按钮连接
            for i in range(self.port_table.rowCount()):
                btn = self.port_table.cellWidget(i, 5)
                if isinstance(btn, QPushButton):
                    btn.disconnect()
                    btn.clicked.connect(lambda checked, idx=i: self.remove_port_row(idx))
            
            # 确保添加按钮在最后一行
            # 先检查是否已经有添加按钮行
            has_add_button = False
            for i in range(self.port_table.rowCount()):
                btn = self.port_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    has_add_button = True
                    if i != self.port_table.rowCount() - 1:
                        # 添加按钮不在最后一行，移动它
                        self.port_table.removeRow(i)
                        self.add_port_lastrow()
                    break
            
            if not has_add_button:
                self.add_port_lastrow()
    
    def get_values(self):
        """获取输入值并返回component数据"""
        vendor = self.vendor_input.text().strip()
        library = self.library_input.text().strip()
        name = self.name_input.text().strip()
        version = self.version_input.text().strip()
        sv_file = self.sv_file_input.text().strip()
        
        # 收集Define信息
        defines = []
        for i in range(self.localparameter_table.rowCount()):
            # 跳过添加按钮行
            btn = self.localparameter_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            define_name = self.localparameter_table.item(i, 0).text().strip()
            define_type = self.localparameter_table.item(i, 1).text().strip()
            define_value = self.localparameter_table.item(i, 2).text().strip()
            if define_name:
                defines.append({"name": define_name, "type": define_type, "default": define_value})
        
        # 收集Parameter信息
        parameters = []
        for i in range(self.parameter_table.rowCount()):
            # 跳过添加按钮行
            btn = self.parameter_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            param_name = self.parameter_table.item(i, 0).text().strip()
            param_type = self.parameter_table.item(i, 1).text().strip()
            param_default = self.parameter_table.item(i, 2).text().strip()
            if param_name:
                parameters.append({"name": param_name, "type": param_type, "default": param_default})
        
        # 收集Port信息
        ports = []
        for i in range(self.port_table.rowCount() - 1):  # 不包括添加按钮所在的行
            port_name = self.port_table.item(i, 0).text().strip()
            direction_widget = self.port_table.cellWidget(i, 1)
            direction = direction_widget.currentText() if direction_widget else "input"
            width = self.port_table.item(i, 2).text().strip()
            msb = self.port_table.item(i, 3).text().strip() if self.port_table.item(i, 3) else "0"
            lsb = self.port_table.item(i, 4).text().strip() if self.port_table.item(i, 4) else "0"
            if port_name:
                ports.append({"name": port_name, "direction": direction, "width": width, "msb": msb, "lsb": lsb})
        
        # 收集BusInterface信息
        bus_interfaces = []
        for i in range(self.bus_interface_table.rowCount()):
            # 跳过添加按钮行
            btn = self.bus_interface_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            interface_name = self.bus_interface_table.item(i, 0).text().strip()
            bus_type_widget = self.bus_interface_table.cellWidget(i, 1)
            bus_type = bus_type_widget.currentText() if bus_type_widget else "amba4.axi4"
            mode_widget = self.bus_interface_table.cellWidget(i, 2)
            mode = mode_widget.currentText() if mode_widget else "master"
            if interface_name:
                bus_interfaces.append({"name": interface_name, "bus_type": bus_type, "mode": mode})
        
        # 收集PortMap信息
        port_maps = []
        for i in range(self.port_map_table.rowCount()):
            # 跳过添加按钮行
            btn = self.port_map_table.cellWidget(i, 0)
            if isinstance(btn, QPushButton):
                continue
            logical_port = self.port_map_table.item(i, 0).text().strip()
            # Physical Port 是 QComboBox，需要用 cellWidget 获取
            physical_port_combo = self.port_map_table.cellWidget(i, 1)
            physical_port = physical_port_combo.currentText().strip() if physical_port_combo else ""
            bus_interface = self.port_map_table.item(i, 4).text().strip() if self.port_map_table.item(i, 4) else ""
            if logical_port and physical_port and physical_port != "Select Port":
                port_maps.append({"logical_port": logical_port, "physical_port": physical_port, "bus_interface": bus_interface})
        
        return {
            "vendor": vendor,
            "library": library,
            "name": name,
            "version": version,
            "sv_file": sv_file,
            "defines": defines,
            "parameters": parameters,
            "ports": ports,
            "bus_interfaces": bus_interfaces,
            "port_maps": port_maps
        }

    def fill_port_table(self, ports):
        if self.port_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.port_table.rowCount() - 1, -1, -1):
                btn = self.port_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.port_table.removeRow(i)
                    break
        
        self.port_table.setRowCount(len(ports))
        for i, port in enumerate(ports):
            self.port_table.setItem(i, 0, QTableWidgetItem(port.get('name', '')))
            # 方向下拉菜单
            direction_combo = QComboBox()
            direction_combo.addItems(["input", "output", "inout"])
            # 映射XML中的direction值到下拉菜单选项
            direction_map = {
                'in': 'input',
                'out': 'output',
                'inout': 'inout'
            }
            xml_direction = port.get('direction', 'input')
            combo_direction = direction_map.get(xml_direction, 'input')
            direction_combo.setCurrentText(combo_direction)
            self.port_table.setCellWidget(i, 1, direction_combo)
            # 使用safe_eval计算公式
            width_value = self.safe_eval(str(port.get('width', '1')))
            self.port_table.setItem(i, 2, QTableWidgetItem(width_value))
            msb_value = self.safe_eval(str(port.get('msb', '0')))
            self.port_table.setItem(i, 3, QTableWidgetItem(msb_value))
            lsb_value = self.safe_eval(str(port.get('lsb', '0')))
            self.port_table.setItem(i, 4, QTableWidgetItem(lsb_value))
            # 添加删除按钮
            delete_button = QPushButton()
            delete_icon = QIcon("src/delete.svg")
            delete_button.setIcon(delete_icon)
            delete_button.setText(" ")
            delete_button.setToolTip("删除Port行")
            delete_button.setFlat(True)
            delete_button.clicked.connect(lambda checked, idx=i: self.remove_port_row(idx))
            self.port_table.setCellWidget(i, 5, delete_button)
    
        # 在表格末尾添加添加按钮行
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加Port行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_port_row)
        add_row = self.port_table.rowCount()
        self.port_table.insertRow(add_row)
        self.port_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.port_table.setSpan(add_row, 0, 1, 6)
        self.port_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    # 填充Define信息
    def fill_define_table(self, defines):
        if self.localparameter_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.localparameter_table.rowCount() - 1, -1, -1):
                btn = self.localparameter_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.localparameter_table.removeRow(i)
                    break
        
        self.localparameter_table.setRowCount(len(defines))
        for i, define in enumerate(defines):
            self.localparameter_table.setItem(i, 0, QTableWidgetItem(define.get('name', '')))
            self.localparameter_table.setItem(i, 1, QTableWidgetItem(define.get('type', 'int')))
            # 使用safe_eval计算公式
            default_value = self.safe_eval(str(define.get('default', '')))
            self.localparameter_table.setItem(i, 2, QTableWidgetItem(default_value))
            # 添加删除按钮
            delete_button = QPushButton()
            delete_icon = QIcon("src/delete.svg")
            delete_button.setIcon(delete_icon)
            delete_button.setText(" ")
            delete_button.setToolTip("删除LocalParameter行")
            delete_button.setFlat(True)
            delete_button.clicked.connect(lambda checked, idx=i: self.remove_define_row(idx))
            self.localparameter_table.setCellWidget(i, 3, delete_button)
    
        self.add_define_lastrow()
    
    # 填充Parameter信息
    def fill_parameter_table(self, parameters):
        if self.parameter_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.parameter_table.rowCount() - 1, -1, -1):
                btn = self.parameter_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.parameter_table.removeRow(i)
                    break
        
        self.parameter_table.setRowCount(len(parameters))
        for i, param in enumerate(parameters):
            self.parameter_table.setItem(i, 0, QTableWidgetItem(param.get('name', '')))
            self.parameter_table.setItem(i, 1, QTableWidgetItem(param.get('type', 'int')))
            # 使用safe_eval计算公式
            default_value = self.safe_eval(str(param.get('default', '')))
            self.parameter_table.setItem(i, 2, QTableWidgetItem(default_value))
            # 添加删除按钮
            delete_button = QPushButton()
            delete_icon = QIcon("src/delete.svg")
            delete_button.setIcon(delete_icon)
            delete_button.setText(" ")
            delete_button.setToolTip("删除Parameter行")
            delete_button.setFlat(True)
            delete_button.clicked.connect(lambda checked, idx=i: self.remove_parameter_row(idx))
            self.parameter_table.setCellWidget(i, 3, delete_button)
    
        # 在表格末尾添加添加按钮行
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加Parameter行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_parameter_row)
        add_row = self.parameter_table.rowCount()
        self.parameter_table.insertRow(add_row)
        self.parameter_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.parameter_table.setSpan(add_row, 0, 1, 4)
        self.parameter_table.setItem(add_row, 0, QTableWidgetItem(""))

    # 填充BusInterface信息
    def fill_bus_interface_table(self, bus_interfaces):
        if self.bus_interface_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.bus_interface_table.rowCount() - 1, -1, -1):
                btn = self.bus_interface_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.bus_interface_table.removeRow(i)
                    break
        
        # 初始化bus_interface_port_maps字典
        self.bus_interface_port_maps = {}
        
        self.bus_interface_table.setRowCount(len(bus_interfaces))
        for i, bus_interface in enumerate(bus_interfaces):
            # Name
            self.bus_interface_table.setItem(i, 0, QTableWidgetItem(bus_interface.get('name', '')))
            
            # Bus Type下拉菜单
            bus_type_combo = QComboBox()
            bus_type_combo.addItems(["amba4.axi4", "amba4.apb", "amba4.ahb"])
            bus_type_combo.setCurrentText(bus_interface.get('bus_type', 'amba4.axi4'))
            self.bus_interface_table.setCellWidget(i, 1, bus_type_combo)
            
            # 初始化该bus interface的port map信息字典
            self.bus_interface_port_maps[i] = {}
            
            # Mode下拉菜单
            mode_combo = QComboBox()
            mode_combo.addItems(["master", "slave"])
            mode_combo.setCurrentText(bus_interface.get('mode', 'master'))
            self.bus_interface_table.setCellWidget(i, 2, mode_combo)
            # 添加删除按钮
            delete_button = QPushButton()
            delete_icon = QIcon("src/delete.svg")
            delete_button.setIcon(delete_icon)
            delete_button.setText(" ")
            delete_button.setToolTip("删除BusInterface行")
            delete_button.setFlat(True)
            delete_button.clicked.connect(lambda checked, idx=i: self.remove_bus_interface_row(idx))
            self.bus_interface_table.setCellWidget(i, 3, delete_button)
        
        self.add_bus_interface_lastrow()

    # 填充PortMap信息
    def fill_port_map_table(self, port_maps):
        if self.port_map_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.port_map_table.rowCount() - 1, -1, -1):
                self.port_map_table.removeRow(i)
        
        self.port_map_table.setRowCount(len(port_maps))
        for i, port_map in enumerate(port_maps):
            # Logical Port
            logical_port_item = QTableWidgetItem(port_map.get('logical_port', ''))
            logical_port_item.setFlags(logical_port_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            self.port_map_table.setItem(i, 0, logical_port_item)
            # Physical Port
            physical_port_combo = QComboBox()
            physical_port_combo.addItems(["Select Port", port_map.get('physical_port', '')])
            physical_port_combo.setCurrentText(port_map.get('physical_port', 'Select Port'))
            self.port_map_table.setCellWidget(i, 1, physical_port_combo)
            # Port Direction
            port_direction_item = QTableWidgetItem(port_map.get('port_direction', ''))
            port_direction_item.setFlags(port_direction_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            self.port_map_table.setItem(i, 2, port_direction_item)
            # Port Width
            port_width_item = QTableWidgetItem(port_map.get('port_width', ''))
            port_width_item.setFlags(port_width_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            self.port_map_table.setItem(i, 3, port_width_item)
            # Bus Interface
            interface_item = QTableWidgetItem(port_map.get('bus_interface', ''))
            interface_item.setFlags(interface_item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            self.port_map_table.setItem(i, 4, interface_item)
