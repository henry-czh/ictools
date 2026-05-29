import xml.etree.ElementTree as ET
import os

class IPXactParser:
    def __init__(self):
        pass
    
    def parse_file(self, file_path):
        """解析IP-XACT文件，提取component信息"""
        try:
            # 解析XML文件
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 定义命名空间
            ns = {
                'ipxact': 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
            }
            
            # 提取component信息
            components = []
            
            # 检查根元素是否是component
            if root.tag == '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}component':
                component_elements = [root]
            else:
                # 查找所有component
                component_elements = root.findall('.//ipxact:component', namespaces=ns)
            
            for component_elem in component_elements:
                component = {
                    'name': '',
                    'description': '',
                    'vendor': '',
                    'library': '',
                    'version': '',
                    'ports': [],
                    'parameters': [],
                    'defines': [],
                    'bus_interfaces': [],
                    'port_maps': []
                }
                
                # 提取component名称
                name_elem = component_elem.find('.//ipxact:name', namespaces=ns)
                if name_elem is not None:
                    component['name'] = name_elem.text
                
                # 提取component描述
                description_elem = component_elem.find('.//ipxact:description', namespaces=ns)
                if description_elem is not None:
                    component['description'] = description_elem.text
                
                # 提取vendor
                vendor_elem = component_elem.find('.//ipxact:vendor', namespaces=ns)
                if vendor_elem is not None:
                    component['vendor'] = vendor_elem.text
                
                # 提取library
                library_elem = component_elem.find('.//ipxact:library', namespaces=ns)
                if library_elem is not None:
                    component['library'] = library_elem.text
                
                # 提取version
                version_elem = component_elem.find('.//ipxact:version', namespaces=ns)
                if version_elem is not None:
                    component['version'] = version_elem.text
                
                # 提取ports
                ports = component_elem.findall('.//ipxact:port', namespaces=ns)
                for port_elem in ports:
                    port = {
                        'name': '',
                        'direction': '',
                        'width': 0,
                        'msb': '0',
                        'lsb': '0'
                    }
                    
                    # 提取port名称
                    port_name_elem = port_elem.find('.//ipxact:name', namespaces=ns)
                    if port_name_elem is not None:
                        port['name'] = port_name_elem.text
                    
                    # 提取port方向
                    direction_elem = port_elem.find('.//ipxact:direction', namespaces=ns)
                    if direction_elem is not None:
                        port['direction'] = direction_elem.text
                    else:
                        print(f"未找到端口 {port['name']} 的方向")
                    
                    # 提取port宽度
                    width_elem = port_elem.find('.//ipxact:wire/ipxact:width', namespaces=ns)
                    if width_elem is not None:
                        try:
                            port['width'] = int(width_elem.text)
                        except ValueError:
                            port['width'] = 0
                    
                    # 提取vector（MSB和LSB）
                    vector_elem = port_elem.find('.//ipxact:wire/ipxact:vector', namespaces=ns)
                    if vector_elem is not None:
                        msb_elem = vector_elem.find('.//ipxact:msb', namespaces=ns)
                        if msb_elem is not None:
                            port['msb'] = msb_elem.text
                        
                        lsb_elem = vector_elem.find('.//ipxact:lsb', namespaces=ns)
                        if lsb_elem is not None:
                            port['lsb'] = lsb_elem.text
                    
                    component['ports'].append(port)
                
                # 提取parameters
                parameters = component_elem.findall('.//ipxact:parameter', namespaces=ns)
                for param_elem in parameters:
                    param = {
                        'name': '',
                        'default': ''
                    }
                    
                    # 提取parameter名称
                    param_name_elem = param_elem.find('.//ipxact:name', namespaces=ns)
                    if param_name_elem is not None:
                        param['name'] = param_name_elem.text
                    
                    # 提取parameter值
                    param_value_elem = param_elem.find('.//ipxact:value', namespaces=ns)
                    if param_value_elem is not None:
                        param['default'] = param_value_elem.text
                    
                    component['parameters'].append(param)
                
                # 提取localParameters
                local_parameters = component_elem.findall('.//ipxact:localParameter', namespaces=ns)
                for local_param_elem in local_parameters:
                    local_param = {
                        'name': '',
                        'default': ''
                    }
                    
                    # 提取localParameter名称
                    local_param_name_elem = local_param_elem.find('.//ipxact:name', namespaces=ns)
                    if local_param_name_elem is not None:
                        local_param['name'] = local_param_name_elem.text
                    
                    # 提取localParameter值
                    local_param_value_elem = local_param_elem.find('.//ipxact:value', namespaces=ns)
                    if local_param_value_elem is not None:
                        local_param['default'] = local_param_value_elem.text
                    
                    component['defines'].append(local_param)
                
                # 提取busInterfaces
                bus_interfaces = component_elem.findall('.//ipxact:busInterface', namespaces=ns)
                for bus_interface_elem in bus_interfaces:
                    bus_interface = {
                        'name': '',
                        'bus_type': '',
                        'mode': 'master',
                        'port_maps': []
                    }

                    # 提取bus interface名称
                    bus_name_elem = bus_interface_elem.find('.//ipxact:name', namespaces=ns)
                    if bus_name_elem is not None:
                        bus_interface['name'] = bus_name_elem.text

                    # 提取bus type
                    bus_type_elem = bus_interface_elem.find('.//ipxact:busType', namespaces=ns)
                    if bus_type_elem is not None:
                        bus_type_name_elem = bus_type_elem.find('.//ipxact:name', namespaces=ns)
                        if bus_type_name_elem is not None:
                            bus_interface['bus_type'] = bus_type_name_elem.text

                    # 提取mode（master/slave）
                    mode_elem = bus_interface_elem.find('.//ipxact:mode', namespaces=ns)
                    if mode_elem is not None:
                        bus_interface['mode'] = mode_elem.text

                    # 提取该bus interface下的portMaps
                    port_maps_elem = bus_interface_elem.find('.//ipxact:portMaps', namespaces=ns)
                    if port_maps_elem is not None:
                        port_map_elems = port_maps_elem.findall('.//ipxact:portMap', namespaces=ns)
                        for port_map_elem in port_map_elems:
                            port_map = {
                                'logical_port': '',
                                'physical_port': '',
                                'bus_interface': bus_interface['name']
                            }

                            # 提取logicalPort
                            logical_port_elem = port_map_elem.find('.//ipxact:logicalPort', namespaces=ns)
                            if logical_port_elem is not None:
                                port_map['logical_port'] = logical_port_elem.text

                            # 提取physicalPort
                            physical_port_elem = port_map_elem.find('.//ipxact:physicalPort', namespaces=ns)
                            if physical_port_elem is not None:
                                port_map['physical_port'] = physical_port_elem.text

                            bus_interface['port_maps'].append(port_map)
                            component['port_maps'].append(port_map)

                    component['bus_interfaces'].append(bus_interface)

                # 提取fileSets（SystemVerilog文件路径）
                sv_file = ''
                file_sets = component_elem.find('.//ipxact:fileSets', namespaces=ns)
                if file_sets is not None:
                    file_set = file_sets.find('.//ipxact:fileSet', namespaces=ns)
                    if file_set is not None:
                        file_elem = file_set.find('.//ipxact:file', namespaces=ns)
                        if file_elem is not None:
                            file_name_elem = file_elem.find('.//ipxact:name', namespaces=ns)
                            if file_name_elem is not None:
                                sv_file = file_name_elem.text
                
                component['sv_file'] = sv_file
                
                components.append(component)
            
            return components
            
        except Exception as e:
            print(f"解析文件时出错: {e}")
            return []
    
    def get_component_details(self, component):
        """获取component的详细信息"""
        details = f"名称: {component.get('name', '未知')}\n"
        details += f"描述: {component.get('description', '无')}\n"
        details += "Ports:\n"
        
        for port in component.get('ports', []):
            details += f"  - {port.get('name', '未知')}: {port.get('direction', '未知')}, 宽度: {port.get('width', 0)}\n"
        
        details += "Parameters:\n"
        for param in component.get('parameters', []):
            details += f"  - {param.get('name', '未知')}: {param.get('default', '无')}\n"
        
        details += "LocalParameters:\n"
        for define in component.get('defines', []):
            details += f"  - {define.get('name', '未知')}: {define.get('default', '无')}\n"
        
        return details
    
    def parse_bus_definition(self, file_path):
        """解析总线定义文件，提取信号信息"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 提取信号信息
            signals = []
            signal_elems = root.findall(".//{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}port")
            for signal_elem in signal_elems:
                signal_name_elem = signal_elem.find(".//{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}logicalName")
                if signal_name_elem is not None:
                    signals.append(signal_name_elem.text)
            
            return signals
        except Exception as e:
            print(f"解析总线定义文件时出错: {e}")
            return []
    
    def parse_abstract_file(self, file_path, signal, mode):
        """解析abstract文件，提取port方向和位宽信息"""
        # 定义命名空间
        ns = {'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'}
        # 如果signal为None，返回所有信号的列表
        if signal is None:
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # 提取信号信息
                signals = []
                
                # 检查是否是abstract bus definition文件
                if 'abstractionDefinition' in root.tag:
                    # 从abstract文件中提取信号
                    for port_elem in root.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}port'):
                        for logical_name_elem in port_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}logicalName'):
                            signals.append(logical_name_elem.text)
                elif 'busDefinition' in root.tag:
                    # 从bus definition文件中提取信号
                    for signal_def_elem in root.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}signalDefinition'):
                        for name_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name'):
                            signals.append(name_elem.text)
                
                return signals
            except Exception as e:
                print(f"解析abstract文件时出错: {e}")
                return []
        
        # 否则，返回指定信号的方向和位宽
        port_direction = ""
        port_width = ""
        
        try:
            # 解析abstract文件
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 检查是否是abstract bus definition文件
            if 'abstractionDefinition' in root.tag:
                # 查找与当前信号匹配的port
                for port_elem in root.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}port'):
                    for logical_name_elem in port_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}logicalName'):
                        if logical_name_elem.text == signal:
                            # 读取port方向
                            for wire_elem in port_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}wire'):
                                if mode == "master":
                                    for on_master_elem in wire_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}onMaster'):
                                        for direction_elem in on_master_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}direction'):
                                            port_direction = direction_elem.text
                                elif mode == "slave":
                                    for on_slave_elem in wire_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}onSlave'):
                                        for direction_elem in on_slave_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}direction'):
                                            port_direction = direction_elem.text
            
            # 尝试从bus definition文件中读取port位宽和方向
            # 查找对应的bus definition文件
            bus_ref_found = False
            for bus_ref_elem in root.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}busRef'):
                bus_ref_found = True
                vendor = bus_ref_elem.get("vendor")
                library = bus_ref_elem.get("library")
                name = bus_ref_elem.get("name")
                version = bus_ref_elem.get("version")
                
                # 构建bus definition文件路径
                busdef_dir = os.path.join(os.path.dirname(file_path), "..", "busdef")
                busdef_file_name = f"{name}_{version}.xml"
                busdef_file_path = os.path.join(busdef_dir, busdef_file_name)
                
                if os.path.exists(busdef_file_path):
                    # 解析bus definition文件
                    bus_tree = ET.parse(busdef_file_path)
                    bus_root = bus_tree.getroot()
                    
                    # 查找与当前信号匹配的signalDefinition
                    for signal_def_elem in bus_root.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}signalDefinition'):
                        for signal_name_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name'):
                            if signal_name_elem.text == signal:
                                # 读取port位宽
                                for width_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}width'):
                                    port_width = width_elem.text
                                # 如果还没有获取到方向，从bus definition文件中获取
                                if not port_direction:
                                    if mode == "master":
                                        for presence_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}presence'):
                                            port_direction = presence_elem.text
                                    elif mode == "slave":
                                        for driver_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}driver'):
                                            port_direction = driver_elem.text
                else:
                    print(f"bus definition文件不存在: {busdef_file_path}")
            # 如果当前文件就是bus definition文件，直接从中获取信息
            if not bus_ref_found and 'busDefinition' in root.tag:
                # 查找与当前信号匹配的signalDefinition
                for signal_def_elem in root.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}signalDefinition'):
                    for signal_name_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name'):
                        if signal_name_elem.text == signal:
                            # 读取port位宽
                            for width_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}width'):
                                port_width = width_elem.text
                            # 读取port方向
                            if mode == "master":
                                for presence_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}presence'):
                                    port_direction = presence_elem.text
                            elif mode == "slave":
                                for driver_elem in signal_def_elem.iter('{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}driver'):
                                    port_direction = driver_elem.text
            
        except Exception as e:
            print(f"从abstract文件中读取port信息时出错: {e}")
        
        return port_direction, port_width
    
    def find_bus_definition_file(self, bus_type, busdef_dir):
        """查找对应的总线定义文件"""
        if not os.path.exists(busdef_dir):
            return None
        
        abstract_file = None
        bus_file = None
        
        for file_name in os.listdir(busdef_dir):
            if file_name.endswith(".xml"):
                file_path = os.path.join(busdef_dir, file_name)
                try:
                    tree = ET.parse(file_path)
                    root = tree.getroot()
                    # 提取总线定义的名称
                    name_elem = root.find(".//{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name")
                    if name_elem is not None:
                        # 检查是否是abstract bus definition文件，并且名称包含bus_type
                        if root.tag == '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}abstractionDefinition' and bus_type in name_elem.text:
                            abstract_file = file_path
                        # 检查是否是bus definition文件，并且名称与bus_type完全匹配
                        elif root.tag == '{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}busDefinition' and name_elem.text == bus_type:
                            bus_file = file_path
                except Exception as e:
                    print(f"解析总线定义文件 {file_name} 时出错: {e}")
        
        # 优先返回abstract bus definition文件
        if abstract_file:
            return abstract_file
        # 如果没有找到abstract文件，返回bus definition文件
        if bus_file:
            return bus_file
        
        return None
    
    def get_bus_definitions(self, busdef_dir):
        """获取所有总线定义的名称"""
        bus_defs = []
        
        if os.path.exists(busdef_dir):
            for file_name in os.listdir(busdef_dir):
                if file_name.endswith(".xml"):
                    file_path = os.path.join(busdef_dir, file_name)
                    try:
                        tree = ET.parse(file_path)
                        root = tree.getroot()
                        # 提取总线定义的名称
                        name_elem = root.find(".//{http://www.accellera.org/XMLSchema/IPXACT/1685-2014}name")
                        if name_elem is not None:
                            bus_defs.append(name_elem.text)
                    except Exception as e:
                        print(f"解析总线定义文件 {file_name} 时出错: {e}")
        
        # 如果没有找到总线定义，添加默认值
        if not bus_defs:
            bus_defs = ["amba4.axi4", "amba4.apb", "amba4.ahb"]
        
        return bus_defs

