# streamlit_manual_select_v2.py
# Updated Streamlit app with:
# - manual file selection
# - manual Excel row selection
# - Select Top 3 / Select All / Deselect All
# - per-row "Generate Now" button in preview
# - uses uploads/ (writable) + /mnt/data/
#
# Usage:
# pip install streamlit openai pandas python-docx openpyxl requests
# streamlit run streamlit_manual_select_v2.py

import os
import time
import json
import re
import uuid
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import openai

# ---------- Config ----------
APP_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(APP_UPLOAD_DIR, exist_ok=True)

MNT_DATA_DIR = "/mnt/data"
# Developer uploaded file paths (use these in prompt as file://...)
DEFAULT_TEMPLATE_PATH = "/mnt/data/GenAI Property Description Auto-Writer for Rental Listings.docx"
DEFAULT_EXCEL_PATH = "/mnt/data/Nagpur_Rental_AI_Data.xlsx"

OUTPUT_JSONL = os.path.join(APP_UPLOAD_DIR, "generated_descriptions.jsonl")
RECENT_JSON = os.path.join(APP_UPLOAD_DIR, "recent_generated.json")

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_SLEEP = 0.6
# ------------------------

st.set_page_config(page_title="GenAI Manual Select v2", layout="wide")
st.title("🧭 GenAI Property Writer — Manual Select (v2)")

# Sidebar: API + settings
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("OpenAI API Key (or set OPENAI_API_KEY env)", type="password")
model = st.sidebar.text_input("Model", value=DEFAULT_MODEL)
sleep_between = st.sidebar.number_input("Pause between rows (s)", min_value=0.0, max_value=5.0, value=DEFAULT_SLEEP)
include_template_default = st.sidebar.checkbox("Include template in prompt by default", value=True)

if api_key:
    openai.api_key = api_key
else:
    openai.api_key = os.environ.get("OPENAI_API_KEY", "")

# Helper: scan files
def scan_files(exts: List[str], dirs: List[str]) -> List[str]:
    found = []
    for d in dirs:
        if not d or not os.path.exists(d):
            continue
        for fname in sorted(os.listdir(d)):
            if any(fname.lower().endswith(e) for e in exts):
                found.append(os.path.join(d, fname))
    seen = set()
    out = []
    for p in found:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out

# Upload area
st.header("1) Upload files (optional)")
uploaded = st.file_uploader("Upload Excel (.xlsx/.xls/.csv) or DOCX template (.docx)", type=["xlsx", "xls", "csv", "docx"], accept_multiple_files=False)
if uploaded is not None:
    save_name = uploaded.name.replace(" ", "_")
    save_path = os.path.join(APP_UPLOAD_DIR, save_name)
    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())
    st.success(f"Saved to `{save_path}` — it will appear in file selectors below.")

# File selectors
docx_files = scan_files([".docx"], [APP_UPLOAD_DIR, MNT_DATA_DIR])
excel_files = scan_files([".xlsx", ".xls", ".csv"], [APP_UPLOAD_DIR, MNT_DATA_DIR])

# Ensure defaults appear first if present
if DEFAULT_TEMPLATE_PATH not in docx_files and os.path.exists(DEFAULT_TEMPLATE_PATH):
    docx_files.insert(0, DEFAULT_TEMPLATE_PATH)
if DEFAULT_EXCEL_PATH not in excel_files and os.path.exists(DEFAULT_EXCEL_PATH):
    excel_files.insert(0, DEFAULT_EXCEL_PATH)

st.header("2) Choose files")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Template (.docx)")
    if docx_files:
        template_choice = st.selectbox("Choose template", options=docx_files, format_func=lambda x: os.path.basename(x))
        st.write("Using template:", template_choice)
    else:
        st.warning("No .docx templates found. Upload one above.")
        template_choice = None

with col2:
    st.subheader("Excel / CSV")
    if excel_files:
        excel_choice = st.selectbox("Choose data file", options=excel_files, format_func=lambda x: os.path.basename(x))
        st.write("Using data file:", excel_choice)
    else:
        st.warning("No Excel/CSV found. Upload one above.")
        excel_choice = None

