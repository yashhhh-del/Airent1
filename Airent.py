"""
AI Property Description Generator - Complete Application
Ready to paste and run - No additional configuration needed
Supports: Single Property Entry | Bulk Upload | Flexible Column Mapping | AI Generation
"""

import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from io import BytesIO

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="AI Property Description Generator",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
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
    .success-box {
        padding: 1rem;
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ==================== FLEXIBLE PROPERTY PARSER ====================
class FlexiblePropertyParser:
    """
    Advanced parser that handles various column name formats and automatically maps them
    """
    
    # Standard column names and their possible variations
    STANDARD_COLUMNS = {
        'property_type': ['property_type', 'property type', 'Property Type', 'type', 'Type', 'property'],
        'bhk': ['bhk', 'BHK', 'Bhk', 'bedroom', 'bedrooms', 'Bedrooms'],
        'area_sqft': ['area_sqft', 'area', 'Area', 'area_sq_ft', 'sqft', 'square_feet', 'Area (sqft)', 'Area (Sqft)'],
        'city': ['city', 'City', 'CITY', 'town'],
        'locality': ['locality', 'Locality', 'location', 'Location', 'area_name', 'Area'],
        'landmark': ['landmark', 'Landmark', 'nearby', 'Near By', 'reference'],
        'floor_no': ['floor_no', 'floor', 'Floor', 'floor_number', 'Floor Number'],
        'total_floors': ['total_floors', 'total_floor', 'Total Floors', 'totalfloors', 'Total Floor'],
        'furnishing_status': ['furnishing_status', 'furnishing', 'Furnishing', 'Furnishing Status', 'furnished', 'Furnished'],
        'rent_amount': ['rent_amount', 'rent', 'Rent', 'monthly_rent', 'rental_amount', 'Rent Amount', 'Monthly Rent'],
        'deposit_amount': ['deposit_amount', 'deposit', 'Deposit', 'security_deposit', 'Security Deposit', 'Deposit Amount'],
        'available_from': ['available_from', 'available', 'Available From', 'availability', 'date', 'Date', 'Available'],
        'preferred_tenants': ['preferred_tenants', 'tenants', 'Preferred Tenants', 'tenant_type', 'Tenant Type'],
        'amenities': ['amenities', 'Amenities', 'facilities', 'Facilities'],
        'rough_description': ['rough_description', 'description', 'Description', 'notes', 'Notes', 'remarks']
    }
    
    REQUIRED_FIELDS = [
        'property_type', 'bhk', 'area_sqft', 'city', 'locality',
        'furnishing_status', 'rent_amount', 'deposit_amount',
        'available_from', 'preferred_tenants'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def auto_detect_columns(self, df):
        """
        Automatically detect and map column names from uploaded file
        Returns: (detected_mapping, unmatched_columns)
        """
        detected = {}
        unmatched = []
        
        for col in df.columns:
            col_stripped = col.strip()
            matched = False
            
            # Try exact match first
            for standard_name, variations in self.STANDARD_COLUMNS.items():
                if col_stripped in variations:
                    detected[col] = standard_name
                    matched = True
                    break
            
            # Try case-insensitive match
            if not matched:
                col_lower = col_stripped.lower()
                for standard_name, variations in self.STANDARD_COLUMNS.items():
                    if col_lower in [v.lower() for v in variations]:
                        detected[col] = standard_name
                        matched = True
                        break
            
            if not matched:
                unmatched.append(col)
        
        return detected, unmatched
    
    def apply_mapping(self, df, mapping):
        """Apply column name mapping to dataframe"""
        return df.rename(columns=mapping)
    
    def validate_required_fields(self, df):
        """Check if all required fields are present after mapping"""
        missing = [field for field in self.REQUIRED_FIELDS if field not in df.columns]
        return len(missing) == 0, missing
    
    def parse_and_clean(self, df):
        """Parse and clean all rows from dataframe"""
        properties = []
        
        for idx, row in df.iterrows():
            try:
                clean_data = self._clean_row(row)
                if clean_data:
                    properties.append(clean_data)
            except Exception as e:
                self.warnings.append(f"Row {idx + 2}: {str(e)}")
        
        return properties
    
    def _clean_row(self, row):
        """Clean and validate a single row of data"""
        # Parse amenities
        amenities = []
        if pd.notna(row.get('amenities', '')):
            amenities_str = str(row['amenities'])
            if ',' in amenities_str:
                amenities = [a.strip() for a in amenities_str.split(',')]
            elif ';' in amenities_str:
                amenities = [a.strip() for a in amenities_str.split(';')]
            else:
                amenities = [amenities_str.strip()] if amenities_str.strip() else []
        
        # Parse date
        available_from = row.get('available_from', datetime.now().date())
        if isinstance(available_from, str):
            try:
                available_from = pd.to_datetime(available_from).date()
            except:
                available_from = datetime.now().date()
        elif isinstance(available_from, pd.Timestamp):
            available_from = available_from.date()
        
        # Build clean data dictionary
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
    
    @staticmethod
    def get_sample_template():
        """Generate a sample template with example data"""
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


# ==================== AI DESCRIPTION GENERATOR ====================
def build_ai_prompt(property_data):
    """Build detailed prompt for AI description generation"""
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


def generate_with_claude_api(property_data, api_key):
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


def generate_demo_description(property_data):
    """Generate demo description when API key is not provided"""
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


def generate_property_description(property_data, api_key=None):
    """Main function to generate property description"""
    if api_key:
        result = generate_with_claude_api(property_data, api_key)
        if result:
            return result
    
    # Fallback to demo mode
    return generate_demo_description(property_data)


# ==================== UI COMPONENTS ====================
def show_single_property_page(api_key):
    """Single property entry form and generation"""
    st.markdown('<p class="main-header">Single Property Description Generator</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Enter property details to generate AI-powered descriptions</p>', unsafe_allow_html=True)
    
    # Property Form
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Basic Information")
        property_type = st.selectbox(
            "Property Type",
            ["flat", "villa", "pg", "shop", "office"],
            help="Select the type of property"
        )
        bhk = st.text_input("BHK Configuration", "2", help="Number of bedrooms (e.g., 2, 3, 1)")
        area_sqft = st.number_input("Area (sq ft)", min_value=100, value=1000, step=50)
        city = st.text_input("City", "Mumbai")
        locality = st.text_input("Locality/Area", "Andheri West")
        landmark = st.text_input("Landmark (Optional)", "Near Metro Station")
    
    with col2:
        st.subheader("Property Details")
        floor_no = st.number_input("Floor Number", min_value=0, value=3)
        total_floors = st.number_input("Total Floors in Building", min_value=1, value=10)
        furnishing = st.selectbox(
            "Furnishing Status",
            ["unfurnished", "semi", "fully"],
            help="Select furnishing level"
        )
        rent_amount = st.number_input("Monthly Rent (Rs.)", min_value=1000, value=25000, step=1000)
        deposit_amount = st.number_input("Security Deposit (Rs.)", min_value=0, value=50000, step=5000)
        available_from = st.date_input("Available From", datetime.now())
    
    # Additional Details
    st.subheader("Additional Information")
    col3, col4 = st.columns(2)
    
    with col3:
        preferred_tenants = st.text_input("Preferred Tenants", "Family", help="e.g., Family, Bachelor, Students")
        amenities_input = st.text_area(
            "Amenities (comma-separated)",
            "Parking, Gym, Security, Power Backup",
            help="List all amenities separated by commas"
        )
    
    with col4:
        rough_description = st.text_area(
            "Additional Notes (Optional)",
            "Spacious apartment in prime location",
            help="Any additional information about the property"
        )
    
    # Generate Button
    st.divider()
    if st.button("🚀 Generate Property Description", type="primary", use_container_width=True):
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
        with st.spinner("🤖 Generating AI description..."):
            result = generate_property_description(property_data, api_key)
            
            if result:
                st.balloons()
                st.success("✅ Description generated successfully!")
                
                # Display results
                st.markdown("---")
                st.subheader("📝 Generated Description")
                
                # Title
                st.markdown(f"### {result['title']}")
                
                # Teaser
                st.info(f"**Teaser:** {result['teaser_text']}")
                
                # Full Description
                st.markdown("**Full Description:**")
                st.write(result['full_description'])
                
                # Bullet Points
                st.markdown("**Key Highlights:**")
                for point in result['bullet_points']:
                    st.markdown(f"• {point}")
                
                # SEO Section
                with st.expander("🔍 SEO Metadata"):
                    st.markdown(f"**Meta Title:** {result['meta_title']}")
                    st.markdown(f"**Meta Description:** {result['meta_description']}")
                    st.markdown(f"**Keywords:** {', '.join(result['seo_keywords'])}")
                
                # Download Options
                st.divider()
                col_dl1, col_dl2 = st.columns(2)
                
                with col_dl1:
                    # JSON download
                    json_str = json.dumps(result, indent=2)
                    st.download_button(
                        label="📥 Download as JSON",
                        data=json_str,
                        file_name=f"property_description_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col_dl2:
                    # Text download
                    text_content = f"""Title: {result['title']}

Teaser: {result['teaser_text']}

Description:
{result['full_description']}

Key Highlights:
{chr(10).join(['• ' + p for p in result['bullet_points']])}

SEO Keywords: {', '.join(result['seo_keywords'])}
"""
                    st.download_button(
                        label="📥 Download as Text",
                        data=text_content,
                        file_name=f"property_description_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )


def show_bulk_upload_page(api_key):
    """Bulk upload page with intelligent column mapping"""
    st.markdown('<p class="main-header">Bulk Property Upload</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload Excel/CSV files to process multiple properties at once</p>', unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2 = st.tabs(["📤 Upload Properties", "📥 Download Template"])
    
    # Tab 1: Upload and Process
    with tab1:
        st.subheader("Upload Property Data File")
        
        # Instructions
        with st.expander("📋 Instructions - Read Before Upload", expanded=True):
            st.markdown("""
            **How to use Bulk Upload:**
            
            1. **Download the template** from the 'Download Template' tab
            2. **Fill in your property data** following the format
            3. **Upload the file** (supports .xlsx, .xls, .csv)
            4. **Review auto-detected mappings** (or adjust manually if needed)
            5. **Process all properties** and generate AI descriptions
            6. **Download results** as Excel file
            
            **Supported File Formats:** CSV, Excel (.xlsx, .xls)
            
            **Column Name Flexibility:** The system can auto-detect various column name formats like:
            - "City" or "city" or "CITY"
            - "Rent" or "rent_amount" or "Monthly Rent"
            - "Furnishing" or "furnishing_status" or "Furnished"
            """)
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file to upload",
            type=['csv', 'xlsx', 'xls'],
            help="Upload your property data file (CSV or Excel)"
        )
        
        if uploaded_file is not None:
            try:
                # Read file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File uploaded successfully: **{uploaded_file.name}**")
                
                # Show file info
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("Total Rows", len(df))
                with col_info2:
                    st.metric("Total Columns", len(df.columns))
                with col_info3:
                    st.metric("File Type", uploaded_file.name.split('.')[-1].upper())
                
                # Show original columns
                st.subheader("🔍 Column Detection")
                st.write("**Columns found in your file:**")
                st.code(", ".join(df.columns))
                
                # Auto-detect column mappings
                parser = FlexiblePropertyParser()
                detected_mapping, unmatched = parser.auto_detect_columns(df)
                
                # Show auto-detected mappings
                if detected_mapping:
                    st.success(f"✅ Auto-detected {len(detected_mapping)} column mappings")
                    with st.expander("View Auto-Detected Mappings"):
                        mapping_df = pd.DataFrame([
                            {"Your Column": k, "Mapped To": v}
                            for k, v in detected_mapping.items()
                        ])
                        st.dataframe(mapping_df, use_container_width=True)
                
                # Show unmatched columns
                if unmatched:
                    st.warning(f"⚠️ {len(unmatched)} columns couldn't be auto-mapped: {', '.join(unmatched)}")
                    st.info("💡 You can manually map these columns below if they contain required data")
                
                # Manual mapping interface (if needed)
                final_mapping = detected_mapping.copy()
                
                if unmatched:
                    with st.expander("⚙️ Manual Column Mapping (Optional)"):
                        st.write("Map unmatched columns to standard fields:")
                        for unmapped_col in unmatched:
                            mapped_to = st.selectbox(
                                f"Map '{unmapped_col}' to:",
                                ['(Skip)'] + list(parser.STANDARD_COLUMNS.keys()),
                                key=f"map_{unmapped_col}"
                            )
                            if mapped_to != '(Skip)':
                                final_mapping[unmapped_col] = mapped_to
                
                # Apply mapping
                df_mapped = parser.apply_mapping(df, final_mapping)
                
                # Validate required fields
                is_valid, missing = parser.validate_required_fields(df_mapped)
                
                st.subheader("✅ Validation")
                
                if not is_valid:
                    st.error(f"❌ Missing required fields: **{', '.join(missing)}**")
                    st.info("💡 Please adjust the column mapping above or update your file to include these fields")
                else:
                    st.success("✅ All required fields are present!")
                    
                    # Preview mapped data
                    st.subheader("👀 Data Preview")
                    st.dataframe(df_mapped.head(10), use_container_width=True)
                    
                    if len(df_mapped) > 10:
                        st.caption(f"Showing first 10 rows of {len(df_mapped)} total rows")
                    
                    # Process button
                    st.divider()
                    if st.button("🚀 Process All Properties", type="primary", use_container_width=True):
                        with st.spinner("⏳ Processing properties..."):
                            # Parse and clean data
                            properties = parser.parse_and_clean(df_mapped)
                            
                            if properties:
                                st.success(f"✅ Successfully processed **{len(properties)}** properties!")
                                
                                # Show warnings if any
                                if parser.warnings:
                                    with st.expander(f"⚠️ Warnings ({len(parser.warnings)})"):
                                        for warning in parser.warnings:
                                            st.warning(warning)
                                
                                # Store in session state
                                st.session_state['bulk_properties'] = properties
                                
                                # Show sample properties
                                st.subheader("📋 Sample Properties")
                                sample_count = min(3, len(properties))
                                
                                for idx in range(sample_count):
                                    prop = properties[idx]
                                    with st.expander(f"Property {idx + 1}: {prop['bhk']} BHK {prop['property_type'].title()} in {prop['locality']}"):
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.write(f"**City:** {prop['city']}")
                                            st.write(f"**Area:** {prop['area_sqft']} sq ft")
                                            st.write(f"**Rent:** Rs.{prop['rent_amount']}/month")
                                            st.write(f"**Deposit:** Rs.{prop['deposit_amount']}")
                                        with col_b:
                                            st.write(f"**Furnishing:** {prop['furnishing_status'].title()}")
                                            st.write(f"**Available:** {prop['available_from']}")
                                            st.write(f"**Tenants:** {prop['preferred_tenants']}")
                                            st.write(f"**Amenities:** {', '.join(prop['amenities'][:3])}")
                                
                                if len(properties) > sample_count:
                                    st.info(f"... and {len(properties) - sample_count} more properties")
                                
                                # Generate AI descriptions
                                st.divider()
                                st.subheader("🤖 AI Description Generation")
                                
                                if st.button("✨ Generate Descriptions for All Properties", type="primary", use_container_width=True):
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    results = []
                                    
                                    for idx, prop in enumerate(properties):
                                        status_text.text(f"Processing property {idx + 1} of {len(properties)}...")
                                        
                                        description = generate_property_description(prop, api_key)
                                        
                                        if description:
                                            results.append({
                                                'property': prop,
                                                'description': description
                                            })
                                        
                                        progress_bar.progress((idx + 1) / len(properties))
                                    
                                    status_text.empty()
                                    progress_bar.empty()
                                    
                                    st.balloons()
                                    st.success(f"🎉 Generated descriptions for **{len(results)}** properties!")
                                    
                                    # Store results in session state
                                    st.session_state['bulk_results'] = results
                                    
                                    # Prepare Excel download
                                    if results:
                                        output_data = []
                                        for item in results:
                                            prop = item['property']
                                            desc = item['description']
                                            output_data.append({
                                                'Property Type': prop['property_type'].title(),
                                                'BHK': prop['bhk'],
                                                'City': prop['city'],
                                                'Locality': prop['locality'],
                                                'Area (sqft)': prop['area_sqft'],
                                                'Rent': prop['rent_amount'],
                                                'Deposit': prop['deposit_amount'],
                                                'Furnishing': prop['furnishing_status'].title(),
                                                'Title': desc['title'],
                                                'Teaser': desc['teaser_text'],
                                                'Full Description': desc['full_description'],
                                                'Bullet Points': ' | '.join(desc['bullet_points']),
                                                'Meta Title': desc['meta_title'],
                                                'Meta Description': desc['meta_description'],
                                                'SEO Keywords': ', '.join(desc['seo_keywords'])
                                            })
                                        
                                        output_df = pd.DataFrame(output_data)
                                        
                                        # Create Excel file
                                        output = BytesIO()
                                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                            output_df.to_excel(writer, index=False, sheet_name='Property Descriptions')
                                        excel_data = output.getvalue()
                                        
                                        # Download button
                                        st.download_button(
                                            label="📥 Download All Descriptions (Excel)",
                                            data=excel_data,
                                            file_name=f"property_descriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            use_container_width=True
                                        )
                                        
                                        # Show preview of results
                                        with st.expander("👀 Preview Generated Descriptions"):
                                            for i, item in enumerate(results[:3], 1):
                                                st.markdown(f"**Property {i}:** {item['description']['title']}")
                                                st.write(item['description']['teaser_text'])
                                                st.markdown("---")
                            else:
                                st.error("❌ No valid properties found in the file")
                                if parser.errors:
                                    with st.expander("View Errors"):
                                        for error in parser.errors:
                                            st.error(error)
            
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
                st.info("💡 Please ensure your file is a valid CSV or Excel file")
    
    # Tab 2: Template Download
    with tab2:
        st.subheader("📥 Download Template File")
        
        st.markdown("""
        Download a sample template with the correct format and example data.
        Use this template to prepare your property data for bulk upload.
        """)
        
        # Generate template
        template_df = FlexiblePropertyParser.get_sample_template()
        
        # Show template preview
        st.subheader("👀 Template Preview")
        st.dataframe(template_df, use_container_width=True)
        st.caption("This template includes 5 sample properties with all required and optional fields")
        
        # Column descriptions
        st.subheader("📖 Column Descriptions")
        
        col_desc1, col_desc2 = st.columns(2)
        
        with col_desc1:
            st.markdown("""
            **Required Columns:**
            - `property_type` - Type of property (flat, villa, pg, shop, office)
            - `bhk` - Number of bedrooms (e.g., 2, 3, 1)
            - `area_sqft` - Property area in square feet
            - `city` - City name
            - `locality` - Locality or area name
            - `furnishing_status` - Furnishing level (unfurnished, semi, fully)
            - `rent_amount` - Monthly rent amount in rupees
            - `deposit_amount` - Security deposit amount in rupees
            - `available_from` - Date when property is available (YYYY-MM-DD)
            - `preferred_tenants` - Target tenant type (e.g., Family, Bachelor)
            """)
        
        with col_desc2:
            st.markdown("""
            **Optional Columns:**
            - `landmark` - Nearby landmark or reference point
            - `floor_no` - Floor number of the property
            - `total_floors` - Total floors in the building
            - `amenities` - Comma-separated list of amenities
            - `rough_description` - Additional notes or description
            
            **Note:** Optional columns will be used if provided, otherwise they'll be set to default values.
            """)
        
        # Download buttons
        st.divider()
        st.subheader("💾 Download Template")
        
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            # Excel download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False, sheet_name='Properties')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download Excel Template (.xlsx)",
                data=excel_data,
                file_name="property_upload_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.caption("Recommended format - includes formatting")
        
        with col_dl2:
            # CSV download
            csv_data = template_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download CSV Template (.csv)",
                data=csv_data,
                file_name="property_upload_template.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.caption("Universal format - works everywhere")


# ==================== MAIN APPLICATION ====================
def main():
    """Main application entry point"""
    
    # Initialize session state
    if 'bulk_properties' not in st.session_state:
        st.session_state['bulk_properties'] = []
    if 'bulk_results' not in st.session_state:
        st.session_state['bulk_results'] = []
    
    # Sidebar
    with st.sidebar:
        st.title("🏠 AI Property Generator")
        st.markdown("---")
        
        # API Configuration
        st.subheader("⚙️ Configuration")
        api_key = st.text_input(
            "Claude API Key (Optional)",
            type="password",
            help="Enter your Claude API key for AI-powered descriptions. Leave empty for demo mode."
        )
        
        if api_key:
            st.success("✅ AI Mode Active")
        else:
            st.info("💡 Demo Mode Active")
            st.caption("Using template-based descriptions. Add API key for AI-powered content.")
        
        st.markdown("---")
        
        # Mode Selection
        st.subheader("📋 Select Mode")
        mode = st.radio(
            "Choose input method:",
            ["🏠 Single Property Entry", "📤 Bulk Upload (Excel/CSV)"],
            help="Select how you want to input property data"
        )
        
        st.markdown("---")
        
        # Statistics
        if st.session_state.get('bulk_properties'):
            st.subheader("📊 Statistics")
            st.metric("Properties Loaded", len(st.session_state['bulk_properties']))
            if st.session_state.get('bulk_results'):
                st.metric("Descriptions Generated", len(st.session_state['bulk_results']))
        
        st.markdown("---")
        
        # About Section
        with st.expander("ℹ️ About"):
            st.markdown("""
            **AI Property Description Generator**
            
            Generate professional, SEO-optimized property descriptions using AI.
            
            **Features:**
            - Single property entry with detailed form
            - Bulk upload via Excel/CSV
            - Intelligent column mapping
            - AI-powered descriptions
            - SEO optimization
            - Multiple export formats
            
            **Supported Properties:**
            - Flats/Apartments
            - Villas
            - PG Accommodations
            - Shops
            - Offices
            
            **Version:** 2.0
            """)
        
        # Tips Section
        with st.expander("💡 Tips"):
            st.markdown("""
            **For Best Results:**
            
            1. Provide complete property details
            2. Use descriptive amenities
            3. Add landmark for better context
            4. Include owner notes if available
            5. For bulk upload, use the template
            6. Check column mappings before processing
            """)
        
        st.markdown("---")
        st.caption("© 2024 AI Property Description Generator")
        st.caption("Powered by Claude AI")
    
    # Main Content Area
    if mode == "🏠 Single Property Entry":
        show_single_property_page(api_key)
    else:
        show_bulk_upload_page(api_key)
    
    # Footer
    st.markdown("---")
    col_foot1, col_foot2, col_foot3 = st.columns(3)
    with col_foot1:
        st.caption("💻 Built with Streamlit")
    with col_foot2:
        st.caption("🤖 Powered by Claude AI")
    with col_foot3:
        st.caption("📧 Support: contact@example.com")


# ==================== RUN APPLICATION ====================
if __name__ == "__main__":
    main()
