#!/bin/bash
set -e

if [ ! -d "benchmark/non-incremental" ]; then
    echo "Decompressing benchmark/QF_LRA.tar.zst"
    cd benchmark
    unzstd QF_LRA.tar.zstd
    cd ..
fi

echo "Creating pytest test cases"
mkdir -p tests
for test in `find benchmark -name '*.smt2'`
do
    path=tests/`dirname "${test}"`
    filename=`basename "${test}"`
    mkdir -p "${path}"
    testname="${filename%.smt2}"
    testname="${testname//\./_}"
    testname="${testname//-/_}"
    testpy="${path}/test_${testname}.py"
    echo "import cdcl_tlra_solver
def test_${testname}():
    filename = \"${test}\"
    status = cdcl_tlra_solver.cdcl_tlra_check_sat(filename)
    assert(status != cdcl_tlra_solver.Status.ERROR)" > "${testpy}"
done
