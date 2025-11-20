"""
AI Property Description Generator - INTERACTIVE COLUMN MAPPER
Click karke columns map karo - Super Simple!
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
def generate_description(property_data, api_key=None):
    """Generate property description"""
    bhk = property_data['bhk']
    prop_type = property_data['property_type'].title()
    locality = property_data['locality']
    city = property_data['city']
    
    if api_key:
        try:
            prompt = f"""Generate rental property description as JSON:
{bhk} BHK {prop_type} in {locality}, {city}
Area: {property_data['area_sqft']} sqft, Rent: Rs.{property_data['rent_amount']}
Return JSON: title, teaser_text, full_description, bullet_points[], seo_keywords[], meta_title, meta_description"""
            
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
            result = response.json()
            return json.loads(result['content'][0]['text'])
        except:
            pass
    
    return {
        "title": f"Spacious {bhk} BHK {prop_type} for Rent in {locality}",
        "teaser_text": f"Well-maintained {bhk} BHK in {locality}, {city}",
        "full_description": f"Beautiful {bhk} BHK {prop_type} in {locality}, {city}. Area: {property_data['area_sqft']} sqft. {property_data['furnishing_status'].title()} furnished.",
        "bullet_points": [
            f"{bhk} BHK with {property_data['area_sqft']} sqft",
            f"{property_data['furnishing_status'].title()} furnishing",
            f"Rent: Rs.{property_data['rent_amount']}/month"
        ],
        "seo_keywords": [f"{bhk} bhk {city}", f"{locality} rental"],
        "meta_title": f"{bhk} BHK {prop_type} - {locality}",
        "meta_description": f"Rent {bhk} BHK in {locality}, {city}"
    }


# ==================== MAIN APP ====================
def main():
    st.title("🏠 AI Property Description Generator")
    
    # Initialize session state
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    if 'df_original' not in st.session_state:
        st.session_state.df_original = None
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Claude API Key", type="password")
        st.divider()
        mode = st.radio("Mode", ["Single Property", "Bulk Upload"])
    
    if mode == "Single Property":
        show_single_property(api_key)
    else:
        show_bulk_upload(api_key)


def show_single_property(api_key):
    """Single property form"""
    st.subheader("Enter Property Details")
    
    col1, col2 = st.columns(2)
    with col1:
        property_type = st.selectbox("Property Type", ["flat", "villa", "pg", "shop", "office"])
        bhk = st.text_input("BHK", "2")
        area_sqft = st.number_input("Area", value=1000, min_value=100)
        city = st.text_input("City", "Mumbai")
        locality = st.text_input("Locality", "Andheri")
    
    with col2:
        furnishing = st.selectbox("Furnishing", ["unfurnished", "semi", "fully"])
        rent = st.number_input("Rent", value=25000)
        deposit = st.number_input("Deposit", value=50000)
        available = st.date_input("Available From")
        tenants = st.text_input("Tenants", "Family")
    
    if st.button("Generate", type="primary"):
        property_data = {
            'property_type': property_type, 'bhk': bhk, 'area_sqft': area_sqft,
            'city': city, 'locality': locality, 'furnishing_status': furnishing,
            'rent_amount': rent, 'deposit_amount': deposit,
            'available_from': str(available), 'preferred_tenants': tenants,
            'amenities': [], 'landmark': '', 'floor_no': None, 
            'total_floors': None, 'rough_description': ''
        }
        
        result = generate_description(property_data, api_key)
        st.success("Generated!")
        st.markdown(f"### {result['title']}")
        st.write(result['full_description'])


def show_bulk_upload(api_key):
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
            st.download_button("CSV", template.to_csv(index=False), "template.csv")
        with col2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template.to_excel(writer, index=False)
            st.download_button("Excel", output.getvalue(), "template.xlsx")
    
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
                            results = []
                            
                            for idx, prop in enumerate(properties):
                                desc = generate_description(prop, api_key)
                                results.append({'property': prop, 'description': desc})
                                progress.progress((idx + 1) / len(properties))
                            
                            progress.empty()
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
                                    'Description': d['full_description'],
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
                            
                            with st.expander("Preview Results"):
                                st.dataframe(result_df.head())
                        else:
                            st.error("No valid properties found")
                            if parser.errors:
                                for err in parser.errors:
                                    st.error(err)
            else:
                missing_count = len(parser_obj.REQUIRED_FIELDS) - len(st.session_state.column_mapping)
                st.warning(f"⚠ Please map all required fields. {missing_count} fields still need mapping.")


if __name__ == "__main__":
    main()
