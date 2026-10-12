import os
from decimal import Decimal
from typing import Optional

import httpx
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def get_api_base_url() -> str:
    """Read the backend URL from the environment or Streamlit Cloud secrets."""
    try:
        cloud_url = st.secrets.get("API_BASE_URL")
    except StreamlitSecretNotFoundError:
        cloud_url = None

    configured_url = os.getenv("API_BASE_URL") or cloud_url
    return (configured_url or "http://localhost:8000").strip().rstrip("/")


API_BASE_URL = get_api_base_url()
API_TIMEOUT_SECONDS = 20.0


class APIError(Exception):
    """An HTTP, connection, timeout, or response error from the FastAPI backend."""


def api_request(
    method: str,
    path: str,
    json_body: Optional[dict] = None,
    timeout: float = API_TIMEOUT_SECONDS,
):
    try:
        response = httpx.request(
            method,
            f"{API_BASE_URL}{path}",
            json=json_body,
            timeout=timeout,
        )
    except httpx.TimeoutException as error:
        raise APIError("The API request timed out. Please try again.") from error
    except httpx.RequestError as error:
        raise APIError(
            "Could not connect to the API. Check that FastAPI is running and "
            "API_BASE_URL is correct."
        ) from error

    if response.status_code == 204:
        return None

    try:
        result = response.json()
    except ValueError as error:
        if response.is_success:
            raise APIError("The API returned an unreadable response.") from error
        result = None

    if not response.is_success:
        detail = result.get("detail") if isinstance(result, dict) else None
        if isinstance(detail, list):
            detail = "; ".join(
                f"{'.'.join(str(part) for part in item.get('loc', []))}: "
                f"{item.get('msg', 'Invalid value')}"
                for item in detail
            )
        message = str(detail or f"The API returned status {response.status_code}.")
        raise APIError(message)

    return result


def format_rupees(amount) -> str:
    return f"₹{Decimal(str(amount)):,.2f}"


def show_flash_message() -> None:
    message = st.session_state.pop("flash_message", None)
    if message:
        kind, text = message
        getattr(st, kind)(text)


def set_flash_and_rerun(kind: str, message: str) -> None:
    st.session_state["flash_message"] = (kind, message)
    st.rerun()


def load_api_data(path: str, description: str):
    try:
        return api_request("GET", path)
    except APIError as error:
        st.error(f"Could not load {description}: {error}")
        return None


def load_groups():
    return load_api_data("/group/", "groups")


def load_users():
    return load_api_data("/users/", "users")


def choose_group(groups: list[dict], key: str):
    group_ids = [group["id"] for group in groups]
    if key in st.session_state and st.session_state[key] not in group_ids:
        del st.session_state[key]
    labels = {group["id"]: f"{group['name']} (ID {group['id']})" for group in groups}
    return st.selectbox(
        "Group",
        group_ids,
        format_func=lambda group_id: labels[group_id],
        key=key,
    )


def get_group_members(group_id: int):
    return load_api_data(f"/group/{group_id}/members", "group members")


def render_balance_data(balance_data: dict) -> None:
    st.caption(
        "A positive net balance means the member is owed money; a negative balance "
        "means the member owes money."
    )

    member_rows = []
    payment_rows = []
    for member in balance_data["members"]:
        owes_text = ", ".join(
            f"{item['name']} {format_rupees(item['amount'])}"
            for item in member["owes"]
        ) or "—"
        owed_by_text = ", ".join(
            f"{item['name']} {format_rupees(item['amount'])}"
            for item in member["owed_by"]
        ) or "—"

        member_rows.append(
            {
                "Member": member["name"],
                "Net balance": format_rupees(member["net_balance"]),
                "Owes": owes_text,
                "Owed by": owed_by_text,
            }
        )
        for payment in member["owes"]:
            payment_rows.append(
                {
                    "Payer": member["name"],
                    "Receiver": payment["name"],
                    "Amount": format_rupees(payment["amount"]),
                }
            )

    if member_rows:
        st.dataframe(member_rows, hide_index=True, use_container_width=True)
    else:
        st.info("This group has no members yet.")

    st.subheader("Suggested payments")
    if payment_rows:
        st.dataframe(payment_rows, hide_index=True, use_container_width=True)
    else:
        st.info("No payments are currently needed between group members.")


