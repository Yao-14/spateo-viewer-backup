from typing import Optional

import numpy as np
from anndata import AnnData
from dynamo.vectorfield import SvcVectorField
from pyvista import PolyData
from scipy.integrate import odeint


def morphogenesis(
    source_adata: AnnData,
    target_adata: AnnData,
    source_pc_model: PolyData,
    mapping_factor: float = 0.001,
    morphofield_factor: int = 3000,
    morphopath_t_end: int = 10000,
    morphopath_sampling: int = 500,
):
    try:
        import spateo as st
    except ImportError:
        raise ImportError(
            "You need to install the package `spateo`. \nInstall spateo via `pip install spateo-release`"
        )

    # Preprocess
    _obs_index = source_pc_model.point_data["obs_index"]
    source_adata = source_adata[_obs_index, :]

    # 3D mapping
    _ = st.tdr.cell_directions(
        adataA=source_adata,
        adataB=target_adata,
        numItermaxEmd=2000000,
        spatial_key="spatial",
        key_added="cells_mapping",
        alpha=mapping_factor,
        device="cpu",
        inplace=True,
    )

    # morphofield
    st.tdr.morphofield(
        adata=source_adata,
        spatial_key="spatial",
        V_key="V_cells_mapping",
        key_added="VecFld_morpho",
        NX=None,
        inplace=True,
    )
    source_adata.obs["V_z"] = source_adata.uns["VecFld_morpho"]["V"][:, 2].flatten()
    source_pc_model.point_data["vectors"] = source_adata.uns["VecFld_morpho"]["V"]
    source_pc_model.point_data["V_Z"] = source_pc_model.point_data["vectors"][
        :, 2
    ].flatten()

    pc_vectors, _ = st.tdr.construct_field(
        model=source_pc_model,
        vf_key="vectors",
        arrows_scale_key="vectors",
        n_sampling=None,
        factor=morphofield_factor,
        key_added="obs_index",
        label=source_pc_model.point_data["obs_index"],
    )

    # trajectory
    st.tdr.morphopath(
        adata=source_adata,
        vf_key="VecFld_morpho",
        key_added="fate_morpho",
        t_end=morphopath_t_end,
        interpolation_num=50,
        cores=20,
    )
    trajectory_model, _ = st.tdr.construct_trajectory(
        adata=source_adata,
        fate_key="fate_morpho",
        n_sampling=morphopath_sampling,
        sampling_method="random",
        key_added="obs_index",
        label=np.asarray(source_adata.obs.index),
    )

    # morphogenesis
    st.tdr.morphofield_acceleration(
        adata=source_adata, vf_key="VecFld_morpho", key_added="acceleration"
    )
    st.tdr.morphofield_curvature(
        adata=source_adata, vf_key="VecFld_morpho", key_added="curvature"
    )
    st.tdr.morphofield_curl(
        adata=source_adata, vf_key="VecFld_morpho", key_added="curl"
    )
    st.tdr.morphofield_torsion(
        adata=source_adata, vf_key="VecFld_morpho", key_added="torsion"
    )

    source_pc_index = source_pc_model.point_data["obs_index"]
    source_pc_model.point_data["acceleration"] = np.asarray(
        source_adata[np.asarray(source_pc_index)].obs["acceleration"]
    )
    source_pc_model.point_data["curvature"] = np.asarray(
        source_adata[np.asarray(source_pc_index)].obs["curvature"]
    )
    source_pc_model.point_data["curl"] = np.asarray(
        source_adata[np.asarray(source_pc_index)].obs["curl"]
    )
    source_pc_model.point_data["torsion"] = np.asarray(
        source_adata[np.asarray(source_pc_index)].obs["torsion"]
    )

    pc_vectors_index = pc_vectors.point_data["obs_index"]
    pc_vectors.point_data["V_Z"] = np.asarray(
        source_adata[np.asarray(pc_vectors_index)].obs["V_z"]
    )
    pc_vectors.point_data["acceleration"] = np.asarray(
        source_adata[np.asarray(pc_vectors_index)].obs["acceleration"]
    )
    pc_vectors.point_data["curvature"] = np.asarray(
        source_adata[np.asarray(pc_vectors_index)].obs["curvature"]
    )
    pc_vectors.point_data["curl"] = np.asarray(
        source_adata[np.asarray(pc_vectors_index)].obs["curl"]
    )
    pc_vectors.point_data["torsion"] = np.asarray(
        source_adata[np.asarray(pc_vectors_index)].obs["torsion"]
    )

    trajectory_index = trajectory_model.point_data["obs_index"]
    trajectory_model.point_data["V_Z"] = np.asarray(
        source_adata[np.asarray(trajectory_index)].obs["V_z"]
    )
    trajectory_model.point_data["acceleration"] = np.asarray(
        source_adata[np.asarray(trajectory_index)].obs["acceleration"]
    )
    trajectory_model.point_data["curvature"] = np.asarray(
        source_adata[np.asarray(trajectory_index)].obs["curvature"]
    )
    trajectory_model.point_data["curl"] = np.asarray(
        source_adata[np.asarray(trajectory_index)].obs["curl"]
    )
    trajectory_model.point_data["torsion"] = np.asarray(
        source_adata[np.asarray(trajectory_index)].obs["torsion"]
    )

    # cell stages of animation
    t_ind = np.asarray(list(source_adata.uns["fate_morpho"]["t"].keys()), dtype=int)
    t_sort_ind = np.argsort(t_ind)
    t = np.asarray(list(source_adata.uns["fate_morpho"]["t"].values()))[t_sort_ind]
    flats = np.unique([int(item) for sublist in t for item in sublist])
    flats = np.hstack((0, flats))
    flats = np.sort(flats) if 3000 is None else np.sort(flats[flats <= 3000])
    time_vec = np.logspace(0, np.log10(max(flats) + 1), 100) - 1
    vf = SvcVectorField()
    vf.from_adata(source_adata, basis="morpho")
    f = lambda x, _: vf.func(x)
    displace = lambda x, dt: odeint(f, x, [0, dt])

    init_states = source_adata.uns["fate_morpho"]["init_states"]
    pts = [i.tolist() for i in init_states]
    stages_X = [source_adata.obs.index.tolist()]
    for i in range(100):
        pts = [displace(cur_pts, time_vec[i])[1].tolist() for cur_pts in pts]
        stages_X.append(pts)

    return source_pc_model, pc_vectors, trajectory_model, stages_X
