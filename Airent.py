"""
AI Property Description Generator - INTERACTIVE COLUMN MAPPER
Multiple AI APIs support: Claude, Grok (Free), OpenAI
"""

import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from io import BytesIO

# Page Configuration
st.set_page_config(
    page_title="AI Property Description Generator",
    page_icon="🏠",
    layout="wide"
)


# ==================== INTERACTIVE PARSER ====================
class InteractiveParser:
    """Parser with interactive column mapping"""
    
    REQUIRED_FIELDS = {
        'property_type': 'Type of property (flat, villa, pg, shop, office)',
        'bhk': 'Number of bedrooms (2, 3, 1 BHK)',
        'area_sqft': 'Area in square feet',
        'city': 'City name (Mumbai, Delhi, etc)',
        'locality': 'Area/Locality name',
        'furnishing_status': 'Furnishing (unfurnished, semi, fully)',
        'rent_amount': 'Monthly rent amount',
        'deposit_amount': 'Security deposit amount',
        'available_from': 'Date when available',
        'preferred_tenants': 'Type of tenants (Family, Bachelor, etc)'
    }
    
    def __init__(self):
        self.errors = []
    
    def read_file(self, uploaded_file):
        """Read file without any changes"""
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            return df
        except Exception as e:
            self.errors.append(f"Error: {str(e)}")
            return None
    
    def apply_mapping(self, df, mapping):
        """Apply user's column mapping"""
        return df.rename(columns=mapping)
    
    def clean_and_process(self, df):
        """Clean and process data"""
        properties = []
        
        for idx, row in df.iterrows():
            try:
                # Parse amenities
                amenities = []
                if 'amenities' in row.index and pd.notna(row.get('amenities')):
                    amenities = [a.strip() for a in str(row['amenities']).split(',')]
                
                # Parse date
                available_from = row.get('available_from', datetime.now().date())
                if isinstance(available_from, str):
                    available_from = pd.to_datetime(available_from).date()
                elif isinstance(available_from, pd.Timestamp):
                    available_from = available_from.date()
                
                properties.append({
                    'property_type': str(row['property_type']).lower().strip(),
                    'bhk': str(row['bhk']).strip(),
                    'area_sqft': int(float(row['area_sqft'])),
                    'city': str(row['city']).strip(),
                    'locality': str(row['locality']).strip(),
                    'landmark': str(row.get('landmark', '')).strip(),
                    'floor_no': int(float(row['floor_no'])) if pd.notna(row.get('floor_no')) else None,
                    'total_floors': int(float(row['total_floors'])) if pd.notna(row.get('total_floors')) else None,
                    'furnishing_status': str(row['furnishing_status']).lower().strip(),
                    'rent_amount': float(row['rent_amount']),
                    'deposit_amount': float(row['deposit_amount']),
                    'available_from': str(available_from),
                    'preferred_tenants': str(row['preferred_tenants']).strip(),
                    'amenities': amenities,
                    'rough_description': str(row.get('rough_description', '')).strip(),
                })
            except Exception as e:
                self.errors.append(f"Row {idx+2}: {str(e)}")
        
        return properties


