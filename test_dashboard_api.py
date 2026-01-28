import sys
sys.path.insert(0, '.')

from app.database import get_all_employees, USE_SUPABASE

print(f'Database: {"Supabase" if USE_SUPABASE else "SQLite"}')
print()

employees = get_all_employees()
print(f'Total employees: {len(employees)}')
print()

if employees:
    print('Sample employee (first record):')
    emp = employees[0]
    print(f'  ID: {emp.get("id")}')
    print(f'  Name: {emp.get("employee_name")}')
    print(f'  Position: {emp.get("position")}')
    print(f'  Location/Branch: {emp.get("location_branch")}')
    print(f'  Department: {emp.get("department")}')
    print(f'  Status: {emp.get("status")}')
    print()
    
    if 'location_branch' in emp:
        print('✅ location_branch field IS PRESENT in database!')
    else:
        print('❌ location_branch field is MISSING from database!')
        print('   Available fields:', list(emp.keys()))
else:
    print('No employees found')
