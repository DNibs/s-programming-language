import utils as s

macros = {
    # add(dst, a, b): computes dst = a + b
    "add": (
        ["dst", "a", "b"],
        [
            # Copy a into dst
            ("loop_a:",),
            ("jnz", "a", "do_a"),
            ("end_a:",),
            ("do_a:",),
            ("dec", "a"),
            ("inc", "dst"),
            ("jnz", "a", "do_a"),

            # Add b into dst
            ("loop_b:",),
            ("jnz", "b", "do_b"),
            ("end_b:",),
            ("do_b:",),
            ("dec", "b"),
            ("inc", "dst"),
            ("jnz", "b", "do_b"),
        ]
    )
}

program = [
    ("add", "y", "x1", "x2")  # y = x1 + x2
]

print(s.run_program(program, {"x1": 2, "x2": 3}, macros))  # → 5
program = [
    ('loop_a:',),
    ('dec', 'x',),
    ('inc', 'y',),
    ('jnz', 'x', 'loop_a'),
]
print(s.run_program(program, {'x':0}))
# Note - this gives the "S"-correct ouptut of y=1 when x=0, which matches what class expects
# need to check on macro implementation, check to ensure other "assumptions" aren't made (like input of less than 0), etc
# rewrite macros to match class-given macros
# Also check for recursion, expansion 