def render_dashboard() -> None:
    st.header("Dashboard")
    groups = load_groups()
    users = load_users()
    if groups is None or users is None:
        return

    all_expenses = []
    all_group_expenses_loaded = True
    for group in groups:
        try:
            group_expenses = api_request(
                "GET", f"/groups/{group['id']}/expenses"
            )
            all_expenses.extend(
                {**expense, "group_name": group["name"]}
                for expense in group_expenses
            )
        except APIError as error:
            st.warning(f"Could not load expenses for {group['name']}: {error}")
            all_group_expenses_loaded = False

    metric_columns = st.columns(3)
    if all_group_expenses_loaded:
        total_spending = sum(
            (Decimal(str(expense["amount"])) for expense in all_expenses),
            Decimal("0.00"),
        )
        metric_columns[0].metric("Total spending", format_rupees(total_spending))
    else:
        metric_columns[0].metric("Total spending", "Unavailable")
    metric_columns[1].metric("Users", len(users))
    metric_columns[2].metric("Groups", len(groups))

    user_names = {user["id"]: user["name"] for user in users}
    st.subheader("Recent expenses")
    if all_group_expenses_loaded and all_expenses:
        recent_expenses = sorted(
            all_expenses,
            key=lambda expense: (expense["created_at"], expense["id"]),
            reverse=True,
        )[:5]
        st.dataframe(
            [
                {
                    "Group": expense["group_name"],
                    "Description": expense["description"],
                    "Paid by": user_names.get(expense["paid_by"], "Unknown"),
                    "Amount": format_rupees(expense["amount"]),
                    "Created": expense["created_at"],
                }
                for expense in recent_expenses
            ],
            hide_index=True,
            use_container_width=True,
        )
    elif all_group_expenses_loaded:
        st.info("No expenses have been recorded yet.")
    else:
        st.info("Recent expenses are unavailable because one or more groups could not be loaded.")

    st.subheader("Group balances")
    if not groups:
        st.info("Create a group to start tracking shared expenses.")
        return

    group_id = choose_group(groups, "dashboard_group")
    try:
        balances = api_request("GET", f"/groups/{group_id}/balances")
        render_balance_data(balances)
    except APIError as error:
        st.error(f"Could not load group balances: {error}")


