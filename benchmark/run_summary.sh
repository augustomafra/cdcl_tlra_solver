#!/bin/bash
echo "### Benchmark Statistics ###"
echo ""

test_results=`find . -name '*.log'`
total=`wc -w <<< ${test_results}`

echo "Number of tests run: ${total}"
echo ""

if [ "${total}" = 0 ]
then
    exit
fi

mkdir -p summary

failures=`grep -lw '^error:\|^Traceback' ${test_results}`
error_count=`wc -w <<< ${failures}`
successes=`grep -Lw '^error:\|^Traceback' ${test_results}`
success_count=`wc -w <<< ${successes}`

echo "Successes: ${success_count}"

sat=`grep -lw '^sat' ${successes}`
sat_count=`wc -w <<< ${sat}`
echo "    sat: ${sat_count}"
echo "${sat}" > summary/sat.txt

unsat=`grep -lw '^unsat' ${successes}`
unsat_count=`wc -w <<< ${unsat}`
echo "    unsat: ${unsat_count}"
echo "${unsat}" > summary/unsat.txt

unknown=`grep -lw '^unknown' ${successes}`
unknown_count=`wc -w <<< ${unknown}`
echo "    unknown: ${unknown_count}"
echo "${unknown}" > summary/unknown.txt
echo ""

echo "Failures: ${error_count}"

soundness=`grep -lw '^error: expected result was' ${failures}`
soundess_count=`wc -w <<< ${soundness}`
echo "    soundness: ${soundess_count}"
echo "${soundness}" > summary/soundness.txt

timeouts=`grep -lw '^error: timed out after' ${failures}`
timeout_count=`wc -w <<< ${timeouts}`
echo "    timeout: ${timeout_count}"
echo "${timeouts}" > summary/timeout.txt

stackoverflow=`grep -lw '^error: maximum recursion depth exceeded' ${failures}`
so_count=`wc -w <<< ${stackoverflow}`
echo "    stack overflow: ${so_count}"
echo "${stackoverflow}" > summary/stackoverflow.txt

exceptions=`grep -lw '^Traceback' ${failures}`
exception_count=`wc -w <<< ${exceptions}`
echo "    python exception: ${exception_count}"

exception_types=`tail -qn2 ${exceptions} \
                | grep -vw '^error:' \
                | awk '{print $1}' \
                | sort -u` \

for type in ${exception_types}
do
    type_list=`grep -lw "^${type}" ${exceptions}`
    type_count=`wc -w <<< ${type_list}`
    echo "        ${type} ${type_count}"
    echo "${type_list}" > summary/"${type//[:.]/}.txt"
done

