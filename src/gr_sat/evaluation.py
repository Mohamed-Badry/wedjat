import pandas as pd
import numpy as np
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.table import Table

from sklearn.metrics import roc_auc_score, roc_curve

import torch
from gr_sat.model_artifacts import load_model_artifacts, split_chronological
from gr_sat.models import compute_anomaly_scores
from gr_sat.processing import annotate_pass_and_cadence_metadata
from gr_sat.satellite_profiles import (
    build_baseline_mask,
    feature_completeness_mask,
    get_satellite_profile,
)

def inject_faults(
    df_test: pd.DataFrame,
    profile,
    n_per_fault: int = 100,
    rng_seed: int = 42,
):
    rng = np.random.RandomState(rng_seed)
    df_faulted = df_test.copy()
    labels = np.zeros(len(df_test), dtype=int)
    fault_types = np.array(["normal"] * len(df_test), dtype=object)

    # 1. Panel Failure (Short Circuit in Sunlight)
    sunlight_mask = df_faulted["temp_panel_z"] > 15
    sun_idx = np.where(sunlight_mask & (labels == 0))[0]
    if len(sun_idx) > 0:
        panel_fail_idx = rng.choice(
            sun_idx, size=min(n_per_fault, len(sun_idx)), replace=False
        )
        # A subtle drop in current during sunlight, undetectable by basic thresholding
        df_faulted.iloc[
            panel_fail_idx, df_faulted.columns.get_loc("batt_current")
        ] = -0.2
        labels[panel_fail_idx] = 1
        fault_types[panel_fail_idx] = "panel_failure"

    # 2. Thermal Runaway (Massive Spike Above Orbit Baselines)
    normal_idx = np.where(labels == 0)[0]
    if len(normal_idx) > 0:
        thermal_idx = rng.choice(
            normal_idx, size=min(n_per_fault, len(normal_idx)), replace=False
        )
        # A relatively small thermal jump within natural variance, but breaking correlation
        df_faulted.iloc[thermal_idx, df_faulted.columns.get_loc("temp_batt_a")] += 7.0
        df_faulted.iloc[thermal_idx, df_faulted.columns.get_loc("temp_batt_b")] += 7.0
        labels[thermal_idx] = 1
        fault_types[thermal_idx] = "thermal_runaway"

    return (
        annotate_pass_and_cadence_metadata(
            df_faulted,
            pass_gap_seconds=profile.pass_gap_seconds,
            cadence_tolerance_ratio=profile.cadence_tolerance_ratio,
            cadence_min_tolerance_seconds=profile.cadence_min_tolerance_seconds,
            rolling_window=profile.rolling_window,
        ),
        labels,
        fault_types,
    )


def calculate_diagnosis_accuracy(recon_errors, flagged_idx, fault_types, feature_names):
    fault_categories = ["panel_failure", "thermal_runaway"]
    accuracy = {ft: {"correct": 0, "flagged": 0} for ft in fault_categories}

    for idx in flagged_idx:
        errors = recon_errors[idx]
        top_feature = feature_names[np.argmax(errors)]
        actual_fault = fault_types[idx]

        if actual_fault != "normal":
            accuracy[actual_fault]["flagged"] += 1

            is_correct = False
            if actual_fault == "panel_failure" and top_feature == "batt_current":
                is_correct = True
            elif actual_fault == "thermal_runaway" and top_feature in [
                "temp_batt_a",
                "temp_batt_b",
            ]:
                is_correct = True

            if is_correct:
                accuracy[actual_fault]["correct"] += 1

    return accuracy


