from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QHeaderView, QHBoxLayout, 
                    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QGroupBox, QLabel, QLineEdit, QGridLayout, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

class PortInfoDialog(QDialog):
    """端口信息显示对话框"""
    def __init__(self, node_name, ports_info, parent=None, graph=None):
        super().__init__(parent)
        self.setWindowTitle(f"模块端口信息 - {node_name}")
        self.setGeometry(100, 100, 700, 400)
        
        self.graph = graph
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建表格
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
        
        # 填充端口信息
        self.fill_port_info(ports_info)
        
        # 添加到布局
        layout.addWidget(self.table)
        
        # 添加按钮布局
        button_layout = QHBoxLayout()
        
        # 添加"添加连接关系"按钮
        add_connection_button = QPushButton("添加连接关系")
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
    
    def get_node_ports(self, node_name):
        """获取指定节点的所有端口名称"""
        if not node_name or node_name == "无连接":
            return []
        
        node = self.get_node_by_name(node_name)
        if not node:
            return []
        
        ports = []
        # 获取输入端口
        for port_name in node.inputs().keys():
            ports.append(port_name)
        # 获取输出端口
        for port_name in node.outputs().keys():
            ports.append(port_name)
        
        return ports
    
    def update_port_combo(self, current_row, node_name):
        """更新指定行的"连接端口"下拉菜单"""
        port_combo = self.table.cellWidget(current_row, 3)
        if port_combo and isinstance(port_combo, QComboBox):
            port_combo.clear()
            port_combo.addItem("")
            ports = self.get_node_ports(node_name)
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
                
                # 连接端口 - 下拉菜单
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
                    
                    # 连接端口 - 下拉菜单
                    port_combo = QComboBox()
                    port_combo.addItem("")
                    ports = self.get_node_ports(node_name) if node_name in all_node_names else []
                    for p in ports:
                        port_combo.addItem(p)
                    if port_name and port_name in ports:
                        port_combo.setCurrentText(port_name)
                    self.table.setCellWidget(current_row, 3, port_combo)
                    
                    current_row += 1
    
    def on_node_changed(self, row, node_name):
        """当"连接节点"下拉菜单改变时，更新"连接端口"下拉菜单"""
        self.update_port_combo(row, node_name)
    
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
        
        QMessageBox.information(self, "信息", "保存成功！")
        self.accept()
