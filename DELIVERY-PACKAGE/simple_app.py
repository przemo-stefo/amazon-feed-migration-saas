#!/usr/bin/env python3
"""
Simple Amazon Feed Migration Tool
One-file application for easy deployment
"""

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import json
import os
import tempfile
from datetime import datetime
import uvicorn

app = FastAPI(title="Amazon Feed Migration Tool")

# Create uploads directory
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Amazon Feed Migration Tool</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #232f3e; color: white; padding: 20px; text-align: center; margin-bottom: 30px; }
        .status { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; margin-bottom: 20px; }
        .upload-area { border: 2px dashed #007bff; padding: 40px; text-align: center; margin-bottom: 20px; }
        .upload-area:hover { background: #f8f9fa; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .progress { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .results { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 10px 0; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; margin: 10px 0; }
        select, input[type="file"] { padding: 8px; margin: 5px; width: 200px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Amazon Feed Migration Tool</h1>
        <p>Convert your XLSB/Excel feeds to Amazon SP-API JSON format</p>
    </div>

    <div class="status">
        <strong>✅ Status: Ready</strong><br>
        Tool is running and ready to process your feeds.
    </div>

    <div class="upload-area">
        <h3>📁 Upload Your XLSB/Excel File</h3>
        <form id="uploadForm" enctype="multipart/form-data">
            <p>Select your feed file:</p>
            <input type="file" id="fileInput" name="file" accept=".xlsb,.xlsx,.xls" required><br><br>

            <p>Choose feed type:</p>
            <select id="feedType" name="feed_type" required>
                <option value="">Select feed type...</option>
                <option value="inventory">Inventory (Stock quantities)</option>
                <option value="pricing">Pricing (Product prices)</option>
                <option value="listings">Listings (Product info)</option>
                <option value="images">Images (Product photos)</option>
            </select><br><br>

            <button type="submit" class="btn">🔄 Process Feed</button>
        </form>
    </div>

    <div id="progress" style="display: none;" class="progress">
        <h4>⏳ Processing...</h4>
        <p id="progressText">Starting...</p>
    </div>

    <div id="results" style="display: none;" class="results">
        <h4>✅ Processing Complete!</h4>
        <div id="resultsContent"></div>
    </div>

    <div id="error" style="display: none;" class="error">
        <h4>❌ Error</h4>
        <div id="errorContent"></div>
    </div>

    <script>
        document.getElementById('uploadForm').onsubmit = async function(e) {
            e.preventDefault();

            const formData = new FormData();
            const fileInput = document.getElementById('fileInput');
            const feedType = document.getElementById('feedType');

            if (!fileInput.files[0]) {
                alert('Please select a file');
                return;
            }

            if (!feedType.value) {
                alert('Please select feed type');
                return;
            }

            formData.append('file', fileInput.files[0]);
            formData.append('feed_type', feedType.value);

            // Show progress
            document.getElementById('progress').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';

            document.getElementById('progressText').textContent = 'Uploading file...';

            try {
                const response = await fetch('/process-feed', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    document.getElementById('progress').style.display = 'none';
                    document.getElementById('results').style.display = 'block';
                    document.getElementById('resultsContent').innerHTML =
                        `<p><strong>📊 ${result.total_items}</strong> items processed</p>
                         <p><strong>✅ ${result.successful_items}</strong> successful</p>
                         <p><strong>⚠️ ${result.warnings || 0}</strong> warnings</p>
                         <p><a href="/download/${result.output_file}" class="btn">📥 Download JSON File</a></p>
                         <p><a href="/download/${result.report_file}" class="btn">📋 Download Report</a></p>`;
                } else {
                    throw new Error(result.detail || 'Processing failed');
                }
            } catch (error) {
                document.getElementById('progress').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('errorContent').textContent = error.message;
            }
        };
    </script>
</body>
</html>
    """

@app.post("/process-feed")
async def process_feed(file: UploadFile = File(...), feed_type: str = Form(...)):
    """Process uploaded feed file"""
    try:
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_filename = f"input_{timestamp}_{file.filename}"
        input_path = os.path.join("uploads", input_filename)

        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Parse file based on extension
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext == '.xlsb':
            df = pd.read_excel(input_path, engine='pyxlsb')
        else:
            df = pd.read_excel(input_path)

        # Clean column names
        df.columns = [str(col).lower().strip().replace(' ', '_') for col in df.columns]

        # Process based on feed type
        json_data = convert_to_amazon_format(df, feed_type)

        # Save output files
        output_filename = f"amazon_feed_{feed_type}_{timestamp}.json"
        output_path = os.path.join("outputs", output_filename)

        with open(output_path, 'w') as f:
            json.dump(json_data, f, indent=2)

        # Generate report
        report_filename = f"report_{feed_type}_{timestamp}.txt"
        report_path = os.path.join("outputs", report_filename)

        with open(report_path, 'w') as f:
            f.write(f"Amazon Feed Migration Report\n")
            f.write(f"==========================\n\n")
            f.write(f"File: {file.filename}\n")
            f.write(f"Feed Type: {feed_type}\n")
            f.write(f"Processed: {datetime.now()}\n\n")
            f.write(f"Total items: {len(df)}\n")
            f.write(f"Successful: {len(json_data.get('messages', []))}\n")
            f.write(f"Output file: {output_filename}\n\n")
            f.write(f"Column mapping:\n")
            for col in df.columns:
                f.write(f"  - {col}\n")

        return {
            "success": True,
            "total_items": len(df),
            "successful_items": len(json_data.get("messages", [])),
            "output_file": output_filename,
            "report_file": report_filename
        }

    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated files"""
    file_path = os.path.join("outputs", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    else:
        return {"error": "File not found"}

def convert_to_amazon_format(df, feed_type):
    """Convert dataframe to Amazon SP-API format"""

    messages = []

    for _, row in df.iterrows():
        sku = str(row.get('sku', row.get('seller_sku', '')))
        if not sku:
            continue

        message = {
            "messageId": sku,
            "sku": sku,
            "operationType": "UPDATE",
            "productType": "GENERIC",
            "attributes": {}
        }

        if feed_type == "inventory":
            quantity = int(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
            message["attributes"]["fulfillment_availability"] = [{
                "fulfillment_channel_code": "DEFAULT",
                "quantity": quantity
            }]

        elif feed_type == "pricing":
            price = float(row.get('price', 0)) if pd.notna(row.get('price')) else 0
            message["attributes"]["purchasable_offer"] = [{
                "currency": "USD",
                "our_price": [{
                    "schedule": [{
                        "value_with_tax": price
                    }]
                }]
            }]

        elif feed_type == "listings":
            title = str(row.get('title', '')) if pd.notna(row.get('title')) else ''
            description = str(row.get('description', '')) if pd.notna(row.get('description')) else ''
            brand = str(row.get('brand', '')) if pd.notna(row.get('brand')) else ''

            if title:
                message["attributes"]["item_name"] = [{"value": title, "language_tag": "en_US"}]
            if description:
                message["attributes"]["description"] = [{"value": description, "language_tag": "en_US"}]
            if brand:
                message["attributes"]["brand"] = [{"value": brand}]

        elif feed_type == "images":
            main_image = str(row.get('main_image', '')) if pd.notna(row.get('main_image')) else ''
            if main_image:
                message["attributes"]["main_product_image_locator"] = [{"media_location": main_image}]

        messages.append(message)

    return {
        "header": {
            "sellerId": "YOUR_SELLER_ID",
            "version": "2021-06-30",
            "issueLocale": "en_US"
        },
        "messages": messages
    }

if __name__ == "__main__":
    print("🚀 Starting Amazon Feed Migration Tool...")
    print("📱 Web interface will open at: http://localhost:8000")
    print("⚠️  Keep this window open while using the tool")
    print()

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")