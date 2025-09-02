import itertools

def expand_macros(instructions, macros):
    """
    Expand parameterized macros into flat instructions.
    - instructions: list of tuples
    - macros: dict {macro_name: (params, code)}
        params: list of formal variable names
        code: list of instructions (with labels + jnz allowed)
    """
    counter = itertools.count()  # unique suffix for labels
    expanded = []

    for instr in instructions:
        if instr[0] in macros:
            name = instr[0]
            args = instr[1:]
            formals, macro_code = macros[name]

            if len(args) != len(formals):
                raise ValueError(f"Macro {name} expects {len(formals)} args, got {len(args)}")

            mapping = dict(zip(formals, args))  # formal → actual
            suffix = f"__{next(counter)}"

            for m in macro_code:
                if m[0].endswith(":"):  # label definition
                    label = m[0][:-1] + suffix + ":"
                    expanded.append((label,))
                elif m[0] == "jnz":
                    var, label = m[1], m[2]
                    expanded.append(("jnz", mapping.get(var, var), label + suffix))
                elif m[0] in ("inc", "dec"):
                    var = m[1]
                    expanded.append((m[0], mapping.get(var, var)))
                else:
                    raise ValueError(f"Invalid instruction in macro {name}: {m}")
        else:
            expanded.append(instr)

    return expanded


def run_program(instructions, inputs=None, macros=None, max_steps=1000):
    """
    Run program with parameterized macros and labels.
    """
    macros = macros or {}
    instructions = expand_macros(instructions, macros)

    # 1. Resolve labels
    label_map = {}
    flat_instructions = []
    for instr in instructions:
        if instr[0].endswith(":"):
            label = instr[0][:-1]
            label_map[label] = len(flat_instructions)
        else:
            flat_instructions.append(instr)

    # 2. Init vars
    vars = {**inputs} if inputs else {}
    vars["y"] = 0

    # 3. Execute
    pc = 0
    steps = 0
    while 0 <= pc < len(flat_instructions) and steps < max_steps:
        op, *args = flat_instructions[pc]

        if op == "inc":
            v = args[0]
            vars[v] = vars.get(v, 0) + 1
            pc += 1

        elif op == "dec":
            v = args[0]
            vars[v] = max(0, vars.get(v, 0) - 1)
            pc += 1

        elif op == "jnz":
            v, label = args
            if vars.get(v, 0) != 0:
                pc = label_map[label]
            else:
                pc += 1

        else:
            raise ValueError(f"Unknown instruction {op}")

        steps += 1

    return vars["y"]
