import streamlit as st
import pandas as pd
import json
import requests
import os
from datetime import datetime
from io import BytesIO

# Page Configuration
st.set_page_config(
    page_title="AI Property Description Generator",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ==================== FILE PARSER CLASS ====================
class PropertyFileParser:
    """Parse and validate property data from Excel/CSV files"""
    
    REQUIRED_COLUMNS = [
        'property_type', 'bhk', 'area_sqft', 'city', 'locality',
        'furnishing_status', 'rent_amount', 'deposit_amount',
        'available_from', 'preferred_tenants'
    ]
    
    OPTIONAL_COLUMNS = [
        'landmark', 'floor_no', 'total_floors', 'amenities', 'rough_description'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def parse_file(self, uploaded_file):
        """Parse uploaded file"""
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(uploaded_file)
            else:
                self.errors.append("Unsupported file format. Use CSV or Excel files.")
                return None
            return df
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return None
    
    def validate_columns(self, df):
        """Validate required columns exist"""
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            self.errors.append(f"Missing required columns: {', '.join(missing)}")
            return False
        return True
    
    def clean_row(self, row):
        """Clean and validate a single row"""
        try:
            # Parse amenities
            amenities = []
            if pd.notna(row.get('amenities', '')):
                amenities_str = str(row['amenities'])
                if ',' in amenities_str:
                    amenities = [a.strip() for a in amenities_str.split(',')]
                elif ';' in amenities_str:
                    amenities = [a.strip() for a in amenities_str.split(';')]
                else:
                    amenities = [amenities_str.strip()]
            
            # Parse date
            available_from = row['available_from']
            if isinstance(available_from, str):
                try:
                    available_from = pd.to_datetime(available_from).date()
                except:
                    available_from = datetime.now().date()
            
            # Build clean data
            clean_data = {
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
            
            return clean_data
        except Exception as e:
            self.warnings.append(f"Error cleaning row: {str(e)}")
            return None
    
    def process_dataframe(self, df):
        """Process entire dataframe"""
        properties = []
        for idx, row in df.iterrows():
            clean_data = self.clean_row(row)
            if clean_data:
                properties.append(clean_data)
            else:
                self.warnings.append(f"Skipped row {idx + 2}")
        return properties
    
    @staticmethod
    def get_sample_template():
        """Generate sample template"""
        sample_data = {
            'property_type': ['flat', 'villa', 'pg', 'shop', 'office'],
            'bhk': ['2', '3', '1', 'N/A', 'N/A'],
            'area_sqft': [1200, 2500, 400, 800, 1500],
            'city': ['Mumbai', 'Bangalore', 'Pune', 'Delhi', 'Hyderabad'],
            'locality': ['Andheri West', 'Koramangala', 'Kothrud', 'Connaught Place', 'Banjara Hills'],
            'landmark': ['Near Metro Station', 'Sony World Signal', 'Near FC Road', 'Central Park', 'KBR Park'],
            'floor_no': [5, 1, 2, 0, 3],
            'total_floors': [10, 2, 4, 2, 8],
            'furnishing_status': ['semi', 'fully', 'unfurnished', 'fully', 'semi'],
            'rent_amount': [25000, 45000, 8000, 30000, 40000],
            'deposit_amount': [50000, 90000, 16000, 60000, 80000],
            'available_from': ['2024-12-01', '2024-12-15', '2024-12-01', '2025-01-01', '2024-12-20'],
            'preferred_tenants': ['Family', 'Family', 'Students/Working Professionals', 'Commercial', 'Company'],
            'amenities': ['Parking, Gym, Security', 'Garden, Swimming Pool, Power Backup', 'WiFi, Meals', 'Parking, AC', 'Cafeteria, Parking'],
            'rough_description': ['Spacious apartment with modern amenities', 'Luxury villa with premium features', 'Budget-friendly PG accommodation', 'Prime location commercial shop', 'Corporate office space']
        }
        return pd.DataFrame(sample_data)


# ==================== AI GENERATION FUNCTIONS ====================
def build_ai_prompt(property_data):
    """Build prompt for AI description generation"""
    amenities_str = ", ".join(property_data.get('amenities', []))
    
    prompt = f"""You are an expert real estate copywriter. Write a professional, engaging, and SEO-friendly rental property description.

Property Details:
- Type: {property_data.get('property_type', 'N/A')}
- BHK: {property_data.get('bhk', 'N/A')}
- Area: {property_data.get('area_sqft', 'N/A')} sq ft
- Location: {property_data.get('locality', 'N/A')}, {property_data.get('city', 'N/A')}
- Landmark: {property_data.get('landmark', 'N/A')}
- Floor: {property_data.get('floor_no', 'N/A')} out of {property_data.get('total_floors', 'N/A')}
- Furnishing: {property_data.get('furnishing_status', 'N/A')}
- Rent: Rs.{property_data.get('rent_amount', 'N/A')}/month
- Deposit: Rs.{property_data.get('deposit_amount', 'N/A')}
- Available From: {property_data.get('available_from', 'N/A')}
- Preferred Tenants: {property_data.get('preferred_tenants', 'N/A')}
- Amenities: {amenities_str}
- Owner Notes: {property_data.get('rough_description', '')}

Please provide output as a JSON object with these exact keys:
{{
    "title": "Catchy headline under 100 characters",
    "teaser_text": "Brief 1-2 line summary",
    "full_description": "2-4 detailed paragraphs highlighting location benefits, property features, lifestyle advantages",
    "bullet_points": ["4-8 key highlights as short bullet points"],
    "seo_keywords": ["8-12 relevant SEO keywords"],
    "meta_title": "SEO title under 60 characters",
    "meta_description": "SEO description 150-160 characters"
}}

Make it compelling, professional, and conversion-focused!"""
    
    return prompt


def generate_with_claude(property_data, api_key):
    """Generate description using Claude API"""
    try:
        prompt = build_ai_prompt(property_data)
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        content = result.get('content', [{}])[0].get('text', '')
        
        # Parse JSON from response
        description_data = json.loads(content)
        return description_data
        
    except Exception as e:
        st.error(f"AI Generation Error: {str(e)}")
        return None


def generate_dummy_description(property_data):
    """Generate dummy description for testing"""
    bhk = property_data.get('bhk', '2')
    prop_type = property_data.get('property_type', 'Flat').title()
    locality = property_data.get('locality', 'Area')
    city = property_data.get('city', 'City')
    
    return {
        "title": f"Spacious {bhk} BHK {prop_type} for Rent in {locality}",
        "teaser_text": f"Well-maintained {bhk} BHK property in prime {locality} location with excellent connectivity.",
        "full_description": f"This beautiful {bhk} BHK {prop_type.lower()} in {locality}, {city} offers comfortable living with modern amenities. The property features spacious rooms with ample natural light and ventilation. Located in a peaceful neighborhood with easy access to markets, schools, and public transport. Perfect for families looking for a convenient and comfortable home. The property is well-maintained and ready for immediate occupancy.",
        "bullet_points": [
            f"Spacious {bhk} BHK with {property_data.get('area_sqft', 'large')} sq ft area",
            f"{property_data.get('furnishing_status', 'Well furnished').title()} with modern fittings",
            f"Located in {locality} with excellent connectivity",
            "24/7 security and power backup available",
            "Close to schools, hospitals and shopping centers"
        ],
        "seo_keywords": [
            f"{bhk} bhk rent {city}",
            f"{locality} {prop_type.lower()} for rent",
            f"rental property {city}",
            f"{prop_type.lower()} for family {city}",
            f"rent {prop_type.lower()} {locality}"
        ],
        "meta_title": f"{bhk} BHK {prop_type} for Rent in {locality}, {city}",
        "meta_description": f"Find your ideal {bhk} BHK {prop_type.lower()} in {locality}, {city}. Well-maintained property with modern amenities. Contact now for viewing!"
    }


# ==================== UI PAGES ====================
def show_single_property_page():
    """Single property entry and generation page"""
    st.markdown('<p class="main-header">Single Property Description Generator</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Enter property details to generate AI-powered descriptions</p>', unsafe_allow_html=True)
    
    # API Key
    with st.sidebar:
        st.subheader("API Configuration")
        api_key = st.text_input("Claude API Key (Optional)", type="password", help="Leave empty for demo mode")
        use_ai = st.checkbox("Use AI Generation", value=bool(api_key))
        
        if not use_ai:
            st.info("Demo mode: Will generate template descriptions")
    
    # Property Form
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Basic Information")
        property_type = st.selectbox(
            "Property Type",
            ["flat", "villa", "pg", "shop", "office"]
        )
        bhk = st.text_input("BHK Configuration", "2")
        area_sqft = st.number_input("Area (sq ft)", min_value=100, value=1000, step=50)
        city = st.text_input("City", "Mumbai")
        locality = st.text_input("Locality", "Andheri West")
        landmark = st.text_input("Landmark (Optional)", "Near Metro Station")
    
    with col2:
        st.subheader("Property Details")
        floor_no = st.number_input("Floor Number", min_value=0, value=3)
        total_floors = st.number_input("Total Floors", min_value=1, value=10)
        furnishing = st.selectbox(
            "Furnishing Status",
            ["unfurnished", "semi", "fully"]
        )
        rent_amount = st.number_input("Monthly Rent (Rs.)", min_value=1000, value=25000, step=1000)
        deposit_amount = st.number_input("Deposit (Rs.)", min_value=0, value=50000, step=5000)
        available_from = st.date_input("Available From")
    
    # Additional Details
    st.subheader("Additional Information")
    col3, col4 = st.columns(2)
    
    with col3:
        preferred_tenants = st.text_input("Preferred Tenants", "Family")
        amenities_input = st.text_area(
            "Amenities (comma-separated)",
            "Parking, Gym, Security, Power Backup"
        )
    
    with col4:
        rough_description = st.text_area(
            "Additional Notes (Optional)",
            "Spacious apartment in prime location"
        )
    
    # Generate Button
    if st.button("Generate Property Description", type="primary"):
        # Prepare property data
        amenities = [a.strip() for a in amenities_input.split(',') if a.strip()]
        
        property_data = {
            'property_type': property_type,
            'bhk': bhk,
            'area_sqft': area_sqft,
            'city': city,
            'locality': locality,
            'landmark': landmark,
            'floor_no': floor_no,
            'total_floors': total_floors,
            'furnishing_status': furnishing,
            'rent_amount': rent_amount,
            'deposit_amount': deposit_amount,
            'available_from': str(available_from),
            'preferred_tenants': preferred_tenants,
            'amenities': amenities,
            'rough_description': rough_description
        }
        
        # Generate description
        with st.spinner("Generating AI description..."):
            if use_ai and api_key:
                result = generate_with_claude(property_data, api_key)
            else:
                result = generate_dummy_description(property_data)
            
            if result:
                st.success("Description generated successfully!")
                
                # Display results
                st.markdown("---")
                st.subheader("Generated Description")
                
                # Title
                st.markdown(f"### {result['title']}")
                
                # Teaser
                st.info(result['teaser_text'])
                
                # Full Description
                st.markdown("**Full Description:**")
                st.write(result['full_description'])
                
                # Bullet Points
                st.markdown("**Key Highlights:**")
                for point in result['bullet_points']:
                    st.markdown(f"- {point}")
                
                # SEO Section
                with st.expander("SEO Metadata"):
                    st.markdown(f"**Meta Title:** {result['meta_title']}")
                    st.markdown(f"**Meta Description:** {result['meta_description']}")
                    st.markdown(f"**Keywords:** {', '.join(result['seo_keywords'])}")
                
                # Download as JSON
                json_str = json.dumps(result, indent=2)
                st.download_button(
                    label="Download as JSON",
                    data=json_str,
                    file_name=f"property_description_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )


def show_bulk_upload_page():
    """Bulk upload page with template download"""
    st.markdown('<p class="main-header">Bulk Property Upload</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload Excel/CSV files to process multiple properties at once</p>', unsafe_allow_html=True)
    
    # API Key
    with st.sidebar:
        st.subheader("API Configuration")
        api_key = st.text_input("Claude API Key (Optional)", type="password", help="Leave empty for demo mode")
        use_ai = st.checkbox("Use AI Generation", value=bool(api_key))
        
        if not use_ai:
            st.info("Demo mode: Will generate template descriptions")
    
    # Tabs
    tab1, tab2 = st.tabs(["Upload Properties", "Download Template"])
    
    # Tab 1: Upload
    with tab1:
        st.subheader("Upload Property Data File")
        
        # Instructions
        st.info("""
        **Upload Instructions:**
        1. Download the template from the 'Download Template' tab
        2. Fill in your property data following the format
        3. Upload the completed file (supports .xlsx, .xls, .csv)
        4. System will validate and process all properties
        """)
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file to upload",
            type=['csv', 'xlsx', 'xls'],
            help="Upload your property data file"
        )
        
        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")
            
            # Parse file
            parser = PropertyFileParser()
            df = parser.parse_file(uploaded_file)
            
            if df is not None:
                st.subheader("File Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", len(df))
                with col2:
                    st.metric("Columns", len(df.columns))
                with col3:
                    st.metric("File Type", uploaded_file.name.split('.')[-1].upper())
                
                # Validate
                if parser.validate_columns(df):
                    st.success("All required columns present!")
                    
                    # Process button
                    if st.button("Process Properties", type="primary"):
                        with st.spinner("Processing properties..."):
                            properties = parser.process_dataframe(df)
                            
                            if properties:
                                st.success(f"Successfully processed {len(properties)} properties!")
                                
                                # Store in session state
                                st.session_state['bulk_properties'] = properties
                                
                                # Show sample
                                st.subheader("Sample Properties")
                                for idx, prop in enumerate(properties[:3], 1):
                                    with st.expander(f"Property {idx}: {prop['bhk']} BHK {prop['property_type'].title()} in {prop['locality']}"):
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.write(f"**City:** {prop['city']}")
                                            st.write(f"**Area:** {prop['area_sqft']} sq ft")
                                            st.write(f"**Rent:** Rs.{prop['rent_amount']}/month")
                                        with col_b:
                                            st.write(f"**Furnishing:** {prop['furnishing_status'].title()}")
                                            st.write(f"**Available:** {prop['available_from']}")
                                            st.write(f"**Tenants:** {prop['preferred_tenants']}")
                                
                                if len(properties) > 3:
                                    st.info(f"... and {len(properties) - 3} more properties")
                                
                                # Generate descriptions
                                st.divider()
                                st.subheader("Generate AI Descriptions")
                                
                                if st.button("Generate Descriptions for All Properties", type="primary"):
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    results = []
                                    
                                    for idx, prop in enumerate(properties):
                                        status_text.text(f"Processing property {idx + 1} of {len(properties)}...")
                                        
                                        if use_ai and api_key:
                                            description = generate_with_claude(prop, api_key)
                                        else:
                                            description = generate_dummy_description(prop)
                                        
                                        if description:
                                            results.append({
                                                'property': prop,
                                                'description': description
                                            })
                                        
                                        progress_bar.progress((idx + 1) / len(properties))
                                    
                                    status_text.text("All properties processed!")
                                    st.success(f"Generated descriptions for {len(results)} properties!")
                                    
                                    # Store results
                                    st.session_state['bulk_results'] = results
                                    
                                    # Download all results
                                    if results:
                                        # Create Excel with all results
                                        output_data = []
                                        for item in results:
                                            prop = item['property']
                                            desc = item['description']
                                            output_data.append({
                                                'Property Type': prop['property_type'],
                                                'BHK': prop['bhk'],
                                                'City': prop['city'],
                                                'Locality': prop['locality'],
                                                'Title': desc['title'],
                                                'Teaser': desc['teaser_text'],
                                                'Full Description': desc['full_description'],
                                                'Meta Title': desc['meta_title'],
                                                'Meta Description': desc['meta_description'],
                                                'Bullet Points': ' | '.join(desc['bullet_points']),
                                                'SEO Keywords': ', '.join(desc['seo_keywords'])
                                            })
                                        
                                        output_df = pd.DataFrame(output_data)
                                        
                                        # Create Excel in memory
                                        output = BytesIO()
                                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                            output_df.to_excel(writer, index=False, sheet_name='Descriptions')
                                        excel_data = output.getvalue()
                                        
                                        st.download_button(
                                            label="Download All Descriptions (Excel)",
                                            data=excel_data,
                                            file_name=f"property_descriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                        )
                            else:
                                st.error("No valid properties found in file")
                else:
                    st.error("Column validation failed!")
                    for error in parser.errors:
                        st.error(error)
            else:
                st.error("Failed to parse file")
                for error in parser.errors:
                    st.error(error)
    
    # Tab 2: Template Download
    with tab2:
        st.subheader("Download Template File")
        
        st.markdown("""
        Download a sample Excel template with the correct format and example data.
        Use this template to prepare your property data for bulk upload.
        """)
        
        # Generate template
        template_df = PropertyFileParser.get_sample_template()
        
        st.subheader("Template Preview")
        st.dataframe(template_df, use_container_width=True)
        
        # Column descriptions
        st.subheader("Column Descriptions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Required Columns:**
            - `property_type`: flat, villa, pg, shop, office
            - `bhk`: Number of bedrooms (e.g., 2, 3, 1)
            - `area_sqft`: Area in square feet
            - `city`: City name
            - `locality`: Locality/area name
            - `furnishing_status`: unfurnished, semi, fully
            - `rent_amount`: Monthly rent amount
            - `deposit_amount`: Security deposit amount
            - `available_from`: Date (YYYY-MM-DD format)
            - `preferred_tenants`: Target tenant type
            """)
        
        with col2:
            st.markdown("""
            **Optional Columns:**
            - `landmark`: Nearby landmark or reference point
            - `floor_no`: Floor number
            - `total_floors`: Total floors in building
            - `amenities`: Comma-separated amenities list
            - `rough_description`: Brief property description
            """)
        
        # Download buttons
        st.subheader("Download Template")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Excel download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False, sheet_name='Properties')
            excel_data = output.getvalue()
            
            st.download_button(
                label="Download Excel Template (.xlsx)",
                data=excel_data,
                file_name="property_upload_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_b:
            # CSV download
            csv_data = template_df.to_csv(index=False)
            
            st.download_button(
                label="Download CSV Template (.csv)",
                data=csv_data,
                file_name="property_upload_template.csv",
                mime="text/csv",
                use_container_width=True
            )


# ==================== MAIN APP ====================
def main():
    """Main application"""
    
    # Sidebar
    st.sidebar.title("AI Property Description Generator")
    st.sidebar.markdown("---")
    
    # Mode selection
    mode = st.sidebar.radio(
        "Select Mode",
        ["Single Property Entry", "Bulk Upload (Excel/CSV)"],
        help="Choose between single property or bulk upload mode"
    )
    
    st.sidebar.markdown("---")
    
    # Info
    with st.sidebar.expander("About"):
        st.markdown("""
        **AI Property Description Generator**
        
        Generate professional, SEO-optimized property descriptions using AI.
        
        **Features:**
        - Single property entry
        - Bulk upload via Excel/CSV
        - AI-powered descriptions
        - SEO optimization
        - Export functionality
        
        **Supported Properties:**
        - Flats/Apartments
        - Villas
        - PG Accommodations
        - Shops
        - Offices
        """)
    
    # Route to appropriate page
    if mode == "Single Property Entry":
        show_single_property_page()
    else:
        show_bulk_upload_page()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2024 AI Property Description Generator")


if __name__ == "__main__":
    main()