# Load DataFrame if excel chosen
df = None
if excel_choice and os.path.exists(excel_choice):
    try:
        if excel_choice.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(excel_choice)
        else:
            df = pd.read_csv(excel_choice)
        df = df.fillna("")
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        df = None

# Preview and manual selection controls
st.header("3) Preview & select rows to generate")
if df is None:
    st.info("Select an Excel file above to preview rows and pick specific rows.")
else:
    # create preview with index column 'row_index' equals original DF index
    df_preview = df.reset_index().rename(columns={"index": "row_index"})
    # determine key columns for compact preview
    key_cols = []
    for c in ["row_index", "locality", "city", "bhk", "property_type", "rent_amount"]:
        if c in df_preview.columns:
            key_cols.append(c)
    # if row_index not present ensure it's first
    if "row_index" not in key_cols:
        df_preview.insert(0, "row_index", df_preview.index)
    # show compact table
    st.dataframe(df_preview[key_cols].head(1000), use_container_width=True)

    # build select options labels
    options = []
    for _, r in df_preview.iterrows():
        idx = int(r["row_index"])
        parts = []
        for c in ["property_type", "bhk", "locality", "city", "rent_amount"]:
            if c in r and str(r[c]).strip():
                parts.append(f"{c}:{r[c]}")
        summary = "; ".join(parts) if parts else "row"
        options.append((idx, f"{idx} — {summary}"))

    labels = [opt[1] for opt in options]
    idx_map = {opt[1]: opt[0] for opt in options}

    # selection control buttons
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1,1,1,2])
    with btn_col1:
        if st.button("Select Top 3"):
            default_labels = labels[:3] if labels else []
            st.session_state["selected_labels"] = default_labels
    with btn_col2:
        if st.button("Select All"):
            st.session_state["selected_labels"] = labels.copy()
    with btn_col3:
        if st.button("Deselect All"):
            st.session_state["selected_labels"] = []
    with btn_col4:
        st.write("Tip: Use Select Top 3 to quickly pick first 3 rows.")

    # multiselect widget (persist selection in session_state)
    selected_labels = st.multiselect("Select rows (multi)", options=labels, default=st.session_state.get("selected_labels", []))
    # map to indices
    selected_rows_indices = [idx_map[lbl] for lbl in selected_labels] if selected_labels else []

    st.write(f"Selected rows: {selected_rows_indices}")

# Single-row edit area & quick generate
st.header("4) Single-row quick edit / generate")
single_prop_text = st.text_area("Paste or edit a single property JSON here", height=260, key="single_prop_area")

if st.button("Load first selected row into editor"):
    if df is None or not selected_rows_indices:
        st.warning("No selected row to load.")
    else:
        idx = selected_rows_indices[0]
        try:
            row = df.reset_index().loc[df.reset_index()["index"] == idx].squeeze()
            row_dict = row.dropna().to_dict()
            st.session_state["single_prop_area"] = json.dumps(row_dict, ensure_ascii=False, indent=2)
            st.success(f"Loaded row {idx} into editor.")
        except Exception as e:
            st.error(f"Error loading row: {e}")

# Generation options
st.header("5) Generate")
colA, colB = st.columns(2)
with colA:
    lang = st.selectbox("Language", ["English","Hindi","Marathi"], index=0)
    tone = st.selectbox("Tone", ["Professional","Luxury","Friendly","Short"], index=0)
with colB:
    include_template = st.checkbox("Include template (file://...)", value=include_template_default)
    model_input = st.text_input("Model override (optional)", value=model)

# Helper functions
PREMIUM_PROMPT = """
You are an elite real-estate copywriter, luxury brand storyteller, and SEO strategist with deep understanding of buyer psychology.
Your mission is to transform structured property inputs into a high-end, persuasive, and SEO-optimized rental listing description that elevates the perceived value of the property.

Use all input fields intelligently. Blend "rough_description" seamlessly if provided.
DO NOT generate generic or repetitive content. DO NOT mention missing data.

Return STRICT JSON ONLY with schema:
{
  "title": "",
  "teaser_text": "",
  "full_description": "",
  "bullet_points": [],
  "seo_keywords": [],
  "meta_title": "",
  "meta_description": ""
}
"""

