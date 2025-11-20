# streamlit_app_full.py
# Streamlit app — Full feature set for GenAI Property Description Auto-Writer
# Features:
# - Upload Excel/DOCX, include template file reference (file://...)
# - Single & batch generation
# - Multi-language (English/Hindi/Marathi)
# - Tone presets (Luxury / Professional / Friendly / Short)
# - Edit & Regenerate for each generated record
# - Auto-save to Django (optional via DJANGO_SAVE_URL)
# - Save & Download JSONL, preview UI
#
# Usage:
#   pip install streamlit openai pandas python-docx openpyxl requests
#   streamlit run streamlit_app_full.py
#
# IMPORTANT:
# - Default template path (uploaded earlier) is included as:
#     /mnt/data/GenAI Property Description Auto-Writer for Rental Listings.docx
#   This path is passed into the prompt as file://... so your infra can transform it if needed.
# - Set OPENAI_API_KEY via st.secrets or environment var OPENAI_API_KEY
# - Optionally set DJANGO_SAVE_URL env var to auto-post outputs to your Django endpoint.

import os
import time
import json
import re
import uuid
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import openai
import requests

# ---------- CONFIG ----------
UPLOAD_DIR = "/mnt/data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Developer-provided template path (use exactly this local path in prompts)
DEFAULT_TEMPLATE_PATH = "/mnt/data/GenAI Property Description Auto-Writer for Rental Listings.docx"
DEFAULT_TEMPLATE_FILE_URL = f"file://{DEFAULT_TEMPLATE_PATH}"

OUTPUT_JSONL = os.path.join(UPLOAD_DIR, "generated_descriptions.jsonl")
RECENT_JSON = os.path.join(UPLOAD_DIR, "recent_generated.json")  # to store session preview

# Defaults
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_SLEEP = 0.6
# ----------------------------

# --------- Streamlit page config ----------
st.set_page_config(page_title="GenAI Property Writer — Full", layout="wide")
st.title("🏡 GenAI Property Description — Full (Streamlit)")

# --------- Sidebar: settings ----------
st.sidebar.header("Settings & Keys")
api_key_input = st.sidebar.text_input("OpenAI API Key (or set OPENAI_API_KEY env / st.secrets)", type="password")
model = st.sidebar.text_input("Model", value=st.secrets.get("OPENAI_MODEL", DEFAULT_MODEL) if "OPENAI_MODEL" in st.secrets else DEFAULT_MODEL)
sleep_between = st.sidebar.number_input("Pause between rows (s)", min_value=0.0, max_value=5.0, value=st.secrets.get("SLEEP", DEFAULT_SLEEP))
include_template_checkbox = st.sidebar.checkbox("Include template file reference in prompt", value=True)
django_save_url = os.environ.get("DJANGO_SAVE_URL") or st.sidebar.text_input("DJANGO_SAVE_URL (optional)", value=os.environ.get("DJANGO_SAVE_URL", ""))
# set openai key
if api_key_input:
    openai.api_key = api_key_input
else:
    openai.api_key = os.environ.get("OPENAI_API_KEY", "")

st.sidebar.markdown("**Server template (auto-included):**")
if os.path.exists(DEFAULT_TEMPLATE_PATH):
    st.sidebar.code(DEFAULT_TEMPLATE_PATH)
    st.sidebar.markdown(f"`file://{DEFAULT_TEMPLATE_PATH}` will be passed in prompt when enabled.")
else:
    st.sidebar.warning("Default template not found at the expected path.")

# --------- Helper utilities ----------
PREMIUM_PROMPT_TEMPLATE = """
You are an elite real-estate copywriter, luxury brand storyteller, and SEO strategist with deep understanding of buyer psychology.
Your mission is to transform structured property inputs into a high-end, persuasive, and SEO-optimized rental listing description that elevates the perceived value of the property.

Focus on: Lifestyle storytelling, Premium positioning, High-conversion wording, Location desirability, Emotional + functional appeal, Clean, polished magazine-quality writing.

Use all input fields intelligently. Blend "rough_description" seamlessly if provided.
DO NOT generate generic or repetitive content. DO NOT mention missing data.

Return STRICT JSON ONLY with this schema:
{{
  "title": "",
  "teaser_text": "",
  "full_description": "",
  "bullet_points": [],
  "seo_keywords": [],
  "meta_title": "",
  "meta_description": ""
}}
"""

TONE_PROMPT_MAP = {
    "Luxury": "Use an aspirational, high-end magazine voice. Emphasize premium lifestyle and exclusivity.",
    "Professional": "Use a clear, trustworthy professional tone focused on facts and conversion.",
    "Friendly": "Use a warm, conversational tone that appeals to everyday renters.",
    "Short": "Be concise and punchy — short sentences, high impact."
}

