# streamlit_manual_select.py
# Streamlit app with manual file selection + manual Excel row selection
#
# Usage:
#   pip install streamlit openai pandas python-docx openpyxl requests python-dotenv
#   streamlit run streamlit_manual_select.py
#
# Notes:
# - Scans both the app 'uploads/' folder and '/mnt/data/' for files.
# - Default uploaded files (from your session) are included:
#     /mnt/data/GenAI Property Description Auto-Writer for Rental Listings.docx
#     /mnt/data/Nagpur_Rental_AI_Data.xlsx
# - Template file is passed to model as file://{path} (so infra can transform it).
# - Make sure OPENAI_API_KEY is set (st.secrets or env).
#
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
# Writable uploads dir inside app folder
APP_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(APP_UPLOAD_DIR, exist_ok=True)

# Additional location (developer-provided uploaded files)
MNT_DATA_DIR = "/mnt/data"

# Known uploaded files (from conversation)
DEFAULT_TEMPLATE_PATH = "/mnt/data/GenAI Property Description Auto-Writer for Rental Listings.docx"
DEFAULT_EXCEL_PATH = "/mnt/data/Nagpur_Rental_AI_Data.xlsx"

OUTPUT_JSONL = os.path.join(APP_UPLOAD_DIR, "generated_descriptions.jsonl")
RECENT_JSON = os.path.join(APP_UPLOAD_DIR, "recent_generated.json")

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_SLEEP = 0.6
# ------------------------

st.set_page_config(page_title="GenAI Manual Select — Streamlit", layout="wide")
st.title("🧭 GenAI Property Writer — Manual File + Row Selection")

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
    # dedupe while preserving order
    seen = set()
    out = []
    for p in found:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out

# Show and allow upload
st.header("1) Upload files (optional)")
uploaded = st.file_uploader("Upload Excel (.xlsx) or DOCX template (.docx)", type=["xlsx", "xls", "docx"], accept_multiple_files=False)
if uploaded is not None:
    save_name = uploaded.name.replace(" ", "_")
    save_path = os.path.join(APP_UPLOAD_DIR, save_name)
    with open(save_path, "wb") as f:
        f.write(uploaded.getbuffer())
    st.success(f"Saved to `{save_path}` — it will appear in the file selectors below.")

# File selectors: assemble list from app uploads + /mnt/data
docx_files = scan_files([".docx"], [APP_UPLOAD_DIR, MNT_DATA_DIR])
excel_files = scan_files([".xlsx", ".xls", ".csv"], [APP_UPLOAD_DIR, MNT_DATA_DIR])

# Ensure defaults appear
if DEFAULT_TEMPLATE_PATH not in docx_files and os.path.exists(DEFAULT_TEMPLATE_PATH):
    docx_files.insert(0, DEFAULT_TEMPLATE_PATH)
if DEFAULT_EXCEL_PATH not in excel_files and os.path.exists(DEFAULT_EXCEL_PATH):
    excel_files.insert(0, DEFAULT_EXCEL_PATH)

st.header("2) Manual file selection")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Choose template (.docx)")
    if docx_files:
        template_choice = st.selectbox("Template file (choose one)", options=docx_files, format_func=lambda x: os.path.basename(x))
        st.write("Selected template path:", template_choice)
    else:
        st.warning("No .docx templates found. Upload one above.")
        template_choice = None

with col2:
    st.subheader("Choose Excel / CSV")
    if excel_files:
        excel_choice = st.selectbox("Excel file (choose one)", options=excel_files, format_func=lambda x: os.path.basename(x))
        st.write("Selected data file path:", excel_choice)
    else:
        st.warning("No Excel/CSV found. Upload one above.")
        excel_choice = None

# Preview Excel and manual row selection
st.header("3) Preview Excel & select rows to generate")
selected_rows_indices: List[int] = []
df = None
if excel_choice and os.path.exists(excel_choice):
    try:
        if excel_choice.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(excel_choice)
        else:
            df = pd.read_csv(excel_choice)
        df = df.fillna("")  # replace NaN
        st.success(f"Loaded {len(df)} rows from `{os.path.basename(excel_choice)}`")
        # show a compact preview: add an index column
        df_preview = df.reset_index().rename(columns={"index": "row_index"})
        # show key columns if they exist for easier selection
        key_cols = []
        for c in ["locality", "city", "bhk", "property_type", "rent_amount"]:
            if c in df_preview.columns:
                key_cols.append(c)
        display_cols = ["row_index"] + key_cols if key_cols else df_preview.columns.tolist()[:6]
        st.dataframe(df_preview[display_cols].head(1000), use_container_width=True)
        # Multi-select rows (show options as "index — brief summary")
        options = []
        for _, r in df_preview.iterrows():
            idx = int(r["row_index"])
            summary_items = []
            for c in key_cols:
                val = r.get(c, "")
                if val not in ("", None):
                    summary_items.append(f"{c}:{val}")
            summary = "; ".join(summary_items) if summary_items else "row"
            options.append((idx, f"{idx} — {summary}"))
        # build mapping for selectbox display
        idx_to_label = {opt[0]: opt[1] for opt in options}
        labels = [opt[1] for opt in options]
        # create multiselect of labels
        default_select = [labels[0]] if labels else []
        chosen_labels = st.multiselect("Select rows to generate (choose one or more)", options=labels, default=default_select, help="Select rows by index. You can pick multiple rows.")
        # map back to indices
        selected_rows_indices = [int(lbl.split(" — ")[0]) for lbl in chosen_labels]
        st.write(f"Selected row indices: {selected_rows_indices}")
    except Exception as e:
        st.error(f"Failed to load Excel: {e}")
else:
    st.info("Select an Excel file above to preview rows and pick specific rows to process.")

