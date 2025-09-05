import s_programming_language as s

# Simple program that uses a macro to calculate the factorial of x and then adds one
program = [
    ('fact', 'y', 'x'),
    ('inc', 'y'),
]

program = [
    ('A:',),
    ('jnz', 'x', 'B'),
    ('inc', 'z'),
    ('jnz', 'z', 'E'),
    ('B:',),
    ('dec', 'x'),
    ('inc', 'y'),
    ('inc', 'z'),
    ('jnz', 'z', 'A'),
    ('E:',),
]

print(s.run_program(program, {'x':2,'z':0,}, s.example_macros, trace=True))  