def render_user_management() -> None:
    st.header("User management")

    with st.form("create_user_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        create_user = st.form_submit_button("Create user")

    if create_user:
        try:
            api_request("POST", "/users/", {"name": name, "email": email})
            set_flash_and_rerun("success", "User created successfully.")
        except APIError as error:
            st.error(f"Could not create user: {error}")

    users = load_users()
    if users is None:
        return

    st.subheader("Users")
    if users:
        st.dataframe(
            [{"ID": user["id"], "Name": user["name"], "Email": user["email"]} for user in users],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No users yet. Create the first user above.")

    with st.expander("Find a user by ID"):
        with st.form("find_user_form"):
            user_id = st.number_input("User ID", min_value=1, step=1)
            find_user = st.form_submit_button("Find user")
        if find_user:
            try:
                user = api_request("GET", f"/users/{int(user_id)}")
                st.success(f"{user['name']} — {user['email']}")
            except APIError as error:
                st.error(f"Could not find user: {error}")


def render_group_management() -> None:
    st.header("Group management")
    with st.form("create_group_form"):
        group_name = st.text_input("Group name")
        create_group = st.form_submit_button("Create group")
    if create_group:
        try:
            api_request("POST", "/group/", {"name": group_name})
            set_flash_and_rerun("success", "Group created successfully.")
        except APIError as error:
            st.error(f"Could not create group: {error}")

    groups = load_groups()
    if groups is None:
        return
    if not groups:
        st.info("No groups yet. Create a group above.")
        return

    group_id = choose_group(groups, "manage_group")
    try:
        group = api_request("GET", f"/group/{group_id}")
        members = api_request("GET", f"/group/{group_id}/members")
    except APIError as error:
        st.error(f"Could not load group details: {error}")
        return

    st.subheader(group["name"])
    st.caption(f"Group ID: {group['id']}")
    users = load_users()
    if users is None:
        return
    member_ids = {member["id"] for member in members}

    st.markdown("**Active members**")
    if members:
        st.dataframe(
            [{"ID": member["id"], "Name": member["name"], "Email": member["email"]} for member in members],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("This group has no active members.")

    available_users = [user for user in users if user["id"] not in member_ids]
    st.subheader("Add a member")
    if available_users:
        users_by_id = {user["id"]: user for user in available_users}
        available_user_ids = ",".join(str(user_id) for user_id in users_by_id)
        with st.form("add_group_member_form"):
            user_id = st.selectbox(
                "Existing user",
                list(users_by_id),
                format_func=lambda value: f"{users_by_id[value]['name']} (ID {value})",
                key=f"add_member_{group_id}_{available_user_ids}",
            )
            add_member = st.form_submit_button("Add to group")
        if add_member:
            try:
                api_request("POST", f"/group/{group_id}/members/{user_id}")
                set_flash_and_rerun("success", "Member added to the group.")
            except APIError as error:
                st.error(f"Could not add member: {error}")
    else:
        st.info("Create a user first, or all users are already members of this group.")

    st.subheader("Remove a member")
    if members:
        members_by_id = {member["id"]: member for member in members}
        active_member_ids = ",".join(str(user_id) for user_id in members_by_id)
        with st.form("remove_group_member_form"):
            user_id = st.selectbox(
                "Active member",
                list(members_by_id),
                format_func=lambda value: f"{members_by_id[value]['name']} (ID {value})",
                key=f"remove_member_{group_id}_{active_member_ids}",
            )
            remove_member = st.form_submit_button("Remove from group")
        if remove_member:
            try:
                api_request("DELETE", f"/group/{group_id}/members/{user_id}")
                set_flash_and_rerun("success", "Member removed from the group.")
            except APIError as error:
                st.error(f"Could not remove member: {error}")


def expense_table_rows(expenses: list[dict], users: list[dict]) -> list[dict]:
    user_names = {user["id"]: user["name"] for user in users}
    rows = []
    for expense in expenses:
        share_descriptions = []
        for split in expense["splits"]:
            user_id = split["user_id"]
            user_name = user_names.get(user_id, f"User {user_id}")
            share_descriptions.append(
                f"{user_name}: {format_rupees(split['amount'])}"
            )

        payer_id = expense["paid_by"]
        rows.append(
            {
                "Date": expense["created_at"],
                "Description": expense["description"],
                "Paid by": user_names.get(payer_id, f"User {payer_id}"),
                "Amount": format_rupees(expense["amount"]),
                "Shares": ", ".join(share_descriptions),
            }
        )
    return rows


def render_expense_management() -> None:
    st.header("Expense management")
    groups = load_groups()
    users = load_users()
    if groups is None or users is None:
        return
    if not groups:
        st.info("Create a group before adding expenses.")
        return

    group_id = choose_group(groups, "expense_group")
    members = get_group_members(group_id)
    if members is None:
        return
    if not members:
        st.info("Add active members to this group before creating an expense.")
        return

    member_names = {member["id"]: member["name"] for member in members}
    member_ids = list(member_names)
    split_method = st.radio(
        "Split method",
        ["Equal split", "Custom split"],
        horizontal=True,
        key="expense_split_method",
    )
    selected_participants = member_ids
    if split_method == "Custom split":
        selected_participants = st.multiselect(
            "Participants in this split",
            member_ids,
            default=member_ids,
            format_func=lambda value: member_names[value],
            key=f"custom_split_participants_{group_id}_{','.join(str(user_id) for user_id in member_ids)}",
        )

    with st.form("create_expense_form"):
        paid_by = st.selectbox(
            "Paid by",
            member_ids,
            format_func=lambda value: f"{member_names[value]} (ID {value})",
            key=f"expense_payer_{group_id}",
        )
        amount_value = st.number_input(
            "Total amount (₹)",
            min_value=0.01,
            step=0.01,
            format="%.2f",
        )
        description = st.text_input("Description")

        split_values = {}
        if split_method == "Custom split":
            st.markdown("**Amount per participant (₹)**")
            for user_id in selected_participants:
                split_values[user_id] = st.number_input(
                    member_names[user_id],
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"custom_share_{group_id}_{user_id}",
                )

        submit_expense = st.form_submit_button("Add expense")

    if submit_expense:
        amount = Decimal(str(amount_value)).quantize(Decimal("0.01"))
        payload = {
            "group_id": group_id,
            "paid_by": paid_by,
            "amount": format(amount, ".2f"),
            "description": description,
        }

        if split_method == "Custom split":
            if not selected_participants:
                st.error("Select at least one participant for the custom split.")
            else:
                splits = [
                    {
                        "user_id": user_id,
                        "amount": format(
                            Decimal(str(split_values[user_id])).quantize(
                                Decimal("0.01")
                            ),
                            ".2f",
                        ),
                    }
                    for user_id in selected_participants
                ]
                split_total = sum(
                    (Decimal(split["amount"]) for split in splits),
                    Decimal("0.00"),
                )
                if any(Decimal(split["amount"]) <= 0 for split in splits):
                    st.error("Each selected participant must have a share greater than ₹0.00.")
                elif split_total != amount:
                    st.error(
                        f"The shares add up to {format_rupees(split_total)}, "
                        f"but the expense is {format_rupees(amount)}."
                    )
                else:
                    payload["splits"] = splits
                    _submit_expense(group_id, payload)
        else:
            _submit_expense(group_id, payload)

    st.subheader("Recorded expenses")
    try:
        expenses = api_request("GET", f"/groups/{group_id}/expenses")
    except APIError as error:
        st.error(f"Could not load expenses: {error}")
        return

    if expenses:
        st.dataframe(
            expense_table_rows(expenses, users),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No expenses have been recorded for this group yet.")


def _submit_expense(group_id: int, payload: dict) -> None:
    try:
        api_request("POST", "/expenses", payload)
        set_flash_and_rerun("success", f"Expense added to group {group_id}.")
    except APIError as error:
        st.error(f"Could not add expense: {error}")


def render_balances() -> None:
    st.header("Group balances")
    groups = load_groups()
    if groups is None:
        return
    if not groups:
        st.info("Create a group to view balances.")
        return

    group_id = choose_group(groups, "balance_group")
    try:
        balance_data = api_request("GET", f"/groups/{group_id}/balances")
    except APIError as error:
        st.error(f"Could not load balances: {error}")
        return
    render_balance_data(balance_data)


def render_settlements() -> None:
    st.header("Record a settlement")
    groups = load_groups()
    if groups is None:
        return
    if not groups:
        st.info("Create a group before recording a settlement.")
        return

    group_id = choose_group(groups, "settlement_group")
    members = get_group_members(group_id)
    if members is None:
        return
    if len(members) < 2:
        st.info("A settlement needs at least two active group members.")
        return

    member_names = {member["id"]: member["name"] for member in members}
    member_ids = list(member_names)
    paid_by = st.selectbox(
        "Payer",
        member_ids,
        format_func=lambda value: f"{member_names[value]} (ID {value})",
        key=f"settlement_payer_{group_id}",
    )
    receiver_ids = [user_id for user_id in member_ids if user_id != paid_by]

    with st.form("create_settlement_form"):
        paid_to = st.selectbox(
            "Receiver",
            receiver_ids,
            format_func=lambda value: f"{member_names[value]} (ID {value})",
            key=f"settlement_receiver_{group_id}_{paid_by}",
        )
        amount_value = st.number_input(
            "Settlement amount (₹)",
            min_value=0.01,
            step=0.01,
            format="%.2f",
        )
        submit_settlement = st.form_submit_button("Record settlement")

    if submit_settlement:
        amount = Decimal(str(amount_value)).quantize(Decimal("0.01"))
        try:
            api_request(
                "POST",
                "/settlements/",
                {
                    "group_id": group_id,
                    "paid_by": paid_by,
                    "paid_to": paid_to,
                    "amount": format(amount, ".2f"),
                },
            )
            set_flash_and_rerun("success", "Settlement recorded and balances refreshed.")
        except APIError as error:
            st.error(f"Could not record settlement: {error}")

    st.subheader("Current balances")
    try:
        render_balance_data(
            api_request("GET", f"/groups/{group_id}/balances")
        )
    except APIError as error:
        st.error(f"Could not load balances: {error}")


def render_ai_summary() -> None:
    st.header("AI expense summary")
    groups = load_groups()
    if groups is None:
        return
    if not groups:
        st.info("Create a group before generating a summary.")
        return

    group_id = choose_group(groups, "summary_group")
    if st.button("Generate summary", type="primary"):
        with st.spinner("Generating the group summary..."):
            try:
                result = api_request(
                    "GET",
                    f"/groups/{group_id}/summary",
                    timeout=75.0,
                )
            except APIError as error:
                st.error(f"Could not generate the summary: {error}")
                return

        st.subheader(result["group_name"])
        st.write(result["summary"])
        statistics = result["statistics"]
        metric_columns = st.columns(2)
        metric_columns[0].metric(
            "Total spending", format_rupees(statistics["total_spending"])
        )
        metric_columns[1].metric("Expenses", statistics["expense_count"])

        st.markdown("**Largest expenses**")
        largest_expenses = statistics["largest_expenses"]
        if largest_expenses:
            st.dataframe(
                [
                    {
                        "Description": expense["description"],
                        "Paid by": expense["paid_by"],
                        "Amount": format_rupees(expense["amount"]),
                    }
                    for expense in largest_expenses
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No expenses to show.")

        st.markdown("**Member balances**")
        render_balance_data({"members": statistics["member_balances"]})


st.set_page_config(page_title="Expense Sharing", page_icon="💸", layout="wide")

with st.sidebar:
    st.title("Expense Sharing")
    selected_page = st.radio(
        "Navigate",
        [
            "Dashboard",
            "Users",
            "Groups",
            "Expenses",
            "Balances",
            "Settlements",
            "AI Summary",
        ],
    )
    st.caption(f"API: {API_BASE_URL}")

show_flash_message()

if selected_page == "Dashboard":
    render_dashboard()
elif selected_page == "Users":
    render_user_management()
elif selected_page == "Groups":
    render_group_management()
elif selected_page == "Expenses":
    render_expense_management()
elif selected_page == "Balances":
    render_balances()
elif selected_page == "Settlements":
    render_settlements()
else:
    render_ai_summary()
