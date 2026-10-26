// SPDX-License-Identifier: MIT
// The output stage of the front-end board of hw/feb.toml (Chapter 24): a FIFO between the event
// logic and the data link. It is here to be read; MiniDAQ does not build it. MiniDAQ's tests use
// the C++ model of the board (minidaq/src/hw/fake_board.cpp), and the test hw.rtl simulates this
// module with its testbench (feb_out_fifo_tb.sv) where Icarus Verilog is installed.
//
// Both sides use a valid/ready handshake: a word moves on a rising clock edge where valid and
// ready are both 1. The event side is never stalled: an event that finds the FIFO full is lost and
// sets the sticky flag `overflow` (ERROR_FLAGS.FIFO_OVERFLOW), which software clears by writing 1
// to it. One word per event, to keep the module short.
// [snippet:module]
module feb_out_fifo #(
    parameter int WIDTH = 64,
    parameter int DEPTH_LOG2 = 12  // 4,096 words
) (
    input  logic                clk,
    input  logic                rst,             // synchronous, active high
    input  logic                trigger_enable,  // CONTROL.TRIGGER_ENABLE
    // From the event logic.
    input  logic                in_valid,
    input  logic [   WIDTH-1:0] in_data,
    // To the data link, which takes a word when it can.
    output logic                out_valid,
    output logic [   WIDTH-1:0] out_data,
    input  logic                out_ready,
    // To the registers.
    output logic                fifo_empty,      // STATUS.FIFO_EMPTY
    output logic [DEPTH_LOG2:0] level,           // FIFO_LEVEL.WORDS
    output logic                overflow,        // ERROR_FLAGS.FIFO_OVERFLOW
    input  logic                overflow_clear   // software wrote 1 to that bit
);
  localparam int Depth = 1 << DEPTH_LOG2;

  logic [WIDTH-1:0] mem[Depth];
  logic [DEPTH_LOG2-1:0] wr_ptr, rd_ptr;
  logic [DEPTH_LOG2:0] count;

  wire full = count == Depth;
  wire event_in = in_valid && trigger_enable;
  wire push = event_in && !full;  // a full FIFO refuses, even if the link takes a word now
  wire pop = out_valid && out_ready;

  always_ff @(posedge clk) begin
    if (rst) begin
      wr_ptr   <= '0;
      rd_ptr   <= '0;
      count    <= '0;
      overflow <= 1'b0;
    end else begin
      if (push) begin
        mem[wr_ptr] <= in_data;
        wr_ptr <= wr_ptr + 1'b1;
      end
      if (pop) rd_ptr <= rd_ptr + 1'b1;
      case ({push, pop})
        2'b10:   count <= count + 1'b1;
        2'b01:   count <= count - 1'b1;
        default: count <= count;
      endcase
      // Set wins over clear: an event lost in the cycle of the clear must not be forgotten.
      if (event_in && full) overflow <= 1'b1;
      else if (overflow_clear) overflow <= 1'b0;
    end
  end

  assign out_valid  = count != 0;
  assign out_data   = mem[rd_ptr];
  assign fifo_empty = count == 0;
  assign level      = count;
endmodule
// [/snippet:module]