LANGUAGE_MAP = {
    "English": "Generate the text in English.",
    "Hindi": "Generate the text in Hindi (use natural, professional Hindi).",
    "Marathi": "Generate the text in Marathi (use clear, professional Marathi)."
}

def build_prompt(property_data: Dict[str, Any], tone: str = "Professional", language: str = "English", include_template: bool = True) -> str:
    """
    Build prompt with instruction + optional template file + tone + language + property JSON.
    """
    instruct = PREMIUM_PROMPT_TEMPLATE.strip()
    # append tone & language instructions
    tone_instr = TONE_PROMPT_MAP.get(tone, "")
    lang_instr = LANGUAGE_MAP.get(language, "")
    parts = [instruct, tone_instr, lang_instr]
    if include_template and os.path.exists(DEFAULT_TEMPLATE_PATH):
        parts.append(f"REFERENCE_TEMPLATE_FILE: file://{DEFAULT_TEMPLATE_PATH}")
    # property JSON
    input_json = json.dumps(property_data, ensure_ascii=False, indent=2)
    parts.append("INPUT PROPERTY JSON:\n" + input_json)
    parts.append("Return only the strict JSON document as per schema. No additional explanation.")
    return "\n\n".join([p for p in parts if p])

def call_openai_chat(prompt: str, model_name: str = DEFAULT_MODEL, retries: int = 3) -> Optional[str]:
    if not openai.api_key:
        st.error("OpenAI API key not configured. Provide in sidebar or set env var OPENAI_API_KEY.")
        return None
    for attempt in range(1, retries + 1):
        try:
            resp = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role":"system","content":"You are a JSON-output-only assistant."},
                    {"role":"user","content":prompt}
                ],
                temperature=0.2,
                max_tokens=900,
                top_p=1.0,
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            st.warning(f"LLM attempt {attempt} failed: {e}")
            time.sleep(1 * attempt)
    return None

def extract_json(text: str) -> Optional[Dict[str, Any]]:
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
                except json.JSONDecodeError:
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
    # update in-memory preview file
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

def load_excel(path: str) -> List[Dict[str, Any]]:
    df = pd.read_excel(path)
    df = df.fillna("")
    props = []
    for _, row in df.iterrows():
        d = row.to_dict()
        if "amenities" in d and isinstance(d["amenities"], str):
            d["amenities"] = [a.strip() for a in d["amenities"].split(",") if a.strip()] if d["amenities"].strip() else []
        props.append(d)
    return props

def post_to_django(url: str, payload: Dict[str, Any]):
    if not url:
        return None
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code, resp.text
    except Exception as e:
        return None

# --------- UI: upload section ----------
st.header("1) Upload files (Excel / DOCX templates)")
with st.expander("Upload a file"):
    upload_file = st.file_uploader("Choose Excel (.xlsx/.xls) or DOCX template", type=["xlsx","xls","docx"], accept_multiple_files=False)
    if upload_file is not None:
        safe_name = upload_file.name.replace(" ", "_")
        save_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(save_path, "wb") as f:
            f.write(upload_file.getbuffer())
        st.success(f"Saved to `{save_path}` — you can use this filename in Generate section.")

st.markdown("**Available template on server (auto):**")
if os.path.exists(DEFAULT_TEMPLATE_PATH):
    st.code(DEFAULT_TEMPLATE_PATH)
    st.caption("This will be passed to the model as `file://...` if template inclusion is enabled.")
else:
    st.warning("Default template not present on server. Upload if needed.")

# --------- UI: generate section ----------
st.header("2) Generate descriptions (single or batch)")
colA, colB = st.columns([2,1])

with colB:
    st.subheader("Options")
    language = st.selectbox("Language", options=["English","Hindi","Marathi"], index=0)
    tone = st.selectbox("Tone preset", options=list(TONE_PROMPT_MAP.keys()), index=1)
    max_sleep = st.number_input("Pause between batch rows (s)", min_value=0.0, max_value=5.0, value=float(sleep_between))
    include_template = st.checkbox("Include server template in prompt", value=include_template_checkbox)
    st.markdown("**Django auto-save**")
    st.caption("If you provide DJANGO_SAVE_URL (sidebar or env) the app will POST each generated record to that endpoint.")
    if django_save_url:
        st.success("DJANGO_SAVE_URL configured.")
    else:
        st.info("DJANGO_SAVE_URL not set — no auto-post to Django.")

