import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Expense Summary", page_icon="💸")
st.title("Expense Sharing Summary")
st.write("Enter a group ID to get a readable summary of its expenses and balances.")

group_id = st.number_input("Group ID", min_value=1, step=1)

if st.button("Generate summary"):
    with st.spinner("Generating the group summary..."):
        try:
            response = httpx.get(
                f"{API_BASE_URL}/groups/{int(group_id)}/summary",
                timeout=45.0,
            )
            if response.is_success:
                result = response.json()
                st.subheader(result["group_name"])
                st.write(result["summary"])

                statistics = result["statistics"]
                st.metric("Total spending", f"₹{statistics['total_spending']}")
                st.metric("Number of expenses", statistics["expense_count"])

                with st.expander("Expense and balance details"):
                    st.write("Largest expenses")
                    st.json(statistics["largest_expenses"])
                    st.write("Member balances")
                    st.json(statistics["member_balances"])
            else:
                try:
                    detail = response.json().get("detail", "The request failed.")
                except ValueError:
                    detail = "The request failed. Please try again."
                st.error(detail)
        except httpx.RequestError:
            st.error(
                "Could not connect to the API. Check that FastAPI is running and "
                "API_BASE_URL is correct."
            )
