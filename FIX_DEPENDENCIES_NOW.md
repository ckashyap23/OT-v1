# Fix: ModuleNotFoundError - flask_cors

## Quick Fix: Install Dependencies Manually

Since auto-build isn't working, install dependencies manually via Azure Console:

### Step 1: Access Azure Console

1. Go to your App Service in Azure Portal
2. Navigate to **Development Tools** → **Console** (or **SSH**)
3. You'll see a command prompt

### Step 2: Install Dependencies

Run these commands in the console:

```bash
cd /home/site/wwwroot
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python -c "import flask_cors; print('flask-cors installed successfully')"
```

### Step 4: Restart App Service

Go back to Azure Portal and click **Restart**

## Alternative: Use Azure CLI

If you have Azure CLI installed:

```powershell
# SSH into the container and install dependencies
az webapp ssh --name ot-v1-backend-a5dcdfh0duadgpce --resource-group <your-resource-group>

# Then run:
cd /home/site/wwwroot
pip install --upgrade pip
pip install -r requirements.txt
exit
```

## Permanent Fix: Enable Auto-Build

After manually installing, ensure auto-build is enabled:

1. Go to **Configuration** → **Application settings**
2. Verify these settings exist:
   - `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true`
   - `ENABLE_ORYX_BUILD` = `true`
3. If missing, add them and click **Save**
4. **Restart** the app

## Why This Happens

Azure App Service sometimes doesn't automatically detect and install Python dependencies from `requirements.txt` during ZIP deployment. The manual installation ensures all dependencies are available.

## After Fixing

Test your API:
```
https://ot-v1-backend-a5dcdfh0duadgpce.centralindia-01.azurewebsites.net/api/health
```

