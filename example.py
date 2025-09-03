import s_programming_language as s





program = [
    ('add', 'y', 'x1', 'x2'),

]
print(s.run_program(program, {'x1':1, 'x2': 2}, s.example_macros, trace=True))  



