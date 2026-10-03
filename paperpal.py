"""PaperPal: turn confusing paperwork into clear actions. Private, offline, in your language.
Run:  pip install streamlit ollama  &&  streamlit run paperpal.py   (local Gemma 4)
"""
import datetime as dt
import json
import re
import uuid

import ollama
import streamlit as st
import streamlit.components.v1 as components

MODEL = "gemma4:e4b"  # gemma4:12b reads small print better if your machine can run it
LANGS = {"Marathi": "mr-IN", "Hindi": "hi-IN", "English": "en-IN"}

ITEM = lambda props: {"type": "array", "items": {"type": "object", "properties": props, "required": list(props)}}  # noqa: E731
S_ = {"type": "string"}
SCHEMA = {"type": "object", "properties": {
    "doc_type": S_, "sender": S_, "summary": S_,
    "urgency": {"type": "string", "enum": ["NOW", "SOON", "FYI"]},
    "deadlines": ITEM({"date": S_, "what": S_, "evidence": S_}),
    "amounts": ITEM({"label": S_, "amount": S_, "evidence": S_}),
    "actions": ITEM({"step": S_, "where_or_who": S_, "evidence": S_}),
    "if_ignored": S_, "if_ignored_evidence": S_},
    "required": ["doc_type", "sender", "summary", "urgency", "deadlines", "amounts", "actions", "if_ignored", "if_ignored_evidence"]}


def norm(s):
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def verified(evidence, text):
    """The trust layer: code checks that every quoted 'receipt' really appears in the document."""
    e = norm(evidence)
    if not e:
        return False
    t = norm(text)
    if e in t:
        return True
    words, pool = e.split(), set(t.split())
    return sum(w in pool for w in words) / len(words) >= 0.85


def chat(system, user, images=None, fmt=None, temp=0.2):
    msg = {"role": "user", "content": user}
    if images:
        msg["images"] = images
    r = ollama.chat(model=MODEL, messages=[{"role": "system", "content": system}, msg], format=fmt, options={"temperature": temp})
    return r["message"]["content"]


def make_ics(deadlines):
    esc = lambda s: s.replace("\\", "").replace(",", "\\,").replace(";", "\\;").replace("\n", " ")  # noqa: E731
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PaperPal//EN"]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for d in deadlines:
        try:
            day = dt.date.fromisoformat(d["date"])
        except ValueError:
            continue
        out += ["BEGIN:VEVENT", f"UID:{uuid.uuid4()}@paperpal", f"DTSTAMP:{now}", f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
                f"SUMMARY:{esc(d['what'])}"]
        for trig in ("-P3D", "-P1D"):
            out += ["BEGIN:VALARM", f"TRIGGER:{trig}", "ACTION:DISPLAY", f"DESCRIPTION:{esc(d['what'])}", "END:VALARM"]
        out.append("END:VEVENT")
    return "\r\n".join(out + ["END:VCALENDAR"])


def explain(a, lang):
    return chat(f"You explain paperwork to a person with little formal education, in {lang}. Short sentences, zero jargon, max 120 words. "
                "Use ONLY the facts given. End with one calm sentence saying what to do first.", f"FACTS: {json.dumps(a)}", temp=0.4)


# ---------------- UI ----------------
st.set_page_config(page_title="PaperPal", page_icon="📄", layout="wide")
S = st.session_state
st.title("📄 PaperPal")
st.caption("Photograph any confusing letter, bill or notice. Get what it means, what to do, and by when. "
           "Private and offline: your documents never leave this device.")
lang = st.sidebar.selectbox("Explain in", list(LANGS))
st.sidebar.warning("PaperPal explains documents. It is not legal or financial advice. Confirm important matters with the issuing office.")

