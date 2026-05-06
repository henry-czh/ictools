import sys
import json

from PyQt5.QtWidgets import QApplication, QMainWindow
from NodeGraphQt import NodeGraph, BaseNode, PropertiesBinWidget, NodesTreeWidget, NodesPaletteWidget, GroupNode, SubGraph
from NodeGraphQt.constants import PipeLayoutEnum
from PyQt5 import QtCore

# ==========================
# 自定义 SoC 节点
# ==========================
class SoCNode(BaseNode):

    __identifier__ = 'soc.nodes'
    NODE_NAME = 'SoC Block'

    def __init__(self):
        super(SoCNode, self).__init__()

        # 添加一个输入端口
        self.add_input('in0')
        self.add_input('in1')

        # 添加一个输出端口
        self.add_output('out0')
        self.add_output('out1')

# ==========================
# 自定义 Group 节点
# ==========================
class MyCustomGroup_org(GroupNode):
    __identifier__ = 'nodes.group'
    NODE_NAME = 'My Math Group'

    def __init__(self):
        super(MyCustomGroup, self).__init__()
        self.set_color(40, 70, 100)
        
        # 获取子图实例
        sub_graph = self.get_sub_graph()
        
        # 在子图内部创建输入/输出接口节点
        # 只要子图里有这两种节点，主图上的 GroupNode 就会自动出现对应的 Port
        input_node = sub_graph.create_node('nodes.group.GroupInput', name='Input Link')
        output_node = sub_graph.create_node('nodes.group.GroupOutput', name='Output Link')
        
        # 在内部创建一个运算节点并连接
        math_node = sub_graph.create_node('nodes.logic.MultiplyNode', pos=[200, 0])
        
        input_node.set_output(0, math_node.input(0))
        math_node.set_output(0, output_node.input(0))

class MyCustomGroup(GroupNode):
    __identifier__ = 'nodes.group'
    NODE_NAME = 'My Math Group'

    def __init__(self):
        super(MyCustomGroup, self).__init__()
        #self._initialized = False

   # def on_mouse_double_click(self, pos):
   #     super(MyCustomGroup, self).on_mouse_double_click(pos)

   #     # 当用户双击进入时初始化内部结构
   #     if not self._initialized:
   #         sub = self.get_sub_graph()
   #         sub.create_node('nodes.group.GroupInput')
   #         sub.create_node('nodes.group.GroupOutput')
   #         self._initialized = True

# ==========================
# 动态创建模板节点
# ==========================
def make_template_node_org(serialized_data, template_name, node_data=None):

    class TemplateNode(BaseNode):
        __identifier__ = "SoC"
        NODE_NAME = template_name
        data = node_data

        def __init__(self):
            super(self).__init__()

            print(self.data)
            for input_port in self.data['data']['ports']['input']:
                self.add_input(input_port)
            for output_port in self.data['data']['ports']['output']:
                self.add_output(output_port)

    return TemplateNode


def make_template_node(serialized_data, template_name, node_data=None):
    """
    根据序列化数据和模板名称动态生成 TemplateNode 类。
    每次调用返回一个**全新的类**，继承自 BaseNode。
    """

    # 1. 定义 __init__ 方法，捕获外部变量
    def __init__(self):
        super(self.__class__, self).__init__()   # 或直接 BaseNode.__init__(self)

        for input_port in node_data['data']['ports']['input']:
            self.add_input(input_port)
        for output_port in node_data['data']['ports']['output']:
            self.add_output(output_port)

    # 2. 准备类的属性字典
    attrs = {
        '__identifier__': 'user.templates',
        'NODE_NAME': template_name,
        'data': node_data,
        '__init__': __init__,
    }

    # 3. 使用 type 动态创建类
    if node_data and node_data['data'].get('group', True):
        TemplateNode = type(
            f'{template_name}_node',          # 类名
            (GroupNode,),            # 基类
            attrs                   # 属性/方法字典
        )
    else:
        TemplateNode = type(
            f'{template_name}_node',          # 类名
            (BaseNode,),            # 基类
            attrs                   # 属性/方法字典
        )

    return TemplateNode
