"""
Script de migración de datos: sistema legacy → nuevo modelo multiempresa.

Ejecutar UNA VEZ después de aplicar migrations/004_multiempresa.sql en Supabase.

Qué hace:
1. Lee todos los usuarios de la tabla legacy 'usuarios'
2. Para cada usuario:
   a. Crea o encuentra su perfil en 'perfiles' (con password_hash)
   b. Si tiene empresa_config, crea la empresa en 'empresas'
   c. Crea el vínculo en 'empresa_usuarios' con rol 'admin_empresa'
3. Si el usuario tenía es_admin=true, marca su perfil como es_superadmin=true

Uso:
    # Antes de correr, asegúrate de tener backup de tu Supabase
    python scripts/migrar_a_multiempresa.py

    # Para simular sin escribir cambios:
    python scripts/migrar_a_multiempresa.py --dry-run

Precondiciones:
- Migración 004_multiempresa.sql ya aplicada
- Variables SUPABASE_URL y SUPABASE_KEY configuradas
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Migración a modelo multiempresa")
    parser.add_argument("--dry-run", action="store_true",
                         help="Simular sin escribir cambios")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Gestor RH IA — Migración a modelo multiempresa              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    if args.dry_run:
        print("🔍 MODO DRY-RUN — no se escribirán cambios")
        print()

    # ── Verificar configuración ─────────────────────────────────────────
    try:
        from config.settings import settings
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        sys.exit(1)

    if not settings.supabase_configurado:
        print("❌ Esta migración requiere Supabase configurado.")
        print("   Verifica SUPABASE_URL y SUPABASE_KEY en .env")
        sys.exit(1)

    from utils.db import _db

    # ── Verificar que las tablas nuevas existen ─────────────────────────
    print("1️⃣  Verificando que las tablas nuevas existen...")
    try:
        _db().table("perfiles").select("id").limit(1).execute()
        _db().table("empresas").select("id").limit(1).execute()
        _db().table("empresa_usuarios").select("id").limit(1).execute()
        _db().table("roles").select("id").limit(1).execute()
        print("   ✅ Tablas nuevas OK")
    except Exception as e:
        print(f"   ❌ Falta migración SQL: {e}")
        print("   Ejecuta primero: migrations/004_multiempresa.sql")
        sys.exit(1)

    # ── Obtener roles ────────────────────────────────────────────────────
    print()
    print("2️⃣  Obteniendo roles del sistema...")
    r = _db().table("roles").select("*").execute()
    roles = {row["codigo"]: row["id"] for row in (r.data or [])}
    if "admin_empresa" not in roles:
        print("   ❌ Falta rol 'admin_empresa'. Ejecuta migrations/004_multiempresa.sql")
        sys.exit(1)
    print(f"   ✅ Roles encontrados: {list(roles.keys())}")

    # ── Leer usuarios legacy ─────────────────────────────────────────────
    print()
    print("3️⃣  Leyendo usuarios existentes (tabla 'usuarios')...")
    try:
        r = _db().table("usuarios").select("*").execute()
        usuarios_legacy = r.data or []
    except Exception as e:
        print(f"   ⚠️  No existe tabla 'usuarios' legacy: {e}")
        print("   No hay datos que migrar. Terminando.")
        return

    if not usuarios_legacy:
        print("   ℹ️  No hay usuarios en la tabla legacy.")
        return

    print(f"   📊 Encontrados {len(usuarios_legacy)} usuario(s) para migrar")

    # ── Migrar cada usuario ──────────────────────────────────────────────
    print()
    print("4️⃣  Migrando usuarios y empresas...")
    print()

    migrados_ok = 0
    ya_existian = 0
    errores = []

    for u in usuarios_legacy:
        email = (u.get("email") or "").strip().lower()
        if not email:
            errores.append(("(sin email)", "Email vacío"))
            continue

        print(f"   👤 {email}")

        # ── Verificar si el perfil ya existe ─────────────────────────
        try:
            r_perfil = _db().table("perfiles").select("*").eq("email", email).execute()
            if r_perfil.data:
                print(f"      ⏭️  Perfil ya existe, saltando")
                ya_existian += 1
                continue
        except Exception as e:
            errores.append((email, f"Error consultando perfil: {e}"))
            continue

        # ── Crear perfil ─────────────────────────────────────────────
        perfil_payload = {
            "email":         email,
            "nombre":        u.get("nombre", "") or email.split("@")[0],
            "password_hash": u.get("password_hash", ""),
            "activo":        u.get("activo", False),
            "es_superadmin": u.get("es_admin", False),
        }

        if args.dry_run:
            print(f"      🔍 [DRY-RUN] Crearía perfil: {perfil_payload['nombre']}")
            perfil_id = "dry-run-id"
        else:
            try:
                r_new = _db().table("perfiles").insert(perfil_payload).execute()
                perfil_id = r_new.data[0]["id"] if r_new.data else None
                if not perfil_id:
                    errores.append((email, "No se pudo crear perfil"))
                    continue
                print(f"      ✅ Perfil creado")
            except Exception as e:
                errores.append((email, f"Error creando perfil: {e}"))
                continue

        # ── Crear empresa (si el usuario tiene datos de empresa) ────
        empresa_cfg = u.get("empresa_config") or {}
        if isinstance(empresa_cfg, str):
            try:
                import json
                empresa_cfg = json.loads(empresa_cfg)
            except Exception:
                empresa_cfg = {}

        # Preparar datos de la empresa
        razon_social = (
            empresa_cfg.get("nombre") or
            empresa_cfg.get("razon_social") or
            f"Empresa de {u.get('nombre','')}" or
            "Empresa sin nombre"
        )

        empresa_payload = {
            "razon_social":        razon_social,
            "nit":                 empresa_cfg.get("nit", ""),
            "direccion":           empresa_cfg.get("direccion", ""),
            "ciudad":              empresa_cfg.get("ciudad", ""),
            "telefono":            empresa_cfg.get("telefono_empresa", ""),
            "correo":              empresa_cfg.get("correo_empresa", ""),
            "representante_legal": empresa_cfg.get("representante", ""),
            "logo_url":            empresa_cfg.get("logo_path", ""),
            "membrete_url":        empresa_cfg.get("membrete_path", ""),
            "plan":                u.get("plan", "gratuito"),
            "estado":              "activa",
            "metadata":            {"origen": "migracion_legacy",
                                     "usuario_original": email},
        }

        if args.dry_run:
            print(f"      🔍 [DRY-RUN] Crearía empresa: {razon_social}")
            empresa_id = "dry-run-id"
        else:
            try:
                r_emp = _db().table("empresas").insert(empresa_payload).execute()
                empresa_id = r_emp.data[0]["id"] if r_emp.data else None
                if not empresa_id:
                    errores.append((email, "No se pudo crear empresa"))
                    continue
                print(f"      ✅ Empresa creada: {razon_social}")
            except Exception as e:
                errores.append((email, f"Error creando empresa: {e}"))
                continue

        # ── Crear vínculo empresa_usuarios ───────────────────────────
        vinculo_payload = {
            "empresa_id": empresa_id,
            "perfil_id":  perfil_id,
            "rol_id":     roles["admin_empresa"],
            "estado":     "activo",
        }

        if args.dry_run:
            print(f"      🔍 [DRY-RUN] Vincularía con rol admin_empresa")
        else:
            try:
                _db().table("empresa_usuarios").insert(vinculo_payload).execute()
                print(f"      ✅ Vinculado como admin_empresa")
            except Exception as e:
                errores.append((email, f"Error creando vínculo: {e}"))
                continue

        migrados_ok += 1
        print()

    # ── Resumen ──────────────────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Resumen de migración                                        ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Usuarios encontrados:    {len(usuarios_legacy):<35}║")
    print(f"║  Migrados exitosamente:   {migrados_ok:<35}║")
    print(f"║  Ya existían (saltados):  {ya_existian:<35}║")
    print(f"║  Errores:                 {len(errores):<35}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    if errores:
        print()
        print("❌ Errores encontrados:")
        for email, err in errores:
            print(f"   • {email}: {err}")

    if args.dry_run:
        print()
        print("🔍 DRY-RUN completado. Ejecuta sin --dry-run para aplicar cambios.")


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
