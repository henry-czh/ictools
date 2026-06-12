from contextlib import nullcontext
from NodeGraphQt import BaseNode, NodeGraph, BaseNodeCircle, Port, BackdropNode as NodeGraphQtBackdropNode
from Qt.QtGui import QColor, QPainter, QPen, QPainterPath
from Qt.QtCore import Qt, QPointF
import math
from collections import defaultdict

class OrthogonalWirePainter:
    """正交布线（Orthogonal Routing）绘制器"""

    WIRE_SPACING = 15
    CORNER_RADIUS = 0

    @staticmethod
    def calculate_orthogonal_path(start_pos, end_pos, start_direction='right', end_direction='left'):
        """
        计算正交布线路径（只使用水平和垂直线段）

        Args:
            start_pos: 起始点 QPointF
            end_pos: 结束点 QPointF
            start_direction: 起始方向 ('right', 'left', 'up', 'down')
            end_direction: 结束方向 ('right', 'left', 'up', 'down')

        Returns:
            list of QPointF: 路径点列表
        """
        path = [start_pos]
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()

        if start_direction in ('right', 'left'):
            if (start_direction == 'right' and dx > 0) or (start_direction == 'left' and dx < 0):
                mid_x = start_pos.x() + dx / 2
                path.append(QPointF(mid_x, start_pos.y()))
                path.append(QPointF(mid_x, end_pos.y()))
            else:
                offset = 50
                if start_direction == 'right':
                    path.append(QPointF(start_pos.x() + offset, start_pos.y()))
                    path.append(QPointF(start_pos.x() + offset, end_pos.y()))
                else:
                    path.append(QPointF(start_pos.x() - offset, start_pos.y()))
                    path.append(QPointF(start_pos.x() - offset, end_pos.y()))
                path.append(end_pos)
        elif start_direction in ('up', 'down'):
            if (start_direction == 'down' and dy > 0) or (start_direction == 'up' and dy < 0):
                mid_y = start_pos.y() + dy / 2
                path.append(QPointF(start_pos.x(), mid_y))
                path.append(QPointF(end_pos.x(), mid_y))
            else:
                offset = 50
                if start_direction == 'down':
                    path.append(QPointF(start_pos.x(), start_pos.y() + offset))
                    path.append(QPointF(end_pos.x(), start_pos.y() + offset))
                else:
                    path.append(QPointF(start_pos.x(), start_pos.y() - offset))
                    path.append(QPointF(end_pos.x(), start_pos.y() - offset))
                path.append(end_pos)

        if path[-1] != end_pos:
            path.append(end_pos)

        return path

    @staticmethod
    def calculate_l_shape_path(start_pos, end_pos, prefer_horizontal=True):
        """
        计算L形正交路径

        Args:
            start_pos: 起始点 QPointF
            end_pos: 结束点 QPointF
            prefer_horizontal: 是否优先水平方向布线

        Returns:
            list of QPointF: 路径点列表
        """
        path = [start_pos]

        if prefer_horizontal:
            mid_x = start_pos.x() + (end_pos.x() - start_pos.x()) / 2
            path.append(QPointF(mid_x, start_pos.y()))
            path.append(QPointF(mid_x, end_pos.y()))
        else:
            mid_y = start_pos.y() + (end_pos.y() - start_pos.y()) / 2
            path.append(QPointF(start_pos.x(), mid_y))
            path.append(QPointF(end_pos.x(), mid_y))

        path.append(end_pos)
        return path

    @staticmethod
    def calculate_z_shape_path(start_pos, end_pos):
        """
        计算Z形正交路径（中间有一层转折）

        Returns:
            list of QPointF: 路径点列表
        """
        path = [start_pos]
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()

        mid_x1 = start_pos.x() + dx / 3
        mid_x2 = start_pos.x() + 2 * dx / 3

        path.append(QPointF(mid_x1, start_pos.y()))
        path.append(QPointF(mid_x1, start_pos.y() + dy / 2))
        path.append(QPointF(mid_x2, start_pos.y() + dy / 2))
        path.append(QPointF(mid_x2, end_pos.y()))
        path.append(end_pos)

        return path

    @staticmethod
    def draw_orthogonal_wire(painter, path, color=None, width=2):
        """
        绘制正交线（使用路径绘制，抗锯齿）

        Args:
            painter: QPainter对象
            path: QPointF列表，代表路径
            color: 线条颜色，默认使用黑色
            width: 线条宽度
        """
        if len(path) < 2:
            return

        if color is None:
            color = QColor(50, 50, 50)

        pen = QPen(color, width)
        pen.setJoinStyle(Qt.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        painterPath = QPainterPath()
        painterPath.moveTo(path[0])

        for i in range(1, len(path)):
            painterPath.lineTo(path[i])

        painter.drawPath(painterPath)

    @staticmethod
    def draw_orthogonal_wire_with_arrow(painter, path, color=None, width=2, arrow_size=8):
        """
        绘制带箭头的正交线

        Args:
            painter: QPainter对象
            path: QPointF列表，代表路径
            color: 线条颜色
            width: 线条宽度
            arrow_size: 箭头大小
        """
        if len(path) < 2:
            return

        OrthogonalWirePainter.draw_orthogonal_wire(painter, path, color, width)

        last_segment_start = path[-2]
        last_segment_end = path[-1]

        dx = last_segment_end.x() - last_segment_start.x()
        dy = last_segment_end.y() - last_segment_start.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        dx /= length
        dy /= length

        arrow_point1 = QPointF(
            last_segment_end.x() - arrow_size * dx + arrow_size * 0.5 * dy,
            last_segment_end.y() - arrow_size * dy - arrow_size * 0.5 * dx
        )
        arrow_point2 = QPointF(
            last_segment_end.x() - arrow_size * dx - arrow_size * 0.5 * dy,
            last_segment_end.y() - arrow_size * dy + arrow_size * 0.5 * dx
        )

        arrowPen = QPen(color, width)
        arrowPen.setCapStyle(Qt.RoundCap)
        painter.setPen(arrowPen)

        painter.drawLine(last_segment_end, arrow_point1)
        painter.drawLine(last_segment_end, arrow_point2)

class EdgeRouter:
    """边路由管理器 - 处理自动避障、正交布线、线间分离和边捆绑"""

    def __init__(self, graph):
        """
        初始化边路由管理器

        Args:
            graph: NodeGraph实例
        """
        self.graph = graph
        self.wire_spacing = OrthogonalWirePainter.WIRE_SPACING
        self.orthogonal_mode = True
        self.bundling_enabled = True
        self.separation_enabled = True
        self.avoidance_enabled = True

    def get_all_wire_paths(self):
        """
        获取所有连线的路径信息，用于后续处理

        Returns:
            list: 每个元素是(source_port, target_port, path_points)的元组
        """
        wire_paths = []

        for node in self.graph.all_nodes():
            for output_port in node.outputs().values():
                connected_ports = output_port.connected_ports()
                for input_port in connected_ports:
                    source_pos = output_port.scene_pos()
                    target_pos = input_port.scene_pos()

                    if self.orthogonal_mode:
                        path = OrthogonalWirePainter.calculate_l_shape_path(
                            source_pos, target_pos
                        )
                    else:
                        path = [source_pos, target_pos]

                    wire_paths.append((output_port, input_port, path))

        return wire_paths

    def separate_parallel_wires(self, wire_paths):
        """
        线间自动分离 - 当多条线平行时，自动增加间距

        Args:
            wire_paths: 连线路径列表

        Returns:
            分离后的路径列表
        """
        if not self.separation_enabled:
            return wire_paths

        connection_groups = defaultdict(list)

        for idx, (src_port, tgt_port, path) in enumerate(wire_paths):
            if len(path) >= 2:
                key = self._get_path_key(path)
                connection_groups[key].append((idx, src_port, tgt_port, path))

        separated_paths = list(wire_paths)

        for key, group in connection_groups.items():
            if len(group) > 1:
                offsets = self._calculate_offsets(len(group))

                for i, (idx, src_port, tgt_port, path) in enumerate(group):
                    if len(path) >= 2:
                        new_path = self._apply_offset_to_path(path, offsets[i])
                        separated_paths[idx] = (src_port, tgt_port, new_path)

        return separated_paths

    def _get_path_key(self, path):
        """获取路径的分组键（用于识别平行线）"""
        if len(path) < 2:
            return None

        start = path[0]
        end = path[-1]

        if abs(end.x() - start.x()) > abs(end.y() - start.y()):
            return ('horizontal', min(start.x(), end.x()), max(start.x(), end.x()))
        else:
            return ('vertical', min(start.y(), end.y()), max(start.y(), end.y()))

    def _calculate_offsets(self, count):
        """
        计算分离偏移量

        Args:
            count: 平行线数量

        Returns:
            list: 每个偏移量
        """
        if count <= 1:
            return [0]

        total_width = (count - 1) * self.wire_spacing
        start_offset = -total_width / 2

        return [start_offset + i * self.wire_spacing for i in range(count)]

    def _apply_offset_to_path(self, path, offset):
        """
        对路径应用偏移量（只在弯折点处应用垂直于线方向的偏移）

        Args:
            path: 原始路径
            offset: 偏移量

        Returns:
            偏移后的路径
        """
        if len(path) < 2:
            return path

        new_path = [path[0]]

        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            curr_point = path[i]
            next_point = path[i + 1]

            dx1 = curr_point.x() - prev_point.x()
            dy1 = curr_point.y() - prev_point.y()
            dx2 = next_point.x() - curr_point.x()
            dy2 = next_point.y() - curr_point.y()

            if abs(dx1) > abs(dy1):
                new_point = QPointF(curr_point.x(), curr_point.y() + offset)
            else:
                new_point = QPointF(curr_point.x() + offset, curr_point.y())

            new_path.append(new_point)

        new_path.append(path[-1])
        return new_path

    def bundle_related_edges(self, wire_paths):
        """
        Edge Bundling - 将相关的边捆绑在一起（简化版本）

        Args:
            wire_paths: 连线路径列表

        Returns:
            捆绑后的路径列表
        """
        if not self.bundling_enabled:
            return wire_paths

        return wire_paths

    def avoid_obstacles(self, wire_paths, obstacles=None):
        """
        自动避障 - 尝试绕过障碍物的连线

        Args:
            wire_paths: 连线路径列表
            obstacles: 障碍物列表（如果是None，使用节点作为障碍物）

        Returns:
            避障后的路径列表
        """
        if not self.avoidance_enabled:
            return wire_paths

        if obstacles is None:
            obstacles = list(self.graph.all_nodes())

        avoided_paths = []

        for src_port, tgt_port, path in wire_paths:
            if len(path) < 2 or not obstacles:
                avoided_paths.append((src_port, tgt_port, path))
                continue

            new_path = self._reroute_around_obstacles(path, obstacles)
            avoided_paths.append((src_port, tgt_port, new_path))

        return avoided_paths

    def _reroute_around_obstacles(self, path, obstacles):
        """
        重新路由路径以绕过障碍物

        Args:
            path: 原始路径
            obstacles: 障碍物列表

        Returns:
            避障后的路径
        """
        if len(path) < 2:
            return path

        new_path = list(path)

        for i in range(1, len(new_path) - 1):
            for obstacle in obstacles:
                if self._point_near_node(new_path[i], obstacle):
                    new_path = self._create_detour(new_path, i, obstacle)

        return new_path

    def _point_near_node(self, point, node):
        """检查点是否靠近节点"""
        node_pos = node.graph_pos if hasattr(node, 'graph_pos') else QPointF(0, 0)
        threshold = 80

        dx = abs(point.x() - node_pos.x())
        dy = abs(point.y() - node_pos.y())

        return dx < threshold and dy < threshold

    def _create_detour(self, path, index, obstacle):
        """创建绕行路径"""
        new_path = list(path[:index + 1])

        if index > 0 and index < len(path) - 1:
            prev_point = path[index - 1]
            next_point = path[index + 1]

            dx = next_point.x() - prev_point.x()
            dy = next_point.y() - prev_point.y()

            detour_distance = 30

            if abs(dx) > abs(dy):
                offset = detour_distance if dy >= 0 else -detour_distance
                new_path.append(QPointF(path[index].x(), path[index].y() + offset))
            else:
                offset = detour_distance if dx >= 0 else -detour_distance
                new_path.append(QPointF(path[index].x() + offset, path[index].y()))

        new_path.extend(path[index + 1:])
        return new_path

    def apply_orthogonal_routing(self):
        """
        应用正交路由到图中所有连线

        Returns:
            应用后的路径字典 {(src_port, tgt_port): path}
        """
        wire_paths = self.get_all_wire_paths()

        if self.separation_enabled:
            wire_paths = self.separate_parallel_wires(wire_paths)

        if self.bundling_enabled:
            wire_paths = self.bundle_related_edges(wire_paths)

        if self.avoidance_enabled:
            wire_paths = self.avoid_obstacles(wire_paths)

        result = {}
        for src_port, tgt_port, path in wire_paths:
            result[(src_port, tgt_port)] = path

        return result

def create_orthogonal_wire_painter_func(wire_spacing=15):
    """
    创建正交布线线缆绘制函数的工厂函数

    Args:
        wire_spacing: 线间间距

    Returns:
        自定义的wire_painter函数
    """
    def orthogonal_wire_painter(painter, points, source_port, target_port):
        """
        自定义正交线缆绘制函数

        Args:
            painter: QPainter对象
            points: 线缆路径点列表
            source_port: 源端口
            target_port: 目标端口
        """
        if len(points) < 2:
            return

        path = [QPointF(p[0], p[1]) if not isinstance(p, QPointF) else p for p in points]

        color = QColor(50, 50, 50)
        width = 2

        OrthogonalWirePainter.draw_orthogonal_wire(painter, path, color, width)

    return orthogonal_wire_painter

class CircleNodeOut(BaseNodeCircle):
    """圆形节点"""
    __identifier__ = 'user.circle'
    NODE_NAME = 'Circle Node Out'
    ports_removable = True
    
    def __init__(self):
        super(CircleNodeOut, self).__init__()
        self.port_name = "out"
        self.set_property('color', (200, 100, 50))
        self.width = 1
        self.port_type = 'signal'
        self.bus_def = None
        self.bus_name = ''
        self.bus_mode = ''
        self.bus_map = []
        self.add_input(self.port_name, display_name=False)

    def set_port_name(self, port_name):
        """设置端口名称"""
        self.set_port_deletion_allowed(True)
        for port_name_old in list(self.inputs().keys()):
            self.delete_input(port_name_old)
        self.add_input(port_name, display_name=False)
        self.port_name = port_name
        self.set_port_deletion_allowed(False)

class CircleNodeIn(BaseNodeCircle):
    """圆形节点"""
    __identifier__ = 'user.circle'
    NODE_NAME = 'Circle Node In'
    PORT_NAME = "in"
    
    def __init__(self):
        super(CircleNodeIn, self).__init__()
        self.set_property('color', (200, 100, 50))
        self.width = 1
        self.port_type = 'signal'
        self.bus_def = None
        self.bus_name = ''
        self.bus_mode = ''
        self.bus_map = []
        self.add_output(self.PORT_NAME, display_name=False)
    
    def set_port_name(self, port_name):
        """设置端口名称"""
        self.set_port_deletion_allowed(True)
        for port_name_old in list(self.outputs().keys()):
            self.delete_output(port_name_old)
        self.add_output(port_name, display_name=False)
        self.PORT_NAME = port_name
        self.set_port_deletion_allowed(False)

def get_all_connections(graph):
    """
    获取当前 NodeGraph 中的所有连接关系。
    返回一个包含连接信息的列表，每条连接是一个字典。
    """
    connections = []
    
    try:
        for node in graph.all_nodes():
            for output_port in node.outputs().values():
                connected_ports = output_port.connected_ports()
                
                for input_port in connected_ports:
                    src_node = output_port.node().name()
                    dst_node = input_port.node().name()
                    
                    connection_info = {
                        "source_node": src_node,
                        "target_node": dst_node,
                        "source_port": output_port.name(),
                        "target_port": input_port.name()
                    }
                    
                    connections.append(connection_info)
        
    except Exception as e:
        print(f"获取连接关系时出错: {e}")
    
    return connections

def make_template_node(serialized_data, template_name, node_data=None):
    """
    根据序列化数据和模板名称动态生成 TemplateNode 类。
    每次调用返回一个**全新的类**，继承自 BaseNode。
    
    Args:
        serialized_data: 序列化数据（保持向后兼容）
        template_name: 模板名称，用于生成类名和节点显示名称
        node_data: 节点数据，包含ports、bus_interfaces、port_maps等信息
    
    Returns:
        动态创建的节点类
    """

    def bus_port_painter(painter, rect, port):
        """
        自定义 bus interface 端口绘制函数
        - 绘制为方形
        - 使用蓝色填充
        """
        painter.setBrush(QColor(100, 150, 255))
        painter.setPen(QColor(60, 100, 200))
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

    def __init__(self):
        super(self.__class__, self).__init__()

        self.set_name(template_name)
        
        self.node_data = node_data
        self.component_data = node_data
        
        mapped_physical_ports = set()
        for port_map in node_data.get('port_maps', []):
            physical_port = port_map.get('physical_port', '')
            if physical_port:
                mapped_physical_ports.add(physical_port)
        
        for port in node_data.get('ports', []):
            port_name = port.get('name', 'Unknown')
            if port_name not in mapped_physical_ports:
                direction = port.get('direction', 'in')
                
                if direction == 'in' or direction == 'input' or direction == 'inout':
                    self.add_input(port_name)
                if direction == 'out' or direction == 'output' or direction == 'inout':
                    self.add_output(port_name)
        
        for bus_interface in node_data.get('bus_interfaces', []):
            bus_name = bus_interface.get('name', '')
            if bus_name:
                mode = bus_interface.get('mode', 'master')
                if mode == 'master':
                    self.add_output(bus_name, painter_func=bus_port_painter)
                elif mode == 'slave':
                    self.add_input(bus_name, painter_func=bus_port_painter)

    attrs = {
        '__identifier__': 'user',
        'NODE_NAME': template_name,
        'data': node_data,
        '__init__': __init__,
    }

    TemplateNode = type(
        f'{template_name}_node',
        (BaseNode,),
        attrs
    )

    return TemplateNode


# 创建自定义 BackdropNode 类，支持节点整体移动
def create_backdrop_node_class():
    """动态创建支持整体移动的 BackdropNode 类"""
    try:
        BaseBackdropNode = NodeGraphQtBackdropNode
        
        class MovableBackdropNode(BaseBackdropNode):
            """
            自定义 BackdropNode，支持节点整体移动
            """
            def __init__(self):
                super().__init__()
                self._child_nodes = []  # 存储子节点列表
                self._last_pos = None   # 记录上一次位置
            
            def wrap_nodes(self, nodes):
                """
                包裹节点到 backdrop 中
                
                Args:
                    nodes: 要包裹的节点列表
                """
                super().wrap_nodes(nodes)
                self._child_nodes = nodes
                self._last_pos = self.pos()
            
            def set_pos(self, x, y):
                """
                重写 set_pos 方法，当 backdrop 移动时同步移动所有子节点
                """
                # 调用父类方法设置位置
                super().set_pos(x, y)
                
                # 如果有子节点且位置发生了变化，则同步移动子节点
                if self._child_nodes and self._last_pos is not None:
                    dx = x - self._last_pos[0]
                    dy = y - self._last_pos[1]
                    
                    # 移动所有子节点
                    for node in self._child_nodes:
                        node_pos = node.pos()
                        if isinstance(node_pos, (list, tuple)):
                            node.set_pos(node_pos[0] + dx, node_pos[1] + dy)
                        else:
                            node.set_pos(node_pos.x() + dx, node_pos.y() + dy)
                
                # 更新上一次位置
                self._last_pos = (x, y)
        
        return MovableBackdropNode
    except ImportError as e:
        print(f"无法导入 BackdropNode: {e}")
        return None


# 导出 BackdropNode（如果可用）
BackdropNode = create_backdrop_node_class()
