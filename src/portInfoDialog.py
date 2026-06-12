from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QHeaderView, QHBoxLayout,
                    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QGroupBox, QLabel, QLineEdit, QGridLayout, QFileDialog, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt

class PortInfoDialog(QDialog):
    """端口信息显示对话框"""
    def __init__(self, node_name, ports_info, parent=None, graph=None, parameters=None):
        super().__init__(parent)
        self.setWindowTitle(f"端口连线 - {node_name}")
        self.setGeometry(100, 100, 700, 500)

        self.node_name = node_name
        self.graph = graph
        self.parameters = parameters or []

        # 创建布局
        layout = QVBoxLayout(self)

        # 创建端口表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["端口名称", "类型", "连接模块", "连接端口"])

        # 设置表格属性
        # 第一列和第二列根据内容适应宽度，第三列和第四列填充剩余空间
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        # 创建Parameter表格
        self.param_group = QGroupBox("模块参数设置")
        param_layout = QVBoxLayout()

        self.param_table = QTableWidget()
        self.param_table.setColumnCount(3)
        self.param_table.setHorizontalHeaderLabels(["参数名称", "默认值", "实例化值"])
        self.param_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.param_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.param_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.param_table.setAlternatingRowColors(True)

        # 填充parameter信息
        self.fill_param_info()

        param_layout.addWidget(self.param_table)
        self.param_group.setLayout(param_layout)

        # 使用Splitter分隔param_group和端口表格，比例2:8
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.param_group)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(0, 2)  # param_group占2份
        splitter.setStretchFactor(1, 8)  # 端口table占8份

        # 填充端口信息
        self.fill_port_info(ports_info)

        # 添加到布局
        layout.addWidget(splitter)

        # 添加按钮布局
        button_layout = QHBoxLayout()

        # 添加"添加连接关系"按钮
        add_connection_button = QPushButton("添加扇出连接")
        add_connection_button.clicked.connect(self.add_connection)
        add_connection_button.setAutoDefault(False)
        button_layout.addWidget(add_connection_button)

        # 添加保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_changes)
        save_button.setAutoDefault(False)
        button_layout.addWidget(save_button)

        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        close_button.setAutoDefault(False)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def fill_param_info(self):
        """填充parameter信息到表格"""
        self.param_table.setRowCount(len(self.parameters))

        for row, param in enumerate(self.parameters):
            param_name = param.get('name', 'Unknown')
            default_value = param.get('default_value', '')
            current_value = param.get('value', default_value)

            # 参数名称（只读）
            name_item = QTableWidgetItem(param_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignVCenter)
            self.param_table.setItem(row, 0, name_item)

            # 默认值（只读）
            default_item = QTableWidgetItem(str(default_value))
            default_item.setFlags(default_item.flags() & ~Qt.ItemIsEditable)
            default_item.setTextAlignment(Qt.AlignVCenter)
            self.param_table.setItem(row, 1, default_item)

            # 当前值（可编辑）
            value_item = QTableWidgetItem(str(current_value))
            value_item.setTextAlignment(Qt.AlignVCenter)
            self.param_table.setItem(row, 2, value_item)

    def get_parameters(self):
        """获取用户修改后的parameter值"""
        result = []
        for row in range(self.param_table.rowCount()):
            name_item = self.param_table.item(row, 0)
            default_item = self.param_table.item(row, 1)
            value_item = self.param_table.item(row, 2)
            if name_item and value_item:
                param = {
                    'name': name_item.text(),
                    'default_value': default_item.text() if default_item else '',
                    'value': value_item.text()
                }
                result.append(param)
        return result

    def get_all_node_names(self):
        """获取当前graph上的所有节点名称"""
        if not self.graph:
            return []

        node_names = []
        for node in self.graph.all_nodes():
            node_names.append(node.name())
        return node_names

    def get_node_by_name(self, node_name):
        """根据节点名称获取节点对象"""
        if not self.graph or not node_name:
            return None

        for node in self.graph.all_nodes():
            if node.name() == node_name:
                return node
        return None

    def get_node_ports(self, node_name, required_type=None):
        """
        获取指定节点的端口名称

        Args:
            node_name: 节点名称
            required_type: 需要的端口类型 (None=全部, 'input'=只输入, 'output'=只输出)
        """
        if not node_name or node_name == "无连接":
            return []

        node = self.get_node_by_name(node_name)
        if not node:
            return []

        ports = []
        # 根据需要的类型获取端口
        if required_type is None or required_type == "input":
            for port_name in node.inputs().keys():
                ports.append(port_name)
        if required_type is None or required_type == "output":
            for port_name in node.outputs().keys():
                ports.append(port_name)

        return ports

    def update_port_combo(self, current_row, node_name):
        """更新指定行的"连接端口"下拉菜单"""
        port_combo = self.table.cellWidget(current_row, 3)
        if port_combo and isinstance(port_combo, QComboBox):
            port_combo.clear()
            port_combo.addItem("")

            # 获取当前行的端口类型（需要查找合并单元格的第一行）
            port_type = None
            for row in range(current_row, -1, -1):
                type_item = self.table.item(row, 1)
                if type_item and type_item.text():
                    port_type = type_item.text()
                    break

            # 确定需要的目标端口类型
            # 如果当前端口是 input，目标需要是 output
            # 如果当前端口是 output，目标需要是 input
            required_type = None
            if port_type == "input":
                required_type = "output"
            elif port_type == "output":
                required_type = "input"

            # 获取过滤后的端口列表
            ports = self.get_node_ports(node_name, required_type)
            for port in ports:
                port_combo.addItem(port)

    def fill_port_info(self, ports_info):
        """填充端口信息到表格"""
        # 计算总行数（每个连接占一行）
        total_rows = 0
        for port_info in ports_info:
            connections = port_info.get('connections', [])
            total_rows += max(1, len(connections))

        self.table.setRowCount(total_rows)

        # 获取所有节点名称
        all_node_names = self.get_all_node_names()

        current_row = 0
        for port_info in ports_info:
            connections = port_info.get('connections', [])
            num_connections = max(1, len(connections))

            # 获取当前端口的类型，用于后续过滤
            current_port_type = port_info.get('type', 'Unknown')
            # 确定需要的目标端口类型
            required_type = None
            if current_port_type == "input":
                required_type = "output"
            elif current_port_type == "output":
                required_type = "input"

            if not connections:
                # 无连接的情况
                # 端口名称
                name_item = QTableWidgetItem(port_info.get('name', 'Unknown'))
                # 垂直居中对齐
                name_item.setTextAlignment(Qt.AlignVCenter)
                self.table.setItem(current_row, 0, name_item)

                # 类型
                port_type = port_info.get('type', 'Unknown')
                type_item = QTableWidgetItem(port_type)
                type_item.setTextAlignment(Qt.AlignVCenter)
                self.table.setItem(current_row, 1, type_item)

                # 连接节点 - 下拉菜单
                node_combo = QComboBox()
                node_combo.addItem("无连接")
                for node_name in all_node_names:
                    node_combo.addItem(node_name)
                node_combo.currentTextChanged.connect(lambda text, row=current_row: self.on_node_changed(row, text))
                self.table.setCellWidget(current_row, 2, node_combo)

                # 连接端口 - 下拉菜单（已过滤）
                port_combo = QComboBox()
                port_combo.addItem("")
                self.table.setCellWidget(current_row, 3, port_combo)

                current_row += 1
            else:
                # 有连接的情况
                for i, conn in enumerate(connections):
                    # 端口名称（只在第一行显示，并设置跨行）
                    if i == 0:
                        name_item = QTableWidgetItem(port_info.get('name', 'Unknown'))
                        # 垂直居中对齐
                        name_item.setTextAlignment(Qt.AlignVCenter)
                        self.table.setItem(current_row, 0, name_item)

                        # 类型（只在第一行显示，并设置跨行）
                        port_type = port_info.get('type', 'Unknown')
                        type_item = QTableWidgetItem(port_type)
                        type_item.setTextAlignment(Qt.AlignVCenter)
                        self.table.setItem(current_row, 1, type_item)

                        # 合并单元格（如果有多个连接）
                        if num_connections > 1:
                            self.table.setSpan(current_row, 0, num_connections, 1)
                            self.table.setSpan(current_row, 1, num_connections, 1)
                    else:
                        # 后续行不需要设置，因为已经合并了
                        pass

                    # 解析连接信息
                    if "." in conn:
                        node_name, port_name = conn.split(".", 1)
                    else:
                        node_name = conn
                        port_name = ""

                    # 连接节点 - 下拉菜单
                    node_combo = QComboBox()
                    node_combo.addItem("无连接")
                    for n in all_node_names:
                        node_combo.addItem(n)
                    # 设置默认值
                    if node_name in all_node_names:
                        node_combo.setCurrentText(node_name)
                    else:
                        node_combo.setCurrentText("无连接")
                    node_combo.currentTextChanged.connect(lambda text, row=current_row: self.on_node_changed(row, text))
                    self.table.setCellWidget(current_row, 2, node_combo)

                    # 连接端口 - 下拉菜单（已过滤）
                    port_combo = QComboBox()
                    port_combo.addItem("")
                    if node_name in all_node_names:
                        ports = self.get_node_ports(node_name, required_type)
                        for p in ports:
                            port_combo.addItem(p)
                    if port_name and port_name in (ports if node_name in all_node_names else []):
                        port_combo.setCurrentText(port_name)
                    self.table.setCellWidget(current_row, 3, port_combo)

                    current_row += 1

    def on_node_changed(self, row, node_name):
        """当"连接节点"下拉菜单改变时，更新"连接端口"下拉菜单"""
        self.update_port_combo(row, node_name)

    def get_node_component_data(self, node):
        """
        获取节点的 component_data

        Args:
            node: 节点对象

        Returns:
            dict: 节点数据，包含 ports、bus_interfaces、port_maps 等
        """
        if hasattr(node, 'component_data') and node.component_data:
            return node.component_data
        elif hasattr(node, 'node_data') and node.node_data:
            return node.node_data
        return {}

    def get_port_width(self, node, port_name):
        """
        获取端口的位宽

        Args:
            node: 节点对象
            port_name: 端口名称

        Returns:
            int: 端口位宽，如果未找到返回 1
        """
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
        """
        判断端口是否是 bus interface 端口

        Args:
            node: 节点对象
            port_name: 端口名称（可能带有 bus_ 前缀）

        Returns:
            tuple: (bool, bus_interface_name) 如果是 bus interface 端口返回 (True, bus_name)，否则返回 (False, None)
        """
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
        """
        获取 bus interface 内部的信号及其位宽映射

        Args:
            node: 节点对象
            bus_if_name: bus interface 名称

        Returns:
            dict: {logical_signal_name: width}
        """
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
        """
        获取 bus interface 的 bus_type

        Args:
            node: 节点对象
            bus_if_name: bus interface 名称

        Returns:
            str: bus_type，如果未找到返回空字符串
        """
        component_data = self.get_node_component_data(node)
        bus_interfaces = component_data.get('bus_interfaces', [])

        for bus_if in bus_interfaces:
            if bus_if.get('name') == bus_if_name:
                return bus_if.get('bus_type', '')

        return ''

    def validate_connection_width(self, source_node, source_port_name, target_node, target_port_name):
        """
        验证两个端口的位宽是否匹配

        Args:
            source_node: 源节点
            source_port_name: 源端口名称
            target_node: 目标节点
            target_port_name: 目标端口名称

        Returns:
            tuple: (bool, str) - (是否有效, 错误信息)
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

            for signal_name in source_signals:
                src_width = source_signals.get(signal_name, 0)
                tgt_width = target_signals.get(signal_name, 0)
                if src_width != tgt_width:
                    return (False, f"信号 '{signal_name}' 位宽不匹配: 源 {src_width} 位 vs 目标 {tgt_width} 位")

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

    def add_connection(self):
        """添加新的连接关系"""
        # 获取当前选中的行
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一行")
            return

        # 获取选中的行号
        current_row = selected_rows[0].row()

        # 获取当前行的端口名称和类型
        port_name_item = self.table.item(current_row, 0)
        type_item = self.table.item(current_row, 1)

        # 如果端口名称为空，说明是合并单元格的后续行，需要找到第一行
        if not port_name_item or not port_name_item.text():
            # 向上查找，直到找到端口名称不为空的行
            for row in range(current_row - 1, -1, -1):
                port_name_item = self.table.item(row, 0)
                if port_name_item and port_name_item.text():
                    current_row = row
                    type_item = self.table.item(row, 1)
                    break

        if not port_name_item or not port_name_item.text():
            QMessageBox.warning(self, "警告", "无法找到有效的端口信息")
            return

        port_name = port_name_item.text()
        port_type = type_item.text() if type_item else ""

        # 判断port_type是input，则不允许扇出连接
        if port_type == "input":
            QMessageBox.warning(self, "警告", "端口类型为input，不允许扇出连接")
            return

        # 如果是output类型，检查是否是bus interface，bus interface也不允许扇出连接
        if port_type == "output":
            current_node = None
            for node in self.graph.all_nodes():
                if node.name() == self.windowTitle().split(" - ")[1]:
                    current_node = node
                    break

            if current_node:
                is_bus, bus_name = self.is_bus_interface_port(current_node, port_name)
                if is_bus:
                    QMessageBox.warning(self, "警告", f"bus interface 端口 '{port_name}' 不允许扇出连接")
                    return

        # 检查该端口是否已经有合并单元格
        # 找到该端口的所有行
        span_row = -1
        span_count = 0
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == port_name:
                # 检查是否有合并
                span = self.table.rowSpan(row, 0)
                if span > 1:
                    span_row = row
                    span_count = span
                break

        # 获取所有节点名称
        all_node_names = self.get_all_node_names()

        # 插入新行
        if span_row >= 0:
            # 如果已经有合并单元格，在合并区域的最后一行之后插入新行
            insert_row = span_row + span_count
            self.table.insertRow(insert_row)

            # 更新合并单元格的行数
            self.table.setSpan(span_row, 0, span_count + 1, 1)
            self.table.setSpan(span_row, 1, span_count + 1, 1)
        else:
            # 如果没有合并单元格，在当前行之后插入新行
            insert_row = current_row + 1
            self.table.insertRow(insert_row)

            # 设置合并单元格
            self.table.setSpan(current_row, 0, 2, 1)
            self.table.setSpan(current_row, 1, 2, 1)

        # 设置新行的后两列（连接节点和连接端口）
        # 连接节点 - 下拉菜单
        node_combo = QComboBox()
        node_combo.addItem("无连接")
        for node_name in all_node_names:
            node_combo.addItem(node_name)
        node_combo.currentTextChanged.connect(lambda text, row=insert_row: self.on_node_changed(row, text))
        self.table.setCellWidget(insert_row, 2, node_combo)

        # 连接端口 - 下拉菜单
        port_combo = QComboBox()
        port_combo.addItem("")
        self.table.setCellWidget(insert_row, 3, port_combo)

        # 前两列不需要设置，因为已经合并了
        # 设置为空的项目
        empty_name_item = QTableWidgetItem("")
        empty_type_item = QTableWidgetItem("")
        self.table.setItem(insert_row, 0, empty_name_item)
        self.table.setItem(insert_row, 1, empty_type_item)

    def save_changes(self):
        """保存用户对表格的修改，更新graph中的连接关系"""
        if not self.graph:
            QMessageBox.warning(self, "警告", "无法保存更改：未找到节点图")
            return

        # 获取当前节点
        current_node = None
        for node in self.graph.all_nodes():
            if node.name() == self.windowTitle().split(" - ")[1]:
                current_node = node
                break

        if not current_node:
            QMessageBox.warning(self, "警告", "无法找到当前节点")
            return

        # 先清除所有端口的连接
        for port_name in current_node.inputs().keys():
            port = current_node.inputs().get(port_name)
            if port:
                port.clear_connections()

        for port_name in current_node.outputs().keys():
            port = current_node.outputs().get(port_name)
            if port:
                port.clear_connections()

        # 记录当前有效的端口名称和类型
        current_port_name = None
        current_port_type = None

        # 遍历表格中的所有行
        for row in range(self.table.rowCount()):
            # 获取端口名称
            port_name_item = self.table.item(row, 0)

            # 如果端口名称不为空，更新当前端口信息
            if port_name_item and port_name_item.text():
                current_port_name = port_name_item.text()

                # 获取类型
                type_item = self.table.item(row, 1)
                current_port_type = type_item.text() if type_item else ""

            # 如果没有有效的端口名称，跳过
            if not current_port_name:
                continue

            # 获取连接节点
            node_combo = self.table.cellWidget(row, 2)
            if not node_combo or not isinstance(node_combo, QComboBox):
                continue

            connected_node_name = node_combo.currentText()

            # 获取连接端口
            port_combo = self.table.cellWidget(row, 3)
            if not port_combo or not isinstance(port_combo, QComboBox):
                continue

            connected_port_name = port_combo.currentText()

            # 处理连接关系
            if connected_node_name and connected_node_name != "无连接" and connected_port_name:
                # 找到目标节点
                target_node = self.get_node_by_name(connected_node_name)
                if not target_node:
                    continue

                # 位宽验证
                if current_port_type == "input":
                    # 当前是输入端口，源是目标节点的输出端口
                    is_valid, error_msg = self.validate_connection_width(
                        target_node, connected_port_name,
                        current_node, current_port_name
                    )
                elif current_port_type == "output":
                    # 当前是输出端口，源是当前节点的输出端口
                    is_valid, error_msg = self.validate_connection_width(
                        current_node, current_port_name,
                        target_node, connected_port_name
                    )
                else:
                    is_valid, error_msg = True, ""

                if not is_valid:
                    QMessageBox.warning(self, "位宽验证失败", error_msg)
                    return

                # 创建新的连接
                if current_port_type == "input":
                    # 输入端口
                    port = current_node.inputs().get(current_port_name)
                    source_port = target_node.outputs().get(connected_port_name)
                    if source_port and port:
                        source_port.connect_to(port)
                elif current_port_type == "output":
                    # 输出端口
                    port = current_node.outputs().get(current_port_name)
                    target_port = target_node.inputs().get(connected_port_name)
                    if target_port and port:
                        port.connect_to(target_port)

        # 更新节点的parameters
        if hasattr(current_node, 'component_data') and current_node.component_data:
            modified_params = self.get_parameters()
            if modified_params:
                current_node.component_data['parameters'] = modified_params

        QMessageBox.information(self, "信息", "保存成功！")
        self.accept()
