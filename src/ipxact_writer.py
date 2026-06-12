import xml.etree.ElementTree as ET
import os
import json

class IPXactWriter:
    def __init__(self):
        pass
    
    def write_file(self, file_path, component_name, connections):
        """将component和连线关系写回IP-XACT文件"""
        try:
            # 定义命名空间
            namespace = 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
            ET.register_namespace('ipxact', namespace)
            
            # 检查文件是否存在且不为空
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                # 创建新的IP-XACT XML结构
                root = ET.Element('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}component')
                
                # 添加基本元素
                vendor = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vendor')
                vendor.text = 'Phytium'
                library = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}library')
                library.text = 'interegrated'
                name = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                name.text = component_name
                version = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}version')
                version.text = '1.0'
                
                # 添加description元素
                description = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}description')
                description.text = ''
                
                # 添加model元素
                model = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}model')
                
                # 添加ports元素
                ports = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}ports')
                
                # 添加componentInstances元素
                component_instances = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}componentInstances')
                
                # 添加interconnections元素
                ET.SubElement(component_instances, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}interconnections')
                
                # 创建树
                tree = ET.ElementTree(root)
            else:
                # 解析现有文件
                tree = ET.parse(file_path)
                root = tree.getroot()
            
            # 定义命名空间
            ns = {
                'ipxact': 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
            }
            
            # 确定component元素
            # 如果root本身就是component元素，直接使用
            if root.tag == '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}component':
                component_elem = root
            else:
                # 否则查找component元素
                component_elem = root.find('.//ipxact:component', namespaces=ns)
                if component_elem is None:
                    print("错误: 未找到component元素")
                    return False
            
            # 查找或创建interconnections
            interconnections_elem = component_elem.find('.//ipxact:interconnections', namespaces=ns)
            if interconnections_elem is None:
                # 查找或创建componentInstances
                component_instances_elem = component_elem.find('.//ipxact:componentInstances', namespaces=ns)
                if component_instances_elem is None:
                    # 创建componentInstances
                    model_elem = component_elem.find('.//ipxact:model', namespaces=ns)
                    if model_elem is None:
                        model_elem = ET.SubElement(component_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}model')
                    component_instances_elem = ET.SubElement(model_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}componentInstances')
                
                # 创建interconnections
                interconnections_elem = ET.SubElement(component_instances_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}interconnections')
            else:
                # 清空现有的interconnections
                for child in interconnections_elem:
                    interconnections_elem.remove(child)
            
            # 添加新的连线关系
            for i, connection in enumerate(connections):
                interconnection_elem = ET.SubElement(interconnections_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}interconnection')
                
                # 设置连线名称
                name_elem = ET.SubElement(interconnection_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                name_elem.text = f"connection_{i+1}"
                
                # 设置源端口
                src_elem = ET.SubElement(interconnection_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}source')
                src_instance_elem = ET.SubElement(src_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}instanceName')
                src_instance_elem.text = connection['source_node']
                src_port_elem = ET.SubElement(src_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}portName')
                src_port_elem.text = connection['source_port']
                
                # 设置目标端口
                dest_elem = ET.SubElement(interconnection_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}destination')
                dest_instance_elem = ET.SubElement(dest_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}instanceName')
                dest_instance_elem.text = connection['target_node']
                dest_port_elem = ET.SubElement(dest_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}portName')
                dest_port_elem.text = connection['target_port']
            
            # 写回文件
            tree.write(file_path, encoding='UTF-8', xml_declaration=True)
            return True
            
        except Exception as e:
            print(f"写入文件时出错: {e}")
            return False
    
    def create_component_file(self, file_path, component_data):
        """创建新的component XML文件"""
        try:
            # 定义命名空间
            namespace = 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
            ET.register_namespace('ipxact', namespace)
            
            # 创建新的IP-XACT XML结构
            root = ET.Element('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}component')
            
            # 添加基本元素
            vendor = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vendor')
            vendor.text = component_data.get('vendor', 'Phytium')
            
            library = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}library')
            library.text = component_data.get('library', 'interegrated')
            
            name = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
            name.text = component_data.get('name', 'UnknownComponent')
            
            version = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}version')
            version.text = component_data.get('version', '1.0')
            
            # 添加description元素
            description = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}description')
            description.text = component_data.get('description', '')
            
            # 添加model元素
            model = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}model')
            
            # 添加ports元素
            ports = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}ports')
            
            # 添加ports
            for port in component_data.get('ports', []):
                port_elem = ET.SubElement(ports, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}port')
                
                # 添加port名称
                port_name = ET.SubElement(port_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                port_name.text = port.get('name', 'UnknownPort')
                
                # 添加port方向（转换为IP-XACT标准格式）
                direction = ET.SubElement(port_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}direction')
                port_direction = port.get('direction', 'input')
                # 转换方向格式
                if port_direction == 'input':
                    direction.text = 'in'
                elif port_direction == 'output':
                    direction.text = 'out'
                else:
                    direction.text = port_direction
                
                # 添加port wire
                wire = ET.SubElement(port_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}wire')
                
                # 添加port width
                width = ET.SubElement(wire, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}width')
                # 尝试解析位宽
                port_width = port.get('width', '1')
                port_msb = port.get('msb', '')
                port_lsb = port.get('lsb', '')
                
                # 如果位宽包含冒号，提取MSB-LSB+1作为宽度
                if ':' in port_width:
                    try:
                        # 尝试提取数字部分
                        parts = port_width.split(':')
                        msb = parts[0].strip().replace('[', '')
                        lsb = parts[1].strip().replace(']', '')
                        # 尝试转换为数字
                        if msb.isdigit() and lsb.isdigit():
                            width_val = int(msb) - int(lsb) + 1
                            width.text = str(width_val)
                        else:
                            width.text = '1'
                    except:
                        width.text = '1'
                else:
                    # 直接使用位宽值
                    try:
                        # 尝试转换为数字
                        width_val = int(port_width)
                        width.text = str(width_val)
                    except:
                        width.text = '1'
                
                # 添加vector元素保存MSB和LSB
                if port_msb and port_lsb:
                    vector = ET.SubElement(wire, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vector')
                    
                    # 添加MSB
                    msb_elem = ET.SubElement(vector, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}msb')
                    msb_elem.text = port_msb
                    
                    # 添加LSB
                    lsb_elem = ET.SubElement(vector, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}lsb')
                    lsb_elem.text = port_lsb
            
            # 添加parameters元素
            parameters = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}parameters')
            
            # 添加parameters
            for param in component_data.get('parameters', []):
                parameter_elem = ET.SubElement(parameters, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}parameter')
                
                param_name = ET.SubElement(parameter_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                param_name.text = param.get('name', 'UnknownParameter')
                
                param_type = ET.SubElement(parameter_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}dataType')
                param_type.text = param.get('type', 'int')
                
                param_value = ET.SubElement(parameter_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}value')
                param_value.text = param.get('default_value', '')
            
            # 添加localParameters元素
            local_parameters = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}localParameters')
            
            # 添加localParameters
            for define in component_data.get('defines', []):
                local_param_elem = ET.SubElement(local_parameters, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}localParameter')
                
                local_param_name = ET.SubElement(local_param_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                local_param_name.text = define.get('name', 'UnknownLocalParameter')
                
                local_param_type = ET.SubElement(local_param_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}dataType')
                local_param_type.text = define.get('type', 'int')
                
                local_param_value = ET.SubElement(local_param_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}value')
                local_param_value.text = define.get('default_value', '')
            
            # 添加componentInstances元素
            component_instances = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}componentInstances')
            
            # 添加interconnections元素
            ET.SubElement(component_instances, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}interconnections')
            
            # 添加fileSets元素（保存SystemVerilog文件路径）
            sv_file = component_data.get('sv_file', '')
            if sv_file:
                file_sets = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}fileSets')
                file_set = ET.SubElement(file_sets, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}fileSet')
                
                # 添加fileSet名称
                file_set_name = ET.SubElement(file_set, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                file_set_name.text = 'sourceFiles'
                
                # 添加file元素
                file_elem = ET.SubElement(file_set, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}file')
                
                # 添加文件路径
                file_name = ET.SubElement(file_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                file_name.text = sv_file
                
                # 添加文件类型
                file_type = ET.SubElement(file_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}fileType')
                file_type.text = 'systemVerilogSource'
            
            # 添加busInterfaces元素
            bus_interfaces_data = component_data.get('bus_interfaces', [])
            if bus_interfaces_data:
                bus_interfaces = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}busInterfaces')
                
                # 添加busInterfaces
                for bus_interface in bus_interfaces_data:
                    bus_interface_elem = ET.SubElement(bus_interfaces, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}busInterface')
                    
                    # 添加busInterface名称
                    interface_name = ET.SubElement(bus_interface_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                    interface_name.text = bus_interface.get('name', 'UnknownBusInterface')
                    
                    # 添加busType
                    bus_type = ET.SubElement(bus_interface_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}busType')
                    vendor_elem = ET.SubElement(bus_type, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vendor')
                    vendor_elem.text = bus_interface.get('vendor', 'amba.org')  # 从数据中获取，默认值为'amba.org'
                    library_elem = ET.SubElement(bus_type, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}library')
                    library_elem.text = bus_interface.get('library', 'AMBA')  # 从数据中获取，默认值为'AMBA'
                    name_elem = ET.SubElement(bus_type, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
                    name_elem.text = bus_interface.get('bus_type', 'AXI4')
                    version_elem = ET.SubElement(bus_type, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}version')
                    version_elem.text = bus_interface.get('version', '1.0')  # 从数据中获取，默认值为'1.0'
                    
                    # 添加mode
                    mode = ET.SubElement(bus_interface_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}mode')
                    mode.text = bus_interface.get('mode', 'master')
                    
                    # 添加portMaps元素
                    port_maps_data = component_data.get('port_maps', [])
                    relevant_port_maps = [pm for pm in port_maps_data if pm.get('bus_interface') == bus_interface.get('name')]
                    if relevant_port_maps:
                        port_maps = ET.SubElement(bus_interface_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}portMaps')
                        
                        # 添加portMaps
                        for port_map in relevant_port_maps:
                            port_map_elem = ET.SubElement(port_maps, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}portMap')
                            
                            # 添加logicalPort
                            logical_port = ET.SubElement(port_map_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}logicalPort')
                            logical_port.text = port_map.get('logical_port', '')
                            
                            # 添加physicalPort
                            physical_port = ET.SubElement(port_map_elem, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}physicalPort')
                            physical_port.text = port_map.get('physical_port', '')
            
            # 创建树
            tree = ET.ElementTree(root)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写回文件
            tree.write(file_path, encoding='UTF-8', xml_declaration=True)
            return True
            
        except Exception as e:
            print(f"创建component文件时出错: {e}")
            return False
    
    def create_top_component_file(self, file_path, project_data, nodes_component_data, connections, node_positions=None, session_json=None):
        """创建顶层component的IP-XACT XML文件，包含port、instance、connection信息和完整的session数据"""
        try:
            # 定义命名空间
            namespace = 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
            ET.register_namespace('ipxact', namespace)
            # 注册自定义扩展命名空间
            ET.register_namespace('viz', 'http://www.phytium.com/XMLSchema/visualizer/1.0')
            
            # 创建新的IP-XACT XML结构
            root = ET.Element('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}component')
            
            # 添加基本元素
            vendor = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vendor')
            vendor.text = project_data.get('vendor', 'Phytium')
            
            library = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}library')
            library.text = project_data.get('library', 'interegrated')
            
            name = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name')
            name.text = project_data.get('module_name', 'UnknownModule')
            
            version = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}version')
            version.text = project_data.get('version', '1.0')
            
            # 添加description元素
            description = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}description')
            description.text = project_data.get('description', '')
            
            # 添加vendorExtensions元素（用于存储可视化信息和session数据）
            vendor_extensions = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vendorExtensions')
            
            # 添加visualizer扩展元素
            viz_extension = ET.SubElement(vendor_extensions, '{http://www.phytium.com/XMLSchema/visualizer/1.0}visualizer')
            
            # 添加component_drag_count（字典类型，需要序列化为JSON）
            drag_count = ET.SubElement(viz_extension, '{http://www.phytium.com/XMLSchema/visualizer/1.0}componentDragCount')
            drag_count_data = project_data.get('component_drag_count', {})
            drag_count.text = json.dumps(drag_count_data)
            
            # 添加完整的session JSON数据（包含节点位置等所有graph信息）
            session_data_elem = ET.SubElement(viz_extension, '{http://www.phytium.com/XMLSchema/visualizer/1.0}sessionData')
            if session_json:
                session_data_elem.text = json.dumps(session_json, ensure_ascii=False)
            
            # 添加model元素
            model = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}model')
            
            # 添加ports元素
            ports = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}ports')
            
            # 添加parameters元素
            parameters = ET.SubElement(model, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}parameters')
            
            # 添加componentInstances元素
            component_instances = ET.SubElement(model, '{http://www.accellera.org/IPXACT/1685-2014}componentInstances')
            
            # 添加interconnections元素
            interconnections = ET.SubElement(component_instances, '{http://www.accellera.org/IPXACT/1685-2014}interconnections')
            
            # 定义命名空间字典
            ns = {'ipxact': namespace}
            
            # 添加顶层输入输出端口
            input_ports = project_data.get('input_ports', [])
            output_ports = project_data.get('output_ports', [])
            
            for port in input_ports:
                port_elem = ET.SubElement(ports, '{http://www.accellera.org/IPXACT/1685-2014}port')
                port_name_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}name')
                port_name_elem.text = port.get('name', 'UnknownPort')
                direction_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}direction')
                direction_elem.text = 'in'
                wire_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}wire')
                width_elem = ET.SubElement(wire_elem, '{http://www.accellera.org/IPXACT/1685-2014}width')
                width_elem.text = str(port.get('width', 1))
            
            for port in output_ports:
                port_elem = ET.SubElement(ports, '{http://www.accellera.org/IPXACT/1685-2014}port')
                port_name_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}name')
                port_name_elem.text = port.get('name', 'UnknownPort')
                direction_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}direction')
                direction_elem.text = 'out'
                wire_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}wire')
                width_elem = ET.SubElement(wire_elem, '{http://www.accellera.org/IPXACT/1685-2014}width')
                width_elem.text = str(port.get('width', 1))
            
            # 添加component instances
            for instance_name, instance_info in nodes_component_data.items():
                component_data = instance_info.get('component_data', {})
                node_type = instance_info.get('node_type', '')
                
                # 跳过CircleNodeIn和CircleNodeOut
                if 'CircleNodeIn' in node_type or 'CircleNodeOut' in node_type:
                    continue
                
                instance_elem = ET.SubElement(component_instances, '{http://www.accellera.org/IPXACT/1685-2014}componentInstance')
                
                # 添加instance名称
                instance_name_elem = ET.SubElement(instance_elem, '{http://www.accellera.org/IPXACT/1685-2014}instanceName')
                instance_name_elem.text = instance_name
                
                # 添加componentRef
                component_ref = ET.SubElement(instance_elem, '{http://www.accellera.org/IPXACT/1685-2014}componentRef')
                
                vendor_ref = ET.SubElement(component_ref, '{http://www.accellera.org/IPXACT/1685-2014}vendor')
                vendor_ref.text = component_data.get('vendor', 'Phytium')
                
                library_ref = ET.SubElement(component_ref, '{http://www.accellera.org/IPXACT/1685-2014}library')
                library_ref.text = component_data.get('library', 'interegrated')
                
                name_ref = ET.SubElement(component_ref, '{http://www.accellera.org/IPXACT/1685-2014}name')
                name_ref.text = component_data.get('name', 'UnknownComponent')
                
                version_ref = ET.SubElement(component_ref, '{http://www.accellera.org/IPXACT/1685-2014}version')
                version_ref.text = component_data.get('version', '1.0')
            
            # 添加interconnections
            for i, connection in enumerate(connections):
                interconnection_elem = ET.SubElement(interconnections, '{http://www.accellera.org/IPXACT/1685-2014}interconnection')
                
                # 添加interconnection名称
                interconnection_name = ET.SubElement(interconnection_elem, '{http://www.accellera.org/IPXACT/1685-2014}name')
                interconnection_name.text = f"connection_{i+1}"
                
                # 添加source
                source_elem = ET.SubElement(interconnection_elem, '{http://www.accellera.org/IPXACT/1685-2014}source')
                
                src_instance_name = ET.SubElement(source_elem, '{http://www.accellera.org/IPXACT/1685-2014}instanceName')
                src_instance_name.text = connection.get('source_instance', '')
                
                src_port_name = ET.SubElement(source_elem, '{http://www.accellera.org/IPXACT/1685-2014}portName')
                src_port_name.text = connection.get('source_port', '')
                
                # 添加destination
                dest_elem = ET.SubElement(interconnection_elem, '{http://www.accellera.org/IPXACT/1685-2014}destination')
                
                dest_instance_name = ET.SubElement(dest_elem, '{http://www.accellera.org/IPXACT/1685-2014}instanceName')
                dest_instance_name.text = connection.get('target_instance', '')
                
                dest_port_name = ET.SubElement(dest_elem, '{http://www.accellera.org/IPXACT/1685-2014}portName')
                dest_port_name.text = connection.get('target_port', '')
            
            # 创建树
            tree = ET.ElementTree(root)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写回文件
            tree.write(file_path, encoding='UTF-8', xml_declaration=True)
            return True
            
        except Exception as e:
            print(f"创建顶层component文件时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def write_bus_definition(self, busdef_data, save_dir):
        """将bus definition写入XML文件"""
        try:
            # 创建XML根元素，使用ipxact前缀
            root = ET.Element('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}busDefinition')
            
            # 添加命名空间
            root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
            root.set('xsi:schemaLocation', 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd')
            
            # 添加vendor
            vendor_elem = ET.SubElement(root, '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}vendor')
            vendor_elem.text = busdef_data['vendor']
            
            # 添加library
            library_elem = ET.SubElement(root, '{http://www.accellera.org/IPXACT/1685-2014}library')
            library_elem.text = busdef_data['library']
            
            # 添加name
            name_elem = ET.SubElement(root, '{http://www.accellera.org/IPXACT/1685-2014}name')
            name_elem.text = busdef_data['name']
            
            # 添加version
            version_elem = ET.SubElement(root, '{http://www.accellera.org/IPXACT/1685-2014}version')
            version_elem.text = busdef_data['version']
            
            # 添加description
            description_elem = ET.SubElement(root, '{http://www.accellera.org/IPXACT/1685-2014}description')
            description_elem.text = busdef_data.get('description', '')
            
            # 添加signalDefinitions
            signal_definitions_elem = ET.SubElement(root, '{http://www.accellera.org/IPXACT/1685-2014}signalDefinitions')
            
            # 添加每个signal
            for signal in busdef_data['signals']:
                signal_elem = ET.SubElement(signal_definitions_elem, '{http://www.accellera.org/IPXACT/1685-2014}signalDefinition')
                
                # 添加signal name
                signal_name_elem = ET.SubElement(signal_elem, '{http://www.accellera.org/IPXACT/1685-2014}name')
                signal_name_elem.text = signal['name']
                
                # 添加signal width
                width_elem = ET.SubElement(signal_elem, '{http://www.accellera.org/IPXACT/1685-2014}width')
                width_elem.text = str(signal['width'])
                
                # 添加signal presence
                if 'presence' in signal:
                    presence_elem = ET.SubElement(signal_elem, '{http://www.accellera.org/IPXACT/1685-2014}presence')
                    presence_elem.text = signal['presence']
                
                # 添加signal driver
                if 'driver' in signal:
                    driver_elem = ET.SubElement(signal_elem, '{http://www.accellera.org/IPXACT/1685-2014}driver')
                    driver_elem.text = signal['driver']
            
            # 创建XML树
            tree = ET.ElementTree(root)
            
            # 构建文件名
            filename = f"{busdef_data['name']}_{busdef_data['version']}.xml"
            
            # 构建完整路径
            file_path = os.path.join(save_dir, filename)
            
            # 保存XML文件
            tree.write(file_path, encoding='UTF-8', xml_declaration=True)
            
            return file_path
        except Exception as e:
            print(f"保存bus definition失败: {e}")
            return None
    
    def write_abstract_bus_definition(self, busdef_data, save_dir):
        """将abstract bus definition写入XML文件"""
        try:
            # 创建XML根元素，使用ipxact前缀
            abstract_root = ET.Element('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}abstractionDefinition')
            
            # 添加命名空间
            abstract_root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
            abstract_root.set('xsi:schemaLocation', 'http://www.accellera.org/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd')
            
            # 添加vendor
            abstract_vendor_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}vendor')
            abstract_vendor_elem.text = busdef_data['vendor']
            
            # 添加library
            abstract_library_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}library')
            abstract_library_elem.text = busdef_data['library']
            
            # 添加name
            abstract_name_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}name')
            abstract_name_elem.text = f"{busdef_data['name']}_abstract"
            
            # 添加version
            abstract_version_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}version')
            abstract_version_elem.text = busdef_data['version']
            
            # 添加description
            abstract_description_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}description')
            abstract_description_elem.text = f"Abstract bus definition for {busdef_data['name']}"
            
            # 添加busRef，引用对应的busDefinition
            bus_ref_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}busRef')
            bus_ref_elem.set('vendor', busdef_data['vendor'])
            bus_ref_elem.set('library', busdef_data['library'])
            bus_ref_elem.set('name', busdef_data['name'])
            bus_ref_elem.set('version', busdef_data['version'])
            
            # 添加ports
            ports_elem = ET.SubElement(abstract_root, '{http://www.accellera.org/IPXACT/1685-2014}ports')
            
            # 添加每个port
            for signal in busdef_data['signals']:
                port_elem = ET.SubElement(ports_elem, '{http://www.accellera.org/IPXACT/1685-2014}port')
                
                # 添加logicalName
                logical_name_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}logicalName')
                logical_name_elem.text = signal['name']
                
                # 添加wire
                wire_elem = ET.SubElement(port_elem, '{http://www.accellera.org/IPXACT/1685-2014}wire')
                
                # 添加onMaster
                on_master_elem = ET.SubElement(wire_elem, '{http://www.accellera.org/IPXACT/1685-2014}onMaster')
                master_direction_elem = ET.SubElement(on_master_elem, '{http://www.accellera.org/IPXACT/1685-2014}direction')
                # 使用用户设置的Master方向
                master_direction_elem.text = signal.get('master_direction', 'out')
                
                # 添加onSlave
                on_slave_elem = ET.SubElement(wire_elem, '{http://www.accellera.org/IPXACT/1685-2014}onSlave')
                slave_direction_elem = ET.SubElement(on_slave_elem, '{http://www.accellera.org/IPXACT/1685-2014}direction')
                # 使用用户设置的Slave方向
                slave_direction_elem.text = signal.get('slave_direction', 'in')
            
            # 创建XML树
            abstract_tree = ET.ElementTree(abstract_root)
            
            # 构建文件名
            abstract_filename = f"{busdef_data['name']}_abstract_{busdef_data['version']}.xml"
            
            # 构建完整路径
            abstract_file_path = os.path.join(save_dir, abstract_filename)
            
            # 保存XML文件
            abstract_tree.write(abstract_file_path, encoding='UTF-8', xml_declaration=True)
            
            return abstract_file_path
        except Exception as e:
            print(f"保存abstract bus definition失败: {e}")
            return None
