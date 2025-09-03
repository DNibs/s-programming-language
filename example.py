import utils as s





program = [
    ('equals', 'y', 'x1'),
    ('equals', 'z', 'x2'),
    
    ('B:',),
    ('jnz', 'z', 'A'),
    ('goto', 'E'),

    ('A:',),
    ('dec', 'z'),
    ('inc', 'y'),
    ('goto', 'B'),

    ('E:',),

]
print(s.run_program(program, {'x1':7, 'x2': 3}, s.macros))  # → 10
# Note - this gives the "S"-correct ouptut of y=1 when x=0, which matches what class expects
# need to check on macro implementation, check to ensure other "assumptions" aren't made (like input of less than 0), etc
# rewrite macros to match class-given macros
# Also check for recursion, expansion 
