from sqlalchemy import inspect
from shared.infrastructure.database.connection import DatabaseConnection

try:
    engine = DatabaseConnection.get_engine()
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    print('¿Existe NOTIFICACION?:', 'NOTIFICACION' in tablas)
    print('Tablas disponibles:', tablas)
except Exception as e:
    print('Error:', type(e).__name__, str(e))