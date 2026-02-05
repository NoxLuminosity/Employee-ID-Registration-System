import sys
sys.path.insert(0, '.')
from app.database import get_all_employees

emps = get_all_employees()
print('Employee location_branch values:')
for e in emps:
    name = e.get('employee_name')
    loc = e.get('location_branch')
    print(f'  {name}: location_branch = {repr(loc)}')
