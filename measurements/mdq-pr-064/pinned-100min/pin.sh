#!/bin/bash
# Pins minidaq_server's pipeline threads to CPUs by name, every 5 s, while the server runs.
declare -A cpu=([mdq-source]=0 [mdq-decode]=1 [mdq-sort]=2 [mdq-pair]=3 [mdq-write]=3)
while true; do
  for pid in $(pgrep -x minidaq_server); do
    for t in /proc/$pid/task/*; do
      n=$(cat $t/comm 2>/dev/null); c=${cpu[$n]:-}
      [ -n "$c" ] && taskset -pc $c ${t##*/} >/dev/null 2>&1
    done
  done
  sleep 5
done
