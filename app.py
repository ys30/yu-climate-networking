import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
from supabase import create_client

st.set_page_config(page_title="Yu Climate Networking", page_icon="🌎", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = """
<style>
:root {
  --bg: #f6f8fc;
  --card: #ffffff;
  --border: #dfe5ee;
  --muted: #64748b;
  --accent: #2563eb;
}
.stApp {
  background:
    radial-gradient(circle at 15% 20%, rgba(14,165,233,.16), transparent 24%),
    radial-gradient(circle at 85% 10%, rgba(168,85,247,.14), transparent 22%),
    linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); color: #172033;
}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}\nh1,h2,h3 {color:#0f172a !important;}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  border-right: 1px solid #e2e8f0;
}
.hero {
  padding: 22px 24px;
  border: 1px solid var(--border);
  border-radius: 22px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
  box-shadow: 0 10px 28px rgba(15,23,42,.07);
  margin-bottom: 18px;
}
.hero h1 {font-size: 2.1rem; margin: 0 0 6px 0;}
.hero p {color: var(--muted); margin: 0;}
.card {
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--card);
  padding: 18px;
  box-shadow: 0 12px 34px rgba(0,0,0,.18);
}
.person-card {
  border: 1px solid #dfe7f1;
  border-radius: 20px;
  background: #ffffff;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: 0 8px 22px rgba(15,23,42,.055);
}
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: .78rem;
  border: 1px solid rgba(255,255,255,.10);
  margin-right: 6px;
  margin-bottom: 6px;
  color: #334155;
  background: #f8fafc;
}
.badge-accent {background: #eff6ff; border-color: #bfdbfe; color:#1d4ed8;}
.badge-green {background: #ecfdf5; border-color: #bbf7d0; color:#15803d;}
.small-muted {color: var(--muted); font-size: .9rem;}
div[data-testid="stMetric"] {
  background: rgba(255,255,255,.055);
  border: 1px solid rgba(255,255,255,.08);
  padding: 14px;
  border-radius: 18px;
}
.stButton>button, .stLinkButton>a {
  border-radius: 12px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

STAGES = ["Recommended","Contacted","Accepted","Replied","Meeting Scheduled","Follow-up","Closed"]
DOMAINS = ["Environmental Data Science","Climate Data Science","GIS/Geospatial","Remote Sensing","Air Quality","Sustainability/Climate Analytics","Environmental Informatics","Applied Research","Other"]

@st.cache_resource
def get_client():
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_KEY") if k not in st.secrets]
    if missing:
        st.error("Supabase is not configured yet.")
        st.info(
            "In Streamlit Community Cloud, open your app → Manage app / Settings → Secrets, "
            "add SUPABASE_URL and SUPABASE_KEY, save, then reboot the app."
        )
        st.code(
            'SUPABASE_URL = "https://jskihhnapgcxnusitung.supabase.co"\n'
            'SUPABASE_KEY = "your Supabase publishable key"',
            language="toml",
        )
        st.stop()
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_client()

def auth_gate():
    if "session" not in st.session_state:
        st.session_state.session = None

    if st.session_state.session is None:
        st.markdown("""
        <div class="hero">
          <h1>🌎 Yu Climate Networking</h1>
          <p>Private networking CRM · Sign in to continue</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": password})
                    if res.session:
                        st.session_state.session = res.session
                        st.success("Signed in.")
                        st.rerun()
                    else:
                        st.error("Sign-in failed.")
                except Exception as e:
                    st.error("Sign-in failed. Check your email/password and make sure this user exists in Supabase Auth.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    session = st.session_state.session
    try:
        sb.postgrest.auth(session.access_token)
    except Exception:
        try:
            refreshed = sb.auth.refresh_session(session.refresh_token)
            st.session_state.session = refreshed.session
            sb.postgrest.auth(refreshed.session.access_token)
        except Exception:
            st.session_state.session = None
            st.rerun()

auth_gate()

def fetch_contacts():
    return sb.table("contacts").select("*").order("created_at", desc=True).execute().data or []

def fetch_interactions(contact_id=None):
    q = sb.table("interactions").select("*")
    if contact_id:
        q = q.eq("contact_id", contact_id)
    return q.order("occurred_at", desc=True).execute().data or []

def save_contact(payload, contact_id=None):
    if contact_id:
        return sb.table("contacts").update(payload).eq("id", contact_id).execute()
    return sb.table("contacts").insert(payload).execute()

def hero(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

def stage_badge(stage):
    cls = "badge badge-green" if stage in ["Accepted","Replied","Meeting Scheduled"] else "badge badge-accent"
    return f'<span class="{cls}">{stage}</span>'

def contact_card(x):
    title = x.get("title") or ""
    company = x.get("company") or ""
    meta = " · ".join([v for v in [title, company, x.get("location") or ""] if v])
    st.markdown(
        f'''
        <div class="person-card">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <div style="font-size:1.2rem;font-weight:700;">{x.get("name","")}</div>
              <div class="small-muted">{meta}</div>
            </div>
            <div>{stage_badge(x.get("stage","Recommended"))}</div>
          </div>
          <div style="margin-top:10px;">
            <span class="badge">{x.get("domain") or "Other"}</span>
            {'<span class="badge badge-green">China background</span>' if x.get("chinese_background") else ''}
          </div>
        </div>
        ''',
        unsafe_allow_html=True
    )

contacts = fetch_contacts()
df = pd.DataFrame(contacts)

with st.sidebar:
    st.markdown("## 🌎 Yu Climate Networking")
    user_email = ""
    try:
        user_email = st.session_state.session.user.email or ""
    except Exception:
        pass
    if user_email:
        st.caption(f"Signed in as {user_email}")
    if st.button("Sign out", use_container_width=True):
        try:
            sb.auth.sign_out()
        except Exception:
            pass
        st.session_state.session = None
        st.rerun()
    st.caption("Bay Area environmental & climate-data networking tracker")
    page = st.radio("Navigate", ["Dashboard","Today's 3","Update status","Contacts","Follow-ups","Add contact","Exports"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Pipeline**")
    if not df.empty:
        for s in STAGES:
            n = int((df["stage"] == s).sum()) if "stage" in df else 0
            st.caption(f"{s}: {n}")

if page == "Update status":
    hero("Update contact status", "Fast manual maintenance for stage, follow-up date, and notes.")
    if not contacts:
        st.info("No contacts yet.")
    else:
        options = {x["name"] + " — " + (x.get("company") or "No company"): x for x in contacts}
        sel = st.selectbox("Choose contact", list(options.keys()))
        x = options[sel]
        contact_card(x)
        with st.form("fast_status_update"):
            c1,c2 = st.columns(2)
            current_stage = x.get("stage","Recommended")
            stage = c1.selectbox("Pipeline stage", STAGES, index=STAGES.index(current_stage) if current_stage in STAGES else 0)
            next_follow = c2.date_input("Next follow-up", value=None)
            notes = st.text_area("Notes", value=x.get("notes") or "", height=120)
            if st.form_submit_button("Save update", use_container_width=True):
                payload = {"stage":stage,"notes":notes,"next_followup_at":str(next_follow) if next_follow else None,"updated_at":datetime.utcnow().isoformat()}
                if stage != "Recommended":
                    payload["last_contacted_at"] = str(date.today())
                    if not x.get("first_contacted_at"):
                        payload["first_contacted_at"] = str(date.today())
                save_contact(payload, x["id"])
                st.success("Status updated.")
                st.rerun()

elif page == "Dashboard":
    hero("Networking Dashboard", "Track momentum, replies, meetings, and the next best follow-up.")
    if df.empty:
        st.info("No contacts yet.")
    else:
        total = len(df)
        accepted = df["stage"].isin(["Accepted","Replied","Meeting Scheduled","Follow-up","Closed"]).sum()
        replied = df["stage"].isin(["Replied","Meeting Scheduled","Follow-up","Closed"]).sum()
        meetings = df["stage"].isin(["Meeting Scheduled","Follow-up","Closed"]).sum()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total contacts", total)
        c2.metric("Acceptance", int(accepted), f"{accepted/total:.0%}" if total else "—")
        c3.metric("Replies", int(replied), f"{replied/total:.0%}" if total else "—")
        c4.metric("Meetings", int(meetings), f"{meetings/total:.0%}" if total else "—")

        l,r = st.columns([1.25,1])
        with l:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Pipeline")
            pipe = df.groupby("stage", dropna=False).size().reindex(STAGES, fill_value=0)
            st.bar_chart(pipe)
            st.markdown('</div>', unsafe_allow_html=True)
        with r:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Domain mix")
            if "domain" in df:
                st.bar_chart(df["domain"].fillna("Other").value_counts().head(8))
            st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("Networking funnel")
        st.caption("A live Sankey view of the current outreach pipeline.")
        sankey_stages = ["Recommended","Contacted","Accepted","Replied","Meeting Scheduled","Follow-up","Closed"]
        counts = {s:int((df["stage"] == s).sum()) for s in sankey_stages}
        labels = ["Total"] + sankey_stages
        source, target, value = [], [], []
        for idx, s in enumerate(sankey_stages, start=1):
            n = counts.get(s, 0)
            if n:
                source.append(0); target.append(idx); value.append(n)
        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(label=labels, pad=22, thickness=22),
            link=dict(source=source, target=target, value=value)
        ))
        fig.update_layout(height=430, margin=dict(l=20,r=20,t=20,b=20), paper_bgcolor="rgba(0,0,0,0)", font=dict(size=13))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Networking growth & conversion")
        st.caption("Cumulative outreach volume and downstream conversion based on dated contact activity.")
        trend_rows = []
        today_d = date.today()
        dated = []
        for z in contacts:
            raw = z.get("recommended_date") or z.get("created_at")
            if raw:
                try:
                    d = date.fromisoformat(str(raw)[:10])
                    dated.append((d, z))
                except Exception:
                    pass
        if dated:
            start_d = min(d for d,_ in dated)
            days = pd.date_range(start=start_d, end=today_d, freq="D")
            for ts in days:
                d = ts.date()
                visible = [z for rd,z in dated if rd <= d]
                total_n = len(visible)
                contacted_n = sum((z.get("first_contacted_at") and str(z.get("first_contacted_at"))[:10] <= str(d)) or z.get("stage") in ["Contacted","Accepted","Replied","Meeting Scheduled","Follow-up","Closed"] for z in visible)
                replied_n = sum(z.get("stage") in ["Replied","Meeting Scheduled","Follow-up","Closed"] for z in visible)
                meeting_n = sum(z.get("stage") in ["Meeting Scheduled","Follow-up","Closed"] for z in visible)
                trend_rows.append({"Date":d,"Total":total_n,"Contacted":contacted_n,"Replied":replied_n,"Meetings":meeting_n})
            trend_df = pd.DataFrame(trend_rows).set_index("Date")
            st.line_chart(trend_df, use_container_width=True)
            st.caption("Conversion snapshot: " + f"Contacted {contacted_n}/{total_n} · Replied {replied_n}/{total_n} · Meetings {meeting_n}/{total_n}")
        else:
            st.info("Trend chart will appear once dated contact records are available.")

        st.subheader("Recent contacts")
        for x in contacts[:8]:
            contact_card(x)

elif page == "Today's 3":
    hero("Today's 3", "Three fresh, deduplicated people for the next round of outreach.")
    today = str(date.today())
    todays = [x for x in contacts if x.get("recommended_date") == today]
    if not todays:
        st.info("No recommendations have been added for today yet.")
    else:
        for i, x in enumerate(todays, start=1):
            contact_card(x)
            a,b = st.columns([1,1])
            with a:
                if x.get("linkedin_url"):
                    st.link_button("Open LinkedIn / profile", x["linkedin_url"], use_container_width=True)
            with b:
                if x.get("profile_source") and x.get("profile_source") != x.get("linkedin_url"):
                    st.link_button("Open source", x["profile_source"], use_container_width=True)
            if x.get("fit_reason"):
                st.markdown("**Why this person fits**")
                st.write(x["fit_reason"])
            if x.get("outreach_draft"):
                st.markdown("**Suggested outreach**")
                st.code(x["outreach_draft"], language=None)
            st.divider()

elif page == "Contacts":
    hero("Contacts", "Filter the network, update status, and log replies or meetings.")
    if df.empty:
        st.info("No contacts yet.")
    else:
        a,b,c = st.columns(3)
        stage_filter = a.multiselect("Stage", STAGES, default=[])
        domains = sorted([x for x in df["domain"].dropna().unique()]) if "domain" in df else []
        domain_filter = b.multiselect("Domain", domains, default=[])
        chinese_only = c.checkbox("China-background only")

        filtered = df.copy()
        if stage_filter:
            filtered = filtered[filtered["stage"].isin(stage_filter)]
        if domain_filter:
            filtered = filtered[filtered["domain"].isin(domain_filter)]
        if chinese_only and "chinese_background" in filtered:
            filtered = filtered[filtered["chinese_background"] == True]

        show_cols = [c for c in ["name","title","company","location","domain","stage","recommended_date","last_contacted_at","next_followup_at","linkedin_url"] if c in filtered.columns]
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

        st.divider()
        options = {f"{x['name']} — {x.get('company','')}": x for x in contacts}
        st.subheader("Quick status update")
        st.caption("Select a contact, change stage or follow-up, add notes, then save.")
        sel = st.selectbox("Contact to maintain", list(options.keys()))
        x = options[sel]
        contact_card(x)

        left,right = st.columns(2)
        with left:
            with st.form("update_contact"):
                current_stage = x.get("stage","Recommended")
                stage = st.selectbox("Stage", STAGES, index=STAGES.index(current_stage) if current_stage in STAGES else 0)
                next_follow = st.date_input("Next follow-up", value=None)
                notes = st.text_area("Notes", value=x.get("notes") or "", height=150)
                if st.form_submit_button("💾 Save status update", use_container_width=True):
                    payload = {"stage":stage,"notes":notes,"next_followup_at":str(next_follow) if next_follow else None,"updated_at":datetime.utcnow().isoformat()}
                    if stage in ["Contacted","Accepted","Replied","Meeting Scheduled","Follow-up","Closed"]:
                        payload["last_contacted_at"] = str(date.today())
                        if not x.get("first_contacted_at"):
                            payload["first_contacted_at"] = str(date.today())
                    save_contact(payload, x["id"])
                    st.success("Saved.")
                    st.rerun()
        with right:
            with st.form("add_interaction"):
                itype = st.selectbox("Interaction type", ["Invitation sent","Accepted","Message sent","Reply received","Meeting","Follow-up","Note"])
                summary = st.text_area("Interaction note", height=150)
                occurred = st.date_input("Date", value=date.today())
                if st.form_submit_button("Add interaction", use_container_width=True):
                    sb.table("interactions").insert({"contact_id":x["id"],"interaction_type":itype,"summary":summary,"occurred_at":str(occurred)}).execute()
                    st.success("Interaction added.")
                    st.rerun()

        history = fetch_interactions(x["id"])
        if history:
            st.subheader("Timeline")
            hdf = pd.DataFrame(history)
            st.dataframe(hdf[["occurred_at","interaction_type","summary"]], use_container_width=True, hide_index=True)

elif page == "Follow-ups":
    hero("Follow-ups", "A focused queue of people who are due for another touch.")
    today = date.today()
    due = []
    for x in contacts:
        d = x.get("next_followup_at")
        if d:
            try:
                if date.fromisoformat(d) <= today:
                    due.append(x)
            except Exception:
                pass
    if not due:
        st.success("No follow-ups due today.")
    else:
        for x in due:
            contact_card(x)
            if x.get("notes"):
                st.write(x["notes"])
            if x.get("linkedin_url"):
                st.link_button("Open profile", x["linkedin_url"])

elif page == "Add contact":
    hero("Add contact", "Manually add a person when you find someone outside the daily recommendations.")
    with st.form("new_contact"):
        c1,c2 = st.columns(2)
        name = c1.text_input("Name *")
        title = c2.text_input("Current title")
        company = c1.text_input("Company")
        location = c2.text_input("Location", value="San Francisco Bay Area")
        linkedin = c1.text_input("LinkedIn / public profile URL")
        profile_source = c2.text_input("Additional public source")
        domain = c1.selectbox("Domain", DOMAINS)
        chinese = c2.checkbox("Chinese / China-education background")
        background_evidence = st.text_input("Evidence for China-background flag")
        recommended_date = st.date_input("Recommended date", value=date.today())
        fit = st.text_area("Why this person matches Yu")
        outreach = st.text_area("Outreach draft")
        stage = st.selectbox("Stage", STAGES)
        notes = st.text_area("Notes")
        if st.form_submit_button("Add contact", use_container_width=True):
            save_contact({"name":name.strip(),"title":title.strip(),"company":company.strip(),"location":location.strip(),"linkedin_url":linkedin.strip() or None,"profile_source":profile_source.strip() or None,"domain":domain,"chinese_background":chinese,"background_evidence":background_evidence.strip() or None,"recommended_date":str(recommended_date),"fit_reason":fit.strip(),"outreach_draft":outreach.strip(),"stage":stage,"notes":notes.strip()})
            st.success("Contact added.")
            st.rerun()

elif page == "Exports":
    hero("Exports", "Download the current network or today's recommended contacts anytime.")
    if df.empty:
        st.info("No data to export.")
    else:
        all_csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download all contacts CSV", data=all_csv, file_name=f"yu_networking_contacts_{date.today()}.csv", mime="text/csv", use_container_width=True)

        todays_df = df[df["recommended_date"].astype(str) == str(date.today())] if "recommended_date" in df else pd.DataFrame()
        if not todays_df.empty:
            st.download_button("Download today's 3 CSV", data=todays_df.to_csv(index=False).encode("utf-8"), file_name=f"yu_networking_today_{date.today()}.csv", mime="text/csv", use_container_width=True)
