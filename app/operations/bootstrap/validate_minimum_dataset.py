import sys
from datetime import date
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from app.modules.catalog.infrastructure.models import Material, Presentacion
from app.modules.pricing.infrastructure.models import PrecioHistorico, ExternalIndexValue
from app.shared.database.session import SessionLocal

EXPECTED_MATERIALS = ["Cemento Portland", "Pastina", "Membrana Megaflex"]
REQUIRED_REGRESSORS = [
    "448.1_NIVEL_GENERAL_0_0_13_46",  # IPIM
]

def check_materials(db: Session) -> bool:
    print("Checking materials...")
    success = True
    for name in EXPECTED_MATERIALS:
        material = db.scalar(select(Material).where(Material.nombre == name))
        if not material:
            print(f"  [FAIL] Material '{name}' not found.")
            success = False
        else:
            print(f"  [OK] Material '{name}' found.")
    return success

def check_presentations(db: Session) -> bool:
    print("Checking presentations...")
    expected = {
        "Cemento Portland": ["Bolsa 25 kg", "Bolsa 50 kg"],
        "Pastina": ["Unidad 1 kg"],
        "Membrana Megaflex": ["Balde 20 kg"],
    }
    success = True
    for mat_name, pres_names in expected.items():
        material = db.scalar(select(Material).where(Material.nombre == mat_name))
        if not material:
            continue
        for pres_name in pres_names:
            pres = db.scalar(
                select(Presentacion).where(
                    Presentacion.material_id == material.id,
                    Presentacion.nombre_presentacion == pres_name
                )
            )
            if not pres:
                print(f"  [FAIL] Presentation '{pres_name}' for '{mat_name}' not found.")
                success = False
            else:
                print(f"  [OK] Presentation '{pres_name}' for '{mat_name}' found.")
    return success

def check_series_continuity(db: Session) -> bool:
    print("Checking series continuity and imputation metadata...")
    success = True
    for name in EXPECTED_MATERIALS:
        material = db.scalar(select(Material).where(Material.nombre == name))
        if not material:
            continue
        
        # Get all months with data
        stmt = (
            select(
                func.date_trunc('month', PrecioHistorico.fecha).label('month'),
                func.count(PrecioHistorico.id).label('count'),
                func.sum(case((PrecioHistorico.origen_dato == 'REAL', 1), else_=0)).label('real_count'),
                func.sum(case((PrecioHistorico.origen_dato == 'ESTIMADO', 1), else_=0)).label('estimado_count')
            )
            .where(PrecioHistorico.material_id == material.id)
            .group_by('month')
            .order_by('month')
        )
        
        rows = db.execute(stmt).all()
        if not rows:
            print(f"  [FAIL] No data for '{name}'.")
            success = False
            continue

        months = [r.month.date() for r in rows]
        first, last = months[0], months[-1]
        
        # Check gaps
        has_gaps = False
        curr = first
        while curr <= last:
            if curr not in months:
                print(f"  [FAIL] Gap detected in '{name}' for month {curr}")
                has_gaps = True
                success = False
            curr = date(curr.year + (1 if curr.month == 12 else 0), 1 if curr.month == 12 else curr.month + 1, 1)
        
        if not has_gaps:
            print(f"  [OK] No gaps in '{name}' from {first} to {last} ({len(months)} months).")

        # Check imputation metadata
        real_total = sum(r.real_count or 0 for r in rows)
        estimado_total = sum(r.estimado_count or 0 for r in rows)
        print(f"    Metadata: {real_total} REAL, {estimado_total} ESTIMADO")
        
        if name == "Cemento Portland" and estimado_total > 0:
            print(f"  [FAIL] Cemento Portland should only have REAL data in canonical bootstrap.")
            success = False
        
        if name in ["Pastina", "Membrana Megaflex"]:
            if real_total == 0 or estimado_total == 0:
                print(f"  [FAIL] {name} should be a hybrid series (REAL + ESTIMADO).")
                success = False
    return success

def check_regressors(db: Session) -> bool:
    print("Checking external indices (regressors)...")
    success = True
    for series_id in REQUIRED_REGRESSORS:
        count = db.scalar(
            select(func.count(ExternalIndexValue.id)).where(ExternalIndexValue.series_id == series_id)
        )
        if not count or count == 0:
            print(f"  [FAIL] Regressor '{series_id}' not found or empty.")
            success = False
        else:
            print(f"  [OK] Regressor '{series_id}' has {count} points.")
    return success

def main():
    print("=== BuildWise Minimum Dataset Validation ===\n")
    with SessionLocal() as db:
        s1 = check_materials(db)
        s2 = check_presentations(db)
        s3 = check_series_continuity(db)
        s4 = check_regressors(db)
    
    print("\n" + "="*44)
    if all([s1, s2, s3, s4]):
        print("  VALIDATION SUCCESSFUL: Dataset ready for Thesis.")
        sys.exit(0)
    else:
        print("  VALIDATION FAILED: Check logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