files = st.file_uploader("Upload one or more pages (photos or scans)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
if files:
    st.image([f.getvalue() for f in files], width=130)
if files and st.button("🔍 Decode this document", type="primary"):
    imgs = [f.getvalue() for f in files]
    try:
        with st.spinner("Step 1/3 · Gemma 4 is reading the pages..."):
            S.text = chat("You are an OCR engine.", "Transcribe ALL text in these document pages exactly as written, in reading order, keeping the original language. Output only the text.", imgs, temp=0)
        with st.spinner("Step 2/3 · Finding deadlines, amounts and actions..."):
            S.a = json.loads(chat(
                f"You analyze official or personal paperwork for a non-expert. Today is {dt.date.today()}. Use ONLY the DOCUMENT TEXT. "
                "For every deadline, amount and action give 'evidence': a SHORT VERBATIM quote (max 15 words) copied exactly from the text. "
                "If something is not stated, leave it out. Never guess. Dates are ISO YYYY-MM-DD only when the full date is stated, otherwise an empty string. "
                "Write all fields in English.", f"DOCUMENT TEXT:\n{S.text}", fmt=SCHEMA))
        with st.spinner(f"Step 3/3 · Explaining in {lang}..."):
            S.explain = explain(S.a, lang)
        S.chat, S.letter = [], None
    except Exception as e:
        st.error(f"Something failed. Is `ollama serve` running? ({e})")
        st.stop()

if S.get("a"):
    a = S.a
    color = {"NOW": "red", "SOON": "orange", "FYI": "green"}[a["urgency"]]
    st.markdown(f"## :{color}[{a['urgency']}]  ·  {a['doc_type']}  \nFrom: **{a['sender']}**")
    st.write(a["summary"])
    tabs = st.tabs(["📌 What it means", "✅ What to do", "💬 Ask the document", "✉️ Reply letter", "🔎 Full text"])

    with tabs[0]:
        st.markdown(f"### In {lang}")
        st.write(S.explain)
        c1, c2 = st.columns([1, 3])
        components.html(f"""<button onclick="s()" style="font-size:16px;padding:8px 14px">🔊 Read aloud</button>
<button onclick="speechSynthesis.cancel()" style="font-size:16px;padding:8px 14px">⏹</button>
<script>function s(){{const u=new SpeechSynthesisUtterance({json.dumps(S.explain)});u.lang="{LANGS[lang]}";u.rate=0.9;
speechSynthesis.cancel();speechSynthesis.speak(u);}}</script>""", height=55)
        if c1.button(f"Re-explain in {lang}"):
            S.explain = explain(a, lang)
            st.rerun()
        if a["if_ignored"]:
            ok = "✅" if verified(a["if_ignored_evidence"], S.text) else "⚠️"
            st.error(f"**If you ignore it:** {a['if_ignored']}  \n{ok} _\"{a['if_ignored_evidence']}\"_")

    with tabs[1]:
        st.subheader("Deadlines")
        if not a["deadlines"]:
            st.caption("No deadlines found in this document.")
        for d in a["deadlines"]:
            ok = "✅ verified in document" if verified(d["evidence"], S.text) else "⚠️ check this one yourself"
            st.markdown(f"- **{d['date'] or 'date unclear'}**: {d['what']}  \n  _\"{d['evidence']}\"_ · {ok}")
        ics = make_ics(a["deadlines"])
        if "BEGIN:VEVENT" in ics:
            st.download_button("📅 Add deadlines to my calendar (.ics, reminders 3 days + 1 day before)", ics, "deadlines.ics", "text/calendar")
        if a["amounts"]:
            st.subheader("Money")
            for m in a["amounts"]:
                ok = "✅" if verified(m["evidence"], S.text) else "⚠️"
                st.markdown(f"- **{m['label']}: {m['amount']}** {ok}  \n  _\"{m['evidence']}\"_")
        st.subheader("Your checklist")
        for k, s in enumerate(a["actions"]):
            ok = "✅" if verified(s["evidence"], S.text) else "⚠️"
            st.checkbox(f"{s['step']}  ·  {s['where_or_who']}  {ok}", key=f"act{k}")
        st.caption("✅ = the quoted line was found in your document by code, not by AI. ⚠️ = could not be matched, verify manually.")

    with tabs[2]:
        for m in S.chat:
            st.chat_message(m["role"]).write(m["content"])
        q = st.chat_input("Ask anything about this document...")
        if q:
            st.chat_message("user").write(q)
            sysm = (f"Answer questions about the document below, in {lang}. Use ONLY the document. If the answer is not in it, say "
                    f"'This is not in the document' and suggest who to ask. Quote the relevant line.\nDOCUMENT:\n{S.text}")
            hist = [{"role": m["role"], "content": m["content"]} for m in S.chat] + [{"role": "user", "content": q}]
            with st.chat_message("assistant"):
                reply = st.write_stream(c["message"]["content"] for c in ollama.chat(
                    model=MODEL, messages=[{"role": "system", "content": sysm}] + hist, stream=True, options={"temperature": 0.2}))
            S.chat += [{"role": "user", "content": q}, {"role": "assistant", "content": reply}]

    with tabs[3]:
        goal = st.selectbox("What do you want to say?", ["Ask for more time", "Ask for clarification / dispute politely",
                                                          "Request copies of documents", "Confirm payment / action completed"])
        llang = st.selectbox("Letter language", ["English", "Marathi", "Hindi"])
        if st.button("Draft the letter"):
            with st.spinner("Drafting..."):
                S.letter = chat(f"Write a polite, formal letter in {llang}. Use placeholders [YOUR NAME], [ADDRESS], [DATE], [REFERENCE NO.]. "
                                "Use ONLY facts from FACTS. Do not threaten and do not cite specific laws or sections. Max 180 words.",
                                f"Goal: {goal}\nFACTS: {json.dumps(a)}", temp=0.4)
        if S.get("letter"):
            S.letter = st.text_area("Edit before sending", S.letter, height=300)
            st.download_button("⬇️ Download letter", S.letter, "reply_letter.txt")

    with tabs[4]:
        st.text_area("What Gemma 4 read from your pages (check this if anything looks wrong)", S.text, height=350)