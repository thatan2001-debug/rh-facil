"""
Rate limiting para el login de Gestor RH IA.

Protege contra ataques de fuerza bruta. Al detectar múltiples intentos
fallidos desde el mismo correo/IP, bloquea temporalmente.

Configuración (variables de entorno):
- LOGIN_MAX_INTENTOS      (default 5)
- LOGIN_VENTANA_MINUTOS   (default 15)
- LOGIN_BLOQUEO_MINUTOS   (default 15)

Almacenamiento:
- Si Supabase está configurado: tabla `intentos_login`
- Si no: en memoria (se pierde al reiniciar la app — no ideal pero
  suficiente para desarrollo)

Uso:
    from services.rate_limit_service import rate_limiter

    # Antes de verificar contraseña:
    bloqueado, tiempo_restante = rate_limiter.esta_bloqueado(email)
    if bloqueado:
        return False, f"Cuenta bloqueada temporalmente. Intenta en {tiempo_restante}"

    # Después de verificar (fallo o éxito):
    rate_limiter.registrar_intento(email, exitoso=ok)
"""

from datetime import datetime, timedelta
from typing import Tuple
from collections import defaultdict, deque
import threading

from config.settings import settings


class RateLimiter:
    """
    Rate limiter para login.

    Almacena intentos de login en memoria (por defecto) o en Supabase
    si está disponible.
    """

    def __init__(self):
        self._max_intentos = settings.login["max_intentos"]
        self._ventana = timedelta(minutes=settings.login["ventana_minutos"])
        self._bloqueo = timedelta(minutes=settings.login["bloqueo_minutos"])

        # Almacenamiento en memoria (fallback)
        self._intentos = defaultdict(lambda: deque(maxlen=100))
        self._lock = threading.Lock()

    def _usar_supabase(self) -> bool:
        """True si podemos usar Supabase para persistir intentos."""
        try:
            from utils.db import supabase_ok
            return supabase_ok()
        except Exception:
            return False

    def esta_bloqueado(self, email: str) -> Tuple[bool, str]:
        """
        Verifica si un email está temporalmente bloqueado.
        Retorna (bloqueado, mensaje_amigable_con_tiempo)
        """
        if not email:
            return False, ""

        email = email.strip().lower()
        ahora = datetime.now()
        cutoff = ahora - self._ventana

        intentos = self._obtener_intentos_recientes(email, cutoff)

        # Contar solo intentos fallidos
        fallidos = [i for i in intentos if not i["exitoso"]]

        if len(fallidos) >= self._max_intentos:
            # Bloqueo activo
            ultimo_fallido = max(fallidos, key=lambda x: x["ts"])
            fin_bloqueo = ultimo_fallido["ts"] + self._bloqueo
            if ahora < fin_bloqueo:
                restante = fin_bloqueo - ahora
                minutos = int(restante.total_seconds() / 60) + 1
                return True, f"{minutos} minuto(s)"

        return False, ""

    def registrar_intento(self, email: str, exitoso: bool, ip: str = ""):
        """Registra un intento de login (exitoso o fallido)."""
        if not email:
            return

        email = email.strip().lower()
        ahora = datetime.now()

        if self._usar_supabase():
            try:
                from utils.db import _db
                _db().table("intentos_login").insert({
                    "email": email,
                    "ip": ip or "unknown",
                    "exitoso": exitoso,
                    "ts": ahora.isoformat(),
                }).execute()
            except Exception:
                # Si falla Supabase, caemos a memoria
                self._registrar_en_memoria(email, exitoso, ahora)
        else:
            self._registrar_en_memoria(email, exitoso, ahora)

    def _registrar_en_memoria(self, email: str, exitoso: bool, ts: datetime):
        with self._lock:
            self._intentos[email].append({"exitoso": exitoso, "ts": ts})

    def _obtener_intentos_recientes(self, email: str,
                                     cutoff: datetime) -> list:
        """Obtiene intentos posteriores a cutoff."""
        if self._usar_supabase():
            try:
                from utils.db import _db
                r = _db().table("intentos_login").select("*") \
                    .eq("email", email) \
                    .gte("ts", cutoff.isoformat()) \
                    .execute()
                # Normalizar los timestamps a datetime
                intentos = []
                for row in (r.data or []):
                    ts_str = row.get("ts", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        # Quitar timezone info para comparar con datetime.now()
                        if ts.tzinfo:
                            ts = ts.replace(tzinfo=None)
                    except Exception:
                        continue
                    intentos.append({"exitoso": row.get("exitoso", False), "ts": ts})
                return intentos
            except Exception:
                pass  # Cae a memoria

        with self._lock:
            return [i for i in self._intentos[email] if i["ts"] >= cutoff]

    def limpiar_intentos(self, email: str):
        """Limpia todos los intentos de un email (útil después de un login exitoso)."""
        email = email.strip().lower()
        with self._lock:
            if email in self._intentos:
                self._intentos[email].clear()


# Instancia global
rate_limiter = RateLimiter()
