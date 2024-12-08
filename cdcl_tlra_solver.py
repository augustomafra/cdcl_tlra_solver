import pysat.formula
import pysmt.operators
import pysat.solvers
import pysmt.shortcuts
import pysmt.smtlib.parser
import pysmt.smtlib.script

import argparse

def eval_smt_lib2_script(script, solver):
    steps = []
    for command in script.commands:
        try:
            result = pysmt.smtlib.script.evaluate_command(command, solver)
            steps.append((command.name, result))
        except RuntimeError as error:
            print("ERROR: {}: {}".format(command.name, error))
            steps.append((command.name, None))

    for command, result in steps:
        match command:
            case "check-sat":
                print("sat" if result else "unsat")
            case "get-model":
                if result:
                    print(result)

class BooleanAbstraction():
    def __init__(self, formula):
        """ TODO: Do conversion to CNF.
            For now we assume the input formula is CNF
        """
        self.formula = formula
        self.atoms = list()
        self.abstractions = dict()
        self.clauses = list()
        for atom in formula.get_atoms():
            if atom not in self.abstractions:
                self.atoms.append(atom)
                self.abstractions[atom] = len(self.atoms)

    def get_abstraction(self, expr):
        return self.abstractions[expr] if expr in self.abstractions else None

    def get_atom(self, abstraction):
        return self.atoms[abstraction - 1]

    def get_clauses(self):
        if self.clauses:
            return self.clauses

        for expr in self.formula.args():
            clause = self.clausify(expr)
            self.clauses.append(clause)

        return self.clauses

    def clausify(self, expr):
        abstraction = self.get_abstraction(expr)
        if abstraction:
            # Expr is an atom, so simply return a clause with its abstraction
            return [abstraction]

        match expr.node_type():
            case pysmt.operators.NOT:
                subexpr = self.clausify(expr.arg(0))
                if len(subexpr) != 1:
                    raise NotImplementedError("Clausifier does not support NOT operation with more than one operand")
                return [-subexpr[0]]

            case pysmt.operators.OR:
                lhs = self.clausify(expr.arg(0))
                if len(lhs) != 1:
                    raise NotImplementedError("Clausifier does not support OR operation with more than one level of nesting")
                rhs = self.clausify(expr.arg(1))
                if len(rhs) != 1:
                    raise NotImplementedError("Clausifier does not support OR operation with more than one level of nesting")
                return [lhs[0], rhs[0]]

            case pysmt.operators.AND:
                raise NotImplementedError("Clausifier does not support AND operation, assuming CNF input for now")

        raise NotImplementedError()

def get_sat_assignment(clauses):
    cnf = pysat.formula.CNF(from_clauses=clauses)
    with pysat.solvers.Solver(name="minisat22", bootstrap_with=cnf) as solver:
        if solver.solve():
            print("sat")
            return solver.get_model()
        else:
            print("unsat")
    return []

def main():
    arg_parser = argparse.ArgumentParser(prog="cdcl_tlra_solver",
                                         description="A Python CDCL(TLRA) SMT solver")
    arg_parser.add_argument("smt_lib2_filename")
    args = arg_parser.parse_args()

    smt_parser = pysmt.smtlib.parser.SmtLibParser()
    script = smt_parser.get_script_fname(args.smt_lib2_filename)

    solver = pysmt.shortcuts.Solver(name="cvc5")

    eval_smt_lib2_script(script, solver)

    bool_abstraction = BooleanAbstraction(script.get_strict_formula())
    print(bool_abstraction.abstractions)

    clauses = bool_abstraction.get_clauses()
    print(clauses)

    assignment = get_sat_assignment(clauses)
    for abstraction in assignment:
        print(bool_abstraction.get_atom(abstraction))

if __name__ == "__main__":
    main()
