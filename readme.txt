main.py -- production entry point
Launch with:
python main.py
First launch: SQL Server setup dialog (server, database, username, password)
Test Connection validates before save
Hub GUI with two centered module cards:
OMR Sheets → opens OMR_Sheets.py
Attendance Sheets → opens AttendanceSheets.py
Database Settings to update connection details later
Responsive layout scales fonts, spacing, and card size from screen and window size
Main window hides while a module is open; returns when you close the module
db_credentials.py — secure credential storage
Credentials are stored at: %APPDATA%\KPSC_OMR\db_config.kpsc

Security:

Windows DPAPI encryption (user-scoped, not plain text)
SHA-256 integrity hash in the file to detect tampering
If the file is missing or invalid, setup is requested again
Updated modules
OMR_Sheets.py and AttendanceSheets.py now use the shared connection from db_credentials instead of hardcoded RAO-PC / kpsc / qwer.

Production deployment
Install dependencies:
pip install -r requirements.txt
Run the suite:
python main.py
Complete database setup on first run.
For a standalone .exe, build from main.py:
pyinstaller --noconfirm --windowed --name "KPSC_OMR_Suite" main.py
Note: Use main.py as the entry point in production. Running OMR_Sheets.py or AttendanceSheets.py directly still works, but they require credentials to be configured via main.py first.

If you want, I can add a PyInstaller .spec with bundled assets (ONNX model, icons) for a full installer build.