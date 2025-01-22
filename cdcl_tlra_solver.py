import pysat.formula
import pysmt.operators
import pysat.solvers
import pysmt.environment
import pysmt.shortcuts
import pysmt.smtlib.parser
import pysmt.smtlib.script

import argparse

verbose = None

def debug_print(fmt, *args):
    global verbose
    if verbose:
        print(fmt.format(*args))

def eval_smt_lib2_script(script, solver, solver_name):
    debug_print("Evaluating SMT-LIB2 script on SMT solver: {}", solver_name)
    steps = []
    for command in script.commands:
        try:
            result = pysmt.smtlib.script.evaluate_command(command, solver)
            steps.append((command.name, result))
        except RuntimeError as error:
            debug_print("ERROR: {}: {}", command.name, error)
            steps.append((command.name, None))

    for command, result in steps:
        match command:
            case "check-sat":
                debug_print("sat" if result else "unsat")
            case "get-model":
                if result:
                    debug_print(result)

class BooleanAbstraction():
    def __init__(self, formula):
        self.formula = formula
        self.expressions = list()
        self.abstractions = dict()
        self.clauses = list()
        for atom in formula.get_atoms():
            self.add_abstraction(atom)

    def add_abstraction(self, expr):
        abstraction = self.get_abstraction(expr)

        if abstraction:
            return abstraction

        self.expressions.append(expr)
        new_abstraction = len(self.expressions)
        self.abstractions[expr] = new_abstraction
        return new_abstraction

    def get_abstraction(self, expr):
        return self.abstractions[expr] if expr in self.abstractions else None

    def get_expression(self, abstraction):
        if abstraction < 0:
            expr = self.expressions[-abstraction - 1]
            return pysmt.environment.get_env().formula_manager.Not(expr)

        return self.expressions[abstraction - 1]

    def get_clauses(self):
        if self.clauses:
            return self.clauses

        abstraction = self.clausify(self.formula)
        self.clauses.append([abstraction])

        return self.clauses

    def clausify(self, expr):
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
                self.clauses.append([-abstraction, -child])

                # -child => abstraction
                self.clauses.append([child, abstraction])

                return abstraction

            case pysmt.operators.OR:
                children = [self.clausify(arg) for arg in expr.args()]

                for child in children:
                    # child => abstraction
                    self.clauses.append([-child, abstraction])

                # abstraction => child1 v child2 v ... v childn
                children.append(-abstraction)
                self.clauses.append(children)

                return abstraction

            case pysmt.operators.AND:
                children = [self.clausify(arg) for arg in expr.args()]

                for child in children:
                    # abstraction => child
                    self.clauses.append([-abstraction, child])

                # child1 ^ child2 ^ ... ^ childn => abstraction
                negated_children = [-child for child in children]
                negated_children.append(abstraction)
                self.clauses.append(negated_children)

                return abstraction

            case pysmt.operators.IMPLIES:
                children = [self.clausify(arg) for arg in expr.args()]
                precondition = children.pop(0)

                # abstraction => (precondition => children)
                clause = [-abstraction, -precondition]
                clause.extend(children)
                self.clauses.append(clause)

                # -precondition => abstraction
                self.clauses.append([precondition, abstraction])

                for child in children:
                    # child => abstraction
                    self.clauses.append([-child, abstraction])

                return abstraction

            case pysmt.operators.IFF:
                lhs, rhs = [self.clausify(arg) for arg in expr.args()]

                # abstraction => (lhs => rhs)
                self.clauses.append([-abstraction, -lhs, rhs])

                # abstraction => (rhs => lhs)
                self.clauses.append([-abstraction, lhs, -rhs])

                # lhs ^ rhs => abstraction
                self.clauses.append([-lhs, -rhs, abstraction])

                # -lhs ^ -rhs => abstraction
                self.clauses.append([lhs, rhs, abstraction])

                return abstraction

        raise NotImplementedError(expr)

def get_sat_assignment(sat_solver, solver_name):
    debug_print("\nRunning SAT solver: {}", solver_name)

    if sat_solver.solve():
        debug_print("sat")
        return sat_solver.get_model()

    debug_print("unsat")
    return []

class UnknownSatSolver(argparse.ArgumentError):
    pass

class SatSolver:
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

def main():
    arg_parser = argparse.ArgumentParser(prog="cdcl_tlra_solver",
                                         description="A Python CDCL(TLRA) SMT solver")
    arg_parser.add_argument("smt_lib2_filename",
                            help="Input file on SMT-LIB2 format")
    arg_parser.add_argument("--sat-solver",
                            type=SatSolver,
                            default="minisat22",
                            help="SAT solver used for solving propositional "
                                 "abstraction (Default: minisat22). "
                                 "Refer to https://pysathq.github.io/docs/html/api/solvers.html#pysat.solvers.SolverNames "
                                 "for available solvers.")
    arg_parser.add_argument("--verbose", "-v",
                            action="store_true",
                            help="Print verbose debugging log")
    args = arg_parser.parse_args()
    global verbose
    verbose = args.verbose

    smt_parser = pysmt.smtlib.parser.SmtLibParser()
    script = smt_parser.get_script_fname(args.smt_lib2_filename)

    with pysat.solvers.Solver(name=args.sat_solver.name) as sat_solver:
        smt_solver_name = "cvc5"
        smt_solver = pysmt.shortcuts.Solver(name=smt_solver_name, logic="QF_LRA")
        smt_solver.cvc5.setOption("incremental", "true")

        formula = script.get_strict_formula()
        bool_abstraction = BooleanAbstraction(formula)
        debug_print("Clausifying SMT-LIB2 formula: {}", formula)

        clauses = bool_abstraction.get_clauses()

        for atom, abs in bool_abstraction.abstractions.items():
            debug_print("{}:\t{}", abs, atom)
        debug_print("\nClauses: {}", clauses)

        cnf = pysat.formula.CNF(from_clauses=clauses)

        for clause in cnf:
            sat_solver.add_clause(clause)

        while True:
            assignment = get_sat_assignment(sat_solver, args.sat_solver.name)

            if not assignment:
                print("unsat")
                break

            smt_solver.push()
            debug_print("\nSatisfying expressions from SAT solver:")
            for abstraction in assignment:
                expr = bool_abstraction.get_expression(abstraction)
                debug_print("{}:\t{}", abstraction, expr)
                smt_solver.add_assertion(expr)

            debug_print("\nChecking assignment on QF_LRA solver: {}", smt_solver_name)
            if smt_solver.solve():
                print("sat")
                print(smt_solver.get_model())
                smt_solver.pop()
                break
            else:
                debug_print("unsat")
                smt_solver.pop()
                conflict_clause = [-literal for literal in assignment]
                if conflict_clause:
                    debug_print("Adding conflict clause: {}", conflict_clause)
                    sat_solver.add_clause(conflict_clause)


if __name__ == "__main__":
    main()
