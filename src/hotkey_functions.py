#!/usr/bin/python

# ------------------------------------------------------------------------------
# menu command functions
# ------------------------------------------------------------------------------

from PyQt5.QtWidgets import QInputDialog, QMessageBox

def add_circle_node_out(graph):
    """添加圆形节点"""
    try:
        # 弹出对话框让用户输入节点名称
        name, ok = QInputDialog.getText(None, "设置Input Port名称", "请输入Input Port名称:", text="OutPort")
        if not ok or not name.strip():
            return
        
        # 在graph中心位置创建圆形节点
        node = graph.create_node(
            'user.circle.CircleNodeOut',
            name=name.strip(),
            pos=graph.cursor_pos()
        )
        
        # 设置端口名称
        #node.set_port_name(name.strip())
        
        # 查找或创建BackdropNode
        backdrop_node = None
        for existing_node in graph.all_nodes():
            # 检查这个BackdropNode是否是用于output port的
            if existing_node.name() == "Output Ports":
                backdrop_node = existing_node
                break
        
        # 如果没有找到，创建一个新的BackdropNode
        if not backdrop_node:
            backdrop_node = graph.create_node('nodeGraphQt.nodes.BackdropNode', name='Output Ports')
            # 设置BackdropNode的颜色
            backdrop_node.set_property('color', (50, 50, 80, 100))
        
        # 将新节点添加到BackdropNode中
        # 找到所有CircleNodeOut节点
        nodes_in_backdrop = []
        for existing_node in graph.all_nodes():
            if existing_node != backdrop_node and existing_node.type_ == 'user.circle.CircleNodeOut':
                nodes_in_backdrop.append(existing_node)
        
        # 将新节点也加入
        nodes_in_backdrop.append(node)
        
        # 使用wrap_nodes方法包裹所有节点
        backdrop_node.wrap_nodes(nodes_in_backdrop)
        
        print(f"已创建圆形节点: {node.name()}")
    except Exception as e:
        print(f"创建圆形节点失败: {e}")
        QMessageBox.critical(None, "错误", f"创建圆形节点失败: {str(e)}")

def add_circle_node_in(graph):
    """添加圆形节点"""
    try:
        # 弹出对话框让用户输入节点名称
        name, ok = QInputDialog.getText(None, "设置Output Port名称", "请输入Output Port名称:", text="InPort")
        if not ok or not name.strip():
            return
        
        # 在graph中心位置创建圆形节点
        node = graph.create_node(
            'user.circle.CircleNodeIn',
            name=name.strip(),
            pos=graph.cursor_pos()
        )
        
        # 设置端口名称
        #node.set_port_name(name.strip())
        
        # 查找或创建BackdropNode
        backdrop_node = None
        for existing_node in graph.all_nodes():
            # 检查这个BackdropNode是否是用于input port的
            if existing_node.name() == "Input Ports":
                backdrop_node = existing_node
                break
        
        # 如果没有找到，创建一个新的BackdropNode
        if not backdrop_node:
            backdrop_node = graph.create_node('nodeGraphQt.nodes.BackdropNode', name='Input Ports')
            # 设置BackdropNode的颜色
            backdrop_node.set_property('color', (80, 50, 50, 100))
        
        # 将新节点添加到BackdropNode中
        # 找到所有CircleNodeIn节点
        nodes_in_backdrop = []
        for existing_node in graph.all_nodes():
            if existing_node != backdrop_node and existing_node.type_ == 'user.circle.CircleNodeIn':
                nodes_in_backdrop.append(existing_node)
        
        # 将新节点也加入
        nodes_in_backdrop.append(node)
        
        # 使用wrap_nodes方法包裹所有节点
        backdrop_node.wrap_nodes(nodes_in_backdrop)
        
        print(f"已创建圆形节点: {node.name()}")
    except Exception as e:
        print(f"创建圆形节点失败: {e}")
        QMessageBox.critical(None, "错误", f"创建圆形节点失败: {str(e)}")


def zoom_in(graph):
    """
    Set the node graph to zoom in by 0.1
    """
    zoom = graph.get_zoom() + 0.1
    graph.set_zoom(zoom)


def zoom_out(graph):
    """
    Set the node graph to zoom in by 0.1
    """
    zoom = graph.get_zoom() - 0.2
    graph.set_zoom(zoom)


def reset_zoom(graph):
    """
    Reset zoom level.
    """
    graph.reset_zoom()


def layout_h_mode(graph):
    """
    Set node graph layout direction to horizontal.
    """
    graph.set_layout_direction(0)


def layout_v_mode(graph):
    """
    Set node graph layout direction to vertical.
    """
    graph.set_layout_direction(1)


def open_session(graph):
    """
    Prompts a file open dialog to load a session.
    """
    current = graph.current_session()
    file_path = graph.load_dialog(current)
    if file_path:
        graph.load_session(file_path)


def import_session(graph):
    """
    Prompts a file open dialog to load a session.
    """
    current = graph.current_session()
    file_path = graph.load_dialog(current)
    if file_path:
        graph.import_session(file_path)


