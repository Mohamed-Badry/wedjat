import pandas as pd
from pathlib import Path
import joblib
import numpy as np

from loguru import logger
from sklearn.preprocessing import StandardScaler

import torch
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from gr_sat.ml_config import (
    DEFAULT_INFERENCE_MODE,
    DEFAULT_KLD_WEIGHT,
    HIDDEN_DIM,
    LATENT_DIM,
    THRESHOLD_PERCENTILE,
)
from gr_sat.model_artifacts import (
    ModelArtifactMetadata,
    model_artifact_paths,
    save_model_metadata,
    split_chronological,
    threshold_from_scores,
)
from gr_sat.models import TelemetryVAE, compute_anomaly_scores, vae_loss
from gr_sat.satellite_profiles import (
    build_baseline_mask,
    feature_completeness_mask,
    get_satellite_profile,
)


def score_scaled_frames(
    vae: TelemetryVAE, X_scaled, diagnosis_mask=None, kld_weight=DEFAULT_KLD_WEIGHT
) -> np.ndarray:
    X_tensor = torch.FloatTensor(X_scaled)
    vae.eval()
    with torch.no_grad():
        recon_x, mu, logvar = vae(X_tensor)
        scores = compute_anomaly_scores(
            recon_x,
            X_tensor,
            mu,
            logvar,
            kld_weight=kld_weight,
            diagnosis_mask=diagnosis_mask
        )
    return scores.numpy()


def train_vae(X_train_scaled, feature_names: list[str], diagnosis_mask=None, epochs: int = 100):
    logger.info("Training PyTorch Variational Autoencoder (VAE)...")

    # 1. Prepare PyTorch Dataset
    X_tensor = torch.FloatTensor(X_train_scaled)
    dataset = TensorDataset(X_tensor)
    dataloader = DataLoader(dataset, batch_size=64, shuffle=True)

    # 2. Init Model
    vae = TelemetryVAE(
        input_dim=len(feature_names),
        hidden_dim=HIDDEN_DIM,
        latent_dim=LATENT_DIM,
    )
    optimizer = optim.Adam(vae.parameters(), lr=1e-3)

    # 3. Training Loop
    vae.train()

    for epoch in range(epochs):
        total_loss = 0
        for batch in dataloader:
            x = batch[0]
            optimizer.zero_grad()

            recon_x, mu, logvar = vae(x)
            loss = vae_loss(
                recon_x,
                x,
                mu,
                logvar,
                kld_weight=DEFAULT_KLD_WEIGHT,
                diagnosis_mask=diagnosis_mask,
            )

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        if (epoch + 1) % 25 == 0:
            logger.debug(
                f"VAE Epoch [{epoch + 1}/{epochs}], Loss: {total_loss / len(dataloader):.4f}"
            )

    return vae


def train_for_satellite(
    norad_id: str, 
    epochs: int = 100, 
    models_dir: str = "models", 
    processed_dir: str = "data/processed"
):
    models_path = Path(models_dir)
    models_path.mkdir(parents=True, exist_ok=True)
    data_path = Path(processed_dir) / f"{norad_id}.csv"
    
    if not data_path.exists():
        logger.error(f"Processed data not found at {data_path}")
        return

    profile = get_satellite_profile(norad_id)
    feature_names = list(profile.feature_contract.feature_names)

    logger.info(
        f"Loading data for NORAD {norad_id} using feature contract "
        f"v{profile.feature_contract.version} ({profile.name})..."
    )
    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    orig_len = len(df)

    extreme_mask = build_baseline_mask(df, profile)
    df_clean = df[~extreme_mask].copy()
    complete_mask = feature_completeness_mask(df_clean, feature_names)
    df_trainable = df_clean[complete_mask].copy()

    split = split_chronological(df_trainable)
    df_train = split.train
    df_validation = split.validation
    df_test = split.test

    X_train = df_train[feature_names].values
    X_validation = df_validation[feature_names].values

    logger.info(f"Cleaned extreme rows: {extreme_mask.sum()}")
    logger.info(f"Dropped incomplete feature rows: {(~complete_mask).sum()}")
    logger.info(
        "Chronological split: "
        f"train={len(df_train)} | validation={len(df_validation)} | test={len(df_test)}"
    )
    logger.info(
        f"Training on {len(X_train)} frames ({len(X_train) / orig_len * 100:.1f}%)"
    )

    # Train Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_validation_scaled = scaler.transform(X_validation)

    artifact_paths = model_artifact_paths(models_path, norad_id)
    joblib.dump(scaler, artifact_paths.scaler)

    diagnosis_mask = [
        feature_names.index(f)
        for f in profile.feature_contract.diagnosis_feature_names
    ]

    # Train PyTorch VAE natively
    vae = train_vae(X_train_scaled, feature_names, diagnosis_mask=diagnosis_mask, epochs=epochs)
    validation_scores = score_scaled_frames(vae, X_validation_scaled, diagnosis_mask=diagnosis_mask)
    threshold = threshold_from_scores(validation_scores, THRESHOLD_PERCENTILE)

    torch.save(vae.state_dict(), artifact_paths.weights)
    logger.success(f"Saved PyTorch VAE → {artifact_paths.weights}")

    metadata = ModelArtifactMetadata.from_split(
        norad_id=norad_id,
        split=split,
        threshold=threshold,
        feature_names=feature_names,
        hidden_dim=HIDDEN_DIM,
        latent_dim=LATENT_DIM,
        kld_weight=DEFAULT_KLD_WEIGHT,
        threshold_percentile=THRESHOLD_PERCENTILE,
        inference_mode=DEFAULT_INFERENCE_MODE,
        feature_contract_version=profile.feature_contract.version,
        diagnosis_feature_names=list(profile.feature_contract.diagnosis_feature_names),
    )
    save_model_metadata(artifact_paths.metadata, metadata)
    logger.success(
        "Saved artifact metadata → "
        f"{artifact_paths.metadata} (threshold={threshold:.6f}, mode={metadata.inference_mode})"
    )

    logger.info("[bold green]Training pipeline completed successfully![/bold green]")
    return metadata
