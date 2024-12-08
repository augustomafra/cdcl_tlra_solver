import pysmt.shortcuts
import pysmt.smtlib.parser
import pysmt.smtlib.script

import sys

smt_parser = pysmt.smtlib.parser.SmtLibParser()
smt_lib2_file = sys.argv[1]
script = smt_parser.get_script_fname(smt_lib2_file)

solver = pysmt.shortcuts.Solver(name="cvc5")

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
