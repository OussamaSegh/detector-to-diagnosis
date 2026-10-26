// SPDX-License-Identifier: MIT
// A testbench for feb_out_fifo (Chapter 24): random events and a random link, against a model
// written the way software would write it. It checks every word's order and value, the level,
// FIFO_EMPTY, the overflow flag (set wins over clear), that nothing enters while the triggers
// are off, and that the FIFO drains once they are. Prints PASS or the first difference.
//
//   iverilog -g2012 -o tb feb_out_fifo.sv feb_out_fifo_tb.sv && vvp tb
module feb_out_fifo_tb;
  localparam int W = 16;
  localparam int L = 3;  // 8 words: small, so that it fills often
  localparam int D = 1 << L;

  logic clk = 0, rst = 1, trig = 0, in_valid = 0, out_ready = 0, clr = 0;
  logic [W-1:0] in_data = '0;
  logic out_valid, fifo_empty, overflow;
  logic [W-1:0] out_data;
  logic [L:0] level;

  feb_out_fifo #(.WIDTH(W), .DEPTH_LOG2(L)) dut (
      .clk(clk), .rst(rst), .trigger_enable(trig), .in_valid(in_valid), .in_data(in_data),
      .out_valid(out_valid), .out_data(out_data), .out_ready(out_ready), .fifo_empty(fifo_empty),
      .level(level), .overflow(overflow), .overflow_clear(clr));

  // The model: a circular buffer and a count.
  logic [W-1:0] q[D];
  int head = 0, n = 0, lost = 0, sent = 0, errors = 0;
  bit m_overflow = 0;

  task automatic check(string what, int got, int want);
    if (got != want) begin
      if (errors == 0) $display("FAIL at %0t: %s is %0d, expected %0d", $time, what, got, want);
      errors++;
    end
  endtask

  always #5 clk = ~clk;

  int phase;
  int seed = 24;  // every run is the same run
  bit push, pop, full_event;

  initial begin
    repeat (2) @(posedge clk);
    rst = 0;
    for (int cycle = 0; cycle < 20000; cycle++) begin
      // Phases: triggers on with a slow link, then a fast one, then off to drain.
      phase = (cycle / 2500) % 4;
      @(negedge clk);
      trig = phase != 3;
      in_valid = ($urandom(seed) % 100) < (phase == 0 ? 60 : 30);
      in_data = in_data + 1'b1;
      out_ready = ($urandom(seed) % 100) < (phase == 0 ? 25 : 70);
      clr = ($urandom(seed) % 100) < 5;
      // What the model expects of this edge, from the signals before it.
      push = in_valid && trig && n < D;
      pop = n > 0 && out_ready;
      full_event = in_valid && trig && n == D;
      begin
        if (pop) begin
          check("out_data", out_data, q[head]);
          head = (head + 1) % D;
          n--;
          sent++;
        end
        if (push) begin
          q[(head + n) % D] = in_data;
          n++;
        end
        if (full_event) begin
          m_overflow = 1;
          lost++;
        end else if (clr) begin
          m_overflow = 0;
        end
      end
      @(posedge clk);
      #1;
      check("level", level, n);
      check("fifo_empty", fifo_empty, n == 0);
      check("out_valid", out_valid, n != 0);
      check("overflow", overflow, m_overflow);
    end
    check("drained at the end", n, 0);
    if (lost == 0) begin
      $display("FAIL: the test never filled the FIFO");
      errors++;
    end
    if (errors == 0) $display("PASS: %0d words sent, %0d events lost to a full FIFO", sent, lost);
    $finish;
  end
endmodule
