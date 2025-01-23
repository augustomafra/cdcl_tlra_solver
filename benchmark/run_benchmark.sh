#!/bin/bash
time_limit="$1"
benchmark="$2"
output_log="$3"
timeout "${time_limit}" python3 ../cdcl_tlra_solver.py "${benchmark}" 2>&1 | tee "${output_log}"
if [ "${PIPESTATUS[0]}" = 124 ]
then
    echo "error: timed out after ${time_limit}" | tee -a "${output_log}"
fi
