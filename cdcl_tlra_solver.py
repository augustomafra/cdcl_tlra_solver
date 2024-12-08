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

def main():
    arg_parser = argparse.ArgumentParser(prog="cdcl_tlra_solver",
                                         description="A Python CDCL(TLRA) SMT solver")
    arg_parser.add_argument("smt_lib2_filename")
    args = arg_parser.parse_args()

    smt_parser = pysmt.smtlib.parser.SmtLibParser()
    script = smt_parser.get_script_fname(args.smt_lib2_filename)

    solver = pysmt.shortcuts.Solver(name="cvc5")

    eval_smt_lib2_script(script, solver)

if __name__ == "__main__":
    main()
