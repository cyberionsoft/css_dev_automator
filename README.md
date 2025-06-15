# CSS Dev Automator - Automated Code Generation Tool

**Version 0.1.0** | **Professional Development Automation**

CSS Dev Automator is a sophisticated GUI-based tool for automating C# code generation and AI prompt processing for .NET ERP applications. It processes Excel specifications and generates comprehensive code files and AI prompts.

## 🚀 **Key Features**

### **4-Step Workflow**
1. **Download Excel Template**: Get standardized data template
2. **Browse Excel File**: Upload and validate Excel specifications
3. **Browse Solution File**: Select .NET solution for integration
4. **Generate Files**: Automated code and prompt generation

### **Excel Processing**
- **Template Download**: Standardized Excel template with validation
- **Data Validation**: Comprehensive structure and content validation
- **PascalCase Conversion**: Automatic C# naming convention compliance
- **Polars Integration**: High-performance data processing

### **Solution Management**
- **.NET Integration**: Automatic .sln file parsing and project setup
- **GTI.API Detection**: Intelligent project identification
- **Connection String Extraction**: Automatic database configuration
- **Project Creation**: CSS.AIReference project with required folders

### **Code Generation**
- **Prompt Templates**: 8 AI prompt templates with placeholder replacement
- **SP File Generation**: 3-file generation per stored procedure
- **Database Integration**: Real-time SP execution and data extraction
- **Organized Output**: Structured file organization in project folders

## 📋 **System Requirements**

- **Operating System**: Windows 10/11
- **Python**: 3.13+ (for development)
- **Dependencies**: PySide6, Polars, PyODBC, FastExcel
- **Database**: SQL Server connectivity
- **.NET**: .NET 9.0 SDK for project operations

## 🔧 **Installation**

### **End User Installation**
DevAutomator is automatically installed by DevManager:
1. Run DevManager.exe
2. DevAutomator installs to `C:\Program Files\DevManager\`
3. Launch via DevManager with secure token

### **Developer Setup**
```bash
# Clone repository
git clone https://github.com/cyberionsoft/css_dev_automator.git
cd css_dev_automator

# Install dependencies with UV
uv sync

# Run in development mode (requires token)
python main.py --token <dev_token>
```

## 🎯 **Usage**

### **Token-Based Startup**
CSS Dev Automator requires a valid token from DevManager:
```bash
# Launched by DevManager
DevAutomator.exe --token <secure_token>

# Development mode
python main.py --token <dev_token>
```

### **4-Step Workflow**

#### **Step 1: Download Excel Template**
- Click "Download Excel Template"
- Template saved to Downloads folder
- Contains required columns: SP Name, Type, Module Name, Entity Name

#### **Step 2: Browse Excel File**
- Click "Browse Excel File"
- Select completed Excel file
- Automatic validation and data extraction
- PascalCase conversion for C# compatibility

#### **Step 3: Browse Solution File**
- Click "Browse Solution File"
- Select .NET solution (.sln) file
- Automatic GTI.API project detection
- Connection string extraction from appsettings.json
- CSS.AIReference project setup

#### **Step 4: Generate Files**
- Click "Generate" button
- Comprehensive prerequisite checking
- Background processing with progress tracking
- File generation in organized folders

## 🏗️ **Architecture**

### **Core Components**
```
src/
├── gui_manager.py          # Main PySide6 GUI with threading
├── excel_manager.py        # Excel processing and validation
├── solution_manager.py     # .NET solution parsing and setup
├── database_manager.py     # SQL Server connectivity and operations
├── sp_executor.py          # Stored procedure execution and file generation
├── prompt_processor.py     # AI prompt template processing
├── project_generator.py    # Orchestrates complete generation workflow
└── token_validator.py     # DevManager token validation
```

### **Data Flow**
```
Excel File → Validation → Data Extraction
     ↓
Solution File → Parsing → Project Setup → Connection String
     ↓
