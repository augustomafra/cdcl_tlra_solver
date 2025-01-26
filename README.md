# CDCL(T<sub>LRA</sub>) SMT Solver
#### [Theory and Practice of SMT Solving - 2024.2](https://hanielb.github.io/2024.2-smt/)
##### Programa de Pós-Graduação em Ciência da Computação [PPGCC](https://ppgcc.dcc.ufmg.br/) - [DCC](https://dcc.ufmg.br/) - [UFMG](https://ufmg.br/)

## Introduction
This project implements a Python CDCL(T<sub>LRA</sub>) SMT solver. It integrates three main components as building blocks:

1. [pySMT](https://github.com/pysmt/pysmt): used as the parser for SMT-LIB2.6 problems.
2. [PySAT](https://github.com/pysathq/pysat): used as the SAT solver for propositional formulas.
3. [cvc5](https://github.com/cvc5/cvc5): used as the Quantifier-Free  Linear Real Arithmetic (QF_LRA) Theory solver.

All components are integrated using their Python APIs.

## Setup Instructions
1. Install Python3 dependencies:
```
pip3 install -r requirements.txt
```
2. Run the solver:
```
python3 cdcl_tlra_solver.py SMT_LIB_FILE.smt2
```
3. Navigate to `benchmark` directory and run `make` to extract the SMT tests.
```
cd benchmark
make
```
1. Run `make test` to launch the benchmark runs. The following Makefile variables are available for configuring the benchmark run:
   - `SOLVER`: the SMT solver used for running the tests. By default, it is set to the Python solver.
   - `TIMEOUT`: the timeout for each test. Use the format as specified by [`timeout(1)` man page](https://man7.org/linux/man-pages/man1/timeout.1.html).
```
# Examples for running the tests:
make test
make test -j4 # Run tests using 4 parallel jobs
make test TIMEOUT=40s # Set timeout of 40s for each test
make test SOLVER=cvc5 # Run tests with cvc5 instead of the Python solver
# Set additional flags to the solver:
make test SOLVER="python3 ../cdcl_tlra_solver.py --dump-models --sat-solver=cadical195"
```

## Command-line Options
```
$ python3 cdcl_tlra_solver.py  -h
usage: cdcl_tlra_solver [-h] [--sat-solver SAT_SOLVER] [--dump-models] [--verbose VERBOSE] smt_lib2_filename

A Python CDCL(TLRA) SMT solver

positional arguments:
  smt_lib2_filename     Input file on SMT-LIB2 format

options:
  -h, --help            show this help message and exit
  --sat-solver SAT_SOLVER, -s SAT_SOLVER
                        SAT solver used for solving propositional abstraction (Default: minisat22). Refer to https://pysathq.github.io/docs/html/api/solvers.html#pysat.solvers.SolverNames for available solvers.
  --dump-models, -m     Print models after every SAT response
  --verbose VERBOSE, -v VERBOSE
                        Print verbose debugging log
```

## Goals

1. Provide a complete and sound Python CDCL(T<sub>LRA</sub>) solver for QF_LRA problems.
2. Validate the solver on QF_LRA SMT-LIB benchmarks.
3. Compare the Python solver performance against cvc5 SMT solver.
4. Measure the performance impacts of varying the SAT solver selected via PySAT.
