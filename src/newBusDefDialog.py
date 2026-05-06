import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QHeaderView, QHBoxLayout, 
                    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QGroupBox, QLabel, QLineEdit, QGridLayout, QFileDialog, QMessageBox)
from PyQt5.QtGui import QIcon
from .ipxact_writer import IPXactWriter

class NewBusDefDialog(QDialog):
    """新建busdef对话框"""
    def __init__(self, parent=None, library_dir=None):
        super().__init__(parent)
        self.setWindowTitle("新建busdef")
        self.resize(600, 500)
        self.library_dir = library_dir
        
        self.layout = QVBoxLayout(self)
        
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
        self.name_input.setText("NewBusDef")
        basic_layout.addWidget(self.name_label, 2, 0)
        basic_layout.addWidget(self.name_input, 2, 1)
        
        # Version
        self.version_label = QLabel("Version:")
        self.version_input = QLineEdit()
        self.version_input.setText("1.0")
        basic_layout.addWidget(self.version_label, 3, 0)
        basic_layout.addWidget(self.version_input, 3, 1)
        
        # Description
        self.description_label = QLabel("Description:")
        self.description_input = QLineEdit()
        self.description_input.setText("New bus definition")
        basic_layout.addWidget(self.description_label, 4, 0)
        basic_layout.addWidget(self.description_input, 4, 1)
        
        basic_info_group.setLayout(basic_layout)
        self.layout.addWidget(basic_info_group)
        
        # Signal信息表格
        signal_group = QGroupBox("Signal信息")
        signal_layout = QVBoxLayout()
        
        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(7)  # 增加一列用于操作按钮
        self.signal_table.setHorizontalHeaderLabels(["Signal名称", "位宽", "Master方向", "Slave方向", "存在性", "驱动类型", "操作"])
        self.signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 初始化信号表格
        row = self.signal_table.rowCount()
        self.signal_table.insertRow(row)
        self.signal_table.setItem(row, 0, QTableWidgetItem("data"))
        
        self.signal_table.setItem(row, 1, QTableWidgetItem("32"))
        
        # Master方向下拉菜单
        master_direction_combo = QComboBox()
        master_direction_combo.addItems(["in", "out", "inout"])
        master_direction_combo.setCurrentText("out")
        self.signal_table.setCellWidget(row, 2, master_direction_combo)
        
        # Slave方向下拉菜单
        slave_direction_combo = QComboBox()
        slave_direction_combo.addItems(["in", "out", "inout"])
        slave_direction_combo.setCurrentText("in")
        self.signal_table.setCellWidget(row, 3, slave_direction_combo)
        
        # 存在性下拉菜单
        presence_combo = QComboBox()
        presence_combo.addItems(["required", "optional", "illegal"])
        presence_combo.setCurrentText("required")
        self.signal_table.setCellWidget(row, 4, presence_combo)
        
        # 驱动类型下拉菜单
        driver_combo = QComboBox()
        driver_combo.addItems(["any", "clock", "singleShot"])
        driver_combo.setCurrentText("any")
        self.signal_table.setCellWidget(row, 5, driver_combo)
        
        # 添加删除按钮
        delete_button = QPushButton()
        delete_icon = QIcon("src/delete.svg")
        delete_button.setIcon(delete_icon)
        delete_button.setText(" ")
        delete_button.setToolTip("删除Signal行")
        delete_button.setFlat(True)
        delete_button.clicked.connect(lambda checked, idx=row: self.remove_signal_row(idx))
        self.signal_table.setCellWidget(row, 6, delete_button)
        
        # 添加添加按钮行
        self.add_signal_lastrow()
        
        signal_layout.addWidget(self.signal_table)
        signal_group.setLayout(signal_layout)
        self.layout.addWidget(signal_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(button_layout)
        
        # 连接信号
        self.ok_button.clicked.connect(self.save_and_accept)
        self.cancel_button.clicked.connect(self.reject)
    
    def add_signal_row(self):
        """添加Signal行"""
        # 移除现有的添加按钮行（如果存在）
        if self.signal_table.rowCount() > 0:
            # 遍历所有行，找到并移除添加按钮行
            for i in range(self.signal_table.rowCount() - 1, -1, -1):
                btn = self.signal_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    self.signal_table.removeRow(i)
                    break
        
        # 在表格末尾添加新的signal行
        row = self.signal_table.rowCount()
        self.signal_table.insertRow(row)
        self.signal_table.setItem(row, 0, QTableWidgetItem(f"signal_{row + 1}"))
        self.signal_table.setItem(row, 1, QTableWidgetItem("32"))
        
        # Master方向下拉菜单
        master_direction_combo = QComboBox()
        master_direction_combo.addItems(["in", "out", "inout"])
        master_direction_combo.setCurrentText("out")
        self.signal_table.setCellWidget(row, 2, master_direction_combo)
        
        # Slave方向下拉菜单
        slave_direction_combo = QComboBox()
        slave_direction_combo.addItems(["in", "out", "inout"])
        slave_direction_combo.setCurrentText("in")
        self.signal_table.setCellWidget(row, 3, slave_direction_combo)
        
        # 存在性下拉菜单
        presence_combo = QComboBox()
        presence_combo.addItems(["required", "optional", "illegal"])
        presence_combo.setCurrentText("required")
        self.signal_table.setCellWidget(row, 4, presence_combo)
        
        # 驱动类型下拉菜单
        driver_combo = QComboBox()
        driver_combo.addItems(["any", "clock", "singleShot"])
        driver_combo.setCurrentText("any")
        self.signal_table.setCellWidget(row, 5, driver_combo)
        
        # 添加删除按钮
        delete_button = QPushButton()
        delete_icon = QIcon("src/delete.svg")
        delete_button.setIcon(delete_icon)
        delete_button.setText(" ")
        delete_button.setToolTip("删除Signal行")
        delete_button.setFlat(True)
        delete_button.clicked.connect(lambda checked, idx=row: self.remove_signal_row(idx))
        self.signal_table.setCellWidget(row, 6, delete_button)
        
        # 添加添加按钮行
        self.add_signal_lastrow()
    
    # 在表格末尾添加添加按钮行
    def add_signal_lastrow(self):
        add_button = QPushButton()
        add_icon = QIcon("src/add.svg")
        add_button.setIcon(add_icon)
        add_button.setText(" ")
        add_button.setToolTip("添加Signal行")
        add_button.setFlat(True)
        add_button.clicked.connect(self.add_signal_row)
        add_row = self.signal_table.rowCount()
        self.signal_table.insertRow(add_row)
        self.signal_table.setCellWidget(add_row, 0, add_button)
        # 合并单元格
        self.signal_table.setSpan(add_row, 0, 1, 7)
        self.signal_table.setItem(add_row, 0, QTableWidgetItem(""))
    
    def remove_signal_row(self, row=None):
        """删除Signal行"""
        if row is None:
            row = self.signal_table.currentRow()
        if row >= 0:
            # 检查是否是添加按钮行
            btn = self.signal_table.cellWidget(row, 0)
            if isinstance(btn, QPushButton):
                return  # 不删除添加按钮行
            
            # 删除指定行
            self.signal_table.removeRow(row)
            
            # 更新剩余行的删除按钮连接
            for i in range(self.signal_table.rowCount()):
                btn = self.signal_table.cellWidget(i, 6)
                if isinstance(btn, QPushButton):
                    btn.disconnect()
                    btn.clicked.connect(lambda checked, idx=i: self.remove_signal_row(idx))
            
            # 确保添加按钮在最后一行
            # 先检查是否已经有添加按钮行
            has_add_button = False
            for i in range(self.signal_table.rowCount()):
                btn = self.signal_table.cellWidget(i, 0)
                if isinstance(btn, QPushButton):
                    has_add_button = True
                    if i != self.signal_table.rowCount() - 1:
                        # 添加按钮不在最后一行，移动它
                        self.signal_table.removeRow(i)
                        self.add_signal_lastrow()
                    break
            
            if not has_add_button:
                # 没有添加按钮，添加一个
                self.add_signal_lastrow()
    
    def save_and_accept(self):
        """保存并接受对话框"""
        # 验证输入
        vendor = self.vendor_input.text().strip()
        library = self.library_input.text().strip()
        name = self.name_input.text().strip()
        version = self.version_input.text().strip()
        
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
        
        # 获取输入值
        busdef_data = self.get_values()
        
        # 确定保存目录
        if self.library_dir:
            # 如果有library目录，保存到busdef子目录
            save_dir = os.path.join(self.library_dir, "busdef")
            os.makedirs(save_dir, exist_ok=True)
        else:
            # 如果没有library目录，弹出选择对话框
            save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", "/Users/czh/Documents/trae_projects")
            if not save_dir:
                return
        
        # 保存XML文件
        try:
            # 创建IPXactWriter实例
            writer = IPXactWriter()
            
            # 保存bus definition
            file_path = writer.write_bus_definition(busdef_data, save_dir)
            if not file_path:
                QMessageBox.critical(self, "错误", "保存bus definition失败")
                return
            
            # 同时保存abstract bus definition
            abstract_file_path = writer.write_abstract_bus_definition(busdef_data, save_dir)
            if not abstract_file_path:
                QMessageBox.critical(self, "错误", "保存abstract bus definition失败")
                return
            
            QMessageBox.information(self, "成功", f"busdef已成功保存到 {file_path}\nabstract bus definition已成功保存到 {abstract_file_path}")
            
            # 接受对话框
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存busdef失败: {e}")
    
    def get_values(self):
        """获取输入值并返回busdef数据"""
        vendor = self.vendor_input.text().strip()
        library = self.library_input.text().strip()
        name = self.name_input.text().strip()
        version = self.version_input.text().strip()
        description = self.description_input.text().strip()
        
        # 收集Signal信息
        signals = []
        for i in range(self.signal_table.rowCount()):
            if isinstance(self.signal_table.cellWidget(i, 0), QPushButton):
                continue
            signal_name = self.signal_table.item(i, 0).text().strip()
            width = self.signal_table.item(i, 1).text().strip()
            # Master方向
            master_direction_widget = self.signal_table.cellWidget(i, 2)
            master_direction = master_direction_widget.currentText() if master_direction_widget else "out"
            # Slave方向
            slave_direction_widget = self.signal_table.cellWidget(i, 3)
            slave_direction = slave_direction_widget.currentText() if slave_direction_widget else "in"
            # 存在性
            presence_widget = self.signal_table.cellWidget(i, 4)
            presence = presence_widget.currentText() if presence_widget else "required"
            # 驱动类型
            driver_widget = self.signal_table.cellWidget(i, 5)
            driver = driver_widget.currentText() if driver_widget else "any"
            
            if signal_name:
                signals.append({
                    "name": signal_name, 
                    "width": width,
                    "presence": presence,   # 存在性对应bus definition中的presence
                    "driver": driver,       # 驱动类型对应bus definition中的driver
                    "master_direction": master_direction,  # Master方向对应abstract中的master direction
                    "slave_direction": slave_direction     # Slave方向对应abstract中的slave direction
                })
        
        return {
            "vendor": vendor,
            "library": library,
            "name": name,
            "version": version,
            "description": description,
            "signals": signals
        }
