#!/bin/bash
mkdir -p summary

echo "### Benchmark Statistics ###" > summary/statistics.txt
echo "" >> summary/statistics.txt

test_results=`find . -name '*.log'`
total=`wc -w <<< ${test_results}`

echo "Number of tests run: ${total}" >> summary/statistics.txt
echo "" >> summary/statistics.txt

if [ "${total}" = 0 ]
then
    cat summary/statistics.txt
    exit
fi


failures=`grep -lw '^error:\|^Traceback' ${test_results}`
error_count=`wc -w <<< ${failures}`
successes=`grep -Lw '^error:\|^Traceback' ${test_results}`
success_count=`wc -w <<< ${successes}`

echo "Successes: ${success_count}" >> summary/statistics.txt
if [ "${success_count}" != 0 ]
then

    sat=`grep -lw '^sat' ${successes}`
    sat_count=`wc -w <<< ${sat}`
    echo "    sat: ${sat_count}" >> summary/statistics.txt
    echo "${sat}" > summary/sat.txt

    unsat=`grep -lw '^unsat' ${successes}`
    unsat_count=`wc -w <<< ${unsat}`
    echo "    unsat: ${unsat_count}" >> summary/statistics.txt
    echo "${unsat}" > summary/unsat.txt

    unknown=`grep -lw '^unknown' ${successes}`
    unknown_count=`wc -w <<< ${unknown}`
    echo "    unknown: ${unknown_count}" >> summary/statistics.txt
    echo "${unknown}" > summary/unknown.txt
    echo "" >> summary/statistics.txt
fi

echo "Failures: ${error_count}" >> summary/statistics.txt
if [ "${error_count}" = 0 ]
then
    cat summary/statistics.txt
    exit
fi

soundness=`grep -lw '^error: expected result was' ${failures}`
soundess_count=`wc -w <<< ${soundness}`
echo "    soundness: ${soundess_count}" >> summary/statistics.txt
echo "${soundness}" > summary/soundness.txt

timeouts=`grep -lw '^error: timed out after' ${failures}`
timeout_count=`wc -w <<< ${timeouts}`
echo "    timeout: ${timeout_count}" >> summary/statistics.txt
echo "${timeouts}" > summary/timeout.txt

stackoverflow=`grep -lw '^error: maximum recursion depth exceeded' ${failures}`
so_count=`wc -w <<< ${stackoverflow}`
echo "    stack overflow: ${so_count}" >> summary/statistics.txt
echo "${stackoverflow}" > summary/stackoverflow.txt

exceptions=`grep -lw '^Traceback' ${failures}`
exception_count=`wc -w <<< ${exceptions}`
echo "    python exception: ${exception_count}" >> summary/statistics.txt

if [ "${exception_count}" = 0 ]
then
    cat summary/statistics.txt
    exit
fi

exception_types=`tail -qn2 ${exceptions} \
                | grep -vw '^error:' \
                | awk '{print $1}' \
                | sort -u` \

for type in ${exception_types}
do
    type_list=`grep -lw "^${type}" ${exceptions}`
    type_count=`wc -w <<< ${type_list}`
    echo "        ${type} ${type_count}" >> summary/statistics.txt
    echo "${type_list}" > summary/"${type//[:.]/}.txt"
done

cat summary/statistics.txt
