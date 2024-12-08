import cvc5.pythonic
import pysmt.fnode
import pysmt.logics
import pysmt.smtlib.parser

import sys

smt_parser = pysmt.smtlib.parser.SmtLibParser()
smt_lib2_file = sys.argv[1]
script = smt_parser.get_script_fname(smt_lib2_file)

solver = cvc5.pythonic.Solver()
constants = dict()
result = None
model = None

for smt_lib2_command in script:
    command, args = smt_lib2_command
    match command:
        case "set-logic":
            solver = cvc5.pythonic.Solver(logic=args[0].name)
        case "set-option":
            option, value = args
            if option[0] == ":":
                option = option[1:]
            solver.setOption(option, value)
        case "declare-const":
            constant = args[0]
            constants[str(constant)] = cvc5.pythonic.Real(str(constant))
        case "assert":
            expr = args[0]
            match expr.node_type():
                case pysmt.operators.EQUALS:
                    lhs, rhs = expr.args()
                    match lhs.node_type():
                        case pysmt.operators.PLUS:
                            LHS = cvc5.pythonic.Add(constants[str(lhs.arg(0))], lhs.arg(1))
                        case pysmt.operators.TIMES:
                            LHS = cvc5.pythonic.Mult(constants[str(lhs.arg(0))], lhs.arg(1))
                        case _:
                            pass
                    match rhs.node_type():
                        case pysmt.operators.PLUS:
                            RHS = cvc5.pythonic.Add(rhs.arg(0), constants[str(rhs.arg(1))])
                        case pysmt.operators.TIMES:
                            RHS = cvc5.pythonic.Mult(rhs.arg(0), constants[str(rhs.arg(1))])
                        case _:
                            pass
                case _:
                    pass
            solver.add(LHS == RHS)
        case "check-sat":
            result = solver.check()
        case "get-model":
            model = solver.model()
        case _:
            print("Skipping unsupported command: {}".format(smt_lib2_command))

print(constants)
if result:
    print(result)
if model:
    print(model)
