"""
Migration Script: SQLite to Supabase
Migrate your existing SQLite data to Supabase
"""

import sqlite3
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY not found in .env file")
    print("Please create .env file with your Supabase credentials")
    sys.exit(1)

# Initialize Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Connected to Supabase")
except Exception as e:
    print(f"❌ Failed to connect to Supabase: {str(e)}")
    sys.exit(1)

# Connect to SQLite
try:
    conn = sqlite3.connect('tps_data.db')
    c = conn.cursor()
    print("✅ Connected to SQLite database")
except Exception as e:
    print(f"❌ SQLite database not found: {str(e)}")
    sys.exit(1)

def migrate_employees():
    """Migrate employees from SQLite to Supabase"""
    try:
        print("\n📊 Migrating Employees...")
        c.execute('SELECT * FROM employees')
        employees = c.fetchall()
        
        if not employees:
            print("⚠️  No employees to migrate")
            return
        
        for emp in employees:
            emp_data = {
                'emp_id': emp[0],
                'emp_name': emp[1],
                'tps_score': emp[2],
                'assigned_partner': emp[3],
                'gst_number': emp[4],
                'department': emp[5],
                'created_date': emp[6]
            }
            
            # Check if already exists
            existing = supabase.table("employees").select("emp_id").eq("emp_id", emp[0]).execute()
            
            if existing.data:
                # Update
                supabase.table("employees").update(emp_data).eq("emp_id", emp[0]).execute()
                print(f"  ✏️  Updated: {emp[1]}")
            else:
                # Insert
                supabase.table("employees").insert(emp_data).execute()
                print(f"  ✅ Inserted: {emp[1]}")
        
        print(f"✅ Migrated {len(employees)} employees")
    except Exception as e:
        print(f"❌ Error migrating employees: {str(e)}")

def migrate_partners():
    """Migrate partners from SQLite to Supabase"""
    try:
        print("\n📋 Migrating Partners...")
        c.execute('SELECT * FROM partners')
        partners = c.fetchall()
        
        if not partners:
            print("⚠️  No partners to migrate")
            return
        
        for partner in partners:
            partner_data = {
                'partner_id': partner[0],
                'partner_name': partner[1],
                'gst_number': partner[2],
                'emp_id': partner[3],
                'status': partner[4],
                'created_date': partner[5]
            }
            
            # Check if already exists
            existing = supabase.table("partners").select("partner_id").eq("partner_id", partner[0]).execute()
            
            if existing.data:
                # Update
                supabase.table("partners").update(partner_data).eq("partner_id", partner[0]).execute()
                print(f"  ✏️  Updated: {partner[1]}")
            else:
                # Insert
                supabase.table("partners").insert(partner_data).execute()
                print(f"  ✅ Inserted: {partner[1]}")
        
        print(f"✅ Migrated {len(partners)} partners")
    except Exception as e:
        print(f"❌ Error migrating partners: {str(e)}")

def migrate_requests():
    """Migrate partner requests from SQLite to Supabase"""
    try:
        print("\n📝 Migrating Partner Requests...")
        c.execute('SELECT * FROM partner_requests')
        requests = c.fetchall()
        
        if not requests:
            print("⚠️  No requests to migrate")
            return
        
        for req in requests:
            request_data = {
                'request_id': req[0],
                'emp_id': req[1],
                'emp_name': req[2],
                'new_partner_name': req[3],
                'new_gst_number': req[4],
                'reason': req[5],
                'requested_date': req[6],
                'status': req[7],
                'tl_comments': req[8],
                'reviewed_by': req[9],
                'reviewed_date': req[10]
            }
            
            # Check if already exists
            existing = supabase.table("partner_requests").select("request_id").eq("request_id", req[0]).execute()
            
            if existing.data:
                # Update
                supabase.table("partner_requests").update(request_data).eq("request_id", req[0]).execute()
                print(f"  ✏️  Updated: Request #{req[0]}")
            else:
                # Insert
                supabase.table("partner_requests").insert(request_data).execute()
                print(f"  ✅ Inserted: Request #{req[0]}")
        
        print(f"✅ Migrated {len(requests)} requests")
    except Exception as e:
        print(f"❌ Error migrating requests: {str(e)}")

def migrate_tl_users():
    """Migrate TL users from SQLite to Supabase"""
    try:
        print("\n👨‍💼 Migrating Team Lead Users...")
        c.execute('SELECT * FROM tl_users')
        tl_users = c.fetchall()
        
        if not tl_users:
            print("⚠️  No TL users to migrate")
            return
        
        for tl in tl_users:
            tl_data = {
                'tl_id': tl[0],
                'tl_name': tl[1],
                'tl_password': tl[2],
                'department': tl[3],
                'created_date': tl[4]
            }
            
            # Check if already exists
            existing = supabase.table("tl_users").select("tl_id").eq("tl_id", tl[0]).execute()
            
            if existing.data:
                # Update
                supabase.table("tl_users").update(tl_data).eq("tl_id", tl[0]).execute()
                print(f"  ✏️  Updated: {tl[1]}")
            else:
                # Insert
                supabase.table("tl_users").insert(tl_data).execute()
                print(f"  ✅ Inserted: {tl[1]}")
        
        print(f"✅ Migrated {len(tl_users)} team lead users")
    except Exception as e:
        print(f"❌ Error migrating TL users: {str(e)}")

def main():
    """Run all migrations"""
    print("=" * 60)
    print("🔄 SQLite to Supabase Migration Tool")
    print("=" * 60)
    
    try:
        migrate_employees()
        migrate_partners()
        migrate_requests()
        migrate_tl_users()
        
        print("\n" + "=" * 60)
        print("✅ Migration Complete!")
        print("=" * 60)
        print("\n📌 Next Steps:")
        print("1. Verify data in Supabase console")
        print("2. Update your app to use tps_app_supabase.py")
        print("3. Run: streamlit run tps_app_supabase.py")
        print("\n✨ Your data has been successfully migrated!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
