#!/usr/bin/env python3
"""
Wrapper CLI: elimina duplicados en alertas_medios vía supabase_limpiar_duplicados.

Uso:
  python eliminar_duplicados.py
  python eliminar_duplicados.py --dry-run
"""
from supabase_limpiar_duplicados import crear_cliente_desde_env, limpiar_duplicados_alertas_medios

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Elimina registros duplicados en alertas_medios (conserva el más reciente)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo reporta qué se borraría, sin eliminar.",
    )
    parser.add_argument(
        "--tabla",
        default="alertas_medios",
        help="Tabla Supabase (default: alertas_medios).",
    )
    args = parser.parse_args()

    print("Verificando y eliminando registros duplicados en Supabase...")
    print("=" * 80)

    sb = crear_cliente_desde_env()
    res = limpiar_duplicados_alertas_medios(
        sb, tabla=args.tabla, dry_run=args.dry_run
    )

    modo = "DRY-RUN" if args.dry_run else "EJECUCIÓN"
    print(f"\n[{modo}] Tabla: {args.tabla}")
    print(f"  Registros leídos: {res['total_registros']}")
    print(f"  Grupos duplicados: {res['grupos']}")
    print(f"  {'A eliminar' if args.dry_run else 'Eliminados'}: {res['eliminados']}")
    if res.get("ids_eliminados"):
        for rid in res["ids_eliminados"][:30]:
            print(f"    - ID {rid}")
        if len(res["ids_eliminados"]) > 30:
            print(f"    ... y {len(res['ids_eliminados']) - 30} más")
    print(f"  Duración: {res['duracion_s']}s")
    print("\n" + "=" * 80)
    print("Proceso completado.")
