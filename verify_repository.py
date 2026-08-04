import sys
sys.path.insert(0, 'new_back/src')
from modules.notificaciones.infrastructure.persistence.notificacion_repository import NotificacionRepositoryAdapter
NotificacionRepositoryAdapter()
print('OK')