# Single-row manual edit area (optional)
st.header("4) Single-row manual edit / quick generate")
st.markdown("You can paste a single property JSON here (or click 'Load from selected row' to populate it).")
single_prop_text = st.text_area("Property JSON (single)", height=250, key="single_prop_area")

if st.button("Load from selected row (populate JSON area)"):
    if df is None or not selected_rows_indices:
        st.warning("No dataframe loaded or no rows selected.")
    else:
        # load first selected index into area
        idx = selected_rows_indices[0]
        try:
            row = df.reset_index().loc[df.reset_index()["index"] == idx].squeeze()
            if row is None or row.empty:
                st.error("Couldn't find the selected row.")
            else:
                row_dict = row.dropna().to_dict()
                st.experimental_set_query_params()  # noop to avoid warning
                st.session_state["single_prop_area"] = json.dumps(row_dict, ensure_ascii=False, indent=2)
                # reflect change
                single_prop_text = st.session_state["single_prop_area"]
                st.success(f"Loaded row {idx} into JSON area.")
        except Exception as e:
            st.error(f"Error loading row: {e}")

# Generation options
st.header("5) Generate (for selected rows or single property)")
lang = st.selectbox("Language", options=["English", "Hindi", "Marathi"], index=0)
tone = st.selectbox("Tone", options=["Professional", "Luxury", "Friendly", "Short"], index=0)
include_template = st.checkbox("Include template file in prompt (file://...)", value=include_template_default)
process_button_col1, process_button_col2 = st.columns(2)

# Helper functions for prompt + LLM
PREMIUM_PROMPT = """
You are an elite real-estate copywriter, luxury brand storyteller, and SEO strategist with deep understanding of buyer psychology.
Your mission is to transform structured property inputs into a high-end, persuasive, and SEO-optimized rental listing description that elevates the perceived value of the property.

Use all input fields intelligently. Blend "rough_description" seamlessly if provided.
DO NOT generate generic or repetitive content. DO NOT mention missing data.

Return STRICT JSON ONLY with this schema:
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
        st.error("OpenAI API key not configured. Set it in the sidebar or environment variable OPENAI_API_KEY.")
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
    # maintain recent
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

# Process selected rows
if process_button_col1.button("Generate selected rows"):
    if not selected_rows_indices:
        st.warning("No rows selected. Choose rows in the Excel preview.")
    else:
        if excel_choice is None or not os.path.exists(excel_choice):
            st.error("Excel file not found. Re-select a valid file.")
        else:
            total = len(selected_rows_indices)
            progress = st.progress(0)
            results = []
            for i, idx in enumerate(selected_rows_indices, start=1):
                # fetch row by original index
                try:
                    row = df.reset_index().loc[df.reset_index()["index"] == idx].squeeze()
                    prop = row.dropna().to_dict()
                except Exception:
                    st.error(f"Could not read row {idx}. Skipping.")
                    prop = {}
                prompt = build_prompt(prop, tone=tone, lang=lang, template_path=(template_choice if include_template else None))
                raw = call_openai(prompt, model_name=model)
                parsed = extract_json_from_text(raw) if raw else None
                record = {
                    "id": str(uuid.uuid4()),
                    "input": prop,
                    "output": parsed,
                    "index": idx,
                    "tone": tone,
                    "language": lang,
                    "template": template_choice if include_template else None,
                    "model": model,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                append_record(record)
                results.append(record)
                progress.progress(i/total)
                st.write(f"Processed {i}/{total} (row {idx})")
                time.sleep(float(sleep_between))
            st.success(f"Finished generating {len(results)} records. Saved to {OUTPUT_JSONL}")
            st.write("Preview of generated outputs:")
            for r in results[:5]:
                st.json(r["output"])

# Process single JSON from text area
if process_button_col2.button("Generate from single JSON"):
    try:
        prop_obj = json.loads(single_prop_text)
    except Exception as e:
        st.error(f"Invalid JSON: {e}")
        prop_obj = None
    if prop_obj:
        prompt = build_prompt(prop_obj, tone=tone, lang=lang, template_path=(template_choice if include_template else None))
        with st.spinner("Calling LLM..."):
            raw = call_openai(prompt, model_name=model)
        if not raw:
            st.error("LLM call failed.")
        else:
            parsed = extract_json_from_text(raw)
            if not parsed:
                st.error("Could not parse JSON. Raw output shown:")
                st.code(raw)
            else:
                record = {
                    "id": str(uuid.uuid4()),
                    "input": prop_obj,
                    "output": parsed,
                    "tone": tone,
                    "language": lang,
                    "template": template_choice if include_template else None,
                    "model": model,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                append_record(record)
                st.success("Generated and saved.")
                st.json(parsed)

# Preview recent records and download
st.header("6) Recent generated records & download")
if os.path.exists(RECENT_JSON):
    recent = json.load(open(RECENT_JSON, "r", encoding="utf-8"))
else:
    recent = []
if recent:
    for rec in recent[:20]:
        st.write(f"Row index: {rec.get('index','-')} — Generated at: {rec.get('timestamp')}")
        st.json(rec.get("output"))
    if st.button("Download all generated_descriptions.jsonl"):
        if os.path.exists(OUTPUT_JSONL):
            with open(OUTPUT_JSONL, "rb") as fh:
                st.download_button("Download JSONL", data=fh, file_name="generated_descriptions.jsonl", mime="application/json")
        else:
            st.warning("No output file yet.")
else:
    st.info("No generated records yet. Generate from selected rows or single JSON.")

st.markdown("---")
st.caption("Manual selection added ✅ — choose template & Excel file from dropdowns, preview rows, pick the rows you want and generate only those. Template file is passed as file://{path} in the prompt.")
