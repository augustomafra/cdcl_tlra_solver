#!/bin/bash
time_limit="$1"
benchmark="$2"
output_log="$3"
timeout "${time_limit}" python3 ../cdcl_tlra_solver.py "${benchmark}" 2>&1 | tee "${output_log}"
status="${PIPESTATUS[0]}"
if [ "${status}" = 124 ]
then
    echo "error: timed out after ${time_limit}" | tee -a "${output_log}"
    exit
fi
if [ "${status}" != 0 ]
then
    echo "error: exit code ${status}" | tee -a "${output_log}"
fi
