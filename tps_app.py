import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase
SUPABASE_URL = https://bfxviifbzulbxdfybtro.supabase.co
SUPABASE_KEY = sb_publishable_BnK0cEUbhJPzn-2EZ4PeIA_VZCbOYU6

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase credentials not found! Please set SUPABASE_URL and SUPABASE_KEY in .env file")
    st.stop()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Failed to connect to Supabase: {str(e)}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="TPS Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database tables
def init_database():
    try:
        # Check if tables exist, if not they will be created via Supabase console
        st.info("✅ Database connected to Supabase")
    except Exception as e:
        st.error(f"Database error: {str(e)}")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_type = None
    st.session_state.user_id = None
    st.session_state.user_name = None

# Add sample data function
def add_sample_data():
    try:
        # Check if data already exists
        result = supabase.table("employees").select("COUNT(*)", count="exact").execute()
        
        if result.data and len(result.data) > 0:
            if result.count == 0:
                # Add sample employees
                employees = [
                    {
                        'emp_id': 'EMP001',
                        'emp_name': 'Rajesh Kumar',
                        'tps_score': 85.5,
                        'assigned_partner': 'Partner A',
                        'gst_number': 'GST123ABC',
                        'department': 'Sales',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'emp_id': 'EMP002',
                        'emp_name': 'Priya Sharma',
                        'tps_score': 92.0,
                        'assigned_partner': 'Partner B',
                        'gst_number': 'GST456DEF',
                        'department': 'Operations',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'emp_id': 'EMP003',
                        'emp_name': 'Amit Patel',
                        'tps_score': 78.5,
                        'assigned_partner': 'Partner A',
                        'gst_number': 'GST789GHI',
                        'department': 'Sales',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'emp_id': 'EMP004',
                        'emp_name': 'Sneha Desai',
                        'tps_score': 88.0,
                        'assigned_partner': 'Partner C',
                        'gst_number': 'GST101JKL',
                        'department': 'Operations',
                        'created_date': datetime.now().isoformat()
                    }
                ]
                supabase.table("employees").insert(employees).execute()
                
                # Add sample partners
                partners = [
                    {
                        'partner_id': 'P001',
                        'partner_name': 'Partner A',
                        'gst_number': 'GST123ABC',
                        'emp_id': 'EMP001',
                        'status': 'Active',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'partner_id': 'P002',
                        'partner_name': 'Partner B',
                        'gst_number': 'GST456DEF',
                        'emp_id': 'EMP002',
                        'status': 'Active',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'partner_id': 'P003',
                        'partner_name': 'Partner A',
                        'gst_number': 'GST789GHI',
                        'emp_id': 'EMP003',
                        'status': 'Active',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'partner_id': 'P004',
                        'partner_name': 'Partner C',
                        'gst_number': 'GST101JKL',
                        'emp_id': 'EMP004',
                        'status': 'Active',
                        'created_date': datetime.now().isoformat()
                    }
                ]
                supabase.table("partners").insert(partners).execute()
                
                # Add sample TL users
                tl_users = [
                    {
                        'tl_id': 'TL001',
                        'tl_name': 'Vikram Singh',
                        'tl_password': 'tl@123',
                        'department': 'Sales',
                        'created_date': datetime.now().isoformat()
                    },
                    {
                        'tl_id': 'TL002',
                        'tl_name': 'Ananya Gupta',
                        'tl_password': 'tl@123',
                        'department': 'Operations',
                        'created_date': datetime.now().isoformat()
                    }
                ]
                supabase.table("tl_users").insert(tl_users).execute()
    except Exception as e:
        pass  # Table might already have data

# Login function
def login():
    st.title("🔐 TPS Management System - Login")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Employee Login")
        emp_id = st.text_input("Employee ID", key="emp_id")
        
        if st.button("Login as Employee", key="emp_login_btn", use_container_width=True):
            try:
                result = supabase.table("employees").select("emp_name").eq("emp_id", emp_id).execute()
                
                if result.data and len(result.data) > 0:
                    st.session_state.logged_in = True
                    st.session_state.user_type = 'employee'
                    st.session_state.user_id = emp_id
                    st.session_state.user_name = result.data[0]['emp_name']
                    st.success(f"Welcome, {result.data[0]['emp_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid Employee ID")
            except Exception as e:
                st.error(f"Login error: {str(e)}")
    
    with col2:
        st.subheader("Team Lead Login")
        tl_id = st.text_input("TL ID", key="tl_id")
        tl_password = st.text_input("Password", type="password", key="tl_password")
        
        if st.button("Login as TL", key="tl_login_btn", use_container_width=True):
            try:
                result = supabase.table("tl_users").select("tl_name").eq("tl_id", tl_id).eq("tl_password", tl_password).execute()
                
                if result.data and len(result.data) > 0:
                    st.session_state.logged_in = True
                    st.session_state.user_type = 'tl'
                    st.session_state.user_id = tl_id
                    st.session_state.user_name = result.data[0]['tl_name']
                    st.success(f"Welcome, {result.data[0]['tl_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid TL ID or Password")
            except Exception as e:
                st.error(f"Login error: {str(e)}")
    
    st.info("📌 Demo Credentials:\n\n**Employee:** EMP001, EMP002, EMP003, EMP004\n\n**TL:** ID: TL001, Password: tl@123")

