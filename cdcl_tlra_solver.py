import pysat.formula
import pysmt.operators
import pysat.solvers
import pysmt.environment
import pysmt.shortcuts
import pysmt.smtlib.commands
import pysmt.smtlib.parser
import pysmt.smtlib.script

import argparse
import enum
import sys

verbose = 0

def debug_print(verbosity_level, fmt, *args):
    global verbose
    if verbose > verbosity_level:
        print(fmt.format(*args))

def eval_smt_lib2_script(script, solver, solver_name):
    """Evaluate an SMT-LIB script on the given solver.
    Note: not used in the CDCL(TLRA) solver, but kept here only for debugging
    purposes.
    """

    debug_print(0, "Evaluating SMT-LIB2 script on SMT solver: {}", solver_name)
    steps = []
    for command in script.commands:
        try:
            result = pysmt.smtlib.script.evaluate_command(command, solver)
            steps.append((command.name, result))
        except RuntimeError as error:
            debug_print(0, "error: {}: {}", command.name, error)
            steps.append((command.name, None))

    for command, result in steps:
        match command:
            case "check-sat":
                debug_print(0, "sat" if result else "unsat")
            case "get-model":
                if result:
                    debug_print(0, result)

class BooleanAbstraction():
    """Encapsulates the mapping between SMT expressions and their corresponding
    propositional encodings.

    Provides the utilites for converting to/from expressions and abstractions:

        expr = smt_script.get_strict_formula()

        # Convert expr to an integer representing the propositional abstraction
        abstraction = self.add_abstraction(expr)

        # Obtaining expressions from abstractions
        assert(expr == self.get_expression(abstraction))
        assert(self.formula_manager.Not(expr) == \
                                            self.get_expression(-abstraction))

        # Obtaining abstractions from expressions
        assert(abstraction == self.get_abstraction(expr))
        assert(-abstraction == \
                        self.get_abstraction(self.formula_manager.Not(expr)))
    """

    def __init__(self, formula):
        self.formula_manager = pysmt.environment.get_env().formula_manager

        self.formula = formula
        self.expressions = list()
        self.abstractions = dict()
        self.clauses = list()

        for atom in formula.get_atoms():
            self.add_abstraction(atom)

        abstraction = self.clausify(self.formula)
        self.add_clause([abstraction])

    def add_abstraction(self, expr):
        abstraction = self.get_abstraction(expr)

        if abstraction:
            return abstraction

        self.expressions.append(expr)
        new_abstraction = len(self.expressions)
        self.abstractions[expr] = new_abstraction
        return new_abstraction

    def get_abstraction(self, expr):
        if expr in self.abstractions:
            return self.abstractions[expr]
        elif expr.node_type() == pysmt.operators.NOT:
            sub_expr = expr.arg(0)
            if sub_expr in self.abstractions:
                return -self.abstractions[sub_expr]

        return None

    def get_expression(self, abstraction):
        if abstraction < 0:
            expr = self.expressions[-abstraction - 1]
            return self.formula_manager.Not(expr)

        return self.expressions[abstraction - 1]

    def add_clause(self, clause):
        self.clauses.append(clause)

    def clausify(self, expr):
        """Compute Tseitin's encoding of the expression and store the created
        clauses into self.clauses.
        Return the integer corresponding to the propositional abstraction.
        """

        abstraction = self.get_abstraction(expr)
        if abstraction:
            # Expr is an atom, so simply return its abstraction
            return abstraction

        abstraction = self.add_abstraction(expr)

        # Recursively apply Tseitin's encoding on the expression
        match expr.node_type():
            case pysmt.operators.NOT:
                child = self.clausify(expr.arg(0))

                # abstraction => -child
                self.add_clause([-abstraction, -child])

                # -child => abstraction
                self.add_clause([child, abstraction])

                return abstraction

            case pysmt.operators.OR:
                children = [self.clausify(arg) for arg in expr.args()]

                for child in children:
                    # child => abstraction
                    self.add_clause([-child, abstraction])

                # abstraction => child1 v child2 v ... v childn
                children.append(-abstraction)
                self.add_clause(children)

                return abstraction

            case pysmt.operators.AND:
                children = [self.clausify(arg) for arg in expr.args()]

                for child in children:
                    # abstraction => child
                    self.add_clause([-abstraction, child])

                # child1 ^ child2 ^ ... ^ childn => abstraction
                negated_children = [-child for child in children]
                negated_children.append(abstraction)
                self.add_clause(negated_children)

                return abstraction

            case pysmt.operators.IMPLIES:
                children = [self.clausify(arg) for arg in expr.args()]
                precondition = children.pop(0)

                # abstraction => (precondition => children)
                clause = [-abstraction, -precondition]
                clause.extend(children)
                self.add_clause(clause)

                # -precondition => abstraction
                self.add_clause([precondition, abstraction])

                for child in children:
                    # child => abstraction
                    self.add_clause([-child, abstraction])

                return abstraction

            case pysmt.operators.IFF:
                lhs, rhs = [self.clausify(arg) for arg in expr.args()]

                # abstraction => (lhs => rhs)
                self.add_clause([-abstraction, -lhs, rhs])

                # abstraction => (rhs => lhs)
                self.add_clause([-abstraction, lhs, -rhs])

                # lhs ^ rhs => abstraction
                self.add_clause([-lhs, -rhs, abstraction])

                # -lhs ^ -rhs => abstraction
                self.add_clause([lhs, rhs, abstraction])

                return abstraction

            case pysmt.operators.ITE:
                cond, then_expr, else_expr = expr.args()

                # Translate ite to equivalent SMT formulas using iff and
                # delegate to recursive clausify calls:
                ite_result = self.formula_manager.FreshSymbol()
                equiv_formula = self.formula_manager.Iff(ite_result, expr)
                self.add_abstraction(equiv_formula)

                # ite_result ^ cond <=> then_expr
                cond_true = self.formula_manager.And(ite_result, cond)
                then_constraint = self.formula_manager.Iff(cond_true, then_expr)
                self.add_clause([self.clausify(then_constraint)])

                # ite_result ^ -cond <=> else_expr
                cond_false = self.formula_manager.And(ite_result, self.formula_manager.Not(cond))
                else_constraint = self.formula_manager.Iff(cond_false, else_expr)
                self.add_clause([self.clausify(else_constraint)])

                return abstraction

            case pysmt.operators.BOOL_CONSTANT:
                self.add_clause([abstraction if expr.is_true() else -abstraction])
                return abstraction

            case pysmt.operators.SYMBOL:
                # Clausify only symbols of Bool type, which may be originated
                # from Fresh Symbols from clausification of ite expressions
                if not expr.symbol_type().is_bool_type():
                    raise NotImplementedError(expr, expr.node_type(), expr.symbol_type())

                # An SMT symbol with Bool sort is its own boolean SAT encoding
                return abstraction

        raise NotImplementedError(expr, expr.node_type())

