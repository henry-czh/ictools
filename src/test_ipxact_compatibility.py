#!/usr/bin/env python3
# 测试IPXactWriter和IPXactParser的兼容性

import os
import sys
from ipxact_writer import IPXactWriter
from ipxact_parser import IPXactParser

# 创建测试数据
component_data = {
    'vendor': 'Phytium',
    'library': 'LowSpeedDevice',
    'name': 'test_module',
    'version': '1.0',
    'description': 'Test module',
    'ports': [
        {'name': 'clk', 'direction': 'input', 'width': '1'},
        {'name': 'rst_n', 'direction': 'input', 'width': '1'},
        {'name': 'data_in', 'direction': 'input', 'width': '32-1:0'},
        {'name': 'data_out', 'direction': 'output', 'width': '32-1:0'}
    ]
}

# 创建IPXactWriter和IPXactParser实例
writer = IPXactWriter()
parser = IPXactParser()

# 生成测试文件路径
test_file = os.path.join(os.path.dirname(__file__), 'test_module_test.xml')

# 写入文件
print(f"创建测试文件: {test_file}")
if writer.create_component_file(test_file, component_data):
    print("成功创建文件")
    
    # 读取文件
    print("\n解析测试文件...")
    components = parser.parse_file(test_file)
    
    if components:
        print(f"成功解析到 {len(components)} 个component")
        component = components[0]
        print(f"Component名称: {component['name']}")
        print(f"Ports数量: {len(component['ports'])}")
        
        for port in component['ports']:
            print(f"  - {port['name']}: {port['direction']}, 宽度: {port['width']}")
        
        # 验证端口信息是否正确读取
        if len(component['ports']) == 4:
            print("\n测试通过: 所有端口都被正确读取")
        else:
            print("\n测试失败: 端口数量不匹配")
    else:
        print("测试失败: 无法解析文件")
else:
    print("测试失败: 无法创建文件")

# 清理测试文件
if os.path.exists(test_file):
    os.remove(test_file)
    print(f"\n清理测试文件: {test_file}")