import sys
import webbrowser
from pathlib import Path

import uvicorn

# Ensure the root directory is on Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, init_db
from app.services import KnowledgeRepository, seed_initial_clinical_data


def main():
    print("=" * 65)
    print("      CLINICAL DECISION SUPPORT SYSTEM (CDSS) LOCAL LAUNCHER")
    print("=" * 65)

    print("\n[1/3] Initializing local database schema...")
    init_db()

    print("[2/3] Checking knowledge base records...")
    with SessionLocal() as session:
        repo = KnowledgeRepository(session)
        stats = repo.stats()
        if stats["conditions"] == 0:
            print("      Database is empty. Seeding standard clinical knowledge...")
            seeded = seed_initial_clinical_data(session)
            print(f"      Seeded {seeded} core conditions with symptoms, tests, and treatments.")
        else:
            print(
                f"      Database ready: {stats['conditions']} conditions, "
                f"{stats['symptoms']} symptoms, {stats['risk_factors']} risk factors, "
                f"{stats['tests']} tests, {stats['treatments']} treatments, "
                f"{stats['evaluations']} saved evaluations."
            )

    print("\n[3/3] Starting unified backend & frontend server...")
    print("      -> Web Application : http://127.0.0.1:8000")
    print("      -> API Docs (Swagger): http://127.0.0.1:8000/docs")
    print("=" * 65)
    print("Press Ctrl+C in this terminal to stop the server.\n")

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