# ==================== AI GENERATION ====================
def generate_with_groq(property_data, api_key):
    """Generate description using Groq API (Free & Super Fast)"""
    try:
        bhk = property_data['bhk']
        prop_type = property_data['property_type'].title()
        locality = property_data['locality']
        city = property_data['city']
        area = property_data['area_sqft']
        rent = property_data['rent_amount']
        furnishing = property_data['furnishing_status']
        amenities = ', '.join(property_data['amenities']) if property_data['amenities'] else 'Standard amenities'
        
        prompt = f"""Generate a professional rental property listing description in JSON format.

Property Details:
- Type: {bhk} BHK {prop_type}
- Location: {locality}, {city}
- Area: {area} sqft
- Rent: Rs.{rent}/month
- Furnishing: {furnishing}
- Amenities: {amenities}
- Preferred Tenants: {property_data['preferred_tenants']}

Return ONLY valid JSON with these exact fields:
{{
    "title": "catchy property title (8-12 words)",
    "teaser_text": "short engaging teaser (15-20 words)",
    "full_description": "detailed description highlighting location, features, and value (100-150 words)",
    "bullet_points": ["key feature 1", "key feature 2", "key feature 3", "key feature 4", "key feature 5"],
    "seo_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "meta_title": "SEO title under 60 characters",
    "meta_description": "SEO description under 160 characters"
}}

Return ONLY the JSON object, no markdown, no explanations."""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key.strip()}"
            },
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 1500,
                "top_p": 1,
                "stream": False,
                "stop": None
            },
            timeout=30
        )
        
        # Debug info with full error details
        if response.status_code != 200:
            error_detail = response.text
            st.error(f"❌ Groq API Error Code: {response.status_code}")
            
            with st.expander("🔍 Full Error Details (Click here)"):
                st.code(error_detail, language="json")
                st.write("**Request Details:**")
                st.write(f"- API Key Length: {len(api_key)}")
                st.write(f"- API Key Starts: {api_key[:8]}...")
                st.write(f"- Model: llama-3.1-70b-versatile")
            
            # Common error solutions
            if response.status_code == 400:
                st.warning("💡 **Possible Issues:**")
                st.markdown("""
                - API key might be invalid or inactive
                - Check if API key is correctly copied (no extra spaces)
                - Verify model name is correct
                - Try regenerating API key at console.groq.com
                """)
            elif response.status_code == 401:
                st.warning("💡 **401 Unauthorized** - API key is invalid. Get a new one from console.groq.com")
            elif response.status_code == 429:
                st.warning("💡 **429 Rate Limit** - Free tier limit reached")
            elif response.status_code == 500:
                st.warning("💡 **500 Server Error** - Groq server issue, try again")
            
            return None
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Clean markdown formatting if present
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        
        return json.loads(content)
            
    except requests.exceptions.Timeout:
        st.error("Groq API timeout - trying fallback...")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Groq API connection error: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Groq returned invalid JSON: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Groq API Error: {str(e)}")
        return None


def generate_with_grok(property_data, api_key):
    """Generate description using Grok API (Free Tier)"""
    try:
        bhk = property_data['bhk']
        prop_type = property_data['property_type'].title()
        locality = property_data['locality']
        city = property_data['city']
        area = property_data['area_sqft']
        rent = property_data['rent_amount']
        furnishing = property_data['furnishing_status']
        amenities = ', '.join(property_data['amenities']) if property_data['amenities'] else 'Standard amenities'
        
        prompt = f"""Generate a professional rental property listing description in JSON format for:

Property Details:
- Type: {bhk} BHK {prop_type}
- Location: {locality}, {city}
- Area: {area} sqft
- Rent: Rs.{rent}/month
- Furnishing: {furnishing}
- Amenities: {amenities}
- Preferred Tenants: {property_data['preferred_tenants']}

Generate ONLY valid JSON with these fields:
{{
    "title": "catchy 8-12 word title",
    "teaser_text": "short 15-20 word teaser",
    "full_description": "detailed 100-150 word description highlighting key features",
    "bullet_points": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5"],
    "seo_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "meta_title": "SEO optimized title under 60 chars",
    "meta_description": "SEO description under 160 chars"
}}

Return ONLY the JSON, no explanations."""

        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "messages": [
                    {"role": "system", "content": "You are a professional real estate content writer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "model": "grok-beta",
                "stream": False,
                "temperature": 0.7
            },
            timeout=60
        )
        
        # Debug info with full error details
        if response.status_code != 200:
            error_detail = response.text
            st.error(f"❌ Grok API Error Code: {response.status_code}")
            with st.expander("🔍 Click to see full error details"):
                st.code(error_detail)
            
            # Common error solutions
            if response.status_code == 400:
                st.warning("💡 **400 Bad Request** - Possible issues:")
                st.markdown("""
                - Check if API key is correct (should start with `xai-`)
                - Model name might be incorrect
                - Request format issue
                """)
            elif response.status_code == 401:
                st.warning("💡 **401 Unauthorized** - API key is invalid or expired")
            elif response.status_code == 429:
                st.warning("💡 **429 Rate Limit** - Too many requests, wait a bit")
            
            return None
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Clean markdown formatting if present
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        
        return json.loads(content)
            
    except requests.exceptions.Timeout:
        st.error("Grok API timeout - trying again with fallback...")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Grok API connection error: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Grok returned invalid JSON: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Grok API Error: {str(e)}")
        return None


def generate_with_claude(property_data, api_key):
    """Generate description using Claude API"""
    try:
        bhk = property_data['bhk']
        prop_type = property_data['property_type'].title()
        locality = property_data['locality']
        city = property_data['city']
        
        prompt = f"""Generate a rental property description in JSON format for:
{bhk} BHK {prop_type} in {locality}, {city}
Area: {property_data['area_sqft']} sqft, Rent: Rs.{property_data['rent_amount']}
Furnishing: {property_data['furnishing_status']}

Return ONLY valid JSON with fields: title, teaser_text, full_description, bullet_points[], seo_keywords[], meta_title, meta_description"""
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['content'][0]['text']
            return json.loads(content)
        else:
            raise Exception(f"Claude API Error: {response.status_code}")
            
    except Exception as e:
        st.error(f"Claude API Error: {str(e)}")
        return None