def build_prompt(property_data: Dict[str, Any], tone: str, lang: str, template_path: Optional[str]):
    tone_map = {
        "Luxury": "Use an aspirational, high-end magazine voice emphasizing exclusivity and lifestyle.",
        "Professional": "Use a clear, trustworthy professional tone focused on facts and conversion.",
        "Friendly": "Use a warm, conversational tone that appeals to everyday renters.",
        "Short": "Be concise and punchy — short sentences, high impact."
    }
    lang_map = {
        "English": "Generate the text in English.",
        "Hindi": "Generate the text in natural, professional Hindi.",
        "Marathi": "Generate the text in clear, professional Marathi."
    }
    parts = [PREMIUM_PROMPT.strip(), tone_map.get(tone,""), lang_map.get(lang,"")]
    if template_path:
        parts.append(f"REFERENCE_TEMPLATE_FILE: file://{template_path}")
    parts.append("INPUT PROPERTY JSON:")
    parts.append(json.dumps(property_data, ensure_ascii=False, indent=2))
    parts.append("Return only the strict JSON document as per schema. No extra commentary.")
    return "\n\n".join([p for p in parts if p])

def call_openai(prompt: str, model_name: str = DEFAULT_MODEL, retries: int = 3) -> Optional[str]:
    if not openai.api_key:
        st.error("OpenAI API key missing. Provide in sidebar or set OPENAI_API_KEY env.")
        return None
    for attempt in range(1, retries+1):
        try:
            resp = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role":"system","content":"You are a JSON-output-only assistant."},
                    {"role":"user","content":prompt}
                ],
                temperature=0.2,
                max_tokens=900,
                top_p=1.0
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            st.warning(f"LLM attempt {attempt} failed: {e}")
            time.sleep(1 * attempt)
    return None

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    first = text.find("{")
    if first == -1:
        return None
    stack = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if start is None:
                start = i
            stack += 1
        elif ch == "}":
            stack -= 1
            if stack == 0 and start is not None:
                candidate = text[start:i+1]
                try:
                    return json.loads(candidate)
                except Exception:
                    cleaned = re.sub(r",\s*}", "}", candidate)
                    cleaned = re.sub(r",\s*\]", "]", cleaned)
                    try:
                        return json.loads(cleaned)
                    except Exception:
                        return None
    return None

def append_record(record: Dict[str, Any]):
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    recent = []
    if os.path.exists(RECENT_JSON):
        try:
            recent = json.load(open(RECENT_JSON, "r", encoding="utf-8"))
        except Exception:
            recent = []
    recent.insert(0, record)
    recent = recent[:200]
    with open(RECENT_JSON, "w", encoding="utf-8") as fh:
        json.dump(recent, fh, ensure_ascii=False, indent=2)

