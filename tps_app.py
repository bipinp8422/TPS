import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import os
import re
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

# Load environment variables (used for local development only)
load_dotenv()

# Initialize Supabase credentials
# On Streamlit Cloud: set these in Settings -> Secrets
# Locally: set these in a .env file (make sure .env is in .gitignore!)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bfxviifbzulbxdfybtro.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmeHZpaWZienVsYnhkZnlidHJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUwMzY2NDksImV4cCI6MjEwMDYxMjY0OX0.aTQJjN4D7WGo8URaoqu3axoloYW6xY46HdmRXx0xDfs")

# UltraMsg WhatsApp API Credentials
ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID", "instance186843")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN", "ckaglr8uezzfvg49")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Supabase credentials not found! Please set SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets (or a local .env file)")
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

# Display columns in Excel-style tables
COUNTER_DISPLAY_COLS = {
    "region": "Region",
    "sales_force_category": "Sales Force Category",
    "emp_id": "Employee ID",
    "emp_name": "Name",
    "contact_number": "Contact Number",
    "email": "FOS Email ID",
    "field_operations_manager": "Field Operations Manager",
    "reporting_manager": "Reporting Manager",
    "regional_manager": "Regional Manager",
    "partner_name": "CAR Counter Name",
    "gst_number": "CAR GST Number",
    "city": "City",
    "state": "State",
}

REQUEST_STATUS_DISPLAY = {
    "pending": "⏳ Pending",
    "approved": "✅ Approved",
    "rejected": "❌ Rejected",
}

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_type = None
    st.session_state.user_id = None
    st.session_state.user_name = None


# ---------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------

def send_whatsapp_notification(to_number: str, message: str) -> dict:
    """Send a WhatsApp text message via UltraMsg API."""
    if not ULTRAMSG_INSTANCE_ID or not ULTRAMSG_TOKEN:
        st.warning("⚠️ UltraMsg credentials not configured. WhatsApp notification skipped.")
        return {"sent": False, "error": "Missing credentials"}

    to_number = str(to_number).strip().replace("+", "").replace(" ", "").replace("-", "")
    
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": to_number,
        "body": message,
        "priority": 10,
    }
    
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f"⚠️ WhatsApp send failed: {e}")
        return {"sent": False, "error": str(e)}


def get_tl_for_employee(emp_id: str):
    """Find the TL responsible for this employee's region."""
    try:
        emp_res = supabase.table("employees").select("region, emp_name").eq("emp_id", emp_id).execute()
        if not emp_res.data:
            return None
        emp_region = emp_res.data[0].get("region")
        emp_name = emp_res.data[0].get("emp_name", emp_id)
        
        if not emp_region:
            return None

        for col in ("region", "Region", "REGION"):
            try:
                tl_res = supabase.table("tl_users").select("tl_id, tl_name, whatsapp_number").eq(col, emp_region).execute()
                if tl_res.data and len(tl_res.data) > 0:
                    tl = tl_res.data[0]
                    tl["employee_region"] = emp_region
                    tl["employee_name"] = emp_name
                    return tl
            except Exception as e:
                if "does not exist" in str(e) or "42703" in str(e):
                    continue
                raise
        return None
    except Exception as e:
        st.warning(f"Could not find TL for notification: {e}")
        return None


def validate_gst_format(gst_number):
    """Validate GST format."""
    if not gst_number:
        return False, "GST Number is required"
    
    gst_number = gst_number.strip().upper()
    
    if len(gst_number) != 15:
        return False, f"❌ GST Number must be exactly 15 characters (currently {len(gst_number)})"
    
    if not gst_number.isalnum():
        return False, "❌ GST Number must contain only letters and numbers"
    
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    
    if re.match(pattern, gst_number):
        return True, "✅ Valid GST format"
    
    return False, "❌ Invalid GST format. Expected format: 27AAFCA1234G2Z0"