Generate → Prompt Processing + SP Execution → Organized Output
```

## 📊 **File Generation**

### **Prompt Files** (AIPrompt folder)
- **8 Template Files**: Prompt1.txt through Prompt8.txt
- **Placeholder Replacement**: Module and Entity name substitution
- **AI-Ready**: Formatted for AI code generation workflows

### **SP Execution Files** (SPExecution folder)
For each stored procedure, generates 3 files:
- **SP{n}_{Type}.txt**: Complete stored procedure definition
- **SP{n}_Input.txt**: JSON input parameters for execution
- **SP{n}_Output.txt**: JSON output results from execution

### **Project Structure**
```
CSS.AIReference/
├── AIPrompt/           # Generated prompt files
├── SPExecution/        # Generated SP files
├── SPReference/        # Reference materials
└── UIReference/        # UI-related references
```

## 🔐 **Security & Authentication**

### **Token Validation**
- **DevManager Integration**: Only accepts tokens from DevManager
- **SHA-256 Hashing**: Secure token verification
- **Expiration Handling**: 24-hour token lifetime
- **One-Time Use**: Prevents token replay attacks

### **Database Security**
- **Connection String Extraction**: Secure configuration from appsettings.json
- **Timeout Management**: Configurable connection and command timeouts
- **Error Handling**: Comprehensive database error management

## 🎨 **User Interface**

### **Professional GUI**
- **Modern Design**: Clean, intuitive PySide6 interface
- **Progress Tracking**: Real-time progress bars and status updates
- **Background Processing**: Non-blocking operations with threading
- **Error Reporting**: Comprehensive error messages and recovery guidance

### **Status & Logging**
- **Real-Time Status**: Live operation status updates
- **Comprehensive Logging**: Detailed operation logs with timestamps
- **Auto-Scrolling**: Automatic log display management
- **Error Highlighting**: Visual error indication and reporting

## 📁 **Templates**

### **Excel Template** (`Templates/Excel/DataTemplate.xlsx`)
Required columns:
- **SP Name**: Stored procedure names
- **Type**: Operation type (List, Save, Get, Delete, etc.)
- **Module Name**: C# module name (first row only)
- **Entity Name**: C# entity name (first row only)

### **Prompt Templates** (`Templates/Prompts/`)
- **8 Template Files**: Prompt1.txt through Prompt8.txt
- **Placeholder Support**: {MODULE_NAME}, {ENTITY_NAME}, [ModuleName], etc.
- **Case Variations**: Multiple placeholder formats supported

## 🔄 **Data Processing**

### **Excel Validation**
- **Structure Validation**: Required columns and format checking
- **Data Validation**: Content validation and type checking
- **PascalCase Conversion**: Automatic C# naming convention compliance
- **Error Reporting**: Detailed validation error messages

### **Solution Processing**
- **.sln Parsing**: Manual parsing for project identification
- **GTI.API Detection**: Intelligent project location
- **appsettings.json Processing**: Comment-aware JSON parsing
- **Project Creation**: Automated .NET project setup

### **Database Operations**
- **SP Execution**: Real-time stored procedure execution
- **JSON Extraction**: Intelligent JSON data extraction from results
- **Batch Processing**: Efficient multi-SP processing
- **Error Recovery**: Robust error handling and recovery

## 🛠️ **Development**

### **Building**
```bash
# Build with PyInstaller
pyinstaller DevAutomator.spec --clean

# Build via DevManager
python scripts/build_devautomator.py --version 1.0.0
```

### **Testing**
```bash
# Test with sample data
python main.py --token <test_token>

# Use provided sample files
# Excel: SampleData.xlsx
# Solution: P:/Repositories/CSS SES/Gti/Gti.sln
```

### **Configuration** (`config.json`)
```json
{
    "database": {
        "connection_string": "...",
        "connection_timeout": 30,
        "command_timeout": 300
    },
    "processing": {
        "batch_size": 5,
        "parallel_processing": true,
        "max_workers": 3
    }
}
```

## 📊 **Performance**

- **Startup Time**: < 4 seconds
- **Excel Processing**: < 2 seconds for typical files
- **Solution Setup**: < 5 seconds
- **File Generation**: Variable based on SP count and complexity
- **Memory Usage**: ~110 MB runtime

## 🚨 **Troubleshooting**

### **Common Issues**

**Token Validation Fails**
- Ensure launched via DevManager
- Check token expiration
- Verify DevManager version compatibility

**Excel Validation Fails**
- Use provided template
- Check required columns
- Verify data format

**Solution Setup Fails**
- Verify .sln file accessibility
- Check GTI.API project exists
- Ensure appsettings.json is readable

**Database Connection Fails**
- Verify connection string
- Check SQL Server accessibility
- Review firewall settings

### **Error Recovery**
- **Graceful Degradation**: Continues operation when possible
- **Detailed Logging**: Comprehensive error information
- **User Guidance**: Clear error messages with resolution steps

## 🔗 **Integration**

### **DevManager Communication**
- **Token-Based Launch**: Secure authentication from DevManager
- **Process Coordination**: Proper startup and shutdown handling
- **Status Reporting**: Real-time operation status to DevManager

### **GitHub Integration**
- **Repository**: `cyberionsoft/css_dev_automator`
- **Automated Builds**: DevManager handles build and release
- **Version Management**: Coordinated with DevManager versioning

## 📝 **Sample Data**

### **Provided Files**
- **SampleData.xlsx**: Example Excel file with real SP data
- **Test Solution**: P:/Repositories/CSS SES/Gti/Gti.sln
- **Expected Output**: 5 SPs with complete file generation

### **Test Workflow**
1. Launch with token from DevManager
2. Download and examine Excel template
3. Browse SampleData.xlsx
4. Browse test solution file
5. Generate files and review output

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** Pull Request

## 📄 **License**

This project is proprietary software developed by CSS Development Team.

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/cyberionsoft/css_dev_automator/issues)
- **Documentation**: [Wiki](https://github.com/cyberionsoft/css_dev_automator/wiki)
- **Contact**: CSS Development Team

---

**CSS Dev Automator** - *Automating Development Excellence Since 2025*
