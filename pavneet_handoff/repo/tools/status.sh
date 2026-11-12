#!/bin/bash
# Quick status: running/pending jobs, recent stage lines from each encoder's logs, RL runs finished.
echo "== jobs"; squeue -u "$USER" -o "%.10i %.28j %.8T %.10M %.10l %.5C %R" | head -40
for W in /scratch1/pbanga/rcwork /scratch1/pbanga/rcwork_x264; do
  [[ -d $W ]] || continue
  echo "== $W"
  ls "$W"/results_*/*.pkl 2>/dev/null | sed "s#$W/##" | awk -F/ '{print $1}' | sort | uniq -c | awk '{printf "  %s: %d stage files\n", $2, $1}'
  echo "  RL runs finished: $(ls "$W"/results_rl/*/eval.pkl 2>/dev/null | wc -l)"
  for f in "$W"/logs/*.log; do [[ -f $f ]] && echo "  $(basename "$f"): $(tail -1 "$f")"; done 2>/dev/null | tail -8
done
