import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
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

/* v2 polish */
[data-testid="stMetric"] {box-shadow:0 8px 24px rgba(15,23,42,.05); min-height:112px;}
[data-testid="stMetricValue"] {font-size:2rem; color:#0f172a;}
[data-testid="stMetricLabel"] {font-weight:600; color:#64748b;}
div[data-testid="stPlotlyChart"], div[data-testid="stVegaLiteChart"] {
  background:#fff; border:1px solid #e6ebf2; border-radius:16px; padding:8px;
  box-shadow:0 8px 24px rgba(15,23,42,.045);
}
.stDataFrame {border:1px solid #e6ebf2; border-radius:14px; overflow:hidden;}
hr {border-color:#e8edf4;}
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

def add_business_days(start, days):
    d = start
    added = 0
    while added < days:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d

def parse_day(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None

def followup_plan(contact, interactions):
    stage = contact.get("stage") or "Recommended"
    if stage in ["Recommended","Meeting Scheduled","Closed"]:
        return None

    cid = contact.get("id")
    hist = [h for h in interactions if h.get("contact_id") == cid]
    hist = sorted(hist, key=lambda h: str(h.get("occurred_at") or ""))
    reply_dates = [parse_day(h.get("occurred_at")) for h in hist if h.get("interaction_type") == "Reply received"]
    outbound = [h for h in hist if h.get("interaction_type") in ["Invitation sent","Message sent","Follow-up sent","Status changed"]]
    outbound_dates = [parse_day(h.get("occurred_at")) for h in outbound if parse_day(h.get("occurred_at"))]
    last_reply = max([d for d in reply_dates if d], default=None)
    last_out = max(outbound_dates, default=None)
    base = last_out or parse_day(contact.get("last_contacted_at")) or parse_day(contact.get("first_contacted_at"))
    followup_count = sum(1 for h in hist if h.get("interaction_type") == "Follow-up sent")

    first = (contact.get("name") or "there").split()[0]
    if stage == "Accepted" and not any(h.get("interaction_type") == "Message sent" for h in hist):
        return {
            "action":"Send first message",
            "due": date.today(),
            "status":"due",
            "reason":"Connection accepted, but no first message is logged.",
            "draft":f"Hi {first}, thanks for connecting. I’m transitioning from environmental research into applied data science and would value one quick perspective: what skill mattered most in your move into this work?"
        }

    if stage == "Replied":
        if last_reply and (not last_out or last_reply >= last_out):
            return None

    if not base:
        return {
            "action":"Set contact date",
            "due":None,
            "status":"missing",
            "reason":"No reliable last-contact date is stored, so a follow-up date cannot be calculated yet.",
            "draft":""
        }

    wait_days = 7 if followup_count >= 1 or stage == "Follow-up" else 5
    due = add_business_days(base, wait_days)

    if followup_count >= 2:
        return {
            "action":"Pause outreach",
            "due":due,
            "status":"due" if due <= date.today() else "scheduled",
            "reason":"Two follow-ups are already logged. Avoid another message unless there is a new reason to reconnect.",
            "draft":""
        }

    if followup_count >= 1:
        draft = f"Hi {first}, one last quick follow-up—totally understand if timing is busy. If you have a moment, I’d appreciate any brief advice. Thanks again."
    elif stage == "Replied":
        draft = f"Hi {first}, just following up on my last note in case it got buried. No rush—I’d still appreciate any thoughts when you have a moment."
    else:
        draft = f"Hi {first}, just following up on my earlier note in case it got buried. I’d really value any quick advice when you have a moment. Thanks!"

    return {
        "action":"Follow up",
        "due":due,
        "status":"due" if due <= date.today() else "scheduled",
        "reason":f"No reply is logged after the latest outreach. Suggested wait: {wait_days} business days.",
        "draft":draft
    }

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
all_interactions = fetch_interactions()
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

        left,right = st.columns([1.05,1])
        with left:
            st.subheader("Needs attention")
            accepted_waiting = df[df["stage"] == "Accepted"]
            replied_waiting = df[df["stage"] == "Replied"]
            follow_due = df[(df["next_followup_at"].notna()) & (df["next_followup_at"].astype(str) <= str(date.today()))] if "next_followup_at" in df else pd.DataFrame()
            a1,a2,a3 = st.columns(3)
            a1.metric("Accepted", len(accepted_waiting))
            a2.metric("Replied", len(replied_waiting))
            a3.metric("Follow-ups due", len(follow_due))
            attention = pd.concat([accepted_waiting, replied_waiting, follow_due]).drop_duplicates(subset=["id"]) if not df.empty else pd.DataFrame()
            if attention.empty:
                st.success("Nothing urgent — your follow-up queue is clear.")
            else:
                cols = [x for x in ["name","company","stage","next_followup_at"] if x in attention.columns]
                st.dataframe(attention[cols].head(8), use_container_width=True, hide_index=True)
        with right:
            st.subheader("Domain mix")
            if "domain" in df:
                st.bar_chart(df["domain"].fillna("Other").value_counts().head(7))

        st.subheader("Networking funnel")
        st.caption("A live Sankey view of the current outreach pipeline.")
        funnel_labels = ["Total","Contacted","Accepted","Replied","Meeting"]
        total_f = len(df)
        contacted_f = int(df["stage"].isin(["Contacted","Accepted","Replied","Meeting Scheduled","Follow-up","Closed"]).sum())
        accepted_f = int(df["stage"].isin(["Accepted","Replied","Meeting Scheduled","Follow-up","Closed"]).sum())
        replied_f = int(df["stage"].isin(["Replied","Meeting Scheduled","Follow-up","Closed"]).sum())
        meeting_f = int(df["stage"].isin(["Meeting Scheduled","Follow-up","Closed"]).sum())
        vals = [contacted_f, accepted_f, replied_f, meeting_f]
        fig = go.Figure(go.Sankey(
            arrangement="snap",
            node=dict(label=funnel_labels, pad=26, thickness=24,
                      color=["#2563eb","#38bdf8","#22c55e","#14b8a6","#8b5cf6"]),
            link=dict(source=[0,1,2,3], target=[1,2,3,4], value=vals,
                      color=["rgba(37,99,235,.22)","rgba(56,189,248,.24)","rgba(34,197,94,.24)","rgba(139,92,246,.24)"])
        ))
        fig.update_layout(height=360, margin=dict(l=24,r=24,t=15,b=15),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(size=14, color="#334155"))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Current funnel · {total_f} total → {contacted_f} contacted → {accepted_f} accepted → {replied_f} replied → {meeting_f} meetings")


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
    hero("Follow-up Assistant", "Automatically identifies people without a reply, recommends when to follow up, and drafts the next message.")
    plans = []
    for x in contacts:
        p = followup_plan(x, all_interactions)
        if p:
            plans.append((x,p))

    due_now = [(x,p) for x,p in plans if p["status"] == "due"]
    scheduled = [(x,p) for x,p in plans if p["status"] == "scheduled"]
    missing = [(x,p) for x,p in plans if p["status"] == "missing"]

    m1,m2,m3 = st.columns(3)
    m1.metric("Due now", len(due_now))
    m2.metric("Scheduled", len(scheduled))
    m3.metric("Need contact date", len(missing))

    tabs = st.tabs(["Due now","Upcoming","Needs a date"])
    groups = [due_now, scheduled, missing]
    for tab, group in zip(tabs, groups):
        with tab:
            if not group:
                st.success("Nothing in this queue.")
            for x,p in group:
                contact_card(x)
                c1,c2 = st.columns([1.4,1])
                with c1:
                    st.markdown(f"**Recommended action:** {p['action']}")
                    if p["due"]:
                        st.write(f"**Recommended date:** {p['due'].strftime('%a, %b %d, %Y')}")
                    st.caption(p["reason"])
                    if p["draft"]:
                        st.markdown("**Suggested message**")
                        st.code(p["draft"], language=None)
                with c2:
                    if x.get("linkedin_url"):
                        st.link_button("Open profile", x["linkedin_url"], use_container_width=True)
                    if p["due"] and p["action"] == "Follow up":
                        if st.button("Schedule recommended date", key="sched_"+x["id"], use_container_width=True):
                            save_contact({"next_followup_at":str(p["due"])}, x["id"])
                            st.success("Follow-up date saved.")
                            st.rerun()
                        if st.button("Mark follow-up sent today", key="sent_"+x["id"], use_container_width=True):
                            next_due = add_business_days(date.today(), 7)
                            save_contact({"stage":"Follow-up","last_contacted_at":str(date.today()),"next_followup_at":str(next_due)}, x["id"])
                            sb.table("interactions").insert({
                                "contact_id":x["id"],
                                "interaction_type":"Follow-up sent",
                                "summary":p["draft"] or "Follow-up sent.",
                                "occurred_at":str(date.today())
                            }).execute()
                            st.success(f"Logged. Next check: {next_due}.")
                            st.rerun()
                    elif p["action"] == "Send first message":
                        if st.button("Mark first message sent", key="first_"+x["id"], use_container_width=True):
                            next_due = add_business_days(date.today(), 5)
                            save_contact({"last_contacted_at":str(date.today()),"next_followup_at":str(next_due)}, x["id"])
                            sb.table("interactions").insert({
                                "contact_id":x["id"],
                                "interaction_type":"Message sent",
                                "summary":p["draft"],
                                "occurred_at":str(date.today())
                            }).execute()
                            st.success(f"Message logged. Follow-up check: {next_due}.")
                            st.rerun()
                st.divider()

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