def generate_fallback(property_data):
    """Fallback template-based generation"""
    bhk = property_data['bhk']
    prop_type = property_data['property_type'].title()
    locality = property_data['locality']
    city = property_data['city']
    area = property_data['area_sqft']
    rent = property_data['rent_amount']
    furnishing = property_data['furnishing_status'].title()
    
    return {
        "title": f"Spacious {bhk} BHK {prop_type} for Rent in {locality}",
        "teaser_text": f"Well-maintained {bhk} BHK {prop_type} in prime {locality} location",
        "full_description": f"Looking for a comfortable home? This beautiful {bhk} BHK {prop_type} in {locality}, {city} is perfect for you. Spread across {area} sqft, this {furnishing} furnished property offers great value at Rs.{rent}/month. Located in a well-connected area with easy access to essential amenities.",
        "bullet_points": [
            f"{bhk} BHK configuration with {area} sqft carpet area",
            f"{furnishing} furnished with modern fittings",
            f"Monthly rent: Rs.{rent} | Deposit: Rs.{property_data['deposit_amount']}",
            f"Preferred for: {property_data['preferred_tenants']}",
            f"Available from: {property_data['available_from']}"
        ],
        "seo_keywords": [
            f"{bhk} bhk {city}",
            f"{locality} rental",
            f"{prop_type} for rent {city}",
            f"{furnishing} flat {locality}",
            f"rent {bhk}bhk {city}"
        ],
        "meta_title": f"{bhk} BHK {prop_type} for Rent in {locality}, {city}",
        "meta_description": f"Rent this spacious {bhk} BHK {prop_type} in {locality}, {city}. {area} sqft, {furnishing} furnished. Rs.{rent}/month. Available now!"
    }


def generate_description(property_data, api_provider, api_key=None):
    """Main generation function with multiple providers"""
    if api_provider == "Groq (Free & Fast)" and api_key:
        result = generate_with_groq(property_data, api_key)
        if result:
            return result
    elif api_provider == "Grok (X.AI)" and api_key:
        result = generate_with_grok(property_data, api_key)
        if result:
            return result
    elif api_provider == "Claude" and api_key:
        result = generate_with_claude(property_data, api_key)
        if result:
            return result
    
    # Fallback to template
    return generate_fallback(property_data)


# ==================== MAIN APP ====================
def main():
    st.title("🏠 AI Property Description Generator")
    st.caption("Powered by Multiple AI Models - Grok Free API Support")
    
    # Initialize session state
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    if 'df_original' not in st.session_state:
        st.session_state.df_original = None
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # AI Provider Selection
        api_provider = st.selectbox(
            "Select AI Provider",
            ["Template (No API)", "Groq (Free & Fast)", "Grok (X.AI)", "Claude"],
            help="Groq & Grok both offer free tier API access!"
        )
        
        # API Key Input
        api_key = None
        if api_provider != "Template (No API)":
            if api_provider == "Groq (Free & Fast)":
                st.info("🆓 Get free Groq API key from: https://console.groq.com")
                api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
            elif api_provider == "Grok (X.AI)":
                st.info("🆓 Get free Grok API key from: https://console.x.ai")
                api_key = st.text_input("Grok API Key", type="password", placeholder="xai-...")
            else:
                st.info("Get Claude API key from: https://console.anthropic.com")
                api_key = st.text_input("Claude API Key", type="password", placeholder="sk-ant-...")
        
        st.divider()
        mode = st.radio("Mode", ["Single Property", "Bulk Upload"])
        
        # API Info
        with st.expander("ℹ️ About API Providers"):
            st.markdown("""
            **Groq (Free & Fast):**
            - ✅ Free tier with generous limits
            - ⚡ Super fast inference (fastest!)
            - 🎯 Llama 3.1 70B model
            - Get key: console.groq.com
            
            **Grok (X.AI):**
            - ✅ Free tier available
            - 🤖 Grok-beta model
            - 💬 Good conversational AI
            - Get key: console.x.ai
            
            **Claude:**
            - 👑 Premium quality
            - 📝 Excellent SEO optimization
            - 💰 Paid API (credits required)
            - Get key: console.anthropic.com
            
            **Template (No API):**
            - 🆓 No API key needed
            - ⚡ Instant generation
            - 📄 Basic quality
            """)
    
    if mode == "Single Property":
        show_single_property(api_provider, api_key)
    else:
        show_bulk_upload(api_provider, api_key)


