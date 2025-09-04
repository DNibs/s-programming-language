import s_programming_language as s

# Simple program that uses a macro to calculate the factorial of x and then adds one
program = [
    ('fact', 'y', 'x'),
    ('inc', 'y'),
]

print(s.run_program(program, {'x':5,}, s.example_macros, trace=False))  



