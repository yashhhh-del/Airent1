"""
AI Property Description Generator - FIXED VERSION
Simplified column detection with detailed debugging
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


# ==================== SIMPLE PARSER WITH DEBUG ====================
class SimplePropertyParser:
    """Simple parser with detailed debugging"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def normalize_column_name(self, col_name):
        """Normalize column names to lowercase with underscores"""
        return col_name.strip().lower().replace(' ', '_')
    
    def parse_file(self, uploaded_file):
        """Parse file and normalize columns"""
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Normalize all column names
            df.columns = [self.normalize_column_name(col) for col in df.columns]
            
            return df
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return None
    
    def check_required_columns(self, df):
        """Check which required columns are present"""
        required = [
            'property_type', 'bhk', 'area_sqft', 'city', 'locality',
            'furnishing_status', 'rent_amount', 'deposit_amount',
            'available_from', 'preferred_tenants'
        ]
        
        present = []
        missing = []
        
        for req in required:
            if req in df.columns:
                present.append(req)
            else:
                missing.append(req)
        
        return present, missing
    
    def clean_row(self, row):
        """Clean a single row"""
        try:
            # Parse amenities
            amenities = []
            if 'amenities' in row.index and pd.notna(row.get('amenities', '')):
                amenities_str = str(row['amenities'])
                amenities = [a.strip() for a in amenities_str.split(',')]
            
            # Parse date
            available_from = row.get('available_from', datetime.now().date())
            if isinstance(available_from, str):
                try:
                    available_from = pd.to_datetime(available_from).date()
                except:
                    available_from = datetime.now().date()
            elif isinstance(available_from, pd.Timestamp):
                available_from = available_from.date()
            
            return {
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
            }
        except Exception as e:
            self.warnings.append(f"Error: {str(e)}")
            return None
    
    def process_dataframe(self, df):
        """Process all rows"""
        properties = []
        for idx, row in df.iterrows():
            clean_data = self.clean_row(row)
            if clean_data:
                properties.append(clean_data)
        return properties
    
    @staticmethod
    def get_template():
        """Get template dataframe"""
        return pd.DataFrame({
            'property_type': ['flat', 'villa', 'pg'],
            'bhk': ['2', '3', '1'],
            'area_sqft': [1200, 2500, 400],
            'city': ['Mumbai', 'Bangalore', 'Pune'],
            'locality': ['Andheri West', 'Koramangala', 'Kothrud'],
            'landmark': ['Near Metro', 'Sony Signal', 'FC Road'],
            'floor_no': [5, 1, 2],
            'total_floors': [10, 2, 4],
            'furnishing_status': ['semi', 'fully', 'unfurnished'],
            'rent_amount': [25000, 45000, 8000],
            'deposit_amount': [50000, 90000, 16000],
            'available_from': ['2024-12-01', '2024-12-15', '2024-12-01'],
            'preferred_tenants': ['Family', 'Family', 'Students'],
            'amenities': ['Parking,Gym,Security', 'Garden,Pool,Backup', 'WiFi,Meals'],
            'rough_description': ['Spacious 2BHK', 'Luxury villa', 'Budget PG']
        })


# ==================== AI GENERATION ====================
def generate_description(property_data, api_key=None):
    """Generate property description"""
    
    # Demo mode
    bhk = property_data['bhk']
    prop_type = property_data['property_type'].title()
    locality = property_data['locality']
    city = property_data['city']
    
    if api_key:
        # Try AI generation
        try:
            prompt = f"""Generate a rental property description as JSON:
Property: {bhk} BHK {prop_type} in {locality}, {city}
Area: {property_data['area_sqft']} sqft, Rent: Rs.{property_data['rent_amount']}
Return JSON with: title, teaser_text, full_description, bullet_points (array), seo_keywords (array), meta_title, meta_description"""
            
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
            content = result['content'][0]['text']
            return json.loads(content)
        except:
            pass
    
    # Template description
    return {
        "title": f"Spacious {bhk} BHK {prop_type} for Rent in {locality}",
        "teaser_text": f"Well-maintained {bhk} BHK in {locality}, {city}",
        "full_description": f"Beautiful {bhk} BHK {prop_type} in {locality}, {city} with {property_data['area_sqft']} sqft area. {property_data['furnishing_status'].title()} furnished with modern amenities.",
        "bullet_points": [
            f"{bhk} BHK with {property_data['area_sqft']} sqft",
            f"{property_data['furnishing_status'].title()} furnishing",
            f"Rent: Rs.{property_data['rent_amount']}/month"
        ],
        "seo_keywords": [f"{bhk} bhk {city}", f"{locality} rental", f"{prop_type} {city}"],
        "meta_title": f"{bhk} BHK {prop_type} - {locality}, {city}",
        "meta_description": f"Rent {bhk} BHK in {locality}, {city}. Rs.{property_data['rent_amount']}/month"
    }


# ==================== MAIN APP ====================
def main():
    st.title("🏠 AI Property Description Generator")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Claude API Key (Optional)", type="password")
        if api_key:
            st.success("✅ AI Mode")
        else:
            st.info("💡 Demo Mode")
        
        st.divider()
        mode = st.radio("Select Mode", ["Single Property", "Bulk Upload"])
    
    # Route to pages
    if mode == "Single Property":
        show_single_property(api_key)
    else:
        show_bulk_upload(api_key)


