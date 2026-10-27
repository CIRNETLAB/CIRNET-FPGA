`timescale 1ns/1ps
// Supplemental abstract RTL evidence; no electrical latency or board ABI claim.
module tb_permit_matrix;
    reg clk=0;
    always #5 clk=~clk;
    reg reset_n=1,command_valid=0;
    reg [7:0] command_code=0;
    reg safe_condition=1,scan_done=0,scan_success=0,plan_valid=1;
    reg routing_ready=1,protection_ready=1,watchdog_armed=1,watchdog_expired=0,fault_in=0;
    reg [31:0] clock_half_period_ticks=3;
    wire command_accepted,topology_scan_enable,routing_enable,drive_enable,experiment_clock,safe_state,status_led;
    wire [3:0] error_code,state;
    reg capture_request=0,generator_request=0;
    wire la,scope,generator,capture_valid,output_enable,sdram_request;
    integer permit_index,tick;
    reg previous_phase;
    netcircuit_experiment_top dut(.*);
    netcircuit_instrument_scaffold instruments(
        .control_clk(clk),.acquisition_clk(clk),.generator_clk(clk),.sdram_clk(clk),.reset_n(reset_n),
        .capture_request(capture_request),.generator_request(generator_request),.logic_analyzer_available(la),
        .scope_2ch_available(scope),.generator_2ch_available(generator),.capture_valid(capture_valid),
        .generator_output_enable(output_enable),.sdram_request(sdram_request));
    task safe_outputs;
        begin
            if ({routing_enable,drive_enable,experiment_clock,safe_state} !== 4'b0001)
                $fatal(1,"outputs not safe, state=%d",state);
        end
    endtask
    task command;
        input [7:0] code;
        input accept;
        begin
            @(negedge clk);command_valid=1;command_code=code;
            @(posedge clk);#1;
            if(command_accepted!==accept) $fatal(1,"unexpected command ack code=%d state=%d",code,state);
            @(negedge clk);command_valid=0;
        end
    endtask
    task reset;
        begin
            reset_n=0;#1;safe_outputs();
            @(negedge clk);reset_n=1;
            safe_condition=1;plan_valid=1;routing_ready=1;protection_ready=1;
            watchdog_armed=1;watchdog_expired=0;fault_in=0;clock_half_period_ticks=3;
        end
    endtask
    task scan;
        input success;
        begin
            command(1,1);
            if(!topology_scan_enable || routing_enable || drive_enable) $fatal(1,"scan output guard");
            scan_done=1;scan_success=success;
            @(posedge clk);#1;
            if(state!==(success?4'd2:4'd0)) $fatal(1,"scan completion state");
            @(negedge clk);scan_done=0;
        end
    endtask
    task run;
        begin
            scan(1);command(2,1);command(3,1);command(4,1);command(5,1);command(6,1);
            if(state!==7 || !drive_enable) $fatal(1,"valid run missing");
        end
    endtask
    initial begin
        #1;reset();
        scan(0);safe_outputs();command(2,0);safe_outputs();
        scan(1);clock_half_period_ticks=0;command(2,0);safe_outputs();
        clock_half_period_ticks=3;
        for(permit_index=0;permit_index<6;permit_index=permit_index+1) begin
            reset();run();
            case(permit_index)
                0:safe_condition=0;
                1:plan_valid=0;
                2:routing_ready=0;
                3:protection_ready=0;
                4:watchdog_armed=0;
                5:watchdog_expired=1;
            endcase
            #1;
            if(drive_enable!==0 || experiment_clock!==0) $fatal(1,"permit loss failed immediate drive inhibit %d",permit_index);
            @(posedge clk);#1;safe_outputs();
            if(state!==8) $fatal(1,"permit loss failed FAULT %d",permit_index);
        end
        reset();run();command(0,1);safe_outputs();command(6,0);safe_outputs();
        reset();run();command(7,1);safe_outputs();command(6,0);safe_outputs();
        reset();run();
        // First RUNNING edge counts one; phase changes on the third edge.
        for(tick=1;tick<=9;tick=tick+1) begin
            @(posedge clk);#1;
            if(experiment_clock!==((tick/3)%2)) $fatal(1,"half-period boundary tick=%d clock=%b",tick,experiment_clock);
        end
        @(negedge clk);fault_in=1;#1;safe_outputs();fault_in=0;#1;safe_outputs();
        command(6,0);safe_outputs();reset();command(6,0);safe_outputs();
        capture_request=1;generator_request=1;#1;
        if({la,scope,generator,capture_valid,output_enable,sdram_request}!==6'b0) $fatal(1,"instrument availability under requests");
        reset_n=0;#1;
        if({la,scope,generator,capture_valid,output_enable,sdram_request}!==6'b0) $fatal(1,"instrument availability under reset");
        $display("PERMIT_MATRIX_RTL_PASS");$finish;
    end
    initial begin #20000;$fatal(1,"supplemental testbench timeout");end
endmodule
