"""
FloodGuard AI — Authentication utilities for Streamlit pages.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import httpx
from backend.config import BACKEND_URL

DEMO_CREDENTIALS = {
    "citizen":  {"password": "citizen123",  "role": "citizen",  "name": "Citizen User"},
    "operator": {"password": "operator123", "role": "operator", "name": "Municipal Operator"},
    "admin":    {"password": "admin123",    "role": "admin",    "name": "Administrator"},
}


def login_form(page_title: str = "FloodGuard AI") -> dict | None:
    """
    Show login form. Returns user dict if logged in, None otherwise.
    For demo mode, uses built-in credentials without requiring backend.
    """
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:2rem">
        <div style="font-size:2.5rem">🌊</div>
        <h2 style="color:#e2e8f0;margin:0.5rem 0">FloodGuard AI</h2>
        <div style="color:#94a3b8;font-size:0.9rem">{page_title}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("**Demo Credentials:**")
        st.markdown("""
        <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:0.5rem">
            Citizen: citizen / citizen123 | Operator: operator / operator123 | Admin: admin / admin123
        </div>
        """, unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

    if submitted:
        user = DEMO_CREDENTIALS.get(username)
        if user and password == user["password"]:
            st.session_state["user"] = {
                "username": username,
                "role": user["role"],
                "name": user["name"],
            }
            return st.session_state["user"]
        else:
            st.error("Invalid credentials. Try: citizen/citizen123, operator/operator123, admin/admin123")
    return None


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def require_role(min_role: str = "citizen") -> dict:
    """
    Check authentication. Redirect to login if not authenticated.
    Returns user dict.
    """
    user = get_current_user()
    role_order = {"citizen": 1, "operator": 2, "admin": 3}

    if not user:
        # Auto-login as citizen for demo
        st.session_state["user"] = {
            "username": "demo",
            "role": "operator",  # Default to operator for full demo access
            "name": "Demo Operator",
        }
        return st.session_state["user"]

    return user


def user_sidebar_widget():
    """Display user info in sidebar."""
    user = get_current_user()
    if not user:
        return

    role_colors = {"citizen": "#22c55e", "operator": "#3b82f6", "admin": "#ef4444"}
    color = role_colors.get(user.get("role", "citizen"), "#94a3b8")

    st.sidebar.markdown(f"""
    <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;
                padding:0.6rem 0.8rem;margin-bottom:0.75rem">
        <div style="font-size:0.8rem;color:#e2e8f0;font-weight:600">{user.get('name','')}</div>
        <div>
            <span style="background:{color};color:white;padding:1px 6px;border-radius:4px;
                         font-size:0.7rem;font-weight:600">{user.get('role','').upper()}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("Logout", use_container_width=True):
        del st.session_state["user"]
        st.rerun()