# Generate selected rows
if st.button("Generate selected rows"):
    if df is None or not selected_rows_indices:
        st.warning("No rows selected.")
    else:
        total = len(selected_rows_indices)
        progress = st.progress(0)
        results = []
        for i, idx in enumerate(selected_rows_indices, start=1):
            try:
                row = df.reset_index().loc[df.reset_index()["index"] == idx].squeeze()
                prop = row.dropna().to_dict()
            except Exception:
                st.error(f"Could not read row {idx}. Skipping.")
                continue
            prompt = build_prompt(prop, tone=tone, lang=lang, template_path=(template_choice if include_template else None))
            raw = call_openai(prompt, model_name=model_input or model)
            parsed = extract_json_from_text(raw) if raw else None
            record = {
                "id": str(uuid.uuid4()),
                "input": prop,
                "output": parsed,
                "index": idx,
                "tone": tone,
                "language": lang,
                "template": template_choice if include_template else None,
                "model": model_input or model,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            append_record(record)
            results.append(record)
            progress.progress(i/total)
            st.write(f"Processed {i}/{total} (row {idx})")
            time.sleep(float(sleep_between))
        st.success(f"Finished {len(results)} rows. Saved to {OUTPUT_JSONL}")

# Generate from the single JSON editor
if st.button("Generate from editor (single JSON)"):
    try:
        prop_obj = json.loads(single_prop_text)
    except Exception as e:
        st.error(f"Invalid JSON in editor: {e}")
        prop_obj = None
    if prop_obj:
        prompt = build_prompt(prop_obj, tone=tone, lang=lang, template_path=(template_choice if include_template else None))
        raw = call_openai(prompt, model_name=model_input or model)
        parsed = extract_json_from_text(raw) if raw else None
        record = {
            "id": str(uuid.uuid4()),
            "input": prop_obj,
            "output": parsed,
            "tone": tone,
            "language": lang,
            "template": template_choice if include_template else None,
            "model": model_input or model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        append_record(record)
        if parsed:
            st.success("Generated and saved.")
            st.json(parsed)
        else:
            st.error("Generation failed or parsing failed. See raw response (if any).")

# Per-row "Generate Now" buttons in preview
st.header("6) Per-row Generate Now (fast actions)")
if df is not None:
    st.write("You can generate for an individual row instantly using the button below each row.")
    # show limited table with basic columns and action buttons
    preview_limit = min(200, len(df))
    for _, r in df.reset_index().head(preview_limit).iterrows():
        idx = int(r["index"])
        cols = st.columns([3,1])
        left, right = cols
        with left:
            summary = []
            for c in ["property_type", "bhk", "locality", "city", "rent_amount"]:
                if c in r and str(r[c]).strip():
                    summary.append(f"{c}:{r[c]}")
            st.write(f"Row {idx} — " + "; ".join(summary))
        with right:
            if st.button(f"Generate row {idx}", key=f"gen_row_{idx}"):
                try:
                    prop = r.dropna().to_dict()
                    prompt = build_prompt(prop, tone=tone, lang=lang, template_path=(template_choice if include_template else None))
                    raw = call_openai(prompt, model_name=model_input or model)
                    parsed = extract_json_from_text(raw) if raw else None
                    rec = {
                        "id": str(uuid.uuid4()),
                        "input": prop,
                        "output": parsed,
                        "index": idx,
                        "tone": tone,
                        "language": lang,
                        "template": template_choice if include_template else None,
                        "model": model_input or model,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    append_record(rec)
                    if parsed:
                        st.success(f"Row {idx} generated and saved.")
                        st.json(parsed)
                    else:
                        st.error(f"Row {idx} generation failed / parse error.")
                except Exception as e:
                    st.error(f"Error generating row {idx}: {e}")
                time.sleep(float(sleep_between))
else:
    st.info("Load an Excel file to use per-row generate buttons.")

# Recent outputs and download
st.header("7) Recent outputs & download")
if os.path.exists(RECENT_JSON):
    recent = json.load(open(RECENT_JSON, "r", encoding="utf-8"))
else:
    recent = []
if recent:
    st.write(f"Showing {min(len(recent), 20)} most recent records:")
    for rec in recent[:20]:
        st.write(f"Row index: {rec.get('index', '-')}, Generated: {rec.get('timestamp')}")
        st.json(rec.get("output"))
    if st.button("Download all generated_descriptions.jsonl"):
        if os.path.exists(OUTPUT_JSONL):
            with open(OUTPUT_JSONL, "rb") as fh:
                st.download_button("Download JSONL", data=fh, file_name="generated_descriptions.jsonl", mime="application/json")
        else:
            st.warning("No output file yet.")
else:
    st.info("No generated records yet. Generate some rows to populate.")

st.markdown("---")
st.caption("Added: Select Top 3 / Select All / Deselect All + per-row 'Generate Now' buttons. Template path used in prompts (file://{path}) when template inclusion checked.")
