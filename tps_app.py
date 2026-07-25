import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_option_menu import option_menu
import json

# Page configuration
st.set_page_config(
    page_title="TPS Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
def init_database():
    conn = sqlite3.connect('tps_data.db')
    c = conn.cursor()
    
    # Employees table
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        emp_id TEXT PRIMARY KEY,
        emp_name TEXT,
        tps_score REAL,
        assigned_partner TEXT,
        gst_number TEXT,
        department TEXT,
        created_date TEXT
    )''')
    
    # Partners/Counters table
    c.execute('''CREATE TABLE IF NOT EXISTS partners (
        partner_id TEXT PRIMARY KEY,
        partner_name TEXT,
        gst_number TEXT,
        emp_id TEXT,
        status TEXT DEFAULT 'Active',
        created_date TEXT,
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
    )''')
    
    # New partner requests table
    c.execute('''CREATE TABLE IF NOT EXISTS partner_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        emp_name TEXT,
        new_partner_name TEXT,
        new_gst_number TEXT,
        reason TEXT,
        requested_date TEXT,
        status TEXT DEFAULT 'Pending',
        tl_comments TEXT,
        reviewed_by TEXT,
        reviewed_date TEXT,
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
    )''')
    
    # TL users table
    c.execute('''CREATE TABLE IF NOT EXISTS tl_users (
        tl_id TEXT PRIMARY KEY,
        tl_name TEXT,
        tl_password TEXT,
        department TEXT,
        created_date TEXT
    )''')
    
    conn.commit()
    conn.close()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_type = None
    st.session_state.user_id = None
    st.session_state.user_name = None

# Add sample data function
def add_sample_data():
    conn = sqlite3.connect('tps_data.db')
    c = conn.cursor()
    
    # Check if data already exists
    c.execute('SELECT COUNT(*) FROM employees')
    if c.fetchone()[0] == 0:
        # Add sample employees
        employees = [
            ('EMP001', 'Rajesh Kumar', 85.5, 'Partner A', 'GST123ABC', 'Sales', datetime.now().strftime('%Y-%m-%d')),
            ('EMP002', 'Priya Sharma', 92.0, 'Partner B', 'GST456DEF', 'Operations', datetime.now().strftime('%Y-%m-%d')),
            ('EMP003', 'Amit Patel', 78.5, 'Partner A', 'GST789GHI', 'Sales', datetime.now().strftime('%Y-%m-%d')),
            ('EMP004', 'Sneha Desai', 88.0, 'Partner C', 'GST101JKL', 'Operations', datetime.now().strftime('%Y-%m-%d')),
        ]
        c.executemany('INSERT INTO employees VALUES (?,?,?,?,?,?,?)', employees)
        
        # Add sample partners
        partners = [
            ('P001', 'Partner A', 'GST123ABC', 'EMP001', 'Active', datetime.now().strftime('%Y-%m-%d')),
            ('P002', 'Partner B', 'GST456DEF', 'EMP002', 'Active', datetime.now().strftime('%Y-%m-%d')),
            ('P003', 'Partner A', 'GST789GHI', 'EMP003', 'Active', datetime.now().strftime('%Y-%m-%d')),
            ('P004', 'Partner C', 'GST101JKL', 'EMP004', 'Active', datetime.now().strftime('%Y-%m-%d')),
        ]
        c.executemany('INSERT INTO partners VALUES (?,?,?,?,?,?)', partners)
        
        # Add sample TL users
        tl_users = [
            ('TL001', 'Vikram Singh', 'tl@123', 'Sales', datetime.now().strftime('%Y-%m-%d')),
            ('TL002', 'Ananya Gupta', 'tl@123', 'Operations', datetime.now().strftime('%Y-%m-%d')),
        ]
        c.executemany('INSERT INTO tl_users VALUES (?,?,?,?,?)', tl_users)
        
        conn.commit()
    
    conn.close()

# Login function
def login():
    st.title("🔐 TPS Management System - Login")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Employee Login")
        emp_id = st.text_input("Employee ID", key="emp_id")
        
        if st.button("Login as Employee", key="emp_login_btn", use_container_width=True):
            conn = sqlite3.connect('tps_data.db')
            c = conn.cursor()
            c.execute('SELECT emp_name FROM employees WHERE emp_id = ?', (emp_id,))
            result = c.fetchone()
            conn.close()
            
            if result:
                st.session_state.logged_in = True
                st.session_state.user_type = 'employee'
                st.session_state.user_id = emp_id
                st.session_state.user_name = result[0]
                st.success(f"Welcome, {result[0]}!")
                st.rerun()
            else:
                st.error("Invalid Employee ID")
    
    with col2:
        st.subheader("Team Lead Login")
        tl_id = st.text_input("TL ID", key="tl_id")
        tl_password = st.text_input("Password", type="password", key="tl_password")
        
        if st.button("Login as TL", key="tl_login_btn", use_container_width=True):
            conn = sqlite3.connect('tps_data.db')
            c = conn.cursor()
            c.execute('SELECT tl_name FROM tl_users WHERE tl_id = ? AND tl_password = ?', (tl_id, tl_password))
            result = c.fetchone()
            conn.close()
            
            if result:
                st.session_state.logged_in = True
                st.session_state.user_type = 'tl'
                st.session_state.user_id = tl_id
                st.session_state.user_name = result[0]
                st.success(f"Welcome, {result[0]}!")
                st.rerun()
            else:
                st.error("Invalid TL ID or Password")
    
    st.info("📌 Demo Credentials:\n\n**Employee:** EMP001, EMP002, EMP003, EMP004\n\n**TL:** ID: TL001, Password: tl@123")

# Employee Dashboard
def employee_dashboard():
    st.title(f"👤 Welcome, {st.session_state.user_name}!")
    
    conn = sqlite3.connect('tps_data.db')
    c = conn.cursor()
    
    # Fetch employee data
    c.execute('SELECT * FROM employees WHERE emp_id = ?', (st.session_state.user_id,))
    emp_data = c.fetchone()
    
    if emp_data:
        emp_id, emp_name, tps_score, partner, gst, dept, created = emp_data
        
        # Display employee info
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("TPS Score", f"{tps_score}%", delta="Performance")
        with col2:
            st.metric("Assigned Partner", partner)
        with col3:
            st.metric("GST Number", gst)
        with col4:
            st.metric("Department", dept)
        
        st.divider()
        
        # Partner details
        st.subheader("📋 Current Partner Details")
        c.execute('SELECT * FROM partners WHERE emp_id = ?', (st.session_state.user_id,))
        partners = c.fetchall()
        
        if partners:
            partner_df = pd.DataFrame(partners, columns=['Partner ID', 'Partner Name', 'GST Number', 'Emp ID', 'Status', 'Created Date'])
            st.dataframe(partner_df[['Partner Name', 'GST Number', 'Status', 'Created Date']], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Request new partner
        st.subheader("➕ Request New Counter/Partner")
        with st.form("new_partner_request"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_partner_name = st.text_input("New Partner Name")
                new_gst = st.text_input("New GST Number")
            
            with col2:
                reason = st.text_area("Reason for New Counter", height=80)
            
            if st.form_submit_button("Submit Request", use_container_width=True):
                if new_partner_name and new_gst and reason:
                    c.execute('''INSERT INTO partner_requests 
                        (emp_id, emp_name, new_partner_name, new_gst_number, reason, requested_date, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (st.session_state.user_id, emp_name, new_partner_name, new_gst, reason, 
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Pending'))
                    conn.commit()
                    st.success("✅ Request submitted successfully! Waiting for TL approval.")
                else:
                    st.error("Please fill all fields")
        
        st.divider()
        
        # View request history
        st.subheader("📜 Your Request History")
        c.execute('SELECT request_id, new_partner_name, new_gst_number, requested_date, status, tl_comments FROM partner_requests WHERE emp_id = ? ORDER BY requested_date DESC', (st.session_state.user_id,))
        requests = c.fetchall()
        
        if requests:
            request_df = pd.DataFrame(requests, columns=['Request ID', 'Partner Name', 'GST Number', 'Requested Date', 'Status', 'TL Comments'])
            st.dataframe(request_df, use_container_width=True, hide_index=True)
        else:
            st.info("No requests yet")
    
    conn.close()

# TL Dashboard
def tl_dashboard():
    st.title(f"👨‍💼 TL Dashboard - {st.session_state.user_name}")
    
    conn = sqlite3.connect('tps_data.db')
    c = conn.cursor()
    
    tab1, tab2, tab3 = st.tabs(["📥 Pending Requests", "✅ Approved Requests", "❌ Rejected Requests"])
    
    # Tab 1: Pending Requests
    with tab1:
        st.subheader("Pending Partner Requests")
        c.execute('SELECT * FROM partner_requests WHERE status = "Pending" ORDER BY requested_date')
        pending_requests = c.fetchall()
        
        if pending_requests:
            for req in pending_requests:
                req_id, emp_id, emp_name, new_partner, new_gst, reason, req_date, status, comments, reviewed_by, reviewed_date = req
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Employee:** {emp_name} ({emp_id})")
                        st.write(f"**New Partner:** {new_partner}")
                        st.write(f"**GST Number:** {new_gst}")
                    
                    with col2:
                        st.write(f"**Reason:** {reason}")
                        st.write(f"**Requested:** {req_date}")
                    
                    with col3:
                        if st.button("View Details", key=f"view_{req_id}"):
                            st.write("Details expanded")
                    
                    st.divider()
                    
                    # Review section
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        tl_comment = st.text_area("Add Comments", key=f"comment_{req_id}", height=80)
                    
                    with col2:
                        if st.button("✅ Approve", key=f"approve_{req_id}"):
                            c.execute('''UPDATE partner_requests 
                                SET status = "Approved", tl_comments = ?, reviewed_by = ?, reviewed_date = ?
                                WHERE request_id = ?''',
                                (tl_comment, st.session_state.user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), req_id))
                            
                            # Add new partner
                            c.execute('''INSERT INTO partners (partner_id, partner_name, gst_number, emp_id, status, created_date)
                                VALUES (?, ?, ?, ?, ?, ?)''',
                                (f"P{datetime.now().strftime('%Y%m%d%H%M%S')}", new_partner, new_gst, emp_id, 'Active',
                                 datetime.now().strftime('%Y-%m-%d')))
                            
                            conn.commit()
                            st.success("✅ Request Approved!")
                            st.rerun()
                        
                        if st.button("❌ Reject", key=f"reject_{req_id}"):
                            c.execute('''UPDATE partner_requests 
                                SET status = "Rejected", tl_comments = ?, reviewed_by = ?, reviewed_date = ?
                                WHERE request_id = ?''',
                                (tl_comment, st.session_state.user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), req_id))
                            conn.commit()
                            st.error("❌ Request Rejected!")
                            st.rerun()
        else:
            st.info("✅ All requests are processed!")
    
    # Tab 2: Approved Requests
    with tab2:
        st.subheader("Approved Partner Requests")
        c.execute('SELECT emp_name, new_partner_name, new_gst_number, requested_date, reviewed_date FROM partner_requests WHERE status = "Approved" ORDER BY reviewed_date DESC')
        approved = c.fetchall()
        
        if approved:
            approved_df = pd.DataFrame(approved, columns=['Employee', 'Partner Name', 'GST Number', 'Requested', 'Approved'])
            st.dataframe(approved_df, use_container_width=True, hide_index=True)
        else:
            st.info("No approved requests")
    
    # Tab 3: Rejected Requests
    with tab3:
        st.subheader("Rejected Partner Requests")
        c.execute('SELECT emp_name, new_partner_name, new_gst_number, requested_date, reviewed_date FROM partner_requests WHERE status = "Rejected" ORDER BY reviewed_date DESC')
        rejected = c.fetchall()
        
        if rejected:
            rejected_df = pd.DataFrame(rejected, columns=['Employee', 'Partner Name', 'GST Number', 'Requested', 'Rejected'])
            st.dataframe(rejected_df, use_container_width=True, hide_index=True)
        else:
            st.info("No rejected requests")
    
    conn.close()

# Main app
def main():
    init_database()
    add_sample_data()
    
    if not st.session_state.logged_in:
        login()
    else:
        # Sidebar logout
        with st.sidebar:
            st.title("Navigation")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_type = None
                st.rerun()
        
        # Route to appropriate dashboard
        if st.session_state.user_type == 'employee':
            employee_dashboard()
        elif st.session_state.user_type == 'tl':
            tl_dashboard()

if __name__ == "__main__":
    main()