def show_single_property(api_key):
    """Single property page"""
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
        rent = st.number_input("Rent (Rs)", value=25000, min_value=1000)
        deposit = st.number_input("Deposit (Rs)", value=50000, min_value=0)
        available = st.date_input("Available From")
        tenants = st.text_input("Preferred Tenants", "Family")
    
    amenities = st.text_input("Amenities (comma-separated)", "Parking, Gym")
    
    if st.button("Generate Description", type="primary"):
        property_data = {
            'property_type': property_type, 'bhk': bhk, 'area_sqft': area_sqft,
            'city': city, 'locality': locality, 'furnishing_status': furnishing,
            'rent_amount': rent, 'deposit_amount': deposit,
            'available_from': str(available), 'preferred_tenants': tenants,
            'amenities': [a.strip() for a in amenities.split(',')],
            'landmark': '', 'floor_no': None, 'total_floors': None, 'rough_description': ''
        }
        
        with st.spinner("Generating..."):
            result = generate_description(property_data, api_key)
            
            st.success("✅ Generated!")
            st.markdown(f"### {result['title']}")
            st.info(result['teaser_text'])
            st.write(result['full_description'])
            
            st.markdown("**Key Points:**")
            for point in result['bullet_points']:
                st.markdown(f"• {point}")
            
            with st.expander("SEO Details"):
                st.write(f"**Meta Title:** {result['meta_title']}")
                st.write(f"**Meta Description:** {result['meta_description']}")
                st.write(f"**Keywords:** {', '.join(result['seo_keywords'])}")
            
            # Download
            json_str = json.dumps(result, indent=2)
            st.download_button("Download JSON", json_str, "description.json", "application/json")


def show_bulk_upload(api_key):
    """Bulk upload with DEBUG mode"""
    st.subheader("Bulk Upload Properties")
    
    # Template download
    with st.expander("📥 Download Template First", expanded=True):
        st.info("Download this template, fill your data, and upload it back")
        
        template_df = SimplePropertyParser.get_template()
        st.dataframe(template_df)
        
        col1, col2 = st.columns(2)
        with col1:
            csv_data = template_df.to_csv(index=False)
            st.download_button("Download CSV", csv_data, "template.csv", "text/csv")
        
        with col2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False)
            st.download_button("Download Excel", output.getvalue(), "template.xlsx",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    st.divider()
    
    # File upload
    uploaded_file = st.file_uploader("Upload Your File", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file:
        parser = SimplePropertyParser()
        df = parser.parse_file(uploaded_file)
        
        if df is not None:
            st.success(f"✅ File loaded: {len(df)} rows")
            
            # DEBUG: Show columns
            st.subheader("🔍 DEBUG: Your File Columns")
            st.write("**Original columns in your file:**")
            
            # Read original file to show original column names
            if uploaded_file.name.endswith('.csv'):
                df_original = pd.read_csv(uploaded_file)
            else:
                df_original = pd.read_excel(uploaded_file)
            
            original_cols = list(df_original.columns)
            st.code(", ".join(original_cols))
            
            st.write("**After normalization (lowercase with underscores):**")
            normalized_cols = list(df.columns)
            st.code(", ".join(normalized_cols))
            
            # Check required columns
            present, missing = parser.check_required_columns(df)
            
            st.subheader("✅ Column Validation")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**✅ Present:**")
                for col in present:
                    st.success(f"✓ {col}")
            
            with col_b:
                st.write("**❌ Missing:**")
                if missing:
                    for col in missing:
                        st.error(f"✗ {col}")
                else:
                    st.success("All required columns present!")
            
            # Show data preview
            st.subheader("👀 Data Preview")
            st.dataframe(df.head(), use_container_width=True)
            
            # If columns are missing, show mapping helper
            if missing:
                st.divider()
                st.subheader("🔧 Column Mapping Helper")
                st.write("Map your columns to required fields:")
                
                mapping = {}
                for missing_col in missing:
                    available_cols = [col for col in df.columns if col not in present]
                    selected = st.selectbox(
                        f"Which column contains '{missing_col}'?",
                        ['(Not in file)'] + available_cols,
                        key=f"map_{missing_col}"
                    )
                    if selected != '(Not in file)':
                        mapping[selected] = missing_col
                
                if st.button("Apply Mapping"):
                    df_mapped = df.rename(columns=mapping)
                    present, missing = parser.check_required_columns(df_mapped)
                    
                    if not missing:
                        st.success("✅ All required columns now present!")
                        st.session_state['mapped_df'] = df_mapped
                        st.rerun()
                    else:
                        st.error(f"Still missing: {', '.join(missing)}")
            
            # Process button (only if all columns present)
            if not missing or 'mapped_df' in st.session_state:
                st.divider()
                
                df_to_process = st.session_state.get('mapped_df', df)
                
                if st.button("🚀 Process All Properties", type="primary"):
                    with st.spinner("Processing..."):
                        properties = parser.process_dataframe(df_to_process)
                        
                        if properties:
                            st.success(f"✅ Processed {len(properties)} properties")
                            
                            # Generate descriptions
                            progress = st.progress(0)
                            results = []
                            
                            for idx, prop in enumerate(properties):
                                desc = generate_description(prop, api_key)
                                results.append({'property': prop, 'description': desc})
                                progress.progress((idx + 1) / len(properties))
                            
                            st.success(f"🎉 Generated {len(results)} descriptions!")
                            
                            # Create output Excel
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
                                    'Meta Title': d['meta_title']
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
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            # Show preview
                            with st.expander("Preview Results"):
                                st.dataframe(result_df.head(), use_container_width=True)
                        else:
                            st.error("No valid properties found")


if __name__ == "__main__":
    main()