def evaluate(norad_id: str, models_dir: str = "models", processed_dir: str = "data/processed", docs_dir: str = "docs"):
    models_path = Path(models_dir)
    processed_path = Path(processed_dir)
    docs_path = Path(docs_dir)
    
    logger.info(f"Evaluating Unified VAE System for NORAD {norad_id}...")
    profile = get_satellite_profile(norad_id)

    try:
        scaler, vae, metadata = load_model_artifacts(norad_id, models_path)
    except FileNotFoundError:
        logger.error(f"Models not found in {models_path}. Run training first.")
        return

    data_path = processed_path / f"{norad_id}.csv"
    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    extreme_mask = build_baseline_mask(df, profile)
    df_clean = df[~extreme_mask].copy()
    complete_mask = feature_completeness_mask(df_clean, metadata.feature_names)
    df_ready = df_clean[complete_mask].copy()

    split = split_chronological(df_ready)
    df_test = split.test.copy()

    df_faulted, y_true, fault_types = inject_faults(df_test, profile, n_per_fault=150)
    X_faulted_scaled = scaler.transform(df_faulted[metadata.feature_names].values)

    # VAE Inference
    # Use the persisted training feature order from the artifact metadata.
    X_tensor = torch.FloatTensor(X_faulted_scaled)
    diagnosis_mask = [
        metadata.feature_names.index(f)
        for f in metadata.diagnosis_feature_names
    ]
    with torch.no_grad():
        X_recon_vae, mu, logvar = vae(X_tensor)
        anomaly_scores = compute_anomaly_scores(
            X_recon_vae,
            X_tensor,
            mu,
            logvar,
            kld_weight=metadata.kld_weight,
            diagnosis_mask=diagnosis_mask,
        ).numpy()

    # ------------------
    # Stage 1: Detector (MAX Loss Score)
    # ------------------
    logger.info("Executing Stage 1: Detection via VAE MSE + KLD Score...")
    operating_threshold = metadata.threshold

    # Trigger Anomaly IF VAE score > threshold
    predicted_anomalies = anomaly_scores > operating_threshold
    flagged_idx = np.where(predicted_anomalies)[0]

    auroc = roc_auc_score(y_true, anomaly_scores)
    fpr_curve, tpr_curve, thresholds = roc_curve(y_true, anomaly_scores)
    recall_at_5 = np.interp(0.05, fpr_curve, tpr_curve)

    # ------------------
    # Stage 2: Diagnoser (Node MSE Isolation)
    # ------------------
    logger.info("Executing Stage 2: Feature Diagnosis via VAE node-MSE...")
    recon_errors_vae = np.abs(X_faulted_scaled - X_recon_vae.numpy())
    
    # We only care about diagnosis features for accuracy evaluation
    masked_recon_errors = np.zeros_like(recon_errors_vae)
    masked_recon_errors[:, diagnosis_mask] = recon_errors_vae[:, diagnosis_mask]
    
    acc_vae = calculate_diagnosis_accuracy(
        masked_recon_errors,
        flagged_idx,
        fault_types,
        feature_names=metadata.feature_names,
    )

    console = Console()
    console.print(
        f"\n[bold green]Unified VAE Benchmark Report — NORAD {norad_id}[/bold green]"
    )
    console.print(
        f"Total Test Frames: {len(X_faulted_scaled)} (Injected Faults: {y_true.sum()})\n"
    )

    table = Table(title="Stage 1: Detection (VAE Max Error)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("AUROC", f"{auroc:.4f}")
    table.add_row("Recall @ 5% FPR", f"{recall_at_5 * 100:.1f}%")
    table.add_row("Operating Threshold", f"{operating_threshold:.6f}")
    console.print(table)

    diag_table = Table(title="Stage 2: Diagnosis (VAE Feature Isolation)")
    diag_table.add_column("Fault Type", style="cyan")
    diag_table.add_column("PyTorch VAE Accuracy", justify="right")

    fault_categories = ["panel_failure", "thermal_runaway"]
    for ft in fault_categories:
        v_flagged = acc_vae[ft]["flagged"]
        v_corr = acc_vae[ft]["correct"]
        v_str = f"{v_corr}/{v_flagged} ({(v_corr / v_flagged * 100) if v_flagged > 0 else 0:.1f}%)"
        diag_table.add_row(ft.replace("_", " ").title(), v_str)

    console.print(diag_table)

    with open(docs_path / f"benchmark_{norad_id}.md", "w") as f:
        f.write(f"# Edge Benchmark for NORAD {norad_id}\n\n")
        f.write(
            "This report is an offline synthetic-fault benchmark using the persisted "
            "training artifact threshold. It should be read as comparative evaluation, "
            "not as proof of a complete live runtime.\n\n"
        )
        f.write("**Unified Architecture:** PyTorch Variational Autoencoder\n\n")
        f.write("## Metrics\n")
        f.write(f"- **AUROC:** {auroc:.4f}\n")
        f.write(f"- **Recall @ 5% FPR:** {recall_at_5 * 100:.1f}%\n\n")
        f.write(f"- **Operating Threshold:** {operating_threshold:.6f}\n\n")

        f.write("## Fault Isolation Performance\n")
        f.write("| Fault Type | Detected by Stage 1 | Isolated by VAE |\n")
        f.write("|------------|---------------------|-----------------|\n")
        for ft in fault_categories:
            total_injected = (fault_types == ft).sum()
            flagged = acc_vae[ft]["flagged"]
            correct = acc_vae[ft]["correct"]
            det_rate = (flagged / total_injected * 100) if total_injected > 0 else 0
            diag_acc = (correct / flagged * 100) if flagged > 0 else 0
            f.write(f"| {ft} | {det_rate:.1f}% | {diag_acc:.1f}% |\n")

    logger.success(f"Saved benchmark report to {docs_path}/benchmark_{norad_id}.md")
