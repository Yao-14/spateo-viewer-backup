from typing import Optional

import anndata as ad
from scipy.sparse import csr_matrix, issparse


def anndata_preprocess(
    path: str,
    output_path: str,
    X_counts: str = "X_counts",
    X_log1p: Optional[str] = "X_log1p",
    spatial_key: str = "3d_align_spatial",
):
    adata = ad.read_h5ad(filename=path)

    # matrices
    X_counts = (
        adata.layers[X_counts].copy()
        if issparse(adata.layers[X_counts])
        else csr_matrix(adata.layers[X_counts])
    )
    if not (X_log1p is None):
        X_log1p = (
            adata.layers[X_log1p].copy()
            if issparse(adata.layers[X_log1p])
            else csr_matrix(adata.layers[X_log1p])
        )
    else:
        import dynamo as dyn

        adata.X = X_counts.copy()
        dyn.pp.normalize_cell_expr_by_size_factors(
            adata=adata, layers="X", skip_log=False
        )
        X_log1p = csr_matrix(adata.X.copy())

    # spatial coordinates
    spatial_coords = adata.obsm[spatial_key]

    # preprocess
    del adata.uns, adata.layers, adata.obsm, adata.obsp, adata.varm
    adata.X = X_counts
    adata.layers["X_log1p"] = X_log1p
    adata.obsm["spatial"] = spatial_coords

    adata.write_h5ad(output_path, compression="gzip")
    return adata


"""
import os
os.chdir(f"spateo-viewer/stviewer/assets/dataset")
adata = anndata_preprocess(
    path=r"drosophila_E8_9h/h5ad/E8_9h_cellbin_v3.h5ad",
    output_path=r"drosophila_E8_9h/h5ad/E8_9h_cellbin_v3_new.h5ad"
)
print(adata)
"""