# Employee Dashboard
def employee_dashboard():
    st.title(f"👤 Welcome, {st.session_state.user_name}!")
    
    try:
        # Fetch employee data
        emp_result = supabase.table("employees").select("*").eq("emp_id", st.session_state.user_id).execute()
        
        if emp_result.data and len(emp_result.data) > 0:
            emp_data = emp_result.data[0]
            
            # Display employee info
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("TPS Score", f"{emp_data['tps_score']}%", delta="Performance")
            with col2:
                st.metric("Assigned Partner", emp_data['assigned_partner'])
            with col3:
                st.metric("GST Number", emp_data['gst_number'])
            with col4:
                st.metric("Department", emp_data['department'])
            
            st.divider()
            
            # Partner details
            st.subheader("📋 Current Partner Details")
            partners_result = supabase.table("partners").select("*").eq("emp_id", st.session_state.user_id).execute()
            
            if partners_result.data and len(partners_result.data) > 0:
                partner_df = pd.DataFrame(partners_result.data)
                st.dataframe(partner_df[['partner_name', 'gst_number', 'status', 'created_date']], use_container_width=True, hide_index=True)
            
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
                        try:
                            request_data = {
                                'emp_id': st.session_state.user_id,
                                'emp_name': emp_data['emp_name'],
                                'new_partner_name': new_partner_name,
                                'new_gst_number': new_gst,
                                'reason': reason,
                                'requested_date': datetime.now().isoformat(),
                                'status': 'Pending'
                            }
                            supabase.table("partner_requests").insert(request_data).execute()
                            st.success("✅ Request submitted successfully! Waiting for TL approval.")
                        except Exception as e:
                            st.error(f"Error submitting request: {str(e)}")
                    else:
                        st.error("Please fill all fields")
            
            st.divider()
            
            # View request history
            st.subheader("📜 Your Request History")
            requests_result = supabase.table("partner_requests").select("*").eq("emp_id", st.session_state.user_id).order("requested_date", desc=True).execute()
            
            if requests_result.data and len(requests_result.data) > 0:
                request_df = pd.DataFrame(requests_result.data)
                st.dataframe(request_df[['request_id', 'new_partner_name', 'new_gst_number', 'requested_date', 'status', 'tl_comments']], use_container_width=True, hide_index=True)
            else:
                st.info("No requests yet")
    
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")

# TL Dashboard
def tl_dashboard():
    st.title(f"👨‍💼 TL Dashboard - {st.session_state.user_name}")
    
    try:
        tab1, tab2, tab3 = st.tabs(["📥 Pending Requests", "✅ Approved Requests", "❌ Rejected Requests"])
        
        # Tab 1: Pending Requests
        with tab1:
            st.subheader("Pending Partner Requests")
            pending_result = supabase.table("partner_requests").select("*").eq("status", "Pending").order("requested_date").execute()
            
            if pending_result.data and len(pending_result.data) > 0:
                for req in pending_result.data:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.write(f"**Employee:** {req['emp_name']} ({req['emp_id']})")
                            st.write(f"**New Partner:** {req['new_partner_name']}")
                            st.write(f"**GST Number:** {req['new_gst_number']}")
                        
                        with col2:
                            st.write(f"**Reason:** {req['reason']}")
                            st.write(f"**Requested:** {req['requested_date']}")
                        
                        st.divider()
                        
                        # Review section
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            tl_comment = st.text_area("Add Comments", key=f"comment_{req['request_id']}", height=80)
                        
                        with col2:
                            if st.button("✅ Approve", key=f"approve_{req['request_id']}"):
                                try:
                                    # Update request status
                                    supabase.table("partner_requests").update({
                                        'status': 'Approved',
                                        'tl_comments': tl_comment,
                                        'reviewed_by': st.session_state.user_id,
                                        'reviewed_date': datetime.now().isoformat()
                                    }).eq("request_id", req['request_id']).execute()
                                    
                                    # Add new partner
                                    partner_data = {
                                        'partner_id': f"P{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                        'partner_name': req['new_partner_name'],
                                        'gst_number': req['new_gst_number'],
                                        'emp_id': req['emp_id'],
                                        'status': 'Active',
                                        'created_date': datetime.now().isoformat()
                                    }
                                    supabase.table("partners").insert(partner_data).execute()
                                    
                                    st.success("✅ Request Approved!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                            
                            if st.button("❌ Reject", key=f"reject_{req['request_id']}"):
                                try:
                                    supabase.table("partner_requests").update({
                                        'status': 'Rejected',
                                        'tl_comments': tl_comment,
                                        'reviewed_by': st.session_state.user_id,
                                        'reviewed_date': datetime.now().isoformat()
                                    }).eq("request_id", req['request_id']).execute()
                                    
                                    st.error("❌ Request Rejected!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
            else:
                st.info("✅ All requests are processed!")
        
        # Tab 2: Approved Requests
        with tab2:
            st.subheader("Approved Partner Requests")
            approved_result = supabase.table("partner_requests").select("*").eq("status", "Approved").order("reviewed_date", desc=True).execute()
            
            if approved_result.data and len(approved_result.data) > 0:
                approved_df = pd.DataFrame(approved_result.data)
                st.dataframe(approved_df[['emp_name', 'new_partner_name', 'new_gst_number', 'requested_date', 'reviewed_date']], use_container_width=True, hide_index=True)
            else:
                st.info("No approved requests")
        
        # Tab 3: Rejected Requests
        with tab3:
            st.subheader("Rejected Partner Requests")
            rejected_result = supabase.table("partner_requests").select("*").eq("status", "Rejected").order("reviewed_date", desc=True).execute()
            
            if rejected_result.data and len(rejected_result.data) > 0:
                rejected_df = pd.DataFrame(rejected_result.data)
                st.dataframe(rejected_df[['emp_name', 'new_partner_name', 'new_gst_number', 'requested_date', 'reviewed_date']], use_container_width=True, hide_index=True)
            else:
                st.info("No rejected requests")
    
    except Exception as e:
        st.error(f"Error loading TL dashboard: {str(e)}")

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
