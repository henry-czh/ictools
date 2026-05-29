import sys
import os
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QTabWidget)
from PyQt5.QtCore import (pyqtSignal, QProcess, Qt)
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPalette

def strip_ansi_escape(text):
    """移除 ANSI 转义序列，但保留实际输出"""
    # 移除 ANSI 转义序列
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    result = ansi_escape.sub('', text)
    
    # 移除其他控制字符（除了换行、回车、制表符）
    result = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', result)
    
    return result

class TerminalTextEdit(QTextEdit):
    """终端文本编辑控件"""
    key_pressed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        self.setAcceptRichText(False)
        self.setFont(QFont('Monaco', 12))
        self.setLineWrapMode(QTextEdit.NoWrap)
        
        # 设置深色主题
        self.set_dark_theme()
        
    def set_dark_theme(self):
        """设置深色主题"""
        palette = QPalette()
        palette.setColor(QPalette.Base, QColor(18, 18, 18))
        palette.setColor(QPalette.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.Highlight, QColor(48, 104, 151))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        
    def keyPressEvent(self, event):
        """处理键盘事件"""
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key_Return:
            self.insertPlainText('\n')
            self.key_pressed.emit('\n')
        elif key == Qt.Key_Backspace:
            cursor = self.textCursor()
            if cursor.position() > 0:
                cursor.deletePreviousChar()
            self.key_pressed.emit('\x7f')
        elif key == Qt.Key_Left:
            cursor = self.textCursor()
            if cursor.position() > 0:
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
            self.key_pressed.emit('\x1b[D')
            event.accept()
            return
        elif key == Qt.Key_Right:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Right)
            self.setTextCursor(cursor)
            self.key_pressed.emit('\x1b[C')
            event.accept()
            return
        elif key == Qt.Key_Up:
            self.key_pressed.emit('\x1b[A')
            event.accept()
            return
        elif key == Qt.Key_Down:
            self.key_pressed.emit('\x1b[B')
            event.accept()
            return
        elif key == Qt.Key_Tab:
            self.key_pressed.emit('\t')
        elif key == Qt.Key_Delete:
            self.key_pressed.emit('\x1b[3~')
        elif modifiers == Qt.ControlModifier and key == Qt.Key_C:
            self.key_pressed.emit('\x03')
        elif modifiers == Qt.ControlModifier and key == Qt.Key_D:
            self.key_pressed.emit('\x04')
        else:
            text = event.text()
            if text:
                self.key_pressed.emit(text)

class TerminalWidget(QWidget):
    """终端组件 - 使用QProcess实现"""
    
    def __init__(self, parent=None, working_dir=None):
        super().__init__(parent)
        self.working_dir = working_dir or os.getcwd()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(5, 2, 5, 2)
        
        self.new_tab_btn = QPushButton('+')
        self.new_tab_btn.clicked.connect(self.add_new_tab)
        toolbar.addWidget(self.new_tab_btn)
        
        self.close_tab_btn = QPushButton('×')
        self.close_tab_btn.clicked.connect(self.close_current_tab)
        toolbar.addWidget(self.close_tab_btn)
        
        toolbar.addStretch()
        
        self.clear_btn = QPushButton('清屏')
        self.clear_btn.clicked.connect(self.clear_terminal)
        toolbar.addWidget(self.clear_btn)
        
        layout.addLayout(toolbar)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tab_widget)
        
        # 添加第一个终端
        self.add_new_tab()
        
    def add_new_tab(self):
        """添加新终端标签"""
        terminal_page = QWidget()
        page_layout = QVBoxLayout(terminal_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        
        # 终端显示区域
        self.terminal_edit = TerminalTextEdit()
        self.terminal_edit.key_pressed.connect(self.on_key_pressed)
        page_layout.addWidget(self.terminal_edit)
        
        # 添加标签页
        index = self.tab_widget.addTab(terminal_page, f'Terminal {self.tab_widget.count() + 1}')
        self.tab_widget.setCurrentIndex(index)
        
        # 启动终端进程
        self.start_terminal_process()
        
    def close_tab(self, index):
        """关闭指定标签"""
        if self.tab_widget.count() > 1:
            self.stop_terminal_process()
            self.tab_widget.removeTab(index)
            
    def close_current_tab(self):
        """关闭当前标签"""
        current_index = self.tab_widget.currentIndex()
        self.close_tab(current_index)
        
    def start_terminal_process(self):
        """启动终端进程"""
        if hasattr(self, 'process') and self.process:
            self.stop_terminal_process()
            
        self.process = QProcess(self)
        
        # 设置工作目录
        self.process.setWorkingDirectory(self.working_dir)
        
        # 设置环境变量
        env = self.process.processEnvironment()
        env.insert("TERM", "xterm-256color")
        env.insert("TERM_PROGRAM", "vscode")
        self.process.setProcessEnvironment(env)
        
        # 根据操作系统选择shell
        if sys.platform == "win32":
            self.process.start("cmd.exe")
        else:
            # 使用 bash
            self.process.start("/bin/bash", ["--norc", "--noprofile", "-i"])
        
        # 连接信号
        self.process.readyReadStandardOutput.connect(self.on_stdout_ready)
        self.process.readyReadStandardError.connect(self.on_stderr_ready)
        self.process.finished.connect(self.on_process_finished)
        
    def stop_terminal_process(self):
        """停止终端进程"""
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            self.process.waitForFinished(1000)
            self.process = None
            
    def on_stdout_ready(self):
        """处理标准输出"""
        output = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        clean_output = strip_ansi_escape(output)
        self.terminal_edit.insertPlainText(clean_output)
        self.terminal_edit.moveCursor(QTextCursor.End)

    def on_stderr_ready(self):
        """处理标准错误输出"""
        error = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        clean_error = strip_ansi_escape(error)
        self.terminal_edit.insertPlainText(clean_error)
        self.terminal_edit.moveCursor(QTextCursor.End)
        
    def on_key_pressed(self, key):
        """处理键盘输入"""
        if hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running:
            self.process.write(key.encode())
            
    def on_process_finished(self, exit_code, exit_status):
        """进程结束处理"""
        self.terminal_edit.insertPlainText(f'\n[进程已结束，退出码: {exit_code}]')
        
    def clear_terminal(self):
        """清空终端"""
        self.terminal_edit.clear()
        
        # 重启终端进程
        self.stop_terminal_process()
        self.start_terminal_process()
        
    def write_output(self, text):
        """写入输出到终端（用于接收print等外部输出）"""
        text = text.strip()
        if text:
            lines = text.split('\n')
            for line in lines:
                if line:
                    output_text = f"[OUTPUT] {line}"
                    self.terminal_edit.insertPlainText(output_text)
                self.terminal_edit.insertPlainText('\n')
            self.terminal_edit.moveCursor(QTextCursor.End)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    window = QMainWindow()
    terminal = TerminalWidget()
    window.setCentralWidget(terminal)
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())