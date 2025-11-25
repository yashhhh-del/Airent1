"""
AI Property Description Generator - WITH REGENERATE FEATURE
Premium Quality with Groq Free API
"""

import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from io import BytesIO
import time

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
def test_groq_api(api_key):
    """Test Groq API connection with simple request"""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key.strip()}"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Say 'API is working!'"}],
                "temperature": 0.5,
                "max_tokens": 50
            },
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ API Connection Successful!"
        else:
            return False, f"Error {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"


def generate_with_groq(property_data, api_key, retry_count=3, variation_seed=0):
    """Generate PREMIUM description using Groq API with variation support"""
    
    # Variation prompts for different creative angles
    variation_prompts = [
        {
            'focus': 'lifestyle and experience',
            'tone': 'aspirational and emotional',
            'instruction': 'Focus on the lifestyle transformation and daily experiences this property offers.'
        },
        {
            'focus': 'investment value and practicality',
            'tone': 'professional and value-driven',
            'instruction': 'Emphasize the practical benefits, value for money, and smart investment aspects.'
        },
        {
            'focus': 'location benefits and connectivity',
            'tone': 'convenience-focused and modern',
            'instruction': 'Highlight the strategic location, connectivity advantages, and nearby conveniences.'
        },
        {
            'focus': 'comfort and luxury features',
            'tone': 'premium and sophisticated',
            'instruction': 'Emphasize the premium features, comfort elements, and luxurious living experience.'
        },
        {
            'focus': 'community and safety',
            'tone': 'warm and family-oriented',
            'instruction': 'Focus on the safe neighborhood, community aspects, and family-friendly environment.'
        }
    ]
    
    # Select variation based on seed
    variation = variation_prompts[variation_seed % len(variation_prompts)]
    
    for attempt in range(retry_count):
        try:
            # Clean API key
            api_key = api_key.strip()
            
            bhk = property_data['bhk']
            prop_type = property_data['property_type'].title()
            locality = property_data['locality']
            city = property_data['city']
            area = property_data['area_sqft']
            rent = property_data['rent_amount']
            furnishing = property_data['furnishing_status']
            amenities = ', '.join(property_data['amenities']) if property_data['amenities'] else 'Standard amenities'
            tenants = property_data['preferred_tenants']
            deposit = property_data['deposit_amount']
            available = property_data['available_from']
            nearby = ', '.join(property_data.get('nearby_points', []))
            
            prompt = f"""You are an expert real estate copywriter specializing in premium property listings that drive high engagement and conversions.

Create a compelling, professional rental property listing for:

**Property Details:**
- Type: {bhk} BHK {prop_type}
- Location: {locality}, {city}
- Area: {area} square feet
- Monthly Rent: ₹{rent}
- Security Deposit: ₹{deposit}
- Furnishing: {furnishing} furnished
- Amenities: {amenities}
- Preferred Tenants: {tenants}
- Available From: {available}
- Nearby: {nearby}

**CREATIVE DIRECTION FOR THIS VERSION:**
- Primary Focus: {variation['focus']}
- Tone: {variation['tone']}
- Special Instruction: {variation['instruction']}

**Requirements:**
1. **Title**: Create an attention-grabbing, emotional title (8-12 words) that highlights the property's unique value proposition and creates desire. Make it DIFFERENT from generic titles.
2. **Teaser**: Write a compelling hook (15-20 words) that creates urgency and paints a lifestyle picture
3. **Full Description**: Craft a detailed, engaging description (150-200 words) that:
   - Paints a vivid picture of living there
   - Highlights lifestyle benefits, not just features
   - Uses emotional, sensory language
   - Emphasizes location advantages and convenience
   - Creates FOMO (fear of missing out)
   - Focuses on the experience and feelings
   - Follows the creative direction provided above
4. **Bullet Points**: 5 compelling features written as BENEFITS (not just specs). Focus on what the tenant gains. Make them unique and specific.
5. **SEO Keywords**: 5 highly relevant, search-optimized keywords that people actually search for
6. **Meta Title**: SEO-optimized title (under 60 chars) with primary keyword
7. **Meta Description**: Compelling SEO description (under 160 chars) with call-to-action

**Tone**: {variation['tone']}. Write like you're selling a dream lifestyle, not just a property.

**IMPORTANT - MAKE IT UNIQUE:**
- Use varied vocabulary and expressions
- Try different angles and perspectives  
- Create original metaphors and descriptions
- Avoid repetitive patterns

Return ONLY valid JSON (no markdown, no ```json):
{{
    "title": "your captivating title here",
    "teaser_text": "your compelling teaser here",
    "full_description": "your detailed engaging description here",
    "bullet_points": ["lifestyle benefit 1", "lifestyle benefit 2", "lifestyle benefit 3", "lifestyle benefit 4", "lifestyle benefit 5"],
    "seo_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "meta_title": "your SEO meta title here",
    "meta_description": "your SEO meta description with CTA here"
}}"""

            # Adjust temperature based on variation for more creativity
            temperature = 0.8 + (variation_seed * 0.05)
            if temperature > 1.0:
                temperature = 0.8 + ((variation_seed % 3) * 0.05)

            # Make API request
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are an expert real estate copywriter creating premium, emotionally engaging property listings. For this generation, your focus is on {variation['focus']} with a {variation['tone']} tone. Write compelling, benefit-focused content that sells lifestyle and experience, not just features. Be creative and avoid repetitive patterns. Always respond with valid JSON only, no markdown formatting."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": 2000,
                    "top_p": 0.9
                },
                timeout=30
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Clean markdown formatting if present
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                # Parse JSON
                parsed = json.loads(content)
                return parsed
            
            # Handle errors
            elif response.status_code == 429:
                if attempt < retry_count - 1:
                    wait_time = (attempt + 1) * 2
                    st.warning(f"⏳ Rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    st.error("❌ Rate limit exceeded. Please wait a minute and try again.")
                    return None
            
            elif response.status_code == 401:
                st.error("❌ Invalid API Key")
                st.info("🔑 Get a new API key from: https://console.groq.com/keys")
                return None
            
            elif response.status_code == 400:
                error_data = response.json()
                st.error(f"❌ Bad Request: {error_data}")
                return None
            
            else:
                st.error(f"❌ API Error {response.status_code}")
                with st.expander("🔍 Error Details"):
                    st.code(response.text)
                return None
                
        except requests.exceptions.Timeout:
            if attempt < retry_count - 1:
                st.warning(f"⏳ Timeout. Retrying... (Attempt {attempt + 2}/{retry_count})")
                time.sleep(2)
                continue
            else:
                st.error("❌ Request timeout after multiple attempts")
                return None
        
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON response from Groq")
            with st.expander("🔍 Response Details"):
                st.text(content if 'content' in locals() else "No content received")
            return None
        
        except Exception as e:
            st.error(f"❌ Unexpected Error: {str(e)}")
            return None
    
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


def generate_description(property_data, api_provider, api_key=None, variation_seed=0):
    """Main generation function with multiple providers and variation support"""
    if api_provider == "Groq Premium (Free)" and api_key:
        result = generate_with_groq(property_data, api_key, variation_seed=variation_seed)
        if result:
            return result
    
    # Fallback to template
    st.info("ℹ️ Using template-based generation")
    return generate_fallback(property_data)


# ==================== MAIN APP ====================
def main():
    st.title("🏠 AI Property Description Generator")
    st.caption("Premium Quality Descriptions - FREE with Groq API 🌟 | Now with Regenerate Feature")
    
    # Initialize session state
    if 'generated_result' not in st.session_state:
        st.session_state.generated_result = None
    if 'property_data' not in st.session_state:
        st.session_state.property_data = None
    if 'generation_count' not in st.session_state:
        st.session_state.generation_count = 0
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # AI Provider Selection
        api_provider = st.selectbox(
            "Select AI Provider",
            ["Groq Premium (Free)", "Template (No API)"],
            help="Groq Premium uses enhanced prompting for free premium quality!",
            key="api_provider_select"
        )
        
        # API Key Input
        api_key = None
        if api_provider != "Template (No API)":
            st.success("🌟 PREMIUM Quality + FREE - Best of Both Worlds!")
            st.info("🆓 Get free Groq API key from: https://console.groq.com/keys")
            api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", key="groq_api_key")
            
            # Test API button
            if api_key:
                if st.button("🧪 Test API Connection", key="test_api_btn"):
                    with st.spinner("Testing..."):
                        success, message = test_groq_api(api_key)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
            
            st.info("💡 **Premium Features:** Enhanced prompting + Emotional copy + Lifestyle focus")
        
        st.divider()
        
        # API Info
        with st.expander("ℹ️ About Regenerate Feature"):
            st.markdown("""
            **🔄 Regenerate Feature:**
            - Generate multiple versions for same property
            - Each version has unique creative angle
            - 5 different styles: Lifestyle, Investment, Location, Luxury, Community
            - No need to re-enter details
            - Pick the best version!
            
            **How to use:**
            1. Fill form and click Generate
            2. See Version #1
            3. Click Regenerate for Version #2
            4. Keep clicking for more versions
            """)
    
    show_single_property(api_provider, api_key)


def show_single_property(api_provider, api_key):
    """Comprehensive Property Input Module with Regenerate"""
    st.subheader("📝 Property Details Entry Form")
    st.caption("Fill in all details to generate premium property description")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🏠 Basic Details", "💰 Pricing & Availability", "✨ Features & Amenities"])
    
    with tab1:
        st.markdown("### Basic Property Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            property_type = st.selectbox(
                "Property Type *",
                ["Flat", "Villa", "Independent House", "PG/Hostel", "Shop", "Office Space", 
                 "Warehouse", "Land/Plot", "Studio Apartment", "Penthouse"],
                help="Select the type of property",
                key="prop_type_select"
            )
            
            bhk = st.selectbox(
                "BHK Configuration / Rooms *",
                ["1 RK", "1 BHK", "2 BHK", "3 BHK", "4 BHK", "5 BHK", "5+ BHK", 
                 "Studio", "Other"],
                help="Number of bedrooms, hall, and kitchen",
                key="bhk_select"
            )
            
            area_unit = st.radio("Area Unit", ["sq ft", "sq m"], horizontal=True, key="area_unit_radio")
            area_sqft = st.number_input(
                f"Built-up Area ({area_unit}) *",
                min_value=100,
                max_value=50000,
                value=1000,
                step=50,
                help="Total built-up area of the property",
                key="area_input"
            )
            
            furnishing = st.selectbox(
                "Furnishing Status *",
                ["Unfurnished", "Semi-Furnished", "Fully Furnished"],
                help="Current furnishing level of the property",
                key="furnishing_select"
            )
        
        with col2:
            city = st.text_input(
                "City *",
                value="Mumbai",
                help="City where property is located",
                key="city_input"
            )
            
            locality = st.text_input(
                "Area/Locality *",
                value="Andheri West",
                help="Specific area or locality name",
                key="locality_input"
            )
            
            landmark = st.text_input(
                "Landmark (Optional)",
                placeholder="e.g., Near XYZ Mall",
                help="Prominent landmark near the property",
                key="landmark_input"
            )
            
            col_floor1, col_floor2 = st.columns(2)
            with col_floor1:
                floor_no = st.number_input(
                    "Floor Number",
                    min_value=0,
                    max_value=100,
                    value=5,
                    help="Floor on which property is located (0 for ground)",
                    key="floor_no_input"
                )
            
            with col_floor2:
                total_floors = st.number_input(
                    "Total Floors",
                    min_value=1,
                    max_value=100,
                    value=10,
                    help="Total floors in the building",
                    key="total_floors_input"
                )
    
    with tab2:
        st.markdown("### Pricing & Availability Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            rent = st.number_input(
                "Monthly Rent (₹) *",
                min_value=1000,
                max_value=10000000,
                value=25000,
                step=1000,
                help="Monthly rental amount",
                key="rent_input"
            )
            
            deposit = st.number_input(
                "Security Deposit (₹) *",
                min_value=0,
                max_value=50000000,
                value=50000,
                step=5000,
                help="Refundable security deposit",
                key="deposit_input"
            )
            
            maintenance = st.number_input(
                "Maintenance (₹/month)",
                min_value=0,
                max_value=100000,
                value=2000,
                step=500,
                help="Monthly maintenance charges (if applicable)",
                key="maintenance_input"
            )
        
        with col2:
            available = st.date_input(
                "Available From *",
                help="Date when property will be available for move-in",
                key="available_date"
            )
            
            preferred_tenants = st.multiselect(
                "Preferred Tenants *",
                ["Family", "Bachelors", "Students", "Company Lease", "Any"],
                default=["Family"],
                help="Type of tenants preferred (can select multiple)",
                key="tenants_multiselect"
            )
            
            negotiable = st.checkbox("Rent Negotiable", value=False, key="negotiable_check")
            parking_charges = st.number_input(
                "Parking Charges (₹/month)",
                min_value=0,
                max_value=10000,
                value=0,
                help="Additional parking charges if any",
                key="parking_input"
            )
    
    with tab3:
        st.markdown("### Features & Amenities")
        
        st.markdown("#### 🏢 Building Amenities")
        col1, col2, col3, col4 = st.columns(4)
        
        amenities = []
        
        with col1:
            if st.checkbox("Lift/Elevator", value=True, key="amenity_lift"):
                amenities.append("Lift")
            if st.checkbox("Parking", value=True, key="amenity_parking"):
                amenities.append("Parking")
            if st.checkbox("Power Backup", value=False, key="amenity_power"):
                amenities.append("Power Backup")
            if st.checkbox("Water Supply", value=True, key="amenity_water"):
                amenities.append("24/7 Water")
        
        with col2:
            if st.checkbox("Security", value=True, key="amenity_security"):
                amenities.append("Security")
            if st.checkbox("CCTV Surveillance", value=False, key="amenity_cctv"):
                amenities.append("CCTV")
            if st.checkbox("Intercom", value=False, key="amenity_intercom"):
                amenities.append("Intercom")
            if st.checkbox("Fire Safety", value=False, key="amenity_fire"):
                amenities.append("Fire Safety")
        
        with col3:
            if st.checkbox("Gym/Fitness Center", value=False, key="amenity_gym"):
                amenities.append("Gym")
            if st.checkbox("Swimming Pool", value=False, key="amenity_pool"):
                amenities.append("Pool")
            if st.checkbox("Garden/Park", value=False, key="amenity_garden"):
                amenities.append("Garden")
            if st.checkbox("Children's Play Area", value=False, key="amenity_play"):
                amenities.append("Play Area")
        
        with col4:
            if st.checkbox("Club House", value=False, key="amenity_club"):
                amenities.append("Club House")
            if st.checkbox("Visitor Parking", value=False, key="amenity_visitor"):
                amenities.append("Visitor Parking")
            if st.checkbox("Maintenance Staff", value=True, key="amenity_maintenance"):
                amenities.append("Maintenance Staff")
            if st.checkbox("Waste Disposal", value=True, key="amenity_waste"):
                amenities.append("Waste Disposal")
        
        st.divider()
        
        st.markdown("#### 🏠 Property Features")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.checkbox("Balcony", value=True, key="feature_balcony"):
                amenities.append("Balcony")
            if st.checkbox("Modular Kitchen", value=False, key="feature_kitchen"):
                amenities.append("Modular Kitchen")
            if st.checkbox("Wardrobe", value=False, key="feature_wardrobe"):
                amenities.append("Wardrobe")
        
        with col2:
            if st.checkbox("AC", value=False, key="feature_ac"):
                amenities.append("Air Conditioning")
            if st.checkbox("Geyser", value=False, key="feature_geyser"):
                amenities.append("Geyser")
            if st.checkbox("WiFi/Internet", value=False, key="feature_wifi"):
                amenities.append("Internet")
        
        with col3:
            if st.checkbox("TV", value=False, key="feature_tv"):
                amenities.append("TV")
            if st.checkbox("Washing Machine", value=False, key="feature_washing"):
                amenities.append("Washing Machine")
            if st.checkbox("Fridge", value=False, key="feature_fridge"):
                amenities.append("Refrigerator")
        
        with col4:
            if st.checkbox("Sofa", value=False, key="feature_sofa"):
                amenities.append("Sofa")
            if st.checkbox("Bed", value=False, key="feature_bed"):
                amenities.append("Bed")
            if st.checkbox("Dining Table", value=False, key="feature_dining"):
                amenities.append("Dining Table")
        
        st.divider()
        
        st.markdown("#### 📍 Nearby Points of Interest")
        col1, col2 = st.columns(2)
        
        nearby_points = []
        
        with col1:
            if st.checkbox("Metro Station", value=False, key="nearby_metro"):
                distance = st.text_input("Distance from Metro", placeholder="e.g., 500m", key="metro_dist")
                nearby_points.append(f"Metro Station ({distance})" if distance else "Metro Station")
            
            if st.checkbox("Bus Stop", value=False, key="nearby_bus"):
                distance = st.text_input("Distance from Bus Stop", placeholder="e.g., 200m", key="bus_dist")
                nearby_points.append(f"Bus Stop ({distance})" if distance else "Bus Stop")
            
            if st.checkbox("Railway Station", value=False, key="nearby_railway"):
                distance = st.text_input("Distance from Railway", placeholder="e.g., 2km", key="railway_dist")
                nearby_points.append(f"Railway Station ({distance})" if distance else "Railway Station")
            
            if st.checkbox("Airport", value=False, key="nearby_airport"):
                distance = st.text_input("Distance from Airport", placeholder="e.g., 15km", key="airport_dist")
                nearby_points.append(f"Airport ({distance})" if distance else "Airport")
        
        with col2:
            if st.checkbox("School", value=False, key="nearby_school"):
                nearby_points.append("School Nearby")
            
            if st.checkbox("Hospital", value=False, key="nearby_hospital"):
                nearby_points.append("Hospital Nearby")
            
            if st.checkbox("Market/Mall", value=False, key="nearby_market"):
                nearby_points.append("Shopping Complex")
            
            if st.checkbox("Restaurant/Cafe", value=False, key="nearby_restaurant"):
                nearby_points.append("Restaurants")
        
        st.divider()
        
        st.markdown("#### 📄 Additional Description (Optional)")
        rough_description = st.text_area(
            "Owner's Description",
            placeholder="Add any additional details, special features, or unique selling points...",
            height=120,
            help="Free text to add any extra information about the property",
            key="rough_desc"
        )
    
    st.divider()
    
    # Prepare property data
    property_data = {
        'property_type': property_type.lower(),
        'bhk': bhk,
        'area_sqft': area_sqft,
        'area_unit': area_unit,
        'city': city,
        'locality': locality,
        'landmark': landmark if landmark else '',
        'floor_no': floor_no,
        'total_floors': total_floors,
        'furnishing_status': furnishing.lower(),
        'rent_amount': rent,
        'deposit_amount': deposit,
        'maintenance': maintenance,
        'parking_charges': parking_charges,
        'negotiable': negotiable,
        'available_from': str(available),
        'preferred_tenants': ', '.join(preferred_tenants),
        'amenities': amenities,
        'nearby_points': nearby_points,
        'rough_description': rough_description if rough_description else ''
    }
    
    # Generate and Regenerate buttons
    btn_col1, btn_col2 = st.columns([3, 1])
    
    with btn_col1:
        generate_clicked = st.button("🚀 Generate Premium Description", type="primary", use_container_width=True, key="generate_btn")
    
    with btn_col2:
        regenerate_clicked = st.button("🔄 Regenerate", type="secondary", use_container_width=True, 
                                      disabled=st.session_state.generated_result is None,
                                      help="Generate a different version with same details",
                                      key="regenerate_btn")
    
    # Handle generation
    if generate_clicked or regenerate_clicked:
        if not city or not locality:
            st.error("❌ Please fill in all required fields marked with *")
            return
        
        st.session_state.property_data = property_data
        
        if regenerate_clicked:
            st.session_state.generation_count += 1
            st.info(f"🔄 Generating version #{st.session_state.generation_count + 1}...")
        else:
            st.session_state.generation_count = 0
        
        with st.spinner(f"✨ Generating premium description with {api_provider}..."):
            result = generate_description(
                property_data, 
                api_provider, 
                api_key,
                variation_seed=st.session_state.generation_count
            )
        
        if result:
            st.session_state.generated_result = result
            st.success("✅ Premium Description Generated Successfully!")
    
    # Display results
    if st.session_state.generated_result:
        result = st.session_state.generated_result
        property_data = st.session_state.property_data
        
        if st.session_state.generation_count > 0:
            st.info(f"📝 Version #{st.session_state.generation_count + 1}")
        
        st.markdown("---")
        st.markdown(f"## 🏠 {result['title']}")
        st.markdown(f"*{result['teaser_text']}*")
        
        st.divider()
        
        st.markdown("### 📝 Full Description")
        st.write(result['full_description'])
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ✨ Key Features")
            for i, point in enumerate(result['bullet_points'], 1):
                st.markdown(f"**{i}.** {point}")
        
        with col2:
            st.markdown("### 🔍 SEO Keywords")
            st.info(", ".join(result['seo_keywords']))
            
            st.markdown("### 📊 SEO Metadata")
            st.text_input("Meta Title", result['meta_title'], disabled=True, key="meta_title_display")
            st.text_area("Meta Description", result['meta_description'], disabled=True, height=100, key="meta_desc_display")
        
        st.divider()
        
        # Download options
        st.markdown("### 💾 Download Options")
        
        download_col1, download_col2, download_col3 = st.columns(3)
        
        with download_col1:
            json_data = json.dumps({
                'property_details': property_data,
                'generated_content': result,
                'generation_version': st.session_state.generation_count + 1
            }, indent=2)
            st.download_button(
                "📄 Download JSON",
                json_data,
                f"property_{property_data['locality'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}_v{st.session_state.generation_count + 1}.json",
                "application/json",
                use_container_width=True,
                key="download_json"
            )
        
        with download_col2:
            text_content = f"""{result['title']}
{result['teaser_text']}

{result['full_description']}

Key Features:
{chr(10).join(f"• {p}" for p in result['bullet_points'])}

SEO Keywords: {', '.join(result['seo_keywords'])}
Meta Title: {result['meta_title']}
Meta Description: {result['meta_description']}

Version: #{st.session_state.generation_count + 1}
            """
            st.download_button(
                "📝 Download TXT",
                text_content,
                f"property_{property_data['locality'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}_v{st.session_state.generation_count + 1}.txt",
                "text/plain",
                use_container_width=True,
                key="download_txt"
            )
        
        with download_col3:
            csv_data = pd.DataFrame([{
                'Property_Type': property_data['property_type'],
                'BHK': property_data['bhk'],
                'Area': f"{property_data['area_sqft']} {property_data['area_unit']}",
                'Location': f"{property_data['locality']}, {property_data['city']}",
                'Rent': property_data['rent_amount'],
                'Title': result['title'],
                'Description': result['full_description'],
                'Features': ' | '.join(result['bullet_points']),
                'SEO_Keywords': ', '.join(result['seo_keywords']),
                'Version': st.session_state.generation_count + 1
            }])
            
            st.download_button(
                "📊 Download CSV",
                csv_data.to_csv(index=False),
                f"property_{property_data['locality'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}_v{st.session_state.generation_count + 1}.csv",
                "text/csv",
                use_container_width=True,
                key="download_csv"
            )


if __name__ == "__main__":
    main()
