// ====================================================
// File: test_module.sv
// 目的：测试解析器对 define、端口、位宽、数组等信息的提取
// ====================================================

`define DATA_WIDTH 32        // 宏定义数据位宽
`define ADDR_WIDTH 8         // 宏定义地址位宽
`define BYTE_EN_WIDTH 4      // 宏定义字节使能位宽

`define BUS_WIDTH `DATA_WIDTH + `ADDR_WIDTH   // 宏中引用其他宏

// 用户自定义类型：使用 typedef 定义结构体（用于端口）
typedef struct packed {
    logic [`DATA_WIDTH-1:0] data;
    logic [`ADDR_WIDTH-1:0] addr;
} bus_pkt_t;

// 使用 typedef 定义枚举类型
typedef enum logic [1:0] {IDLE, READ, WRITE, WAIT} state_t;

// 主模块，包含多种端口形式
module test_module #(
    // 参数化位宽（可覆盖）
    parameter int P_DATA_WIDTH = 16,
    parameter int P_ADDR_WIDTH = 4
) (
    // 时钟与复位（单比特）
    input  logic       clk,
    input  logic       rst_n,

    // 使用 `define 宏定义位宽的信号
    input  logic [`DATA_WIDTH-1:0]   data_in,        // 多 bit 输入
    output logic [`DATA_WIDTH-1:0]   data_out,       // 多 bit 输出
    input  logic [`ADDR_WIDTH-1:0]   addr_in,

    // 单 bit 控制信号
    input  logic                     wr_en,
    input  logic                     rd_en,
    output logic                     busy,
    output logic                     done,

    // 三态信号（inout）
    inout  wire [`DATA_WIDTH-1:0]    data_bus,

    // 字节使能（向量，使用宏）
    input  logic [`BYTE_EN_WIDTH-1:0] byte_en,

    // 使用参数化位宽的端口
    input  logic [P_DATA_WIDTH-1:0]  param_data_in,
    output logic [P_DATA_WIDTH-1:0]  param_data_out,

);

    // 内部信号示例（不会影响端口解析）
    logic [`DATA_WIDTH-1:0] internal_reg;
    logic [`ADDR_WIDTH-1:0] internal_addr;

    // 使用宏进行计算（示例）
    localparam TOTAL_BITS = `BUS_WIDTH;   // 宏展开后为 32+8=40

    // 一个简单的组合逻辑（仅作示例）
    always_comb begin
        data_out = data_in;
        done = rd_en | wr_en;
        busy = ~done;
        param_data_out = param_data_in;
        next_state = current_state;
        bus_pkt_out = bus_pkt_in;
    end

endmodule

// 第二个模块：演示接口与 modport（若解析器支持更复杂的场景）
interface simple_bus_if (input logic clk);
    logic [7:0] data;
    logic       valid;
    modport master (output data, output valid);
    modport slave  (input  data, input  valid);
endinterface

module top_with_interface (
    simple_bus_if.master bus_if,
    input  logic         rst
);
    // 模块内部逻辑略
endmodule