#!/usr/bin/env python3
"""
FloodGuard AI — Setup Script
Generates demo data, trains ML model, and validates the installation.
Run this once before starting the application.
"""
import sys
import os

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from pathlib import Path


def main():
    print("=" * 60)
    print("  FloodGuard AI — Setup & Initialization")
    print("  Ahmedabad & Surat Urban Flood Management System")
    print("=" * 60)
    print()
    print("[NOTICE] All generated data is SYNTHETIC/DEMO data.")
    print("[NOTICE] It does not represent real government data.")
    print()

    # Step 1: Create required directories
    print("Step 1: Creating directories...")
    dirs = ["data", "ml/models", "logs"]
    for d in dirs:
        Path(project_root, d).mkdir(parents=True, exist_ok=True)
    print("  ✓ Directories created")

    # Step 2: Generate synthetic datasets
    print("\nStep 2: Generating synthetic demo datasets...")
    from data.seed_generator import write_seed_data
    write_seed_data(Path(project_root) / "data")

    # Step 3: Train ML model
    print("\nStep 3: Training flood risk ML model...")
    print("  (Using synthetic training data)")
    from ml.flood_risk_model import FloodRiskModel, _train_and_save
    model = FloodRiskModel()
    _train_and_save(model)
    print("  ✓ Model trained and saved")

    # Step 4: Test agent pipeline
    print("\nStep 4: Testing agent pipeline...")
    from agents.orchestrator import AgentOrchestrator
    orch = AgentOrchestrator()
    state = orch.run_pipeline("NORMAL", "All")

    predictions = state.get("risk_predictions", [])
    drains = state.get("drain_analysis", {}).get("scored_drains", [])
    reports = state.get("report_analysis", {}).get("total_reports", 0)

    print(f"  ✓ Risk predictions: {len(predictions)} areas")
    print(f"  ✓ Drain analysis: {len(drains)} drains scored")
    print(f"  ✓ Report analysis: {reports} reports processed")

    critical = sum(1 for p in predictions if p["risk_level"] == "CRITICAL")
    high = sum(1 for p in predictions if p["risk_level"] == "HIGH")
    print(f"  ✓ Risk distribution: {critical} CRITICAL, {high} HIGH")

    # Step 5: Test Granite service
    print("\nStep 5: Checking IBM Granite service...")
    from agents.granite_service import granite_status
    gst = granite_status()
    if gst["available"]:
        print("  ✓ IBM Granite: CONNECTED (live mode)")
    else:
        print("  ⚠ IBM Granite: Not configured (fallback mode)")
        print("    Set WATSONX_API_KEY in .env to enable live Granite")

    # Step 6: Create DB tables
    print("\nStep 6: Initializing database...")
    from backend.models.database import create_tables
    create_tables()
    print("  ✓ Database tables created (SQLite)")

    print()
    print("=" * 60)
    print("  ✅ Setup complete! FloodGuard AI is ready.")
    print()
    print("  To start the application:")
    print("  streamlit run app.py")
    print()
    print("  Demo credentials:")
    print("  Citizen:  citizen  / citizen123")
    print("  Operator: operator / operator123")
    print("  Admin:    admin    / admin123")
    print("=" * 60)


if __name__ == "__main__":
    main()