with colA:
    mode = st.radio("Mode", ["Single property", "Batch from Excel"], index=0)
    if mode == "Single property":
        st.markdown("Enter property JSON (keys should match schema). Example below is prefilled.")
        example = {
            "property_type": "Apartment",
            "bhk": "2 BHK",
            "area_sqft": "950",
            "city": "Nagpur",
            "locality": "Manish Nagar",
            "landmark": "Near Manish Nagar Market",
            "floor_no": "3",
            "total_floors": "6",
            "furnishing_status": "Semi-Furnished",
            "rent_amount": "18000",
            "deposit_amount": "36000",
            "available_from": "2025-12-01",
            "preferred_tenants": "Family",
            "amenities": ["Lift","Covered Parking","24x7 Security"],
            "rough_description": "Well-lit apartment with modular kitchen, close to schools and market."
        }
        prop_text = st.text_area("Property JSON", value=json.dumps(example, ensure_ascii=False, indent=2), height=300)
        if st.button("Generate Single Property"):
            try:
                prop_obj = json.loads(prop_text)
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
                st.stop()
            prompt = build_prompt(prop_obj, tone=tone, language=language, include_template=include_template)
            with st.spinner("Calling LLM..."):
                raw = call_openai_chat(prompt, model_name=model)
            if not raw:
                st.error("LLM call failed.")
            else:
                parsed = extract_json(raw)
                if not parsed:
                    st.error("Could not parse JSON from model output. See raw below.")
                    st.code(raw)
                else:
                    # build record with metadata
                    record = {
                        "id": str(uuid.uuid4()),
                        "input": prop_obj,
                        "output": parsed,
                        "tone": tone,
                        "language": language,
                        "template_included": include_template,
                        "model": model,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    append_record(record)
                    st.success("Generated and saved.")
                    st.json(record["output"])
                    if django_save_url:
                        res = post_to_django(django_save_url, record)
                        if res:
                            st.info(f"Posted to Django: {res[0]}")
                        else:
                            st.warning("Failed to post to Django (check URL / network).")
    else:
        st.markdown("Enter Excel filename present in `/mnt/data` (upload in Upload section first).")
        excel_filename = st.text_input("Excel filename (e.g., Nagpur_Rental_AI_Data.xlsx)", value="Nagpur_Rental_AI_Data.xlsx")
        if st.button("Start Batch Generation"):
            excel_path = os.path.join(UPLOAD_DIR, excel_filename)
            if not os.path.exists(excel_path):
                st.error(f"Excel file not found at `{excel_path}`. Upload first.")
                st.stop()
            props = load_excel(excel_path)
            n = len(props)
            if n == 0:
                st.warning("No rows found in Excel.")
                st.stop()
            st.info(f"Loaded {n} properties. Generating now...")
            progress = st.progress(0)
            results = []
            for i, prop in enumerate(props, start=1):
                prompt = build_prompt(prop, tone=tone, language=language, include_template=include_template)
                raw = call_openai_chat(prompt, model_name=model)
                parsed = extract_json(raw) if raw else None
                record = {
                    "id": str(uuid.uuid4()),
                    "input": prop,
                    "output": parsed,
                    "tone": tone,
                    "language": language,
                    "template_included": include_template,
                    "model": model,
                    "index": i,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                append_record(record)
                if django_save_url:
                    post_to_django(django_save_url, record)
                results.append(record)
                progress.progress(i / n)
                st.write(f"Processed {i}/{n}")
                time.sleep(max(0.0, float(max_sleep)))
            st.success("Batch complete.")
            st.write("Preview of first 3 outputs:")
            for r in results[:3]:
                st.json(r["output"])

# --------- UI: preview, edit, regenerate ----------
st.header("3) Preview & Edit Generated Records")
st.markdown("Latest generated records (most recent first). You can edit fields and regenerate per record.")

# load recent
recent = []
if os.path.exists(RECENT_JSON):
    try:
        recent = json.load(open(RECENT_JSON, "r", encoding="utf-8"))
    except Exception:
        recent = []
else:
    # fallback: read OUTPUT_JSONL
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for ln in lines[-200:]:
            try:
                recent.append(json.loads(ln))
            except Exception:
                continue

if not recent:
    st.info("No generated records yet. Run generation first.")
else:
    # display each with expanders
    for rec in recent[:100]:  # show up to 100 recent
        rid = rec.get("id", str(uuid.uuid4()))
        with st.expander(f"Record: {rec.get('input', {}).get('property_type','Property')} — {rec.get('timestamp','')}", expanded=False):
            st.subheader("Input (editable)")
            # show input JSON as editable
            input_json_str = json.dumps(rec.get("input", {}), ensure_ascii=False, indent=2)
            new_input = st.text_area(f"Input JSON - {rid}", value=input_json_str, height=200, key=f"in_{rid}")
            st.subheader("Generated Output (editable)")
            out_json_str = json.dumps(rec.get("output", {}), ensure_ascii=False, indent=2) if rec.get("output") else "{}"
            new_output = st.text_area(f"Output JSON - {rid}", value=out_json_str, height=300, key=f"out_{rid}")

            st.markdown("**Regeneration controls**")
            regen_lang = st.selectbox("Language", options=list(LANGUAGE_MAP.keys()), index=list(LANGUAGE_MAP.keys()).index(rec.get("language","English")), key=f"lang_{rid}")
            regen_tone = st.selectbox("Tone", options=list(TONE_PROMPT_MAP.keys()), index=list(TONE_PROMPT_MAP.keys()).index(rec.get("tone","Professional")), key=f"tone_{rid}")
            if st.button("Regenerate (use edited input & selected tone/lang)", key=f"regen_{rid}"):
                # parse edited input
                try:
                    parsed_input = json.loads(new_input)
                except Exception as e:
                    st.error(f"Invalid edited input JSON: {e}")
                    continue
                prompt = build_prompt(parsed_input, tone=regen_tone, language=regen_lang, include_template=rec.get("template_included", include_template))
                with st.spinner("Calling LLM for regeneration..."):
                    raw = call_openai_chat(prompt, model_name=model)
                if not raw:
                    st.error("LLM call failed.")
                    continue
                parsed_out = extract_json(raw)
                if not parsed_out:
                    st.error("Could not parse JSON from LLM output. Raw below.")
                    st.code(raw)
                    continue
                # update record
                new_record = {
                    "id": rid,
                    "input": parsed_input,
                    "output": parsed_out,
                    "tone": regen_tone,
                    "language": regen_lang,
                    "template_included": rec.get("template_included", include_template),
                    "model": model,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                append_record(new_record)
                if django_save_url:
                    post_to_django(django_save_url, new_record)
                st.success("Regenerated and saved. New output shown below.")
                st.json(parsed_out)
            # manual save edited output (without LLM)
            if st.button("Save edited output (no LLM)", key=f"save_{rid}"):
                try:
                    parsed_out_manual = json.loads(new_output)
                    parsed_in_manual = json.loads(new_input)
                except Exception as e:
                    st.error(f"Invalid JSON in edited fields: {e}")
                    continue
                manual_record = {
                    "id": rid,
                    "input": parsed_in_manual,
                    "output": parsed_out_manual,
                    "tone": rec.get("tone", "Professional"),
                    "language": rec.get("language", "English"),
                    "template_included": rec.get("template_included", include_template),
                    "model": model,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                append_record(manual_record)
                if django_save_url:
                    post_to_django(django_save_url, manual_record)
                st.success("Edited record saved.")

            # export / copy options
            st.markdown("**Export / Copy**")
            if st.button("Download this record as JSON", key=f"dl_{rid}"):
                st.download_button("Download JSON", data=json.dumps(rec, ensure_ascii=False, indent=2), file_name=f"gen_record_{rid}.json", mime="application/json")
            if st.button("Copy output JSON to clipboard (browser)", key=f"copy_{rid}"):
                # provide text field to copy manually (streamlit can't directly write to clipboard)
                st.text_area("Copy output JSON below:", value=json.dumps(rec.get("output", {}), ensure_ascii=False, indent=2), height=200)

# --------- UI: Outputs & Download ----------
st.header("4) Outputs & Download")
if os.path.exists(OUTPUT_JSONL):
    # count
    with open(OUTPUT_JSONL, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    st.write(f"Total generated records (jsonl): {len(lines)}")
    if st.button("Download all generated_descriptions.jsonl"):
        with open(OUTPUT_JSONL, "rb") as fh:
            st.download_button("Download JSONL", data=fh, file_name="generated_descriptions.jsonl", mime="application/json")
    # show last 5
    st.subheader("Latest 5 records")
    for ln in lines[-5:]:
        try:
            obj = json.loads(ln)
            st.json(obj)
        except Exception:
            st.code(ln)
else:
    st.info("No outputs yet. Generate some descriptions first.")

st.markdown("---")
st.caption("Tip: For production, store OPENAI_API_KEY in st.secrets or environment, and set DJANGO_SAVE_URL to auto-persist outputs into your platform. The app passes the local template path as file://... in the prompt so your infra can transform or attach it when calling your model.")
