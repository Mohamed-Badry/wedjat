# Edge Benchmark for NORAD 43880

This report is an offline synthetic-fault benchmark using the persisted training artifact threshold. It should be read as comparative evaluation, not as proof of a complete live runtime.

**Unified Architecture:** PyTorch Variational Autoencoder

## Metrics
- **AUROC:** 0.9169
- **Recall @ 5% FPR:** 84.3%

- **Operating Threshold:** 0.314559

## Fault Isolation Performance
| Fault Type | Detected by Stage 1 | Isolated by VAE |
|------------|---------------------|-----------------|
| panel_failure | 68.7% | 45.6% |
| thermal_runaway | 88.7% | 51.9% |
