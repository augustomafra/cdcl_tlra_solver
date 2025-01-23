SMTLIB_BENCHMARKS = $(shell find . -name '*.smt2')
TEST_RESULTS = $(SMTLIB_BENCHMARKS:.smt2=.log)
TIMEOUT = 1s

.PHONY: all test clean

all: non-incremental

non-incremental:
	unzstd QF_LRA.tar.zstd

test: non-incremental $(TEST_RESULTS)

%.log: %.smt2
	./run_benchmark.sh $(TIMEOUT) $< $@

clean:
	@echo "Removing all .log test results"
	@$(RM) $(TEST_RESULTS)