def save_session(graph):
    """
    Prompts a file save dialog to serialize a session if required.
    """
    current = graph.current_session()
    if current:
        graph.save_session(current)
        msg = 'Session layout saved:\n{}'.format(current)
        viewer = graph.viewer()
        viewer.message_dialog(msg, title='Session Saved')
    else:
        save_session_as(graph)


def save_session_as(graph):
    """
    Prompts a file save dialog to serialize a session.
    """
    current = graph.current_session()
    file_path = graph.save_dialog(current)
    if file_path:
        graph.save_session(file_path)


def clear_session(graph):
    """
    Prompts a warning dialog to new a node graph session.
    """
    if graph.question_dialog('Clear Current Session?', 'Clear Session'):
        graph.clear_session()

def quit_qt(graph):
    """
    Quit the Qt application.
    """
    from Qt import QtCore
    QtCore.QCoreApplication.quit()

def clear_undo(graph):
    """
    Prompts a warning dialog to clear undo.
    """
    viewer = graph.viewer()
    msg = 'Clear all undo history, Are you sure?'
    if viewer.question_dialog('Clear Undo History', msg):
        graph.clear_undo_stack()


def copy_nodes(graph):
    """
    Copy nodes to the clipboard.
    """
    graph.copy_nodes()


def cut_nodes(graph):
    """
    Cut nodes to the clip board.
    """
    graph.cut_nodes()


def paste_nodes(graph):
    """
    Pastes nodes copied from the clipboard.
    """
    # by default the graph will inherite the global style
    # from the graph when pasting nodes.
    # to disable this behaviour set `adjust_graph_style` to False.
    graph.paste_nodes(adjust_graph_style=False)


def delete_nodes_and_pipes(graph):
    """
    Delete selected nodes and connections.
    """
    graph.delete_nodes(graph.selected_nodes())
    for pipe in graph.selected_pipes():
        pipe[0].disconnect_from(pipe[1])


def extract_nodes(graph):
    """
    Extract selected nodes.
    """
    graph.extract_nodes(graph.selected_nodes())


def clear_node_connections(graph):
    """
    Clear port connection on selected nodes.
    """
    graph.undo_stack().beginMacro('clear selected node connections')
    for node in graph.selected_nodes():
        for port in node.input_ports() + node.output_ports():
            port.clear_connections()
    graph.undo_stack().endMacro()


def select_all_nodes(graph):
    """
    Select all nodes.
    """
    graph.select_all()


def clear_node_selection(graph):
    """
    Clear node selection.
    """
    graph.clear_selection()


def invert_node_selection(graph):
    """
    Invert node selection.
    """
    graph.invert_selection()


def disable_nodes(graph):
    """
    Toggle disable on selected nodes.
    """
    graph.disable_nodes(graph.selected_nodes())


def duplicate_nodes(graph):
    """
    Duplicated selected nodes.
    """
    graph.duplicate_nodes(graph.selected_nodes())


def expand_group_node(graph):
    """
    Expand selected group node.
    """
    selected_nodes = graph.selected_nodes()
    if not selected_nodes:
        graph.message_dialog('Please select a "GroupNode" to expand.')
        return
    graph.expand_group_node(selected_nodes[0])


def fit_to_selection(graph):
    """
    Sets the zoom level to fit selected nodes.
    """
    graph.fit_to_selection()


def show_undo_view(graph):
    """
    Show the undo list widget.
    """
    graph.undo_view.show()


def curved_pipe(graph):
    """
    Set node graph pipes layout as curved.
    """
    from NodeGraphQt.constants import PipeLayoutEnum
    graph.set_pipe_style(PipeLayoutEnum.CURVED.value)


def straight_pipe(graph):
    """
    Set node graph pipes layout as straight.
    """
    from NodeGraphQt.constants import PipeLayoutEnum
    graph.set_pipe_style(PipeLayoutEnum.STRAIGHT.value)


def angle_pipe(graph):
    """
    Set node graph pipes layout as angled.
    """
    from NodeGraphQt.constants import PipeLayoutEnum
    graph.set_pipe_style(PipeLayoutEnum.ANGLE.value)


def bg_grid_none(graph):
    """
    Turn off the background patterns.
    """
    from NodeGraphQt.constants import ViewerEnum
    graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_NONE.value)


def bg_grid_dots(graph):
    """
    Set background node graph background with grid dots.
    """
    from NodeGraphQt.constants import ViewerEnum
    graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_DOTS.value)


def bg_grid_lines(graph):
    """
    Set background node graph background with grid lines.
    """
    from NodeGraphQt.constants import ViewerEnum
    graph.set_grid_mode(ViewerEnum.GRID_DISPLAY_LINES.value)


def layout_graph_down(graph):
    """
    Auto layout the nodes down stream.
    """
    nodes = graph.selected_nodes() or graph.all_nodes()
    graph.auto_layout_nodes(nodes=nodes, down_stream=True)


def layout_graph_up(graph):
    """
    Auto layout the nodes up stream.
    """
    nodes = graph.selected_nodes() or graph.all_nodes()
    graph.auto_layout_nodes(nodes=nodes, down_stream=False)


def toggle_node_search(graph):
    """
    show/hide the node search widget.
    """
    graph.toggle_node_search()
