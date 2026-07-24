"""
Script para crear el primer administrador de Gestor RH IA.

Uso:
    python scripts/crear_primer_admin.py

El script te pedirá:
- Correo del administrador
- Nombre completo
- Contraseña (por prompt, no visible en pantalla)
- Confirmación de contraseña

La contraseña se hashea con Argon2 antes de insertarse en la BD.
Nunca se guarda en texto claro ni en variables de entorno.

Precondiciones:
- Variables SUPABASE_URL y SUPABASE_KEY configuradas (o usar JSON local)
- Ejecutar desde el directorio raíz del proyecto
"""

import sys
import os
import getpass
from pathlib import Path

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Gestor RH IA — Crear primer administrador                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # ── Cargar configuración ─────────────────────────────────────────────
    try:
        from config.settings import settings
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        print("   Verifica que .env esté configurado.")
        sys.exit(1)

    print(f"Entorno detectado: {settings.environment}")
    if settings.supabase_configurado:
        print(f"Base de datos:    Supabase ({settings.supabase_url[:40]}...)")
    else:
        print(f"Base de datos:    JSON local (salidas/.usuarios.json)")
        if settings.is_production:
            print()
            print("❌ ERROR: En producción no se permite crear admins sin Supabase.")
            print("   Configura SUPABASE_URL y SUPABASE_KEY primero.")
            sys.exit(1)

    print()

    # ── Solicitar datos ──────────────────────────────────────────────────
    email = input("Correo del administrador: ").strip().lower()
    if not email or "@" not in email:
        print("❌ Correo inválido")
        sys.exit(1)

    # Verificar si ya existe
    from utils.db import usuario_obtener
    if usuario_obtener(email):
        print(f"❌ Ya existe un usuario con el correo {email}")
        respuesta = input("¿Quieres RESETEAR su contraseña? (escribe 'SI' para confirmar): ")
        if respuesta.strip() != "SI":
            print("Cancelado")
            sys.exit(0)
        reset_mode = True
    else:
        reset_mode = False

    nombre = ""
    if not reset_mode:
        nombre = input("Nombre completo: ").strip()
        if not nombre:
            print("❌ Nombre requerido")
            sys.exit(1)

    # ── Solicitar contraseña por prompt (no visible) ─────────────────────
    while True:
        password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
        password_confirm = getpass.getpass("Confirmar contraseña:              ")

        if password != password_confirm:
            print("❌ Las contraseñas no coinciden. Inténtalo de nuevo.\n")
            continue

        # Validar fortaleza
        from services.auth_service import evaluar_fortaleza_password
        cumple, problemas = evaluar_fortaleza_password(password)
        if not cumple:
            print("❌ Contraseña insegura:")
            for p in problemas:
                print(f"   • {p}")
            print("Inténtalo de nuevo.\n")
            continue

        break

    # ── Hashear y guardar ────────────────────────────────────────────────
    from services.auth_service import auth_service
    hash_seguro = auth_service.hash_password(password)

    if reset_mode:
        # Solo actualizar contraseña
        from utils.auth import _actualizar_hash_usuario
        if _actualizar_hash_usuario(email, hash_seguro):
            print()
            print(f"✅ Contraseña actualizada para {email}")
            print()
            sys.exit(0)
        else:
            print("❌ Error actualizando contraseña")
            sys.exit(1)

    # Crear usuario nuevo con permisos de admin
    from utils.db import usuario_crear, usuario_activar, supabase_ok

    ok = usuario_crear(email, nombre, hash_seguro, plan="empresarial")
    if not ok:
        print("❌ Error creando el usuario")
        sys.exit(1)

    # Activarlo y marcarlo como admin
    usuario_activar(email)

    # Marcar como admin (esto varía según el backend)
    try:
        if supabase_ok():
            from utils.db import _db
            _db().table("usuarios").update(
                {"es_admin": True}
            ).eq("email", email).execute()
        else:
            from utils.db import _jl, _js
            d = _jl()
            if email in d:
                d[email]["es_admin"] = True
                d[email]["activo"] = True
                d[email]["activado_admin"] = True
                _js(d)
    except Exception as e:
        print(f"⚠️  Usuario creado pero no se pudo marcar como admin: {e}")
        print("   Márcalo manualmente en la BD.")
        sys.exit(1)

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  ✅ Administrador creado exitosamente                        ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Correo:  {email:<50}║")
    print(f"║  Nombre:  {nombre[:50]:<50}║")
    print("║  Plan:    empresarial                                        ║")
    print("║  Rol:     Administrador                                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Ya puedes iniciar sesión en la aplicación.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
