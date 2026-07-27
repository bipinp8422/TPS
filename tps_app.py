import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import os
import re
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables (used for local development only)
load_dotenv()

# Initialize Supabase credentials
# On Streamlit Cloud: set these in Settings -> Secrets
# Locally: set these in a .env file (make sure .env is in .gitignore!)
SUPABASE_URL = "https://bfxviifbzulbxdfybtro.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmeHZpaWZienVsYnhkZnlidHJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUwMzY2NDksImV4cCI6MjEwMDYxMjY0OX0.aTQJjN4D7WGo8URaoqu3axoloYW6xY46HdmRXx0xDfs"

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

# Columns shown in Excel-style tables, in the same order as TPS_New.xlsx
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

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_type = None
    st.session_state.user_id = None
    st.session_state.user_name = None


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def validate_gst_format(gst_number):
    """
    Validate GST format.
    GST is 15 characters: 2 digits (state code) + 10 chars (PAN) + 1 char (entity) + 1 checksum
    Valid GST format examples: 27AAFCA1234G2Z0
    
    Returns: (is_valid: bool, message: str)
    """
    if not gst_number:
        return False, "GST Number is required"
    
    gst_number = gst_number.strip().upper()
    
    # Check length
    if len(gst_number) != 15:
        return False, f"❌ GST Number must be exactly 15 characters (currently {len(gst_number)})"
    
    # Check if all characters are alphanumeric
    if not gst_number.isalnum():
        return False, "❌ GST Number must contain only letters and numbers (no spaces or special characters)"
    
    # Standard GST format: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric (1-9 or A-Z) + Z + 1 alphanumeric
    # Pattern breakdown:
    # ^[0-9]{2}     - State code (2 digits)
    # [A-Z]{5}      - PAN prefix (5 letters)
    # [0-9]{4}      - PAN sequence (4 digits)
    # [A-Z]{1}      - PAN check digit (1 letter)
    # [1-9A-Z]{1}   - Entity code (1 to 9 or A to Z)
    # [Z]{1}        - Fixed Z
    # [0-9A-Z]{1}$  - Checksum (0-9 or A-Z)
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    
    if re.match(pattern, gst_number):
        return True, "✅ Valid GST format"
    
    return False, "❌ Invalid GST format. Expected 15 alphanumeric characters (e.g., 27AAFCA1234G2Z0)"


def fetch_all_rows(table_name, select="*", eq_filters=None):
    """Fetch every row from a Supabase table, paging past the default
    1000-row response limit (this app's `partners` table can hold
    thousands of counter rows)."""
    rows = []
    page_size = 1000
    start = 0
    while True:
        query = supabase.table(table_name).select(select)
        if eq_filters:
            for col, val in eq_filters.items():
                query = query.eq(col, val)
        result = query.range(start, start + page_size - 1).execute()
        chunk = result.data or []
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        start += page_size
    return rows


@st.cache_data(ttl=120)
def get_all_employees_df():
    data = fetch_all_rows("employees")
    return pd.DataFrame(data)


@st.cache_data(ttl=120)
def get_all_partners_df():
    data = fetch_all_rows("partners")
    return pd.DataFrame(data)


def format_display(df, col_map=COUNTER_DISPLAY_COLS):
    cols = [c for c in col_map if c in df.columns]
    out = df[cols].rename(columns=col_map)
    return out