def fetch_all_rows(table_name, select="*", eq_filters=None):
    """Fetch every row from a Supabase table, paging past the 1000-row limit."""
    rows = []
    page_size = 1000
    start = 0
    while True:
        query = supabase.table(table_name).select(select)
        if eq_filters:
            for col, val in eq_filters.items():
                query = query.eq(col, val)
        result = query.range(start, start + page_size - 1).execute()
        rows.extend(result.data)
        if len(result.data) < page_size:
            break
        start += page_size
    return rows


@st.cache_data(ttl=60)
def get_all_employees_df():
    """Fetch all employees as a DataFrame."""
    try:
        employees = fetch_all_rows("employees")
        return pd.DataFrame(employees)
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_all_partners_df():
    """Fetch all partners (counters) as a DataFrame."""
    try:
        partners = fetch_all_rows("partners")
        return pd.DataFrame(partners)
    except Exception as e:
        st.error(f"Error fetching partners: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_pending_requests_df():
    """Fetch all pending partner requests as a DataFrame."""
    try:
        requests_data = fetch_all_rows("partner_requests", eq_filters={"status": "pending"})
        return pd.DataFrame(requests_data)
    except Exception as e:
        st.error(f"Error fetching pending requests: {e}")
        return pd.DataFrame()


def format_display(df):
    """Format DataFrame for display using COUNTER_DISPLAY_COLS."""
    if df.empty:
        return df
    
    cols_to_display = [c for c in COUNTER_DISPLAY_COLS.keys() if c in df.columns]
    display_df = df[cols_to_display].copy()
    display_df.columns = [COUNTER_DISPLAY_COLS[c] for c in cols_to_display]
    return display_df


def to_excel_bytes(sheets_dict):
    """Convert dictionary of DataFrames to Excel bytes."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in sheets_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


# ---------------------------------------------------------------
# Login
# ---------------------------------------------------------------

def login():
    """Login page with role selection."""
    st.title("🔐 TPS Management System Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Select Your Role")
        
        role = st.radio("Login as:", ["Employee", "Team Lead (TL)", "Admin"], horizontal=True)
        
        user_id = st.text_input("User ID / Employee ID")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True, type="primary"):
            if not user_id or not password:
                st.error("❌ Please enter both User ID and Password")
            else:
                # Validate credentials (in production, query database)
                try:
                    # Try to find user in appropriate table
                    if role == "Employee":
                        result = supabase.table("employees").select("emp_id, emp_name").eq("emp_id", user_id).execute()
                        table_name = "employees"
                    elif role == "Team Lead (TL)":
                        result = supabase.table("tl_users").select("tl_id, tl_name").eq("tl_id", user_id).execute()
                        table_name = "tl_users"
                    else:  # Admin
                        result = supabase.table("admins").select("admin_id, admin_name").eq("admin_id", user_id).execute()
                        table_name = "admins"
                    
                    if result.data and len(result.data) > 0:
                        # In production, verify password against hash
                        st.session_state.logged_in = True
                        st.session_state.user_type = role.lower().replace(" (tl)", "").replace(" ", "_")
                        st.session_state.user_id = user_id
                        
                        if role == "Employee":
                            st.session_state.user_name = result.data[0].get("emp_name", user_id)
                        elif role == "Team Lead (TL)":
                            st.session_state.user_name = result.data[0].get("tl_name", user_id)
                        else:
                            st.session_state.user_name = result.data[0].get("admin_name", user_id)
                        
                        st.success(f"✅ Welcome, {st.session_state.user_name}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid User ID")
                except Exception as e:
                    st.error(f"❌ Login error: {str(e)}")


# ---------------------------------------------------------------
# Employee Dashboard
# ---------------------------------------------------------------

def employee_dashboard():
    """Employee dashboard for submitting partner/counter requests."""
    st.title(f"👤 Welcome, {st.session_state.user_name}!")
    st.subheader("Partner/Counter Request Management")
    
    try:
        emp_df = get_all_employees_df()
        emp_info = emp_df[emp_df["emp_id"] == st.session_state.user_id].to_dict('records')
        
        if emp_info:
            emp_info = emp_info[0]
            st.info(f"**Region:** {emp_info.get('region', 'N/A')} | **Category:** {emp_info.get('sales_force_category', 'N/A')}")
        
        st.divider()
        
        # Submit new request
        st.subheader("📝 Submit New Counter/Partner Request")
        
        with st.form("partner_request_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                partner_name = st.text_input("Counter/Partner Name *")
                gst_number = st.text_input("GST Number *")
                city = st.text_input("City")
            
            with col2:
                state = st.text_input("State")
                contact_person = st.text_input("Contact Person Name")
                contact_phone = st.text_input("Contact Phone")
            
            remarks = st.text_area("Remarks (optional)")
            
            submit = st.form_submit_button("Submit Request", use_container_width=True, type="primary")
            
            if submit:
                if not partner_name or not gst_number:
                    st.error("❌ Partner Name and GST Number are required")
                else:
                    is_valid, msg = validate_gst_format(gst_number)
                    if not is_valid:
                        st.error(msg)
                    else:
                        try:
                            request_data = {
                                "emp_id": st.session_state.user_id,
                                "partner_name": partner_name.strip(),
                                "gst_number": gst_number.strip().upper(),
                                "city": city or None,
                                "state": state or None,
                                "contact_person": contact_person or None,
                                "contact_phone": contact_phone or None,
                                "remarks": remarks or None,
                                "status": "pending",
                                "created_date": datetime.now().isoformat(),
                                "updated_date": datetime.now().isoformat(),
                            }
                            
                            supabase.table("partner_requests").insert(request_data).execute()
                            
                            # Get TL info for notification
                            tl_info = get_tl_for_employee(st.session_state.user_id)
                            if tl_info and tl_info.get("whatsapp_number"):
                                msg = f"New Counter Request from {emp_info.get('emp_name', 'Employee')}: {partner_name} (GST: {gst_number})"
                                send_whatsapp_notification(tl_info["whatsapp_number"], msg)
                            
                            st.success("✅ Request submitted successfully! Your TL will review it shortly.")
                            get_pending_requests_df.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error submitting request: {str(e)}")
        
        st.divider()
        
        # View my requests
        st.subheader("📋 My Requests")
        
        try:
            my_requests = fetch_all_rows("partner_requests", eq_filters={"emp_id": st.session_state.user_id})
            if my_requests:
                requests_df = pd.DataFrame(my_requests)
                requests_df["Status"] = requests_df["status"].map(REQUEST_STATUS_DISPLAY)
                requests_df["Created"] = pd.to_datetime(requests_df["created_date"]).dt.strftime("%Y-%m-%d %H:%M")
                requests_df["Updated"] = pd.to_datetime(requests_df["updated_date"]).dt.strftime("%Y-%m-%d %H:%M")
                
                display_cols = ["partner_name", "gst_number", "city", "state", "Status", "Created", "Updated"]
                if all(col in requests_df.columns for col in display_cols):
                    st.dataframe(
                        requests_df[display_cols].rename(columns={
                            "partner_name": "Counter Name",
                            "gst_number": "GST",
                            "city": "City",
                            "state": "State"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.dataframe(requests_df, use_container_width=True, hide_index=True)
            else:
                st.info("No requests yet. Submit your first request above!")
        except Exception as e:
            st.warning(f"Could not load your requests: {e}")
    
    except Exception as e:
        st.error(f"Error loading Employee dashboard: {str(e)}")


# ---------------------------------------------------------------
# Team Lead (TL) Dashboard
# ---------------------------------------------------------------

def tl_dashboard():
    """TL dashboard for reviewing and approving partner requests."""
    st.title(f"👔 Team Lead Dashboard - {st.session_state.user_name}")
    st.subheader("Review Pending Partner Requests from Your Team")
    
    try:
        # Get TL's region
        tl_df = st.session_state.get('tl_df')
        if not tl_df:
            tl_res = supabase.table("tl_users").select("region, tl_name").eq("tl_id", st.session_state.user_id).execute()
            if tl_res.data:
                tl_region = tl_res.data[0].get("region")
                st.session_state['tl_df'] = tl_res.data[0]
            else:
                st.error("Could not find TL information")
                return
        else:
            tl_region = tl_df.get("region")
        
        # Get employees in TL's region
        emp_df = get_all_employees_df()
        region_employees = emp_df[emp_df["region"] == tl_region]
        emp_ids_in_region = region_employees["emp_id"].tolist()
        
        st.info(f"**Region:** {tl_region} | **Employees in region:** {len(emp_ids_in_region)}")
        st.divider()
        
        # Fetch pending requests from employees in this region
        all_pending = fetch_all_rows("partner_requests", eq_filters={"status": "pending"})
        my_pending = [r for r in all_pending if r.get("emp_id") in emp_ids_in_region]
        
        if not my_pending:
            st.success("✅ No pending requests! All caught up.")
            return
        
        st.subheader(f"⏳ Pending Requests ({len(my_pending)})")
        
        # Display pending requests
        for idx, req in enumerate(my_pending):
            with st.expander(f"📝 {req.get('partner_name')} - {req.get('emp_id')} (GST: {req.get('gst_number')})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Employee ID:** {req.get('emp_id')}")
                    emp = region_employees[region_employees["emp_id"] == req.get('emp_id')]
                    if not emp.empty:
                        st.write(f"**Employee Name:** {emp.iloc[0].get('emp_name')}")
                    st.write(f"**Counter Name:** {req.get('partner_name')}")
                    st.write(f"**GST Number:** {req.get('gst_number')}")
                
                with col2:
                    st.write(f"**City:** {req.get('city', 'N/A')}")
                    st.write(f"**State:** {req.get('state', 'N/A')}")
                    st.write(f"**Contact Person:** {req.get('contact_person', 'N/A')}")
                    st.write(f"**Phone:** {req.get('contact_phone', 'N/A')}")
                
                if req.get('remarks'):
                    st.write(f"**Remarks:** {req.get('remarks')}")
                
                st.write(f"**Submitted:** {pd.to_datetime(req.get('created_date')).strftime('%Y-%m-%d %H:%M')}")
                
                # Action buttons
                acol1, acol2, acol3 = st.columns(3)
                
                with acol1:
                    if st.button("✅ Approve", key=f"approve_{idx}_{req.get('id', '')}"):
                        try:
                            supabase.table("partner_requests").update({
                                "status": "approved",
                                "updated_date": datetime.now().isoformat(),
                                "approved_by": st.session_state.user_id,
                                "approved_date": datetime.now().isoformat(),
                            }).eq("id", req.get("id")).execute()
                            
                            st.success(f"✅ Request approved!")
                            get_pending_requests_df.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error approving request: {e}")
                
                with acol2:
                    if st.button("❌ Reject", key=f"reject_{idx}_{req.get('id', '')}"):
                        st.session_state[f"reject_{req.get('id')}"] = True
                
                with acol3:
                    st.write("")  # Spacer
                
                # Rejection reason
                if st.session_state.get(f"reject_{req.get('id')}"):
                    rejection_reason = st.text_area(f"Reason for rejection:", key=f"reject_reason_{req.get('id')}")
                    if st.button("Submit Rejection", key=f"submit_reject_{req.get('id')}"):
                        try:
                            supabase.table("partner_requests").update({
                                "status": "rejected",
                                "updated_date": datetime.now().isoformat(),
                                "rejected_by": st.session_state.user_id,
                                "rejected_date": datetime.now().isoformat(),
                                "rejection_reason": rejection_reason or None,
                            }).eq("id", req.get("id")).execute()
                            
                            st.success("❌ Request rejected.")
                            st.session_state[f"reject_{req.get('id')}"] = False
                            get_pending_requests_df.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error rejecting request: {e}")
    
    except Exception as e:
        st.error(f"Error loading TL dashboard: {str(e)}")


# ---------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------

def admin_dashboard():
    """Admin dashboard for system management and viewing all requests."""
    st.title(f"🔧 Admin Dashboard - {st.session_state.user_name}")
    
    try:
        admin_tabs = st.tabs([
            "📊 Dashboard",
            "⏳ Pending Requests (TL Bucket)",
            "📋 All Requests",
            "👥 Manage Users",
            "📤 Bulk Upload"
        ])
        
        # ---- Tab 1: Dashboard ----
        with admin_tabs[0]:
            st.subheader("System Overview")
            
            emp_df = get_all_employees_df()
            partners_df = get_all_partners_df()
            pending_df = get_pending_requests_df()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Employees", len(emp_df))
            with col2:
                st.metric("Total Counters", len(partners_df))
            with col3:
                st.metric("Pending Requests", len(pending_df))
            with col4:
                try:
                    approved = len(fetch_all_rows("partner_requests", eq_filters={"status": "approved"}))
                    st.metric("Approved Requests", approved)
                except:
                    st.metric("Approved Requests", "N/A")
            
            st.divider()
            
            # Regional breakdown
            st.subheader("Regional Breakdown")
            if not emp_df.empty:
                regional = emp_df["region"].value_counts()
                st.bar_chart(regional)
        
        # ---- Tab 2: Pending Requests (TL Bucket) ----
        with admin_tabs[1]:
            st.subheader("⏳ Pending Requests - TL Review Queue")
            st.write("View all pending requests waiting for Team Lead approval")
            
            pending_requests = fetch_all_rows("partner_requests", eq_filters={"status": "pending"})
            
            if not pending_requests:
                st.info("✅ No pending requests!")
            else:
                pending_df = pd.DataFrame(pending_requests)
                
                # Merge with employee info
                emp_df = get_all_employees_df()
                if not emp_df.empty:
                    pending_df = pending_df.merge(
                        emp_df[["emp_id", "emp_name", "region"]],
                        on="emp_id",
                        how="left"
                    )
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Pending", len(pending_df))
                with col2:
                    if "region" in pending_df.columns:
                        st.metric("Regions", pending_df["region"].nunique())
                with col3:
                    st.metric("Employees", pending_df["emp_id"].nunique())
                
                st.divider()
                
                # Filters
                fcol1, fcol2, fcol3 = st.columns(3)
                
                with fcol1:
                    if "region" in pending_df.columns:
                        regions = ["All"] + sorted(pending_df["region"].dropna().unique().tolist())
                        region_filter = st.selectbox("Filter by Region", regions, key="pending_region")
                    else:
                        region_filter = "All"
                
                with fcol2:
                    sort_by = st.selectbox("Sort by", ["Oldest First", "Newest First"], key="pending_sort")
                
                with fcol3:
                    search_term = st.text_input("Search (Counter/Employee)", key="pending_search")
                
                # Apply filters
                filtered_pending = pending_df.copy()
                
                if region_filter != "All" and "region" in filtered_pending.columns:
                    filtered_pending = filtered_pending[filtered_pending["region"] == region_filter]
                
                if search_term:
                    mask = (
                        filtered_pending["partner_name"].str.contains(search_term, case=False, na=False) |
                        filtered_pending["emp_id"].str.contains(search_term, case=False, na=False)
                    )
                    filtered_pending = filtered_pending[mask]
                
                if sort_by == "Newest First":
                    filtered_pending = filtered_pending.sort_values("created_date", ascending=False)
                else:
                    filtered_pending = filtered_pending.sort_values("created_date", ascending=True)
                
                # Display requests with details
                st.subheader(f"Showing {len(filtered_pending)} pending request(s)")
                
                for idx, row in filtered_pending.iterrows():
                    with st.expander(f"📝 {row.get('partner_name')} | {row.get('emp_id')} | {row.get('region', 'N/A')}"):
                        col1, col2, col3 = st.columns([2, 2, 2])
                        
                        with col1:
                            st.write("**Employee Details**")
                            st.write(f"ID: {row.get('emp_id')}")
                            st.write(f"Name: {row.get('emp_name', 'N/A')}")
                            st.write(f"Region: {row.get('region', 'N/A')}")
                        
                        with col2:
                            st.write("**Counter/Partner Details**")
                            st.write(f"Name: {row.get('partner_name')}")
                            st.write(f"GST: {row.get('gst_number')}")
                            st.write(f"City: {row.get('city', 'N/A')}")
                            st.write(f"State: {row.get('state', 'N/A')}")
                        
                        with col3:
                            st.write("**Contact Details**")
                            st.write(f"Contact: {row.get('contact_person', 'N/A')}")
                            st.write(f"Phone: {row.get('contact_phone', 'N/A')}")
                            st.write(f"Submitted: {pd.to_datetime(row.get('created_date')).strftime('%Y-%m-%d %H:%M')}")
                        
                        if row.get('remarks'):
                            st.write(f"**Remarks:** {row.get('remarks')}")
                        
                        # Admin actions
                        st.divider()
                        st.write("**Admin Actions**")
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            if st.button("ℹ️ View Full Details", key=f"view_details_{idx}"):
                                st.json(dict(row))
                        
                        with action_col2:
                            if st.button("👁️ Track Status", key=f"track_status_{idx}"):
                                st.info(f"Status: Pending | Assigned to TL in {row.get('region', 'N/A')}")
                        
                        with action_col3:
                            if st.button("📧 Notify TL", key=f"notify_tl_{idx}"):
                                # Get TL info
                                tl_info = get_tl_for_employee(row.get('emp_id'))
                                if tl_info and tl_info.get("whatsapp_number"):
                                    msg = f"Reminder: Pending counter approval - {row.get('partner_name')} from {row.get('emp_name', 'Employee')}"
                                    result = send_whatsapp_notification(tl_info["whatsapp_number"], msg)
                                    if result.get("sent"):
                                        st.success("✅ TL notified via WhatsApp")
                                    else:
                                        st.warning(f"⚠️ Could not send notification: {result.get('error')}")
                                else:
                                    st.warning("⚠️ TL WhatsApp number not found")
        
        # ---- Tab 3: All Requests ----
        with admin_tabs[2]:
            st.subheader("📋 All Partner Requests")
            
            all_requests = fetch_all_rows("partner_requests")
            
            if not all_requests:
                st.info("No requests found.")
            else:
                requests_df = pd.DataFrame(all_requests)
                
                # Add status display
                requests_df["Status"] = requests_df["status"].map(REQUEST_STATUS_DISPLAY)
                requests_df["Created"] = pd.to_datetime(requests_df["created_date"]).dt.strftime("%Y-%m-%d")
                
                # Merge with employee info
                emp_df = get_all_employees_df()
                if not emp_df.empty:
                    requests_df = requests_df.merge(
                        emp_df[["emp_id", "emp_name", "region"]],
                        on="emp_id",
                        how="left"
                    )
                
                # Filters
                fcol1, fcol2, fcol3 = st.columns(3)
                
                with fcol1:
                    statuses = ["All"] + [s for s in requests_df["status"].unique() if pd.notna(s)]
                    status_filter = st.selectbox("Filter by Status", statuses, key="all_status")
                
                with fcol2:
                    if "region" in requests_df.columns:
                        regions = ["All"] + sorted([r for r in requests_df["region"].unique() if pd.notna(r)])
                        region_filter = st.selectbox("Filter by Region", regions, key="all_region")
                    else:
                        region_filter = "All"
                
                with fcol3:
                    search = st.text_input("Search", key="all_search")
                
                # Apply filters
                filtered = requests_df.copy()
                
                if status_filter != "All":
                    filtered = filtered[filtered["status"] == status_filter]
                
                if region_filter != "All" and "region" in filtered.columns:
                    filtered = filtered[filtered["region"] == region_filter]
                
                if search:
                    mask = (
                        filtered["partner_name"].str.contains(search, case=False, na=False) |
                        filtered["emp_id"].str.contains(search, case=False, na=False)
                    )
                    filtered = filtered[mask]
                
                # Display
                display_cols = ["partner_name", "gst_number", "emp_id", "emp_name", "region", "Status", "Created"]
                display_cols = [c for c in display_cols if c in filtered.columns]
                
                st.dataframe(
                    filtered[display_cols].rename(columns={
                        "partner_name": "Counter Name",
                        "emp_id": "Emp ID",
                        "emp_name": "Employee",
                        "region": "Region"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Export option
                export_bytes = to_excel_bytes({"All Requests": filtered[display_cols]})
                st.download_button(
                    "⬇️ Download (Excel)",
                    export_bytes,
                    file_name=f"Partner_Requests_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="export_all_requests"
                )
        
        # ---- Tab 4: Manage Users ----
        with admin_tabs[3]:
            st.subheader("👥 User Management")
            
            user_tabs = st.tabs(["Add Employee", "Add Team Lead", "View All Users"])
            
            # Add Employee
            with user_tabs[0]:
                st.write("Add a new employee to the system")
                with st.form("add_emp_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        emp_id = st.text_input("Employee ID *")
                        emp_name = st.text_input("Name *")
                        contact = st.text_input("Contact Number")
                        email = st.text_input("Email")
                    with col2:
                        region = st.text_input("Region *")
                        category = st.text_input("Sales Force Category")
                        fom = st.text_input("Field Operations Manager")
                        rm = st.text_input("Reporting Manager")
                    
                    if st.form_submit_button("Add Employee", use_container_width=True, type="primary"):
                        if emp_id and emp_name and region:
                            try:
                                supabase.table("employees").insert({
                                    "emp_id": emp_id.strip(),
                                    "emp_name": emp_name.strip(),
                                    "region": region.strip(),
                                    "contact_number": contact or None,
                                    "email": email or None,
                                    "sales_force_category": category or None,
                                    "field_operations_manager": fom or None,
                                    "reporting_manager": rm or None,
                                }).execute()
                                st.success(f"✅ Employee {emp_id} added!")
                                get_all_employees_df.clear()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.error("Employee ID, Name, and Region are required")
            
            # Add Team Lead
            with user_tabs[1]:
                st.write("Add a new team lead to the system")
                with st.form("add_tl_form", clear_on_submit=True):
                    tl_id = st.text_input("Team Lead ID *")
                    tl_name = st.text_input("Name *")
                    region = st.text_input("Region/Area *")
                    whatsapp = st.text_input("WhatsApp Number")
                    email = st.text_input("Email")
                    
                    if st.form_submit_button("Add Team Lead", use_container_width=True, type="primary"):
                        if tl_id and tl_name and region:
                            try:
                                supabase.table("tl_users").insert({
                                    "tl_id": tl_id.strip(),
                                    "tl_name": tl_name.strip(),
                                    "region": region.strip(),
                                    "whatsapp_number": whatsapp or None,
                                    "email": email or None,
                                }).execute()
                                st.success(f"✅ Team Lead {tl_id} added!")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.error("TL ID, Name, and Region are required")
            
            # View All Users
            with user_tabs[2]:
                st.write("View all employees and team leads")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Employees")
                    emp_df = get_all_employees_df()
                    if not emp_df.empty:
                        st.dataframe(
                            emp_df[["emp_id", "emp_name", "region", "contact_number"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No employees")
                
                with col2:
                    st.subheader("Team Leads")
                    try:
                        tl_data = fetch_all_rows("tl_users")
                        if tl_data:
                            tl_df = pd.DataFrame(tl_data)
                            st.dataframe(
                                tl_df[["tl_id", "tl_name", "region"]],
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("No team leads")
                    except Exception as e:
                        st.warning(f"Could not load TLs: {e}")
        
        # ---- Tab 5: Bulk Upload ----
        with admin_tabs[4]:
            st.subheader("📤 Bulk Data Upload")
            st.write("Upload Excel file with employee and counter data")
            
            uploaded_file = st.file_uploader("Choose Excel file (TPS_New.xlsx format)", type=['xlsx'])
            
            if uploaded_file:
                try:
                    excel_file = pd.ExcelFile(uploaded_file)
                    st.info(f"Sheets found: {', '.join(excel_file.sheet_names)}")
                    
                    emp_count = 0
                    counter_count = 0
                    invalid_gst_count = 0
                    
                    progress_bar = st.progress(0)
                    
                    # Process employees sheet
                    if 'employees' in excel_file.sheet_names or 'Employees' in excel_file.sheet_names:
                        sheet_name = 'employees' if 'employees' in excel_file.sheet_names else 'Employees'
                        emp_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                        
                        for idx, row in emp_sheet.iterrows():
                            if pd.notna(row.get('emp_id')) and pd.notna(row.get('emp_name')):
                                try:
                                    supabase.table("employees").insert({
                                        "emp_id": str(row.get('emp_id')).strip(),
                                        "emp_name": str(row.get('emp_name')).strip(),
                                        "region": row.get('region'),
                                        "contact_number": row.get('contact_number'),
                                        "email": row.get('email'),
                                        "sales_force_category": row.get('sales_force_category'),
                                        "field_operations_manager": row.get('field_operations_manager'),
                                        "reporting_manager": row.get('reporting_manager'),
                                        "regional_manager": row.get('regional_manager'),
                                    }).execute()
                                    emp_count += 1
                                except:
                                    pass
                            progress_bar.progress((idx + 1) / len(emp_sheet))
                    
                    # Process counters/partners sheet
                    if 'partners' in excel_file.sheet_names or 'Partners' in excel_file.sheet_names:
                        sheet_name = 'partners' if 'partners' in excel_file.sheet_names else 'Partners'
                        counter_sheet = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                        
                        for idx, row in counter_sheet.iterrows():
                            if pd.notna(row.get('partner_name')) and pd.notna(row.get('gst_number')):
                                is_valid, _ = validate_gst_format(str(row.get('gst_number')))
                                if is_valid:
                                    try:
                                        supabase.table("partners").insert({
                                            "emp_id": str(row.get('emp_id', '')).strip(),
                                            "partner_name": row.get('partner_name'),
                                            "gst_number": str(row.get('gst_number')).strip().upper(),
                                            "city": row.get('city'),
                                            "state": row.get('state'),
                                            "created_date": datetime.now().isoformat(),
                                        }).execute()
                                        counter_count += 1
                                    except:
                                        pass
                                else:
                                    invalid_gst_count += 1
                    
                    progress_bar.progress(100)
                    st.success(f"✅ Upload Complete!\n- Employees: {emp_count}\n- Counters: {counter_count}\n- Invalid GST: {invalid_gst_count}")
                    get_all_employees_df.clear()
                    get_all_partners_df.clear()
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    except Exception as e:
        st.error(f"Error loading Admin dashboard: {str(e)}")


# ---------------------------------------------------------------
# Main App
# ---------------------------------------------------------------

def main():
    if not st.session_state.logged_in:
        login()
    else:
        with st.sidebar:
            st.title("Navigation")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_type = None
                st.rerun()
        
        if st.session_state.user_type == 'employee':
            employee_dashboard()
        elif st.session_state.user_type == 'team_lead':
            tl_dashboard()
        elif st.session_state.user_type == 'admin':
            admin_dashboard()
        else:
            st.error("Unknown user type")


if __name__ == "__main__":
    main()