def get_sat_assignment(sat_solver, solver_name):
    """Solve the propositional problem in the given SAT solver and return the
    asserted literals corresponding to the model, if any.
    """

    debug_print(0, "\nRunning SAT solver: {}", solver_name)

    if sat_solver.solve():
        debug_print(0, "sat")
        return sat_solver.get_model()

    debug_print(0, "unsat")
    return []

class UnknownSatSolver(argparse.ArgumentError):
    """Placeholder exception type for reporting invalid command-line SAT solver
    name."""
    pass

class SatSolver:
    """Validator class for checking command-line SAT solver name arguments.
    On construction, check if the given name matches any of the available pysat
    solvers, and raise UnknownSatSolver exception if no match was found.
    """
    def __init__(self, solver_name):
        self.validate_name(solver_name)
        self.name = solver_name

    def validate_name(self, solver_name):
        available_solvers = pysat.solvers.SolverNames.__dict__
        for member, available_names in available_solvers.items():
            if member.startswith("__"):
                continue
            if solver_name in available_names:
                return

        raise UnknownSatSolver(solver_name)

class Status(enum.Enum):
    UNSAT = 0
    SAT = 1
    ERROR = 2

def cdcl_tlra_check_sat(smt_lib2_filename, sat_solver_name="minisat22", dump_models=False, verbosity=0):
    """Core CDCL(TLRA) loop"""

    global verbose
    verbose = verbosity

    smt_parser = pysmt.smtlib.parser.SmtLibParser()
    script = smt_parser.get_script_fname(smt_lib2_filename)
    expected = None
    for info_cmd in script.filter_by_command_name([pysmt.smtlib.commands.SET_INFO]):
        key, value = info_cmd.args
        if key == ":status":
            expected = value

    with pysat.solvers.Solver(name=sat_solver_name) as sat_solver:
        smt_solver_name = "cvc5"
        smt_solver = pysmt.shortcuts.Solver(name=smt_solver_name, logic="QF_LRA")
        smt_solver.cvc5.setOption("incremental", "true")
        smt_solver.cvc5.setOption("produce-unsat-cores", "true")
        smt_solver.cvc5.setOption("ite-simp", "false")

        formula = script.get_strict_formula()

        debug_print(1, "Clausifying SMT-LIB2 formula: {}", formula)
        try:
            bool_abstraction = BooleanAbstraction(formula)
        except RecursionError as stack_overflow_error:
            print("error: {}".format(stack_overflow_error))
            return Status.ERROR
        clauses = bool_abstraction.clauses

        for atom, abs in bool_abstraction.abstractions.items():
            debug_print(1, "{}:\t{}", abs, atom)
        debug_print(1, "\nClauses: {}", clauses)

        cnf = pysat.formula.CNF(from_clauses=clauses)

        for clause in cnf:
            sat_solver.add_clause(clause)

        while True:
            assignment = get_sat_assignment(sat_solver, sat_solver_name)

            if not assignment:
                print("unsat")
                if expected is not None and expected != "unsat":
                    print("error: expected result was {}".format(expected))
                    return Status.ERROR
                return Status.UNSAT

            smt_solver.push()
            smt_assertions = dict()
            debug_print(1, "\nSatisfying expressions from SAT solver:")
            for abstraction in assignment:
                expr = bool_abstraction.get_expression(abstraction)
                debug_print(1, "{}:\t{}", abstraction, expr)
                term = smt_solver.converter.convert(expr)
                smt_assertions[term] = expr
                smt_solver.cvc5.assertFormula(term)

            debug_print(0, "\nChecking assignment on QF_LRA solver: {}", smt_solver_name)
            if smt_solver.solve():
                print("sat")
                if dump_models:
                    print(smt_solver.get_model())
                smt_solver.pop()
                smt_assertions.clear()
                if expected is not None and expected != "sat":
                    print("error: expected result was {}".format(expected))
                    return Status.ERROR
                return Status.SAT
            else:
                debug_print(0, "unsat")
                unsat_core = smt_solver.cvc5.getUnsatCore()
                debug_print(0, "Unsat core: {}", unsat_core)
                unsat_core_abs = list()
                for term in unsat_core:
                    abs = None
                    if term in smt_assertions:
                        abs = bool_abstraction.get_abstraction(smt_assertions[term])
                    unsat_core_abs.append(abs)
                debug_print(0, "Unsat core abstraction: {}", unsat_core_abs)
                conflict_clause = [-abs for abs in unsat_core_abs]
                smt_solver.pop()
                smt_assertions.clear()
                if conflict_clause:
                    debug_print(0, "Adding conflict clause: {}", conflict_clause)
                    bool_abstraction.add_clause(conflict_clause)
                    sat_solver.add_clause(conflict_clause)


def main():
    arg_parser = argparse.ArgumentParser(prog="cdcl_tlra_solver",
                                         description="A Python CDCL(TLRA) SMT solver")
    arg_parser.add_argument("smt_lib2_filename",
                            help="Input file on SMT-LIB2 format")
    arg_parser.add_argument("--sat-solver", "-s",
                            type=SatSolver,
                            default="minisat22",
                            help="SAT solver used for solving propositional "
                                 "abstraction (Default: minisat22). "
                                 "Refer to https://pysathq.github.io/docs/html/api/solvers.html#pysat.solvers.SolverNames "
                                 "for available solvers.")
    arg_parser.add_argument("--dump-models", "-m",
                            action="store_true",
                            help="Print models after every SAT response")
    arg_parser.add_argument("--verbose", "-v",
                            type=int,
                            default=0,
                            help="Print verbose debugging log")
    args = arg_parser.parse_args()

    status = cdcl_tlra_check_sat(args.smt_lib2_filename,
                                 args.sat_solver.name,
                                 args.dump_models,
                                 args.verbose)
    if status == Status.ERROR:
        sys.exit(1)

if __name__ == "__main__":
    main()