def to_excel_bytes(sheets: dict):
    """Build an in-memory .xlsx file from {sheet_name: DataFrame}."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]  # Excel sheet name limit
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return buffer.getvalue()


# ---------------------------------------------------------------
# Login
# ---------------------------------------------------------------

def login():
    st.title("🔐 TPS Management System - Login")

    col1, col2, col3 = st.columns([1, 1, 1])

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

    with col3:
        st.subheader("Admin Login")
        admin_id = st.text_input("Admin ID", key="admin_id")
        admin_password = st.text_input("Password", type="password", key="admin_password")

        if st.button("Login as Admin", key="admin_login_btn", use_container_width=True):
            try:
                result = supabase.table("admin_users").select("admin_name").eq("admin_id", admin_id).eq("admin_password", admin_password).execute()

                if result.data and len(result.data) > 0:
                    st.session_state.logged_in = True
                    st.session_state.user_type = 'admin'
                    st.session_state.user_id = admin_id
                    st.session_state.user_name = result.data[0]['admin_name']
                    st.success(f"Welcome, {result.data[0]['admin_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid Admin ID or Password")
            except Exception as e:
                st.error(f"Login error: {str(e)}")


# ---------------------------------------------------------------
# Employee Dashboard
# ---------------------------------------------------------------

def employee_dashboard():
    st.title(f"👤 Welcome, {st.session_state.user_name}!")

    try:
        emp_result = supabase.table("employees").select("*").eq("emp_id", st.session_state.user_id).execute()

        if not (emp_result.data and len(emp_result.data) > 0):
            st.warning("No profile data found for this employee ID.")
            return

        emp_data = emp_result.data[0]

        # ---- Profile card (mirrors the master fields in the Excel sheet) ----
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Employee ID", emp_data.get("emp_id", "-"))
        with col2:
            st.metric("Region", emp_data.get("region") or "-")
        with col3:
            st.metric("Category", emp_data.get("sales_force_category") or "-")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Contact Number:** {emp_data.get('contact_number') or '-'}")
            st.write(f"**Email:** {emp_data.get('email') or '-'}")
        with col2:
            st.write(f"**Field Operations Manager:** {emp_data.get('field_operations_manager') or '-'}")
            st.write(f"**Reporting Manager:** {emp_data.get('reporting_manager') or '-'}")
        with col3:
            st.write(f"**Regional Manager:** {emp_data.get('regional_manager') or '-'}")

        st.divider()

        # ---- All counters/partners assigned to this employee, Excel-style ----
        st.subheader("📋 My CAR Counters")
        partners_data = fetch_all_rows("partners", eq_filters={"emp_id": st.session_state.user_id})

        if partners_data:
            full_partner_df = pd.DataFrame(partners_data)
            display_cols = [c for c in ["partner_name", "gst_number", "city", "state", "status", "created_date"] if c in full_partner_df.columns]
            rename = {
                "partner_name": "CAR Counter Name",
                "gst_number": "CAR GST Number",
                "city": "City",
                "state": "State",
                "status": "Status",
                "created_date": "Created Date",
            }

            dl_col, search_col = st.columns([1, 3])
            with search_col:
                search = st.text_input("🔎 Search my counters (name, GST, city, state)", key="my_counter_search")
            with dl_col:
                st.write("")
                profile_df = pd.DataFrame([{
                    "Employee ID": emp_data.get("emp_id"),
                    "Name": emp_data.get("emp_name"),
                    "Region": emp_data.get("region"),
                    "Category": emp_data.get("sales_force_category"),
                    "Contact Number": emp_data.get("contact_number"),
                    "Email": emp_data.get("email"),
                    "Field Operations Manager": emp_data.get("field_operations_manager"),
                    "Reporting Manager": emp_data.get("reporting_manager"),
                    "Regional Manager": emp_data.get("regional_manager"),
                }])
                excel_bytes = to_excel_bytes({
                    "My Profile": profile_df,
                    "My Counters": full_partner_df[display_cols].rename(columns=rename),
                })
                st.download_button(
                    "⬇️ Download My TPS (Excel)",
                    excel_bytes,
                    file_name=f"TPS_{st.session_state.user_id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            partner_df = full_partner_df
            if search:
                mask = partner_df.apply(
                    lambda r: search.lower() in " ".join(str(v).lower() for v in r.values), axis=1
                )
                partner_df = partner_df[mask]

            st.caption(f"{len(partner_df)} counter(s)")
            st.dataframe(partner_df[display_cols].rename(columns=rename), use_container_width=True, hide_index=True)
        else:
            st.info("No counters assigned yet.")

        st.divider()

        # ---- Request new partner/counter ----
        st.subheader("➕ Request New Counter/Partner")
        
        st.info("📋 **GST Format:** 15 alphanumeric characters (e.g., 27AAFCA1234G2Z0)")
        
        with st.form("new_partner_request"):
            col1, col2 = st.columns(2)

            with col1:
                new_partner_name = st.text_input("New Partner Name")
                new_gst = st.text_input("New GST Number", placeholder="e.g., 27AAFCA1234G2Z0")
                new_city = st.text_input("City")

            with col2:
                new_state = st.text_input("State")
                reason = st.text_area("Reason for New Counter", height=80)

            # Validate GST format before submission
            gst_valid = True
            if new_gst:
                gst_valid, gst_message = validate_gst_format(new_gst)
                if not gst_valid:
                    st.error(gst_message)

            if st.form_submit_button("Submit Request", use_container_width=True):
                if new_partner_name and new_gst and reason:
                    if gst_valid:
                        try:
                            request_data = {
                                'emp_id': st.session_state.user_id,
                                'emp_name': emp_data['emp_name'],
                                'new_partner_name': new_partner_name,
                                'new_gst_number': new_gst.strip().upper(),
                                'new_city': new_city,
                                'new_state': new_state,
                                'reason': reason,
                                'requested_date': datetime.now().isoformat(),
                                'status': 'Pending'
                            }
                            supabase.table("partner_requests").insert(request_data).execute()
                            st.success("✅ Request submitted successfully! Waiting for TL approval.")
                            get_all_partners_df.clear()
                        except Exception as e:
                            st.error(f"Error submitting request: {str(e)}")
                    else:
                        st.error("❌ Please enter a valid GST number before submitting.")
                else:
                    st.error("Please fill all required fields (name, GST, reason)")

        st.divider()

        # ---- Request history ----
        st.subheader("📜 Your Request History")
        requests_result = supabase.table("partner_requests").select("*").eq("emp_id", st.session_state.user_id).order("requested_date", desc=True).execute()

        if requests_result.data and len(requests_result.data) > 0:
            request_df = pd.DataFrame(requests_result.data)
            cols = [c for c in ["request_id", "new_partner_name", "new_gst_number", "new_city", "new_state", "requested_date", "status", "tl_comments"] if c in request_df.columns]
            st.dataframe(request_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No requests yet")

    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")


# ---------------------------------------------------------------
# TL Dashboard
# ---------------------------------------------------------------

def tl_dashboard():
    st.title(f"👨‍💼 TL Dashboard - {st.session_state.user_name}")

    try:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📥 Pending Requests", "✅ Approved Requests", "❌ Rejected Requests",
            "👥 All Employees", "🏬 All Counters (Excel view)"
        ])

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
                            st.write(f"**City/State:** {req.get('new_city') or '-'} / {req.get('new_state') or '-'}")

                        with col2:
                            st.write(f"**Reason:** {req['reason']}")
                            st.write(f"**Requested:** {req['requested_date']}")

                        st.divider()

                        col1, col2 = st.columns(2)

                        with col1:
                            tl_comment = st.text_area("Add Comments", key=f"comment_{req['request_id']}", height=80)

                        with col2:
                            if st.button("✅ Approve", key=f"approve_{req['request_id']}"):
                                try:
                                    supabase.table("partner_requests").update({
                                        'status': 'Approved',
                                        'tl_comments': tl_comment,
                                        'reviewed_by': st.session_state.user_id,
                                        'reviewed_date': datetime.now().isoformat()
                                    }).eq("request_id", req['request_id']).execute()

                                    partner_data = {
                                        'partner_id': f"P{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                        'partner_name': req['new_partner_name'],
                                        'gst_number': req['new_gst_number'],
                                        'city': req.get('new_city'),
                                        'state': req.get('new_state'),
                                        'emp_id': req['emp_id'],
                                        'status': 'Active',
                                        'created_date': datetime.now().isoformat()
                                    }
                                    supabase.table("partners").insert(partner_data).execute()

                                    st.success("✅ Request Approved!")
                                    get_all_partners_df.clear()
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
                cols = [c for c in ["emp_name", "new_partner_name", "new_gst_number", "new_city", "new_state", "requested_date", "reviewed_date"] if c in approved_df.columns]
                st.dataframe(approved_df[cols], use_container_width=True, hide_index=True)
            else:
                st.info("No approved requests")

        # Tab 3: Rejected Requests
        with tab3:
            st.subheader("Rejected Partner Requests")
            rejected_result = supabase.table("partner_requests").select("*").eq("status", "Rejected").order("reviewed_date", desc=True).execute()

            if rejected_result.data and len(rejected_result.data) > 0:
                rejected_df = pd.DataFrame(rejected_result.data)
                cols = [c for c in ["emp_name", "new_partner_name", "new_gst_number", "new_city", "new_state", "requested_date", "reviewed_date"] if c in rejected_df.columns]
                st.dataframe(rejected_df[cols], use_container_width=True, hide_index=True)
            else:
                st.info("No rejected requests")

        # Tab 4: All Employees (master data)
        with tab4:
            st.subheader("Employee Master Data")
            emp_df = get_all_employees_df()
            partners_df = get_all_partners_df()

            if emp_df.empty:
                st.info("No employees found.")
            else:
                counter_counts = (
                    partners_df.groupby("emp_id").size().rename("counter_count")
                    if not partners_df.empty else pd.Series(dtype=int)
                )
                emp_df = emp_df.merge(counter_counts, how="left", left_on="emp_id", right_index=True)
                emp_df["counter_count"] = emp_df["counter_count"].fillna(0).astype(int)

                fcol1, fcol2, fcol3 = st.columns(3)
                with fcol1:
                    regions = ["All"] + sorted([r for r in emp_df["region"].dropna().unique()])
                    region_filter = st.selectbox("Region", regions)
                with fcol2:
                    cats = ["All"] + sorted([c for c in emp_df["sales_force_category"].dropna().unique()])
                    cat_filter = st.selectbox("Category", cats)
                with fcol3:
                    search = st.text_input("🔎 Search (name / ID / manager)")

                filtered = emp_df.copy()
                if region_filter != "All":
                    filtered = filtered[filtered["region"] == region_filter]
                if cat_filter != "All":
                    filtered = filtered[filtered["sales_force_category"] == cat_filter]
                if search:
                    mask = filtered.apply(
                        lambda r: search.lower() in " ".join(str(v).lower() for v in r.values), axis=1
                    )
                    filtered = filtered[mask]

                display_cols = ["emp_id", "emp_name", "region", "sales_force_category", "contact_number",
                                 "email", "field_operations_manager", "reporting_manager", "regional_manager",
                                 "counter_count"]
                display_cols = [c for c in display_cols if c in filtered.columns]
                rename = {
                    "emp_id": "Employee ID", "emp_name": "Name", "region": "Region",
                    "sales_force_category": "Category", "contact_number": "Contact Number",
                    "email": "FOS Email ID", "field_operations_manager": "Field Operations Manager",
                    "reporting_manager": "Reporting Manager", "regional_manager": "Regional Manager",
                    "counter_count": "# Counters",
                }
                st.caption(f"{len(filtered)} employee(s)")
                st.dataframe(filtered[display_cols].rename(columns=rename), use_container_width=True, hide_index=True)

        # Tab 5: All Counters, flat Excel-style view
        with tab5:
            st.subheader("All CAR Counters (matches TPS_New.xlsx layout)")
            emp_df = get_all_employees_df()
            partners_df = get_all_partners_df()

            if partners_df.empty:
                st.info("No counters found.")
            else:
                merge_cols = [c for c in ["emp_id", "region", "sales_force_category", "emp_name",
                                           "contact_number", "email", "field_operations_manager",
                                           "reporting_manager", "regional_manager"] if c in emp_df.columns]
                merged = partners_df.merge(emp_df[merge_cols], on="emp_id", how="left")

                fcol1, fcol2, fcol3, fcol4 = st.columns(4)
                with fcol1:
                    regions = ["All"] + sorted([r for r in merged["region"].dropna().unique()])
                    region_filter = st.selectbox("Region", regions, key="counters_region")
                with fcol2:
                    states = ["All"] + sorted([s for s in merged["state"].dropna().unique()])
                    state_filter = st.selectbox("State", states, key="counters_state")
                with fcol3:
                    cats = ["All"] + sorted([c for c in merged["sales_force_category"].dropna().unique()])
                    cat_filter = st.selectbox("Category", cats, key="counters_cat")
                with fcol4:
                    search = st.text_input("🔎 Search (name, GST, city...)", key="counters_search")

                filtered = merged.copy()
                if region_filter != "All":
                    filtered = filtered[filtered["region"] == region_filter]
                if state_filter != "All":
                    filtered = filtered[filtered["state"] == state_filter]
                if cat_filter != "All":
                    filtered = filtered[filtered["sales_force_category"] == cat_filter]
                if search:
                    mask = filtered.apply(
                        lambda r: search.lower() in " ".join(str(v).lower() for v in r.values), axis=1
                    )
                    filtered = filtered[mask]

                st.caption(f"{len(filtered)} counter(s)")
                display_df = format_display(filtered)
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                st.download_button(
                    "⬇️ Download filtered view as CSV",
                    display_df.to_csv(index=False).encode("utf-8"),
                    file_name="tps_counters_export.csv",
                    mime="text/csv",
                )

    except Exception as e:
        st.error(f"Error loading TL dashboard: {str(e)}")


# ---------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------

def admin_dashboard():
    st.title(f"🛡️ Admin Dashboard - {st.session_state.user_name}")

    try:
        emp_df = get_all_employees_df()
        partners_df = get_all_partners_df()
        requests_result = supabase.table("partner_requests").select("*").execute()
        requests_df = pd.DataFrame(requests_result.data or [])

        # ---- Overview metrics ----
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Employees", len(emp_df))
        with col2:
            st.metric("Total Counters", len(partners_df))
        with col3:
            pending_n = len(requests_df[requests_df["status"] == "Pending"]) if not requests_df.empty else 0
            st.metric("Pending Requests", pending_n)
        with col4:
            approved_n = len(requests_df[requests_df["status"] == "Approved"]) if not requests_df.empty else 0
            st.metric("Approved (TL confirmed)", approved_n)

        st.divider()

        # ---- Upload TPS Excel File ----
        st.subheader("📤 Upload TPS Excel File")
        
        with st.expander("ℹ️ Upload Instructions", expanded=False):
            st.info("""
            **Excel File Requirements:**
            - File must have sheets with employees and counters data
            - Expected columns for employees: emp_id, emp_name, region, sales_force_category, contact_number, email, field_operations_manager, reporting_manager, regional_manager
            - Expected columns for counters: partner_name, gst_number, city, state, emp_id (to link to employee)
            - GST numbers must be in valid format (15 alphanumeric characters, e.g., 27AAFCA1234G2Z0)
            """)
        
        uploaded_file = st.file_uploader("Choose TPS Excel file", type=["xlsx", "xls"], key="tps_upload")
        
        if uploaded_file:
            try:
                # Read Excel file
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                
                st.info(f"📋 Found sheets: {', '.join(sheet_names)}")
                
                # Let admin select which sheets contain employees and counters
                col1, col2 = st.columns(2)
                with col1:
                    emp_sheet = st.selectbox("Sheet with Employee Data", sheet_names, key="emp_sheet_select")
                with col2:
                    counter_sheet = st.selectbox("Sheet with Counter Data", sheet_names, key="counter_sheet_select")
                
                if st.button("Preview Data", key="preview_upload_btn"):
                    emp_df_upload = pd.read_excel(uploaded_file, sheet_name=emp_sheet)
                    counter_df_upload = pd.read_excel(uploaded_file, sheet_name=counter_sheet)
                    
                    st.subheader("👥 Employee Preview")
                    st.dataframe(emp_df_upload.head(), use_container_width=True)
                    
                    st.subheader("🏬 Counter Preview")
                    st.dataframe(counter_df_upload.head(), use_container_width=True)
                
                if st.button("⬆️ Upload & Import Data", key="upload_tps_btn", type="primary"):
                    emp_df_upload = pd.read_excel(uploaded_file, sheet_name=emp_sheet)
                    counter_df_upload = pd.read_excel(uploaded_file, sheet_name=counter_sheet)
                    
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_placeholder = st.empty()
                    
                    try:
                        # Clean column names (remove whitespace)
                        emp_df_upload.columns = emp_df_upload.columns.str.strip()
                        counter_df_upload.columns = counter_df_upload.columns.str.strip()
                        
                        # Upload employees
                        emp_count = 0
                        for idx, row in emp_df_upload.iterrows():
                            emp_data = {
                                "emp_id": str(row.get("emp_id", "")).strip(),
                                "emp_name": str(row.get("emp_name", "")).strip(),
                                "region": str(row.get("region", "")) if pd.notna(row.get("region")) else None,
                                "sales_force_category": str(row.get("sales_force_category", "")) if pd.notna(row.get("sales_force_category")) else None,
                                "contact_number": str(row.get("contact_number", "")) if pd.notna(row.get("contact_number")) else None,
                                "email": str(row.get("email", "")) if pd.notna(row.get("email")) else None,
                                "field_operations_manager": str(row.get("field_operations_manager", "")) if pd.notna(row.get("field_operations_manager")) else None,
                                "reporting_manager": str(row.get("reporting_manager", "")) if pd.notna(row.get("reporting_manager")) else None,
                                "regional_manager": str(row.get("regional_manager", "")) if pd.notna(row.get("regional_manager")) else None,
                            }
                            
                            # Skip if emp_id is empty
                            if emp_data["emp_id"]:
                                try:
                                    supabase.table("employees").insert(emp_data).execute()
                                    emp_count += 1
                                except Exception as e:
                                    # Employee might already exist, try update
                                    try:
                                        supabase.table("employees").update(emp_data).eq("emp_id", emp_data["emp_id"]).execute()
                                        emp_count += 1
                                    except:
                                        pass
                        
                        progress_bar.progress(50)
                        status_placeholder.info(f"✅ Imported {emp_count} employees")
                        
                        # Upload counters
                        counter_count = 0
                        invalid_gst_count = 0
                        
                        for idx, row in counter_df_upload.iterrows():
                            gst = str(row.get("gst_number", "")).strip().upper()
                            
                            # Validate GST
                            gst_valid, _ = validate_gst_format(gst)
                            
                            if not gst_valid:
                                invalid_gst_count += 1
                                st.warning(f"Row {idx+2}: Invalid GST format '{gst}' - Skipping this counter")
                                continue
                            
                            counter_data = {
                                "partner_id": f"P{datetime.now().strftime('%Y%m%d%H%M%S')}{idx}",
                                "partner_name": str(row.get("partner_name", "")).strip(),
                                "gst_number": gst,
                                "city": str(row.get("city", "")) if pd.notna(row.get("city")) else None,
                                "state": str(row.get("state", "")) if pd.notna(row.get("state")) else None,
                                "emp_id": str(row.get("emp_id", "")).strip(),
                                "status": "Active",
                                "created_date": datetime.now().isoformat()
                            }
                            
                            if counter_data["partner_name"] and counter_data["emp_id"]:
                                try:
                                    supabase.table("partners").insert(counter_data).execute()
                                    counter_count += 1
                                except Exception as e:
                                    st.warning(f"Row {idx+2}: Could not insert counter - {str(e)}")
                        
                        progress_bar.progress(100)
                        
                        st.success(f"""
                        ✅ **Upload Complete!**
                        - Employees imported: {emp_count}
                        - Counters imported: {counter_count}
                        - Invalid GST numbers skipped: {invalid_gst_count}
                        """)
                        
                        # Clear cache
                        get_all_employees_df.clear()
                        get_all_partners_df.clear()
                        
                        # Rerun after a delay
                        import time
                        time.sleep(2)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error during upload: {str(e)}")
                        
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")

        st.divider()

        # ---- Compute the Excel-style merged counters view (used below) ----
        if not partners_df.empty:
            merge_cols = [c for c in ["emp_id", "region", "sales_force_category", "emp_name",
                                       "contact_number", "email", "field_operations_manager",
                                       "reporting_manager", "regional_manager"] if c in emp_df.columns]
            merged = partners_df.merge(emp_df[merge_cols], on="emp_id", how="left")
            counters_export = format_display(merged)
        else:
            counters_export = pd.DataFrame()

        # ---- Manage Employees ----
        st.subheader("👤 Manage Employees")
        add_tab, delete_tab = st.tabs(["➕ Add Employee", "🗑️ Delete Employee"])

        with add_tab:
            with st.form("add_employee_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_emp_id = st.text_input("Employee ID *")
                    new_emp_name = st.text_input("Name *")
                    new_contact = st.text_input("Contact Number")
                    new_email = st.text_input("Email")
                    new_category = st.text_input("Sales Force Category")
                with col2:
                    new_region = st.text_input("Region")
                    new_fom = st.text_input("Field Operations Manager")
                    new_rm = st.text_input("Reporting Manager")
                    new_regional_mgr = st.text_input("Regional Manager")

                if st.form_submit_button("Add Employee", use_container_width=True):
                    if new_emp_id and new_emp_name:
                        try:
                            supabase.table("employees").insert({
                                "emp_id": new_emp_id.strip(),
                                "emp_name": new_emp_name.strip(),
                                "contact_number": new_contact or None,
                                "email": new_email or None,
                                "sales_force_category": new_category or None,
                                "region": new_region or None,
                                "field_operations_manager": new_fom or None,
                                "reporting_manager": new_rm or None,
                                "regional_manager": new_regional_mgr or None,
                            }).execute()
                            st.success(f"✅ Employee {new_emp_id} added.")
                            get_all_employees_df.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding employee: {str(e)}")
                    else:
                        st.error("Employee ID and Name are required")

        with delete_tab:
            if emp_df.empty:
                st.info("No employees to delete.")
            else:
                options = (emp_df["emp_id"] + " - " + emp_df["emp_name"].fillna("")).tolist()
                choice = st.selectbox("Select employee to delete", options, key="delete_emp_select")
                emp_id_to_delete = choice.split(" - ")[0] if choice else None

                if emp_id_to_delete:
                    counter_count = len(partners_df[partners_df["emp_id"] == emp_id_to_delete]) if not partners_df.empty else 0
                    st.warning(
                        f"Deleting **{choice}** will also permanently delete their "
                        f"**{counter_count} counter(s)** and any partner request history for this employee."
                    )
                    confirm = st.checkbox("I understand this cannot be undone", key="delete_emp_confirm")
                    if st.button("🗑️ Delete Employee", disabled=not confirm, use_container_width=True):
                        try:
                            supabase.table("partners").delete().eq("emp_id", emp_id_to_delete).execute()
                            supabase.table("partner_requests").delete().eq("emp_id", emp_id_to_delete).execute()
                            supabase.table("employees").delete().eq("emp_id", emp_id_to_delete).execute()
                            st.success(f"✅ Employee {emp_id_to_delete} and related data deleted.")
                            get_all_employees_df.clear()
                            get_all_partners_df.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting employee: {str(e)}")

        st.divider()

        # ---- Full data view, Excel-style, filterable ----
        st.subheader("📊 All Counters (Excel view)")
        if counters_export.empty:
            st.info("No counters found.")
        else:
            fcol1, fcol2, fcol3, fcol4 = st.columns(4)
            with fcol1:
                regions = ["All"] + sorted([r for r in counters_export["Region"].dropna().unique()])
                region_filter = st.selectbox("Region", regions, key="admin_region")
            with fcol2:
                states = ["All"] + sorted([s for s in counters_export["State"].dropna().unique()])
                state_filter = st.selectbox("State", states, key="admin_state")
            with fcol3:
                cats = ["All"] + sorted([c for c in counters_export["Sales Force Category"].dropna().unique()])
                cat_filter = st.selectbox("Category", cats, key="admin_cat")
            with fcol4:
                search = st.text_input("🔎 Search", key="admin_search")

            filtered = counters_export.copy()
            if region_filter != "All":
                filtered = filtered[filtered["Region"] == region_filter]
            if state_filter != "All":
                filtered = filtered[filtered["State"] == state_filter]
            if cat_filter != "All":
                filtered = filtered[filtered["Sales Force Category"] == cat_filter]
            if search:
                mask = filtered.apply(
                    lambda r: search.lower() in " ".join(str(v).lower() for v in r.values), axis=1
                )
                filtered = filtered[mask]

            st.caption(f"{len(filtered)} counter(s)")
            st.dataframe(filtered, use_container_width=True, hide_index=True)

            filtered_excel_bytes = to_excel_bytes({"Filtered Counters": filtered})
            st.download_button(
                "⬇️ Download this view (Excel)",
                filtered_excel_bytes,
                file_name=f"TPS_Counters_Filtered_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        st.error(f"Error loading Admin dashboard: {str(e)}")


# ---------------------------------------------------------------
# Main app
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
        elif st.session_state.user_type == 'tl':
            tl_dashboard()
        elif st.session_state.user_type == 'admin':
            admin_dashboard()

if __name__ == "__main__":
    main()