def show_single_property(api_provider, api_key):
    """Single property form"""
    st.subheader("Enter Property Details")
    
    col1, col2 = st.columns(2)
    with col1:
        property_type = st.selectbox("Property Type", ["flat", "villa", "pg", "shop", "office"])
        bhk = st.text_input("BHK", "2")
        area_sqft = st.number_input("Area (sqft)", value=1000, min_value=100)
        city = st.text_input("City", "Mumbai")
        locality = st.text_input("Locality", "Andheri")
    
    with col2:
        furnishing = st.selectbox("Furnishing", ["unfurnished", "semi", "fully"])
        rent = st.number_input("Monthly Rent (₹)", value=25000)
        deposit = st.number_input("Deposit (₹)", value=50000)
        available = st.date_input("Available From")
        tenants = st.text_input("Preferred Tenants", "Family")
    
    amenities = st.text_input("Amenities (comma separated)", "Parking, Gym, Security")
    
    if st.button("🚀 Generate Description", type="primary", use_container_width=True):
        property_data = {
            'property_type': property_type, 'bhk': bhk, 'area_sqft': area_sqft,
            'city': city, 'locality': locality, 'furnishing_status': furnishing,
            'rent_amount': rent, 'deposit_amount': deposit,
            'available_from': str(available), 'preferred_tenants': tenants,
            'amenities': [a.strip() for a in amenities.split(',')],
            'landmark': '', 'floor_no': None, 
            'total_floors': None, 'rough_description': ''
        }
        
        with st.spinner(f"Generating with {api_provider}..."):
            result = generate_description(property_data, api_provider, api_key)
        
        if result:
            st.success("✅ Generated Successfully!")
            
            # Display results
            st.markdown(f"### {result['title']}")
            st.caption(result['teaser_text'])
            st.divider()
            
            st.markdown("**Full Description:**")
            st.write(result['full_description'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Key Features:**")
                for point in result['bullet_points']:
                    st.markdown(f"• {point}")
            
            with col2:
                st.markdown("**SEO Keywords:**")
                st.write(", ".join(result['seo_keywords']))
            
            st.divider()
            st.markdown("**SEO Metadata:**")
            st.text(f"Title: {result['meta_title']}")
            st.text(f"Description: {result['meta_description']}")


def show_bulk_upload(api_provider, api_key):
    """Bulk upload with interactive mapper"""
    st.subheader("Bulk Upload - Interactive Column Mapping")
    
    # Template
    with st.expander("📥 Download Template", expanded=False):
        template = pd.DataFrame({
            'property_type': ['flat', 'villa'],
            'bhk': ['2', '3'],
            'area_sqft': [1200, 2500],
            'city': ['Mumbai', 'Pune'],
            'locality': ['Andheri', 'Kothrud'],
            'landmark': ['Metro', 'FC Road'],
            'floor_no': [5, 1],
            'total_floors': [10, 2],
            'furnishing_status': ['semi', 'fully'],
            'rent_amount': [25000, 45000],
            'deposit_amount': [50000, 90000],
            'available_from': ['2024-12-01', '2024-12-15'],
            'preferred_tenants': ['Family', 'Family'],
            'amenities': ['Parking,Gym', 'Pool,Garden'],
            'rough_description': ['Nice flat', 'Luxury villa']
        })
        
        st.dataframe(template)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📄 CSV", template.to_csv(index=False), "template.csv")
        with col2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template.to_excel(writer, index=False)
            st.download_button("📊 Excel", output.getvalue(), "template.xlsx")
    
    st.divider()
    
    # File Upload
    uploaded_file = st.file_uploader("Upload Your File", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file:
        parser = InteractiveParser()
        df = parser.read_file(uploaded_file)
        
        if df is not None:
            st.session_state.df_original = df
            
            st.success(f"✅ File loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # Show all columns from file
            st.subheader("📋 Your File Has These Columns:")
            
            your_columns = list(df.columns)
            
            # Display in a nice grid
            cols_per_row = 4
            for i in range(0, len(your_columns), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(your_columns[i:i+cols_per_row]):
                    with cols[j]:
                        st.info(f"**{col}**")
            
            st.divider()
            
            # Interactive Mapping Section
            st.subheader("🔗 Map Your Columns to Required Fields")
            st.write("For each required field, select which column from your file contains that data:")
            
            parser_obj = InteractiveParser()
            
            for required_field, description in parser_obj.REQUIRED_FIELDS.items():
                st.markdown(f"**{required_field}** - *{description}*")
                
                # Check if already mapped
                current_mapping = st.session_state.column_mapping.get(required_field, None)
                
                # Create selectbox with current mapping as default
                if current_mapping and current_mapping in your_columns:
                    default_index = your_columns.index(current_mapping) + 1
                else:
                    default_index = 0
                
                selected = st.selectbox(
                    f"Select column for '{required_field}':",
                    ['-- Select Column --'] + your_columns,
                    index=default_index,
                    key=f"select_{required_field}"
                )
                
                if selected != '-- Select Column --':
                    st.session_state.column_mapping[required_field] = selected
                    st.success(f"✓ Mapped: **{selected}** → **{required_field}**")
                else:
                    st.warning(f"⚠ Not mapped yet")
                
                st.divider()
            
            # Show current mapping summary
            if st.session_state.column_mapping:
                st.subheader("📊 Current Mapping Summary")
                
                mapping_data = []
                for req_field in parser_obj.REQUIRED_FIELDS.keys():
                    mapped_to = st.session_state.column_mapping.get(req_field, "NOT MAPPED")
                    status = "✅" if mapped_to != "NOT MAPPED" else "❌"
                    mapping_data.append({
                        "Status": status,
                        "Required Field": req_field,
                        "Your Column": mapped_to
                    })
                
                mapping_df = pd.DataFrame(mapping_data)
                st.dataframe(mapping_df, use_container_width=True)
            
            # Check if all required fields are mapped
            all_mapped = all(
                field in st.session_state.column_mapping 
                for field in parser_obj.REQUIRED_FIELDS.keys()
            )
            
            if all_mapped:
                st.success("🎉 All required fields are mapped!")
                
                # Create reverse mapping (your_column -> required_field)
                reverse_mapping = {v: k for k, v in st.session_state.column_mapping.items()}
                
                # Apply mapping
                df_mapped = parser.apply_mapping(df, reverse_mapping)
                
                # Show preview
                st.subheader("👀 Preview Mapped Data")
                preview_cols = list(parser_obj.REQUIRED_FIELDS.keys())
                available_preview = [col for col in preview_cols if col in df_mapped.columns]
                st.dataframe(df_mapped[available_preview].head(), use_container_width=True)
                
                # Process button
                st.divider()
                if st.button("🚀 Process All Properties", type="primary", use_container_width=True):
                    with st.spinner("Processing..."):
                        properties = parser.clean_and_process(df_mapped)
                        
                        if properties:
                            st.success(f"✅ Processed {len(properties)} properties!")
                            
                            # Generate descriptions
                            progress = st.progress(0)
                            status_text = st.empty()
                            results = []
                            
                            for idx, prop in enumerate(properties):
                                status_text.text(f"Generating description {idx+1}/{len(properties)} using {api_provider}...")
                                desc = generate_description(prop, api_provider, api_key)
                                results.append({'property': prop, 'description': desc})
                                progress.progress((idx + 1) / len(properties))
                            
                            progress.empty()
                            status_text.empty()
                            st.success(f"🎉 Generated {len(results)} descriptions!")
                            
                            # Create output
                            output_data = []
                            for item in results:
                                p = item['property']
                                d = item['description']
                                output_data.append({
                                    'Type': p['property_type'],
                                    'BHK': p['bhk'],
                                    'City': p['city'],
                                    'Locality': p['locality'],
                                    'Area': p['area_sqft'],
                                    'Rent': p['rent_amount'],
                                    'Title': d['title'],
                                    'Teaser': d['teaser_text'],
                                    'Description': d['full_description'],
                                    'Features': ' | '.join(d['bullet_points']),
                                    'SEO_Keywords': ', '.join(d['seo_keywords']),
                                    'Meta_Title': d['meta_title'],
                                    'Meta_Description': d['meta_description']
                                })
                            
                            result_df = pd.DataFrame(output_data)
                            
                            # Download
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                result_df.to_excel(writer, index=False)
                            
                            st.download_button(
                                "📥 Download All Descriptions",
                                output.getvalue(),
                                f"descriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                            
                            with st.expander("📊 Preview Results"):
                                st.dataframe(result_df.head(10))
                        else:
                            st.error("❌ No valid properties found")
                            if parser.errors:
                                for err in parser.errors:
                                    st.error(err)
            else:
                missing_count = len(parser_obj.REQUIRED_FIELDS) - len(st.session_state.column_mapping)
                st.warning(f"⚠ Please map all required fields. {missing_count} fields still need mapping.")


if __name__ == "__main__":
    main()
