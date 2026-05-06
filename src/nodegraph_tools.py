from contextlib import nullcontext
from NodeGraphQt import BaseNode, NodeGraph, BaseNodeCircle, Port

class CircleNodeOut(BaseNodeCircle):
    """圆形节点"""
    __identifier__ = 'user.circle'
    NODE_NAME = 'Circle Node Out'
    ports_removable = True
    
    def __init__(self):
        super(CircleNodeOut, self).__init__()
        self.port_name = "out"
        self.set_property('color', (200, 100, 50))
        self.add_input(self.port_name, display_name=False)

    def set_port_name(self, port_name):
        """设置端口名称"""
        # 启用端口删除
        self.set_port_deletion_allowed(True)
        # 移除旧端口
        for port_name_old in list(self.inputs().keys()):
            self.delete_input(port_name_old)
        # 添加新端口
        self.add_input(port_name, display_name=False)
        self.port_name = port_name
        # 禁用端口删除
        self.set_port_deletion_allowed(False)

class CircleNodeIn(BaseNodeCircle):
    """圆形节点"""
    __identifier__ = 'user.circle'
    NODE_NAME = 'Circle Node In'
    PORT_NAME = "in"
    
    def __init__(self):
        super(CircleNodeIn, self).__init__()
        self.set_property('color', (200, 100, 50))
        self.add_output(self.PORT_NAME, display_name=False)
    
    def set_port_name(self, port_name):
        """设置端口名称"""
        # 启用端口删除
        self.set_port_deletion_allowed(True)
        # 移除旧端口
        for port_name_old in list(self.outputs().keys()):
            print(port_name_old)
            self.delete_output(port_name_old)
        # 添加新端口
        self.add_output(port_name, display_name=False)
        self.PORT_NAME = port_name
        # 禁用端口删除
        self.set_port_deletion_allowed(False)

def get_all_connections(graph):
    """
    获取当前 NodeGraph 中的所有连接关系。
    返回一个包含连接信息的列表，每条连接是一个字典。
    """
    connections = []
    
    try:
        # 遍历所有节点
        for node in graph.all_nodes():
            # 遍历节点的所有输出端口
            for output_port in node.outputs().values():
                # 获取连接到该输出端口的所有输入端口
                connected_ports = output_port.connected_ports()
                
                for input_port in connected_ports:
                    # 获取节点名称
                    src_node = output_port.node().name()
                    dst_node = input_port.node().name()
                    
                    # 创建连接关系
                    connection_info = {
                        "source_node": src_node,
                        "target_node": dst_node,
                        "source_port": output_port.name(),
                        "target_port": input_port.name()
                    }
                    
                    connections.append(connection_info)
        
        print(f"共获取 {len(connections)} 个连接关系")
    except Exception as e:
        print(f"获取连接关系时出错: {e}")
    
    return connections

def make_template_node(serialized_data, template_name, node_data=None):
    """
    根据序列化数据和模板名称动态生成 TemplateNode 类。
    每次调用返回一个**全新的类**，继承自 BaseNode。
    """

    # 1. 定义 __init__ 方法，捕获外部变量
    def __init__(self):
        super(self.__class__, self).__init__()   # 或直接 BaseNode.__init__(self)

        # 存储component数据
        self.node_data = node_data
        
        # 根据component的ports创建输入和输出端口
        for port in node_data.get('ports', []):
            port_name = port.get('name', 'Unknown')
            direction = port.get('direction', 'in')
            print(f"模板节点端口: {port_name}, 方向: {direction}")
            
            if direction == 'in' or direction == 'input' or direction == 'inout':
                # in、input和inout端口都添加为输入
                self.add_input(port_name)
            if direction == 'out' or direction == 'output' or direction == 'inout':
                # out、output和inout端口都添加为输出
                self.add_output(port_name)

    # 2. 准备类的属性字典
    attrs = {
        '__identifier__': 'user',
        'NODE_NAME': template_name,
        'data': node_data,
        '__init__': __init__,
    }

    # 3. 使用 type 动态创建类
    #if node_data and node_data['data'].get('group', True):
    #    TemplateNode = type(
    #        f'{template_name}_node',          # 类名
    #        (GroupNode,),            # 基类
    #        attrs                   # 属性/方法字典
    #    )
    #else:
    #    TemplateNode = type(
    #        f'{template_name}_node',          # 类名
    #        (BaseNode,),            # 基类
    #        attrs                   # 属性/方法字典
    #    )
    TemplateNode = type(
        f'{template_name}_node',          # 类名
        (BaseNode,),            # 基类
        attrs                   # 属性/方法字典
    )

    print(TemplateNode.NODE_NAME)

    return TemplateNode
