# IP-XACT Visualizer - Product Requirement Document

## Overview
- **Summary**: IP-XACT Visualizer是一个基于PyQt的工具，用于解析IP-XACT XML文件，可视化展示component信息，并支持拖拽连接功能，最终将连接关系写回IP-XACT文件。
- **Purpose**: 简化IP-XACT文件的管理和修改过程，通过可视化界面提高工作效率，减少手动编辑XML文件的错误。
- **Target Users**: FPGA/ASIC设计工程师，IP集成工程师，需要处理IP-XACT文件的开发人员。

## Goals
- 解析IP-XACT文件，提取component信息并在列表中显示
- 提供详细信息窗口展示component的具体属性
- 支持component的拖拽功能，从左侧列表拖拽到右侧工作区
- 在工作区中以带port的框形式显示component
- 支持多个component的port之间连线
- 记录component的连线关系，并写回IP-XACT XML文件

## Non-Goals (Out of Scope)
- 不支持IP-XACT文件的完整编辑功能
- 不支持复杂的IP-XACT结构修改
- 不提供IP-XACT文件的版本控制
- 不处理IP-XACT文件的语法错误

## Background & Context
- IP-XACT是一种用于描述IP核元数据的XML标准，由Accellera组织定义
- 手动编辑IP-XACT文件容易出错，需要可视化工具辅助
- 现有的IP-XACT工具要么功能复杂，要么缺乏直观的拖拽界面

## Functional Requirements
- **FR-1**: 解析IP-XACT XML文件，提取component信息
- **FR-2**: 在左侧列表中显示component名称和基本信息
- **FR-3**: 点击component后在详细信息窗口展示完整属性
- **FR-4**: 支持从左侧列表拖拽component到右侧工作区
- **FR-5**: 在工作区中以带port的框形式显示component
- **FR-6**: 支持component的port之间连线
- **FR-7**: 记录component的连线关系
- **FR-8**: 将连线关系写回IP-XACT XML文件

## Non-Functional Requirements
- **NFR-1**: 界面响应速度快，拖拽操作流畅
- **NFR-2**: 支持标准的IP-XACT 2014格式
- **NFR-3**: 代码结构清晰，易于维护
- **NFR-4**: 错误处理机制完善，提供友好的错误提示

## Constraints
- **Technical**: 使用PyQt框架和nodegraphqt库实现图形界面
- **Technical**: 后台处理使用Python语言
- **Dependencies**: 需要安装PyQt、nodegraphqt和XML解析库

## Assumptions
- 用户提供的IP-XACT文件格式正确，符合标准
- 用户具备基本的IP-XACT知识
- 运行环境已安装必要的依赖库

## Acceptance Criteria

### AC-1: IP-XACT文件解析
- **Given**: 用户选择一个有效的IP-XACT XML文件
- **When**: 工具加载并解析该文件
- **Then**: 左侧列表显示文件中的所有component
- **Verification**: `programmatic`

### AC-2: Component详细信息显示
- **Given**: 用户在左侧列表中选择一个component
- **When**: 点击该component
- **Then**: 详细信息窗口显示该component的完整属性
- **Verification**: `human-judgment`

### AC-3: Component拖拽功能
- **Given**: 左侧列表中显示了component
- **When**: 用户拖动一个component到右侧工作区
- **Then**: 工作区中出现一个带port的component框
- **Verification**: `human-judgment`

### AC-4: Port连线功能
- **Given**: 工作区中有多个component
- **When**: 用户点击一个component的输出port并拖动到另一个component的输入port
- **Then**: 两个port之间形成连线
- **Verification**: `human-judgment`

### AC-5: 连线关系写回
- **Given**: 工作区中存在component之间的连线
- **When**: 用户保存文件
- **Then**: 连线关系被写回IP-XACT XML文件
- **Verification**: `programmatic`

## Open Questions
- [ ] 如何处理IP-XACT文件中的复杂层次结构？
- [ ] 是否需要支持多个IP-XACT文件的同时处理？
- [ ] 连线关系在IP-XACT文件中的具体存储方式？