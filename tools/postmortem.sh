#!/usr/bin/env bash
# Opens a core dump of a MiniDAQ program and prints what a first look at a crash needs
# (Chapter 21): the signal, the crashing thread's stack, every thread's stack, and the frame
# where it stopped, with the program's debug information.
#
#   tools/postmortem.sh CORE PROGRAM [DEBUG_FILE]
#
# PROGRAM is the program as shipped (bin/minidaq_server of the release package); DEBUG_FILE
# its debug information (debug/minidaq_server.debug), if the program was stripped. Before gdb
# runs, the build IDs of the core's program, PROGRAM and DEBUG_FILE must be one and the same:
# gdb shows a core with the wrong build as plausible, wrong stacks. Exit status 0 after the
# report, 2 if the build IDs differ or a file is missing.
set -euo pipefail
core=${1:?usage: tools/postmortem.sh CORE PROGRAM [DEBUG_FILE]}
program=${2:?usage: tools/postmortem.sh CORE PROGRAM [DEBUG_FILE]}
debug=${3:-}
root=$(cd "$(dirname "$0")/.." && pwd)

build_id() { readelf -n "$1" 2>/dev/null | sed -n 's/^ *Build ID: //p' | head -1; }

# [snippet:check]
in_core=$(python3 "$root/tools/core_build_id.py" "$core" "$(basename "$program")") || exit 2
in_program=$(build_id "$program")
echo "build ID in the core:       $in_core"
echo "build ID of the program:    ${in_program:-none}"
if [ "$in_core" != "$in_program" ]; then
  echo "postmortem: $program is not the program of $core; find the build with ID $in_core" >&2
  exit 2
fi
if [ -n "$debug" ]; then
  in_debug=$(build_id "$debug")
  echo "build ID of the debug file: ${in_debug:-none}"
  if [ "$in_debug" != "$in_core" ]; then
    echo "postmortem: $debug is the debug information of another build" >&2
    exit 2
  fi
fi
# [/snippet:check]

# [snippet:gdb]
args=(-batch -nx -iex "set debuginfod enabled off" -iex "set auto-load safe-path /")
[ -n "$debug" ] && args+=(-ex "symbol-file $debug")
gdb "${args[@]}" \
  -ex "echo \n== signal (si_code 0 or less: sent by kill, raise or abort, not a fault)\n" \
  -ex "print \$_siginfo.si_signo" -ex "print \$_siginfo.si_code" -ex "print \$_siginfo._sifields._sigfault.si_addr" \
  -ex "echo \n== crashing thread\n" -ex "bt" \
  -ex "echo \n== all threads\n" -ex "info threads" -ex "thread apply all bt" \
  -ex "echo \n== innermost frame\n" -ex "frame 0" -ex "info locals" \
  "$program" "$core" 2>&1
# [/snippet:gdb]
