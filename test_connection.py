import sys
import os

# Disable dotenv loading
os.environ['DOTENV'] = 'false'

# Mock load_dotenv to do nothing
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: None

from sqlalchemy import create_engine, inspect

# Test direct connection with hardcoded URL
database_url = "postgresql://user:password@localhost:5432/comunicados_db"
print(f"Probando conexión con: {database_url}")

try:
    engine = create_engine(database_url)
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    print('¿Existe NOTIFICACION?:', 'NOTIFICACION' in tablas)
    print('Tablas disponibles:', tablas)
except Exception as e:
    print('Error:', type(e).__name__, str(e))
    import traceback
    traceback.print_exc()