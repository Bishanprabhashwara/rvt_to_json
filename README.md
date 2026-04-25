# Revit-to-JSON Converter

In this pipeline, the `.rvt` file is first converted to an `.ifc` file using the Autodesk APS API, and then that `.ifc` file is processed into the final JSON structure.

### Why is Autodesk APS needed?
The `.rvt` (Revit) format is a **proprietary, closed binary format** created by Autodesk. Standard Python libraries cannot naturally "read" or "unlock" the data inside a Revit file. So In here the .rvt file is converted to .ifc file using APS API and then the .ifc file is converted to JSON file.
*   **Translation**: APS acts as a cloud-based translator that turns the encrypted Revit data into the open-standard IFC format.
*   **Accessibility**: Without APS, you would need to have the full Revit desktop software installed on your machine to access the data. Using APS allows this tool to be lightweight and run anywhere.

## 🛠️ How it Works

The pipeline is managed by specialized "Agents" in the following sequence:

1.  **APS Conversion**: Converts the Revit file into a standard BIM format (IFC) via the Autodesk cloud.
2.  **`load_model_agent`**: Downloads model data and prepares it for processing.
3.  **`extract_elements_agent`**: Extracts exact measurements for walls, floors, and doors. All dimensions are converted to **SI Meters**.
4.  **`llm_gap_analysis_agent`**: Scans for missing information (such as fire ratings or materials) and suggests technical inferences using Google Gemini.
5.  **`schema_alignment_agent`**: Organizes all data into the final hierarchical JSON structure.

## 💡 Architecture Approach

The system follows a **Hybrid Methodology**:
*   **Dimensional Accuracy**: Measurements are pulled directly from model data using code. AI is not used for geometric extraction to ensure 100% mathematical precision.
*   **Semantic Intelligence**: AI is used for data auditing. If a parameter is missing, the system suggests values based on element names or spatial context.(Added just to get summery about the building. build using gemini because it has a free trial and sutable for this task.)

## 📌 Important Notes

*   **Units**: All linear dimensions are stored in **Meters** (keys end in `_m`).
*   **ID Mapping**: The `UniqueId` from Revit is used as the primary identifier for consistent tracking across model updates.
*   **Spatial Gaps**: If the model lacks "Room" definitions, the tool identifies the gap and provides suggestions for reconstructing spatial boundaries using wall connections.

## 🚀 Getting Started

### 1. Setup Virtual Environment
It is recommended to use a virtual environment to keep dependencies isolated:
```bash
# Create the environment
python -m venv .venv

# Activate the environment (Windows)
.venv\Scripts\activate

# Activate the environment (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements_langgraph.txt
```

### 2. Configure Credentials
Create a file named `.env` in the main folder to store API credentials.
```env
APS_CLIENT_ID="your_client_id"
APS_CLIENT_SECRET="your_client_secret"
GEMINI_API_KEY="your_api_key"
APS_AUTH_URL="your_aps_auth_url"
APS_OSS_BASE="your_aps_oss_base"
APS_MD_BASE="your_aps_md_base"
BUCKET_KEY="your_bucket_key"
```

### 2. Run
To convert a Revit file, execute the following command in the terminal:
```bash
python revit_extractor.py --rvt "path/to/file.rvt"
```

```bash
python revit_extractor.py --rvt "path/to/file.rvt" --output-dir "path/to/output_folder"
```

### 4. Running Tests
To verify the pipeline logic and ensure all agents are working correctly:
```bash
python -m pytest tests/
```

## 📁 Folder Guide
- `app/agents/`: Node implementations for data extraction and gap analysis.
- `app/adapters/`: Communication logic for the Autodesk APS API.
- `output/`: Storage for generated JSON and IFC artifacts.
