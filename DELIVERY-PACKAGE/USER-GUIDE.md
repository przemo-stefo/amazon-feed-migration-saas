# 📖 USER GUIDE - How to Use

## What This Tool Does (Simple Explanation)

**Before (Your Old Way):**
- You had XLSB files with product data
- You uploaded via SFTP to Amazon
- Amazon used old XML format

**After (New Way):**
- You upload same XLSB files to this tool
- Tool converts to new JSON format
- You send JSON to Amazon SP-API
- Amazon is happy, you're compliant!

## Step-by-Step Usage

### Step 1: Start the Tool
1. Double-click the startup file for your system
2. Browser opens showing the dashboard
3. You'll see: "Amazon Feed Migration Tool - Ready"

### Step 2: Add Your Amazon Credentials (One Time Setup)
1. Click "Settings" tab
2. Fill in your Amazon SP-API details:

**Where to find these:**
- Log into Amazon Seller Central
- Go to Apps & Services > Develop Apps
- Your details are listed there

**What to enter:**
```
Client ID: amzn1.application-oa2-client.xxxxxxxx
Client Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Refresh Token: Atzr|xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Seller ID: A3DEXAMPLE123456
Marketplace ID: ATVPDKIKX0DER (for US)
```

3. Click "Save Settings"
4. You'll see: "✅ Amazon connection verified"

### Step 3: Process Your First Feed

#### Upload File:
1. Click "Upload Feed" tab
2. Click "Choose File" and select your XLSB file
3. Choose feed type:
   - **Inventory** = stock quantities
   - **Pricing** = product prices
   - **Listings** = product information
   - **Images** = product photos

#### Process:
1. Click "Process Feed"
2. Wait 1-3 minutes (progress bar shows status)
3. You'll see results:
   ```
   ✅ Processing Complete!
   📊 1,247 products processed
   ✅ 1,201 successful
   ⚠️ 46 warnings (see details below)
   ```

#### Download Results:
1. Click "Download JSON" - this is your new feed file
2. Click "Download Report" - shows any errors/warnings

### Step 4: Send to Amazon
1. Log into Amazon Seller Central
2. Go to Inventory > Upload Products via File
3. Choose "JSON_LISTINGS_FEED"
4. Upload the JSON file you downloaded
5. Amazon processes it (usually 15-30 minutes)

## Different Feed Types Explained

### Inventory Feeds
**Purpose:** Update stock quantities
**Your XLSB columns needed:** SKU, Quantity
**Result:** Amazon knows how many you have in stock

### Pricing Feeds
**Purpose:** Update product prices
**Your XLSB columns needed:** SKU, Price, Currency
**Result:** Amazon shows new prices to customers

### Listings Feeds
**Purpose:** Create/update product information
**Your XLSB columns needed:** SKU, Title, Description, Brand, Category
**Result:** New products appear on Amazon or existing ones get updated

### Images Feeds
**Purpose:** Add/update product photos
**Your XLSB columns needed:** SKU, Main Image URL, Additional Images
**Result:** Product photos appear on Amazon listings

## Troubleshooting Common Issues

### "No SKU column found"
- Make sure your XLSB file has a column named "SKU" or "Seller SKU"
- Column names are case-sensitive

### "Amazon credentials invalid"
- Double-check your SP-API credentials in Settings
- Make sure you're using the right marketplace ID

### "Processing failed"
- Check the error report for specific issues
- Common fixes:
  - Remove special characters from SKUs
  - Fix price formatting (use numbers only)
  - Check image URLs are valid

### "Upload to Amazon failed"
- Use Amazon Seller Central instead
- The JSON file is correct, just upload it manually

## Tips for Success

### Before Processing:
- ✅ Clean your XLSB data (remove empty rows)
- ✅ Check SKUs are consistent
- ✅ Verify prices are numbers (not text)
- ✅ Test with small file first (10-20 products)

### After Processing:
- ✅ Always check the report for warnings
- ✅ Fix any issues and re-process if needed
- ✅ Keep backups of your original XLSB files

### Regular Use:
- ✅ Process feeds daily/weekly as needed
- ✅ Monitor Amazon's processing results
- ✅ Keep tool updated (I'll send updates)

## FAQ

**Q: How often should I run feeds?**
A: Depends on your business. Daily for active inventory, weekly for pricing updates.

**Q: Can I process multiple files at once?**
A: Yes, upload them one by one or merge them in Excel first.

**Q: What if Amazon rejects my feed?**
A: Check Amazon Seller Central for specific errors. Usually formatting issues.

**Q: Is my data safe?**
A: Yes, everything processes locally on your computer. Nothing is stored online.

**Q: Can multiple people use this?**
A: Yes, install on multiple computers or share the folder.

**Q: What about the September 2025 deadline?**
A: You're already compliant! This creates the new JSON format Amazon requires.

## Getting Help

**Email Support:** Include these details:
1. Screenshot of the error
2. Sample of your XLSB file (first 5 rows)
3. What you were trying to do
4. Your operating system

**Response Time:** Within 24 hours
**Support Period:** 30 days included

---

**🎉 Congratulations! You're now using modern Amazon feed technology ahead of the September 2025 deadline!**