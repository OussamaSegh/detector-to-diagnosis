#!/usr/bin/env bash
# 3 repetitions x {idle, load} x {default, rt-pin, rt-fifo}, 20 s each, due-time origin.
L=${L:-build/release/minidaq/apps/minidaq_latency}
P=${P:-minidaq/profiles}
out=${OUT:-measurements/ch04/latency/new}; mkdir -p $out
for cond in idle load; do
  for rep in 1 2 3; do
    for p in default rt-pin rt-fifo; do
      arg=""; [ $p != default ] && arg="--profile $P/$p.conf"
      if [ $cond = load ]; then stress-ng --cpu 4 --vm 2 --vm-bytes 256M --io 1 --timeout 26s >/dev/null 2>&1 & sp=$!; sleep 3; fi
      $L --rate 10e6 --seconds 20 --batch 4096 $arg > $out/${cond}_${p}_${rep}.txt 2>&1
      if [ $cond = load ]; then wait $sp; fi
    done
  done
done
echo "results in $out"
