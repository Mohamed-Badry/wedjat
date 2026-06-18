import torch
import torch.nn as nn
import torch.nn.functional as F

from gr_sat.ml_config import DEFAULT_KLD_WEIGHT


class TelemetryVAE(nn.Module):
    """
    Variational Autoencoder (VAE) for Telemetry Anomaly Detection.
    Maps physical bounds into a probabilistic latent space.
    """

    def __init__(self, input_dim=5, hidden_dim=12, latent_dim=3):
        super().__init__()

        # Encoder
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        # Decoder
        self.fc3 = nn.Linear(latent_dim, hidden_dim)
        self.fc4 = nn.Linear(hidden_dim, input_dim)

    def encode(self, x):
        h1 = F.relu(self.fc1(x))
        return self.fc_mu(h1), self.fc_logvar(h1)

    def reparameterize(self, mu, logvar, sample=None):
        if sample is None:
            sample = self.training
        if not sample:
            return mu
        # Sample standard deviation
        std = torch.exp(0.5 * logvar)
        # Sample noise
        eps = torch.randn_like(std)
        # Reparameterization trick
        return mu + eps * std

    def decode(self, z):
        h3 = F.relu(self.fc3(z))
        return self.fc4(h3)

    def forward(self, x, sample=None):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar, sample=sample)
        recon_x = self.decode(z)
        return recon_x, mu, logvar


def compute_kld(mu, logvar, reduction="none"):
    kld = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1)
    if reduction == "mean":
        return torch.mean(kld)
    if reduction == "sum":
        return torch.sum(kld)
    return kld


def compute_anomaly_scores(recon_x, x, mu, logvar, kld_weight=DEFAULT_KLD_WEIGHT, diagnosis_mask=None):
    if diagnosis_mask is not None:
        mse = torch.mean(((x - recon_x) ** 2)[:, diagnosis_mask], dim=1)
    else:
        mse = torch.mean((x - recon_x) ** 2, dim=1)
    kld = compute_kld(mu, logvar, reduction="none")
    return mse + kld_weight * kld


def vae_loss(recon_x, x, mu, logvar, kld_weight=0.01, diagnosis_mask=None):
    """
    Loss function for VAE.
    1. MSE Loss (Reconstruction)
    2. KL Divergence (Latent space regularization)
    """
    if diagnosis_mask is not None:
        MSE = F.mse_loss(recon_x[:, diagnosis_mask], x[:, diagnosis_mask], reduction="mean")
    else:
        MSE = F.mse_loss(recon_x, x, reduction="mean")

    # KL Divergence: -0.5 * sum(1 + log(sigma^2) - mu^2 - sigma^2)
    # Using 'mean' to keep it scaled nicely with MSE
    KLD = compute_kld(mu, logvar, reduction="mean")

    return MSE + kld_weight * KLD
