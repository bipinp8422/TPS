"""
Data Import Script - Import employee and partner data from Excel
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os

def import_employees_from_excel(excel_file, sheet_name='Employees'):
    """
    Import employee data from Excel
    
    Expected columns in Excel:
    - emp_id: Employee ID
    - emp_name: Employee Name
    - tps_score: TPS Score
    - assigned_partner: Assigned Partner
    - gst_number: GST Number
    - department: Department
    """
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        conn = sqlite3.connect('tps_data.db')
        c = conn.cursor()
        
        # Clear existing employee data (optional)
        # c.execute('DELETE FROM employees')
        
        for idx, row in df.iterrows():
            try:
                c.execute('''INSERT OR REPLACE INTO employees 
                    (emp_id, emp_name, tps_score, assigned_partner, gst_number, department, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (
                        str(row.get('emp_id', '')).strip(),
                        str(row.get('emp_name', '')).strip(),
                        float(row.get('tps_score', 0)),
                        str(row.get('assigned_partner', '')).strip(),
                        str(row.get('gst_number', '')).strip(),
                        str(row.get('department', '')).strip(),
                        datetime.now().strftime('%Y-%m-%d')
                    )
                )
                print(f"✓ Imported: {row.get('emp_name')}")
            except Exception as e:
                print(f"✗ Error importing row {idx}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Successfully imported {len(df)} employees!")
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {excel_file}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def import_partners_from_excel(excel_file, sheet_name='Partners'):
    """
    Import partner data from Excel
    
    Expected columns in Excel:
    - partner_id: Partner ID
    - partner_name: Partner Name
    - gst_number: GST Number
    - emp_id: Employee ID
    - status: Status (Active/Inactive)
    """
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        conn = sqlite3.connect('tps_data.db')
        c = conn.cursor()
        
        for idx, row in df.iterrows():
            try:
                c.execute('''INSERT OR REPLACE INTO partners 
                    (partner_id, partner_name, gst_number, emp_id, status, created_date)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (
                        str(row.get('partner_id', '')).strip(),
                        str(row.get('partner_name', '')).strip(),
                        str(row.get('gst_number', '')).strip(),
                        str(row.get('emp_id', '')).strip(),
                        str(row.get('status', 'Active')).strip(),
                        datetime.now().strftime('%Y-%m-%d')
                    )
                )
                print(f"✓ Imported: {row.get('partner_name')}")
            except Exception as e:
                print(f"✗ Error importing row {idx}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Successfully imported {len(df)} partners!")
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {excel_file}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def export_to_excel(output_file='tps_export.xlsx'):
    """
    Export current database to Excel file
    """
    try:
        conn = sqlite3.connect('tps_data.db')
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Export employees
            employees_df = pd.read_sql_query('SELECT * FROM employees', conn)
            employees_df.to_excel(writer, sheet_name='Employees', index=False)
            
            # Export partners
            partners_df = pd.read_sql_query('SELECT * FROM partners', conn)
            partners_df.to_excel(writer, sheet_name='Partners', index=False)
            
            # Export requests
            requests_df = pd.read_sql_query('SELECT * FROM partner_requests', conn)
            requests_df.to_excel(writer, sheet_name='Requests', index=False)
        
        conn.close()
        print(f"✅ Successfully exported to {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def create_sample_excel_template(filename='sample_import.xlsx'):
    """
    Create a sample Excel template for data import
    """
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Sample employees
        employees_sample = pd.DataFrame({
            'emp_id': ['EMP001', 'EMP002', 'EMP003'],
            'emp_name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'tps_score': [85.5, 92.0, 78.5],
            'assigned_partner': ['Partner A', 'Partner B', 'Partner A'],
            'gst_number': ['GST123ABC', 'GST456DEF', 'GST789GHI'],
            'department': ['Sales', 'Operations', 'Sales']
        })
        employees_sample.to_excel(writer, sheet_name='Employees', index=False)
        
        # Sample partners
        partners_sample = pd.DataFrame({
            'partner_id': ['P001', 'P002', 'P003'],
            'partner_name': ['Partner A', 'Partner B', 'Partner A'],
            'gst_number': ['GST123ABC', 'GST456DEF', 'GST789GHI'],
            'emp_id': ['EMP001', 'EMP002', 'EMP003'],
            'status': ['Active', 'Active', 'Active']
        })
        partners_sample.to_excel(writer, sheet_name='Partners', index=False)
    
    print(f"✅ Sample template created: {filename}")

if __name__ == "__main__":
    print("=== TPS Data Import Tool ===\n")
    
    # Option 1: Create sample template
    print("1. Creating sample template...")
    create_sample_excel_template()
    
    print("\n2. Use one of the following functions in your Python script:")
    print("   - import_employees_from_excel('your_file.xlsx', 'Sheet_Name')")
    print("   - import_partners_from_excel('your_file.xlsx', 'Sheet_Name')")
    print("   - export_to_excel('output.xlsx')")
    
    print("\nExample:")
    print("   from import_data import import_employees_from_excel")
    print("   import_employees_from_excel('TPS_New.xlsx', 'Employees')")
