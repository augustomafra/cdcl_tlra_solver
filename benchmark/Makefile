SMTLIB_BENCHMARKS = $(shell find . -name '*.smt2')
TEST_RESULTS = $(SMTLIB_BENCHMARKS:.smt2=.log)
TIMEOUT = 1s

.PHONY: all test summary clean

all: pj2-tests

pj2-tests:
	tar -xvf pj2-tests.tar.gz

test: pj2-tests $(TEST_RESULTS)

%.log: %.smt2
	./run_benchmark.sh $(TIMEOUT) $< $@

summary:
	@./run_summary.sh

clean:
	@echo "Removing all .log test results"
	@$(RM) $(TEST_RESULTS)
