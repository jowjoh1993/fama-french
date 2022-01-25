set PGBIN=C:\Program Files\pgAdmin 4\v5\runtime\
set PGHOST="localhost"
set PGUSER="postgres"
set PGPORT="5432"
set BACKUPDIR=C:\Users\saknox\OneDrive - SAS\Documents\fama\utility_scripts\
set PASSWRD="Sk138125!"

"%PGBIN%pg_dump.exe" -f "%BACKUPDIR%pg_dump.sql" --host %PGHOST% --port %PGPORT% --username %PGUSER% --no-password --verbose --format=c --blobs --encoding "UTF8" --schema "price_data" "postgres"