# ==========================
# 自定义节点图
# ==========================
class MyNodeGraph(NodeGraph):

    def __init__(self, parent=None):
        super(MyNodeGraph, self).__init__(parent)

        # properties bin widget.
        self._prop_bin = PropertiesBinWidget(node_graph=self)
        self._prop_bin.setWindowFlags(QtCore.Qt.Tool)

        # wire signal.
        #self.node_double_clicked.connect(self.display_prop_bin)

    def display_prop_bin(self, node):
        """
        function for displaying the properties bin when a node
        is double clicked
        """
        if not self._prop_bin.isVisible():
            self._prop_bin.show()

    def make_template_node(serialized_data, template_name, node_data=None):
        """
        根据序列化数据和模板名称动态生成 TemplateNode 类。
        每次调用返回一个**全新的类**，继承自 BaseNode。
        """

        # 1. 定义 __init__ 方法，捕获外部变量
        def __init__(self):
            super(self.__class__, self).__init__()   # 或直接 BaseNode.__init__(self)

            for input_port in node_data['data']['ports']['input']:
                self.add_input(input_port)
            for output_port in node_data['data']['ports']['output']:
                self.add_output(output_port)

        # 2. 准备类的属性字典
        attrs = {
            '__identifier__': 'user.templates',
            'NODE_NAME': template_name,
            'data': node_data,
            '__init__': __init__,
        }

        # 3. 使用 type 动态创建类
        if node_data and node_data['data'].get('group', True):
            TemplateNode = type(
                f'{template_name}_node',          # 类名
                (GroupNode,),            # 基类
                attrs                   # 属性/方法字典
            )
        else:
            TemplateNode = type(
                f'{template_name}_node',          # 类名
                (BaseNode,),            # 基类
                attrs                   # 属性/方法字典
            )

        return TemplateNode

# ==========================
# 主窗口
# ==========================
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NodeGraphQt SoC Demo")
        self.resize(900, 600)

        # 创建图
        self.graph = MyNodeGraph()

        # 关闭有向图限制，允许循环连接
        self.graph.set_acyclic(False)

        # 创建组节点
        group = GroupNode()
        self.graph.add_node(group)
        group.set_name("我的组")

        self.graph.register_node(MyCustomGroup)

        # 设置右键菜单
        #setup_context_menu(self.graph)

        # 创建一个组节点实例
        my_group = self.graph.create_node('nodes.group.MyCustomGroup', name='Calculated Group')
        #if my_group.get_sub_graph() is None:
        #    print("Forcing sub-graph initialization...")
        #    # 1. 手动创建子图控制器
        #    new_sub_graph = SubGraph(self.graph, my_group)
        #    # 2. 强行塞进主图表的维护字典中
        #    # 注意：NodeGraph 内部使用 _sub_graphs 字典存储，Key 是节点的 ID
        #    self.graph._sub_graphs[my_group.id] = new_sub_graph
    
        #    print(f"Sub-graph forced for node {my_group.id}")
        print(f"Graph reference: {my_group.graph}")
        print(f"Sub-graph: {my_group.get_sub_graph()}")

        # 加载json文件中的节点模板
        with open('template.json', 'r') as f:
            template_data = json.load(f)

        for template_name, node_data in template_data['templates'].items():
            TemplateClass = make_template_node(None, template_name, node_data=node_data)
            print(f"Registering template node: {TemplateClass.NODE_NAME}")
            # 注册节点类型
            self.graph.register_node(TemplateClass)

        # 从文件加载右键菜单
        self.graph.set_context_menu_from_file('hotkeys.json')

        # 设置管道布局为角度
        self.graph.set_pipe_style(PipeLayoutEnum.ANGLE.value)

        # 注册节点类型
        self.graph.register_node(SoCNode)

        # 把graph widget嵌入窗口
        self.setCentralWidget(self.graph.widget)

        # 创建两个节点
        self.create_nodes()

        # 监听连接信号
        self.graph.port_connected.connect(self.on_port_connected)

        # create node tree widget.
        self.nodes_tree = NodesTreeWidget(parent=None, node_graph=self.graph)
        self.nodes_tree.show()

        ## create nodes palette widget.
        #self.nodes_palette = NodesPaletteWidget(parent=None, node_graph=self.graph)
        #self.nodes_palette.show()

        # 强制将视图切换到该组的内部（用于测试）
        #self.graph.expand_group_node(my_group)

        self.graph.node_double_clicked.connect(self.on_double_click)

    # --- 强力补丁部分 ---
    def on_double_click(self, node):
        print(f"检测到双击: {node.name()}")
        if isinstance(node, GroupNode):
            self.graph.expand_group_node(node)
            sub = node.get_sub_graph()
            #sub.register_node(SoCNode)
            sub.create_node('soc.nodes.SoCNode', name='内部 SoC')
            sub.create_node('soc.nodes.SoCNode', name='内部 SoC 2', pos=[0, 100])

    def create_nodes(self):

        node1 = self.graph.create_node(
            'soc.nodes.SoCNode',
            name='CPU',
            pos=[-200, 0]
        )
        data = node1.serialize()
        #print("Serialized Node Data:", data)
        #TemplateClass = make_template_node(data, "CPU Template")
        #self.graph.register_node(TemplateClass)

        node2 = self.graph.create_node(
            'soc.nodes.SoCNode',
            name='MEM',
            pos=[200, 0]
        )
        #data = node2.serialize()
        #TemplateClass1 = make_template_node(data, "MEM Template")
        #self.graph.register_node(TemplateClass1)

    def on_port_connected(self, input_port, output_port):

        src_node = output_port.node().name()
        dst_node = input_port.node().name()

        print(f"Connected: {src_node} -> {dst_node}")


# ==========================
# 启动
# ==========================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())