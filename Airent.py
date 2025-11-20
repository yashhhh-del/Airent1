import React, { useState } from 'react';
import { FileCode, Database, Brain, CheckCircle, ChevronRight, Copy, Check, Upload } from 'lucide-react';

const SetupGuide = () => {
  const [activePhase, setActivePhase] = useState(1);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const phases = [
    {
      id: 1,
      title: "Phase 1: Setup & Basics",
      icon: FileCode,
      color: "bg-blue-500",
      steps: [
        {
          title: "Create Django Project Structure",
          commands: [
            "# Install Django and dependencies",
            "pip install django djangorestframework python-dotenv requests pandas openpyxl",
            "",
            "# Create project",
            "django-admin startproject rental_ai_writer",
            "cd rental_ai_writer",
            "",
            "# Create app",
            "python manage.py startapp properties"
          ]
        },
        {
          title: "Configure Settings",
          file: "rental_ai_writer/settings.py",
          code: `INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # Add this
    'properties',      # Add this
]

# Media files configuration for file uploads
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Add at the end of settings.py
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB`
        },
        {
          title: "Create Media Directory",
          commands: [
            "# Create directories for file uploads",
            "mkdir -p media/uploads",
            "mkdir -p media/temp"
          ]
        }
      ]
    },
    {
      id: 2,
      title: "Phase 2: Models & Database",
      icon: Database,
      color: "bg-green-500",
      steps: [
        {
          title: "Create Models",
          file: "properties/models.py",
          code: `from django.db import models
from django.contrib.auth.models import User
import json

class Property(models.Model):
    PROPERTY_TYPES = [
        ('flat', 'Flat/Apartment'),
        ('villa', 'Villa'),
        ('pg', 'PG'),
        ('shop', 'Shop'),
        ('office', 'Office'),
    ]
    
    FURNISHING_CHOICES = [
        ('unfurnished', 'Unfurnished'),
        ('semi', 'Semi-Furnished'),
        ('fully', 'Fully Furnished'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPES)
    bhk = models.CharField(max_length=10)
    area_sqft = models.IntegerField()
    city = models.CharField(max_length=100)
    locality = models.CharField(max_length=200)
    landmark = models.CharField(max_length=200, blank=True)
    floor_no = models.IntegerField(null=True, blank=True)
    total_floors = models.IntegerField(null=True, blank=True)
    furnishing_status = models.CharField(max_length=20, choices=FURNISHING_CHOICES)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    available_from = models.DateField()
    preferred_tenants = models.CharField(max_length=100)
    amenities = models.TextField(help_text="JSON array of amenities")
    rough_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.bhk} {self.property_type} in {self.locality}, {self.city}"
    
    def get_amenities_list(self):
        try:
            return json.loads(self.amenities)
        except:
            return []

class PropertyDescription(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='descriptions')
    title = models.CharField(max_length=500)
    teaser_text = models.TextField()
    full_description = models.TextField()
    bullet_points = models.TextField(help_text="JSON array")
    seo_keywords = models.TextField(help_text="JSON array")
    meta_title = models.CharField(max_length=200)
    meta_description = models.CharField(max_length=300)
    version_no = models.IntegerField(default=1)
    language_code = models.CharField(max_length=10, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-version_no', '-created_at']
    
    def __str__(self):
        return f"Description v{self.version_no} for {self.property}"
    
    def get_bullet_points_list(self):
        try:
            return json.loads(self.bullet_points)
        except:
            return []
    
    def get_seo_keywords_list(self):
        try:
            return json.loads(self.seo_keywords)
        except:
            return []

class FileUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    
    def __str__(self):
        return f"Upload {self.id} - {self.file.name} ({self.status})"
    
    class Meta:
        ordering = ['-uploaded_at']`
        },
        {
          title: "Run Migrations",
          commands: [
            "python manage.py makemigrations",
            "python manage.py migrate",
            "python manage.py createsuperuser"
          ]
        }
      ]
    },
    {
      id: 3,
      title: "Phase 3: File Processing Service",
      icon: Upload,
      color: "bg-indigo-500",
      steps: [
        {
          title: "Create File Parser Service",
          file: "properties/services/file_parser.py",
          code: `import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Optional

class FileParser:
    """Service to parse Excel/CSV files and extract property data"""
    
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
    
    def parse_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Parse Excel or CSV file"""
        try:
            # Determine file type and read
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                self.errors.append("Unsupported file format. Use CSV or Excel files.")
                return None
            
            return df
        
        except Exception as e:
            self.errors.append(f"Error reading file: {str(e)}")
            return None
    
    def validate_columns(self, df: pd.DataFrame) -> bool:
        """Validate that all required columns exist"""
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        
        if missing_columns:
            self.errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            return False
        
        return True
    
    def clean_row_data(self, row: pd.Series) -> Optional[Dict]:
        """Clean and validate a single row of data"""
        try:
            # Convert amenities string to list if present
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
                    available_from = datetime.strptime(available_from, '%Y-%m-%d').date()
                except:
                    try:
                        available_from = datetime.strptime(available_from, '%d/%m/%Y').date()
                    except:
                        available_from = datetime.now().date()
            
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
                'available_from': available_from,
                'preferred_tenants': str(row['preferred_tenants']).strip(),
                'amenities': json.dumps(amenities),
                'rough_description': str(row.get('rough_description', '')).strip(),
            }
            
            return clean_data
        
        except Exception as e:
            self.errors.append(f"Error cleaning row data: {str(e)}")
            return None
    
    def process_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Process entire dataframe and return list of clean property data"""
        properties = []
        
        for idx, row in df.iterrows():
            clean_data = self.clean_row_data(row)
            if clean_data:
                properties.append(clean_data)
            else:
                self.warnings.append(f"Skipped row {idx + 2} due to validation errors")
        
        return properties
    
    def get_sample_template(self) -> pd.DataFrame:
        """Generate a sample template DataFrame"""
        sample_data = {
            'property_type': ['flat', 'villa', 'pg'],
            'bhk': ['2', '3', '1'],
            'area_sqft': [1200, 2500, 400],
            'city': ['Mumbai', 'Bangalore', 'Pune'],
            'locality': ['Andheri West', 'Koramangala', 'Kothrud'],
            'landmark': ['Near Metro Station', 'Sony World Signal', 'Near FC Road'],
            'floor_no': [5, 1, 2],
            'total_floors': [10, 2, 4],
            'furnishing_status': ['semi', 'fully', 'unfurnished'],
            'rent_amount': [25000, 45000, 8000],
            'deposit_amount': [50000, 90000, 16000],
            'available_from': ['2024-12-01', '2024-12-15', '2024-12-01'],
            'preferred_tenants': ['Family', 'Family', 'Students/Working Professionals'],
            'amenities': ['Parking, Gym, Security', 'Garden, Swimming Pool, Power Backup', 'WiFi, Meals'],
            'rough_description': ['Spacious apartment with modern amenities', 'Luxury villa with premium features', 'Budget-friendly PG accommodation']
        }
        
        return pd.DataFrame(sample_data)

# Singleton instance
file_parser = FileParser()`
        },
        {
          title: "Create Bulk Import Service",
          file: "properties/services/bulk_importer.py",
          code: `from typing import List, Dict, Tuple
from ..models import Property, FileUpload
from .file_parser import file_parser
import traceback

class BulkImporter:
    """Service to handle bulk import of properties from parsed file data"""
    
    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.errors = []
    
    def import_properties(self, properties_data: List[Dict], file_upload: FileUpload) -> Tuple[int, int, List[str]]:
        """
        Import multiple properties from parsed data
        Returns: (success_count, failed_count, errors)
        """
        self.success_count = 0
        self.failed_count = 0
        self.errors = []
        
        file_upload.status = 'processing'
        file_upload.total_rows = len(properties_data)
        file_upload.save()
        
        for idx, prop_data in enumerate(properties_data, 1):
            try:
                # Create property
                property_obj = Property.objects.create(**prop_data)
                self.success_count += 1
                
                # Update progress
                file_upload.processed_rows = idx
                file_upload.save()
                
            except Exception as e:
                self.failed_count += 1
                error_msg = f"Row {idx}: {str(e)}"
                self.errors.append(error_msg)
                print(f"Error importing property: {error_msg}")
                print(traceback.format_exc())
        
        # Update file upload status
        file_upload.processed_rows = len(properties_data)
        file_upload.failed_rows = self.failed_count
        file_upload.status = 'completed' if self.failed_count == 0 else 'failed'
        file_upload.error_log = '\\n'.join(self.errors) if self.errors else ''
        file_upload.save()
        
        return self.success_count, self.failed_count, self.errors

# Singleton instance
bulk_importer = BulkImporter()`
        }
      ]
    },
    {
      id: 4,
      title: "Phase 4: AI Integration",
      icon: Brain,
      color: "bg-purple-500",
      steps: [
        {
          title: "Create AI Service Module",
          file: "properties/ai_services/genai_writer.py",
          code: `import os
import requests
from typing import Dict, Optional
import json

class GenAIWriter:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-sonnet-4-20250514"
    
    def build_prompt(self, property_data: Dict) -> str:
        """Build the prompt for the AI model"""
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
- Rent: ₹{property_data.get('rent_amount', 'N/A')}/month
- Deposit: ₹{property_data.get('deposit_amount', 'N/A')}
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
    
    def generate_description(self, property_data: Dict) -> Optional[Dict]:
        """Generate property description using AI"""
        
        # FOR TESTING: Return dummy data first
        if not self.api_key:
            return self._generate_dummy_description(property_data)
        
        try:
            prompt = self.build_prompt(property_data)
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 2000,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '')
            
            # Parse JSON from response
            description_data = json.loads(content)
            return description_data
            
        except Exception as e:
            print(f"AI Generation Error: {str(e)}")
            return self._generate_dummy_description(property_data)
    
    def _generate_dummy_description(self, property_data: Dict) -> Dict:
        """Generate dummy description for testing"""
        bhk = property_data.get('bhk', '2')
        prop_type = property_data.get('property_type', 'Flat')
        locality = property_data.get('locality', 'Area')
        city = property_data.get('city', 'City')
        
        return {
            "title": f"Spacious {bhk} BHK {prop_type} for Rent in {locality}",
            "teaser_text": f"Well-maintained {bhk} BHK property in prime {locality} location with excellent connectivity.",
            "full_description": f"This beautiful {bhk} BHK {prop_type.lower()} in {locality}, {city} offers comfortable living with modern amenities. The property features spacious rooms with ample natural light and ventilation. Located in a peaceful neighborhood with easy access to markets, schools, and public transport. Perfect for families looking for a convenient and comfortable home.",
            "bullet_points": [
                f"Spacious {bhk} BHK with {property_data.get('area_sqft', 'large')} sq ft area",
                f"{property_data.get('furnishing_status', 'Well furnished')} with modern fittings",
                f"Located in {locality} with excellent connectivity",
                "24/7 security and power backup",
                "Close to schools, hospitals and shopping centers"
            ],
            "seo_keywords": [
                f"{bhk} bhk rent {city}",
                f"{locality} {prop_type.lower()} for rent",
                f"rental property {city}",
                f"{prop_type.lower()} for family {city}"
            ],
            "meta_title": f"{bhk} BHK {prop_type} for Rent in {locality}, {city}",
            "meta_description": f"Find your ideal {bhk} BHK {prop_type.lower()} in {locality}, {city}. Well-maintained property with modern amenities. Contact now for viewing!"
        }

# Singleton instance
genai_writer = GenAIWriter()`
        },
        {
          title: "Create Environment File",
          file: ".env",
          code: `# Add your API key here
OPENAI_API_KEY=your_api_key_here
# Or use Claude API
ANTHROPIC_API_KEY=your_claude_api_key_here

DEBUG=True
SECRET_KEY=your-secret-key-here`
        }
      ]
    },
    {
      id: 5,
      title: "Phase 5: Views & URLs",
      icon: CheckCircle,
      color: "bg-orange-500",
      steps: [
        {
          title: "Create Views with File Upload",
          file: "properties/views.py",
          code: `from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Property, PropertyDescription, FileUpload
from .ai_services.genai_writer import genai_writer
from .services.file_parser import file_parser
from .services.bulk_importer import bulk_importer
import json
import os

def home(request):
    return render(request, 'properties/home.html')

def property_list(request):
    properties = Property.objects.all().order_by('-created_at')
    return render(request, 'properties/property_list.html', {'properties': properties})

def add_property(request):
    if request.method == 'POST':
        # Extract form data
        property_data = {
            'property_type': request.POST.get('property_type'),
            'bhk': request.POST.get('bhk'),
            'area_sqft': request.POST.get('area_sqft'),
            'city': request.POST.get('city'),
            'locality': request.POST.get('locality'),
            'landmark': request.POST.get('landmark', ''),
            'floor_no': request.POST.get('floor_no') or None,
            'total_floors': request.POST.get('total_floors') or None,
            'furnishing_status': request.POST.get('furnishing_status'),
            'rent_amount': request.POST.get('rent_amount'),
            'deposit_amount': request.POST.get('deposit_amount'),
            'available_from': request.POST.get('available_from'),
            'preferred_tenants': request.POST.get('preferred_tenants'),
            'amenities': json.dumps(request.POST.getlist('amenities')),
            'rough_description': request.POST.get('rough_description', ''),
        }
        
        property_obj = Property.objects.create(**property_data)
        
        # Check if user wants to generate with AI
        if 'generate_ai' in request.POST:
            return redirect('generate_description', property_id=property_obj.id)
        
        messages.success(request, 'Property added successfully!')
        return redirect('property_list')
    
    return render(request, 'properties/add_property.html')

def bulk_upload(request):
    """Handle bulk property upload via Excel/CSV"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'No file uploaded!')
            return redirect('bulk_upload')
        
        uploaded_file = request.FILES['file']
        
        # Validate file extension
        if not uploaded_file.name.endswith(('.csv', '.xlsx', '.xls')):
            messages.error(request, 'Invalid file format. Please upload CSV or Excel file.')
            return redirect('bulk_upload')
        
        # Create FileUpload record
        file_upload = FileUpload.objects.create(
            file=uploaded_file,
            uploaded_by=request.user if request.user.is_authenticated else None,
            status='pending'
        )
        
        try:
            # Parse file
            file_path = file_upload.file.path
            df = file_parser.parse_file(file_path)
            
            if df is None:
                raise Exception("Failed to parse file: " + ", ".join(file_parser.errors))
            
            # Validate columns
            if not file_parser.validate_columns(df):
                raise Exception("Column validation failed: " + ", ".join(file_parser.errors))
            
            # Process data
            properties_data = file_parser.process_dataframe(df)
            
            if not properties_data:
                raise Exception("No valid property data found in file")
            
            # Import properties
            success_count, failed_count, errors = bulk_importer.import_properties(
                properties_data, 
                file_upload
            )
            
            # Show results
            if success_count > 0:
                messages.success(
                    request, 
                    f'Successfully imported {success_count} properties!'
                )
            
            if failed_count > 0:
                messages.warning(
                    request,
                    f'{failed_count} properties failed to import. Check upload history for details.'
                )
            
            return redirect('upload_history')
        
        except Exception as e:
            file_upload.status = 'failed'
            file_upload.error_log = str(e)
            file_upload.save()
            
            messages.error(request, f'Upload failed: {str(e)}')
            return redirect('bulk_upload')
    
    # GET request - show upload form
    recent_uploads = FileUpload.objects.all()[:5]
    return render(request, 'properties/bulk_upload.html', {
        'recent_uploads': recent_uploads
    })

def upload_history(request):
    """View upload history"""
    uploads = FileUpload.objects.all()
    return render(request, 'properties/upload_history.html', {
        'uploads': uploads
    })

def download_template(request):
    """Download sample Excel template"""
    import pandas as pd
    from django.http import HttpResponse
    
    # Generate sample template
    template_df = file_parser.get_sample_template()
    
    # Create Excel file in memory
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=property_upload_template.xlsx'
    
    # Write to response
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Properties')
    
    return response

def generate_description(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    
    # Prepare data for AI
    property_data = {
        'property_type': property_obj.property_type,
        'bhk': property_obj.bhk,
        'area_sqft': property_obj.area_sqft,
        'city': property_obj.city,
        'locality': property_obj.locality,
        'landmark': property_obj.landmark,
        'floor_no': property_obj.floor_no,
        'total_floors': property_obj.total_floors,
        'furnishing_status': property_obj.furnishing_status,
        'rent_amount': str(property_obj.rent_amount),
        'deposit_amount': str(property_obj.deposit_amount),
        'available_from': str(property_obj.available_from),
        'preferred_tenants': property_obj.preferred_tenants,
        'amenities': property_obj.get_amenities_list(),
        'rough_description': property_obj.rough_description,
    }
    
    # Generate description
    ai_result = genai_writer.generate_description(property_data)
    
    if ai_result:
        # Get latest version number
        latest = PropertyDescription.objects.filter(property=property_obj).first()
        version = (latest.version_no + 1) if latest else 1
        
        # Save description
        description = PropertyDescription.objects.create(
            property=property_obj,
            title=ai_result['title'],
            teaser_text=ai_result['teaser_text'],
            full_description=ai_result['full_description'],
            bullet_points=json.dumps(ai_result['bullet_points']),
            seo_keywords=json.dumps(ai_result['seo_keywords']),
            meta_title=ai_result['meta_title'],
            meta_description=ai_result['meta_description'],
            version_no=version
        )
        
        messages.success(request, 'AI description generated successfully!')
        return redirect('edit_description', description_id=description.id)
    
    messages.error(request, 'Failed to generate description')
    return redirect('property_list')

def bulk_generate_descriptions(request):
    """Generate AI descriptions for all properties without descriptions"""
    if request.method == 'POST':
        # Get properties without descriptions
        properties = Property.objects.filter(descriptions__isnull=True)
        
        success_count = 0
        failed_count = 0
        
        for prop in properties:
            property_data = {
                'property_type': prop.property_type,
                'bhk': prop.bhk,
                'area_sqft': prop.area_sqft,
                'city': prop.city,
                'locality': prop.locality,
                'landmark': prop.landmark,
                'floor_no': prop.floor_no,
                'total_floors': prop.total_floors,
                'furnishing_status': prop.furnishing_status,
                'rent_amount': str(prop.rent_amount),
                'deposit_amount': str(prop.deposit_amount),
                'available_from': str(prop.available_from),
                'preferred_tenants': prop.preferred_tenants,
                'amenities': prop.get_amenities_list(),
                'rough_description': prop.rough_description,
            }
            
            ai_result = genai_writer.generate_description(property_data)
            
            if ai_result:
                PropertyDescription.objects.create(
                    property=prop,
                    title=ai_result['title'],
                    teaser_text=ai_result['teaser_text'],
                    full_description=ai_result['full_description'],
                    bullet_points=json.dumps(ai_result['bullet_points']),
                    seo_keywords=json.dumps(ai_result['seo_keywords']),
                    meta_title=ai_result['meta_title'],
                    meta_description=ai_result['meta_description'],
                    version_no=1
                )
                success_count += 1
            else:
                failed_count += 1
        
        messages.success(request, f'Generated {success_count} descriptions. Failed: {failed_count}')
        return redirect('property_list')
    
    properties_without_desc = Property.objects.filter(descriptions__isnull=True).count()
    return render(request, 'properties/bulk_generate.html', {
        'count': properties_without_desc
    })

def edit_description(request, description_id):
    description = get_object_or_404(PropertyDescription, id=description_id)
    
    if request.method == 'POST':
        description.title = request.POST.get('title')
        description.teaser_text = request.POST.get('teaser_text')
        description.full_description = request.POST.get('full_description')
        description.meta_title = request.POST.get('meta_title')
        description.meta_description = request.POST.get('meta_description')
        description.save()
        
        messages.success(request, 'Description updated successfully!')
        return redirect('property_list')
    
    context = {
        'description': description,
        'property': description.property,
        'bullet_points': description.get_bullet_points_list(),
        'seo_keywords': description.get_seo_keywords_list(),
    }
    
    return render(request, 'properties/edit_description.html', context)`
        },
        {
          title: "Configure URLs",
          file: "properties/urls.py",
          code: `from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('properties/', views.property_list, name='property_list'),
    path('properties/add/', views.add_property, name='add_property'),
    path('properties/bulk-upload/', views.bulk_upload, name='bulk_upload'),
    path('properties/upload-history/', views.upload_history, name='upload_history'),
    path('properties/download-template/', views.download_template, name='download_template'),
    path('properties/<int:property_id>/generate/', views.generate_description, name='generate_description'),
    path('properties/bulk-generate/', views.bulk_generate_descriptions, name='bulk_generate_descriptions'),
    path('descriptions/<int:description_id>/edit/', views.edit_description, name='edit_description'),
]`
        },
        {
          title: "Update Main URLs",
          file: "rental_ai_writer/urls.py",
          code: `from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('properties.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)`
        }
      ]
    },
    {
      id: 6,
      title: "Phase 6: Templates",
      icon: FileCode,
      color: "bg-pink-500",
      steps: [
        {
          title: "Create Bulk Upload Template",
          file: "properties/templates/properties/bulk_upload.html",
          code: `<!DOCTYPE html>
<html>
<head>
    <title>Bulk Upload Properties</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg p-8">
                <h1 class="text-3xl font-bold text-gray-800 mb-6">Bulk Upload Properties</h1>
                
                {% if messages %}
                    {% for message in messages %}
                        <div class="mb-4 p-4 rounded {% if message.tags == 'success' %}bg-green-100 text-green-800{% elif message.tags == 'error' %}bg-red-100 text-red-800{% else %}bg-yellow-100 text-yellow-800{% endif %}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
                
                <div class="mb-8">
                    <div class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                        <h3 class="font-bold text-blue-900 mb-2">📋 Upload Instructions</h3>
                        <ul class="text-sm text-blue-800 space-y-1">
                            <li>• Download the template Excel file below</li>
                            <li>• Fill in your property data following the format</li>
                            <li>• Upload the completed file (supports .xlsx, .xls, .csv)</li>
                            <li>• System will validate and import all properties</li>
                        </ul>
                    </div>
                    
                    <a href="{% url 'download_template' %}" 
                       class="inline-block bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 mb-4">
                        📥 Download Template File
                    </a>
                </div>
                
                <form method="post" enctype="multipart/form-data" class="space-y-6">
                    {% csrf_token %}
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Select File to Upload
                        </label>
                        <input type="file" 
                               name="file" 
                               accept=".csv,.xlsx,.xls"
                               required
                               class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                    </div>
                    
                    <button type="submit" 
                            class="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium">
                        🚀 Upload and Import Properties
                    </button>
                </form>
                
                {% if recent_uploads %}
                <div class="mt-8 pt-8 border-t">
                    <h2 class="text-xl font-bold text-gray-800 mb-4">Recent Uploads</h2>
                    <div class="space-y-2">
                        {% for upload in recent_uploads %}
                            <div class="flex items-center justify-between p-4 bg-gray-50 rounded">
                                <div>
                                    <p class="font-medium">{{ upload.file.name }}</p>
                                    <p class="text-sm text-gray-600">{{ upload.uploaded_at|date:"Y-m-d H:i" }}</p>
                                </div>
                                <span class="px-3 py-1 rounded text-sm {% if upload.status == 'completed' %}bg-green-100 text-green-800{% elif upload.status == 'failed' %}bg-red-100 text-red-800{% elif upload.status == 'processing' %}bg-yellow-100 text-yellow-800{% else %}bg-gray-100 text-gray-800{% endif %}">
                                    {{ upload.status }}
                                </span>
                            </div>
                        {% endfor %}
                    </div>
                    <a href="{% url 'upload_history' %}" class="inline-block mt-4 text-blue-600 hover:underline">
                        View All Uploads →
                    </a>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>`
        },
        {
          title: "Create Upload History Template",
          file: "properties/templates/properties/upload_history.html",
          code: `<!DOCTYPE html>
<html>
<head>
    <title>Upload History</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-6xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg p-8">
                <h1 class="text-3xl font-bold text-gray-800 mb-6">Upload History</h1>
                
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">File</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Success</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Failed</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {% for upload in uploads %}
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap text-sm">{{ upload.file.name }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm">{{ upload.uploaded_at|date:"Y-m-d H:i" }}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="px-2 py-1 rounded text-xs {% if upload.status == 'completed' %}bg-green-100 text-green-800{% elif upload.status == 'failed' %}bg-red-100 text-red-800{% elif upload.status == 'processing' %}bg-yellow-100 text-yellow-800{% else %}bg-gray-100 text-gray-800{% endif %}">
                                        {{ upload.status }}
                                    </span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm">{{ upload.total_rows }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-green-600">{{ upload.processed_rows|add:"-"|add:upload.failed_rows }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-red-600">{{ upload.failed_rows }}</td>
                            </tr>
                            {% if upload.error_log %}
                            <tr>
                                <td colspan="6" class="px-6 py-2 bg-red-50">
                                    <details class="text-xs text-red-800">
                                        <summary class="cursor-pointer font-medium">View Errors</summary>
                                        <pre class="mt-2 whitespace-pre-wrap">{{ upload.error_log }}</pre>
                                    </details>
                                </td>
                            </tr>
                            {% endif %}
                            {% empty %}
                            <tr>
                                <td colspan="6" class="px-6 py-4 text-center text-gray-500">No uploads yet</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                
                <div class="mt-6">
                    <a href="{% url 'bulk_upload' %}" class="text-blue-600 hover:underline">← Back to Upload</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>`
        }
      ]
    }
  ];

  const currentPhase = phases.find(p => p.id === activePhase);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            GenAI Property Description Auto-Writer
          </h1>
          <p className="text-gray-600 text-lg">Django + Python Setup Guide with Bulk Upload</p>
          <div className="mt-4 flex gap-3">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">Django</span>
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">AI Integration</span>
            <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">File Upload</span>
            <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm">Bulk Import</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Phase Navigation */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6 sticky top-6">
              <h2 className="text-xl font-bold mb-4 text-gray-800">Phases</h2>
              <div className="space-y-2">
                {phases.map((phase) => {
                  const Icon = phase.icon;
                  return (
                    <button
                      key={phase.id}
                      onClick={() => setActivePhase(phase.id)}
                      className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${
                        activePhase === phase.id
                          ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-md'
                          : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className={`p-2 rounded ${activePhase === phase.id ? 'bg-white/20' : phase.color}`}>
                        <Icon size={20} className={activePhase === phase.id ? 'text-white' : 'text-white'} />
                      </div>
                      <span className="text-sm font-medium text-left flex-1">
                        Phase {phase.id}
                      </span>
                      {activePhase === phase.id && <ChevronRight size={20} />}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Phase Content */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow-lg p-8">
              <div className="flex items-center gap-4 mb-6">
                {React.createElement(currentPhase.icon, {
                  size: 32,
                  className: 'text-blue-600'
                })}
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">
                    {currentPhase.title}
                  </h2>
                  <p className="text-gray-600">Step-by-step implementation guide</p>
                </div>
              </div>

              <div className="space-y-8">
                {currentPhase.steps.map((step, stepIndex) => (
                  <div key={stepIndex} className="border-l-4 border-blue-500 pl-6">
                    <h3 className="text-xl font-semibold text-gray-800 mb-3">
                      {step.title}
                    </h3>
                    
                    {step.file && (
                      <div className="mb-2 text-sm text-gray-600 font-mono bg-gray-50 inline-block px-3 py-1 rounded">
                        📄 {step.file}
                      </div>
                    )}

                    {step.commands && (
                      <div className="relative">
                        <button
                          onClick={() => copyToClipboard(step.commands.join('\n'), `cmd-${stepIndex}`)}
                          className="absolute top-2 right-2 p-2 bg-gray-700 hover:bg-gray-600 rounded text-white transition-colors"
                          title="Copy commands"
                        >
                          {copiedIndex === `cmd-${stepIndex}` ? <Check size={16} /> : <Copy size={16} />}
                        </button>
                        <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto font-mono text-sm">
                          {step.commands.join('\n')}
                        </pre>
                      </div>
                    )}

                    {step.code && (
                      <div className="relative">
                        <button
                          onClick={() => copyToClipboard(step.code, `code-${stepIndex}`)}
                          className="absolute top-2 right-2 p-2 bg-gray-700 hover:bg-gray-600 rounded text-white transition-colors z-10"
                          title="Copy code"
                        >
                          {copiedIndex === `code-${stepIndex}` ? <Check size={16} /> : <Copy size={16} />}
                        </button>
                        <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
                          <code>{step.code}</code>
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Navigation Buttons */}
              <div className="flex justify-between mt-8 pt-6 border-t">
                <button
                  onClick={() => setActivePhase(Math.max(1, activePhase - 1))}
                  disabled={activePhase === 1}
                  className={`px-6 py-2 rounded-lg font-medium ${
                    activePhase === 1
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Previous
                </button>
                <button
                  onClick={() => setActivePhase(Math.min(phases.length, activePhase + 1))}
                  disabled={activePhase === phases.length}
                  className={`px-6 py-2 rounded-lg font-medium ${
                    activePhase === phases.length
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  Next Phase
                </button>
              </div>
            </div>

            {/* Quick Tips */}
            <div className="mt-6 bg-blue-50 border-l-4 border-blue-500 p-6 rounded-lg">
              <h3 className="font-bold text-blue-900 mb-2">💡 Quick Tips</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Copy code blocks using the copy button in the top-right corner</li>
                <li>• Download the template file to see the required format</li>
                <li>• Supported formats: .xlsx, .xls, .csv</li>
                <li>• Use bulk upload for importing multiple properties at once</li>
                <li>• Generate AI descriptions for all uploaded properties in one click</li>
                <li>• Check upload history to track import status and errors</li>
              </ul>
            </div>

            {/* Features Overview */}
            <div className="mt-6 bg-gradient-to-r from-purple-50 to-pink-50 border-l-4 border-purple-500 p-6 rounded-lg">
              <h3 className="font-bold text-purple-900 mb-3">🚀 New Features</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-semibold text-purple-800 mb-1">📤 Bulk Upload</h4>
                  <p className="text-purple-700">Upload Excel/CSV files with multiple properties</p>
                </div>
                <div>
                  <h4 className="font-semibold text-purple-800 mb-1">📋 Template Download</h4>
                  <p className="text-purple-700">Get pre-formatted Excel template with sample data</p>
                </div>
                <div>
                  <h4 className="font-semibold text-purple-800 mb-1">✅ Data Validation</h4>
                  <p className="text-purple-700">Automatic validation of uploaded data</p>
                </div>
                <div>
                  <h4 className="font-semibold text-purple-800 mb-1">📊 Upload History</h4>
                  <p className="text-purple-700">Track all uploads with detailed error logs</p>
                </div>
                <div>
                  <h4 className="font-semibold text-purple-800 mb-1">🤖 Bulk AI Generation</h4>
                  <p className="text-purple-700">Generate descriptions for all properties at once</p>
                </div>
                <div>
                  <h4 className="font-semibold text-purple-800 mb-1">🔄 Progress Tracking</h4>
                  <p className="text-purple-700">Real-time status updates during import</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SetupGuide;
