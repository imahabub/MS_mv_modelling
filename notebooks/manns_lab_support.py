import pandas as pd
import numpy as np
import scanpy as sc
import os

"""

    Functions to load and preprocess the dataset from Mann's lab.
     - loading
     - preprocessing / filtering
     - combining
     - summarizing
     - batch correcting

"""


def load_main_data(dir: str):
    annotations_path = os.path.join(dir, "annotations_main_lt_v21_Sc11_AIMsplit3.tsv")
    data_path = os.path.join(
        dir,
        "DA-F08.4_-SEC-pass_v06Sc_ion_LibPGQVal1perc_precdLFQdefFull_prot_preprSc03.tsv",
    )
    stats_path = os.path.join(
        dir, "DA-F08.4_PL01-POL-LT-QC2_DA-SER1.19_C20Lib02_.stats.tsv"
    )

    data = pd.read_csv(data_path, sep="\t", index_col="protein")
    obs = pd.read_csv(annotations_path, sep="\t")
    stats = pd.read_csv(stats_path, sep="\t")

    data.drop("Unnamed: 0", axis=1, inplace=True)
    obs.drop("Unnamed: 0", axis=1, inplace=True)

    # extract vars
    var_cols = [c for c in data.columns if "JaBa" not in c]
    vars = data[var_cols]
    data.drop(var_cols, axis=1, inplace=True)

    data = data.T

    # extract the "run number" from the run name - which is unique shared between the files
    data["filename"] = [run.split("/")[-1].split(".")[0] for run in data.index]
    data.set_index("filename", drop=True, inplace=True, verify_integrity=True)

    obs["filename"] = [run.split("/")[-1].split(".")[0] for run in obs["Run"]]
    obs.set_index("filename", drop=True, inplace=True, verify_integrity=True)

    stats["filename"] = [run.split("/")[-1].split(".")[0] for run in stats["File.Name"]]
    stats.set_index("filename", drop=True, inplace=True, verify_integrity=True)

    drop = [
        "Comment",
        "CVsampleInfo_I",
        "CVsampleInfo_II",
        "CVsampleInfo_III",
        "QC_Experiment",
        "QC_Sample_ID",
        "QC_Patient_ID",
        "QC_Condition",
        "QC_Condition_numeric",
        "PatientID_LT",
        "N_puncture_LT",
        "Diff_to_first_puncture_LT",
        "ID_MAIN_LT",
    ]
    obs = obs.drop(drop, axis=1)

    # ignore LT, QC, PO plates and plates with multiple runs
    obs = obs[obs["Sample_plate"].str.match(r"^plate\d+$")]

    # remove more quality control samples
    obs = obs[["Pool" not in obs for obs in obs["MSgroup"]]]

    for o in [
        "Leukocyte_count",
        "Albumin_CSF",
        "QAlb",
        "IgG_CSF",
        "QIgG",
        "Total_protein",
    ]:
        obs[o] = [
            np.nan if a in ["n. best.", "n. best. ", "na", "not measured"] else float(a)
            for a in obs[o]
        ]
    obs["Erythrocytes_in_CSF"] = [
        np.nan if a in ["n. best.", "n. best. ", "na", "not measured"] else a
        for a in obs["Erythrocytes_in_CSF"]
    ]

    obs["Total_protein"][obs["Total_protein"] == 0] = np.nan
    obs["Diagnosis_group_subtype"][obs["Diagnosis_group_subtype"] == "unknown"] = np.nan

    obs["Evosept"] = [a.split("_")[4][1] for a in obs["Run"]]
    obs["Column"] = [a.split("_")[4][3] for a in obs["Run"]]
    obs["Emitter"] = [a.split("_")[4][5] for a in obs["Run"]]
    obs["Capillary"] = [a.split("_")[4][7] for a in obs["Run"]]
    obs["Maintenance"] = [a.split("_")[4][9:11] for a in obs["Run"]]

    obs["Age"] = obs["Age"].astype("float")
    obs["log Qalb"] = np.log(obs["QAlb"])

    obs.rename(
        {
            "Leukocyte_count": "Leukocyte count",
            "Total_protein": "Total protein",
            "IgG_CSF": "IgG CSF",
            "QAlb": "Qalb",
            "Albumin_CSF": "Albumin CSF",
            "Erythrocytes_in_CSF": "Erythrocytes",
            "Sample_plate": "Plate",
            "Sample_preparation_batch": "Preparation day",
        },
        axis=1,
        inplace=True,
    )

    ## create adata from data, vars, obs
    obs = pd.merge(obs, stats, how="inner", left_index=True, right_index=True)
    obs = pd.merge(
        pd.DataFrame(index=data.index),
        obs,
        how="inner",
        left_index=True,
        right_index=True,
    )

    data = data.loc[obs.index]

    adata = sc.AnnData(data, var=vars, obs=obs)
    adata.obs = adata.obs.set_index("ID", drop=True, verify_integrity=True)

    adata.strings_to_categoricals()

    return adata


def load_pilot_data(dir: str):
    ANNOTATIONS_PATH = os.path.join(
        dir, "2023_sample annotation_PILOTcohorts combined_v21_Sc06.tsv"
    )
    DATA_PATH = os.path.join(
        dir,
        "DAP-F03.4_-SEC-pass_v06Sc_ion_LibPGQVal1perc_precdLFQdefFull_protein_intensities.tsv",
    )
    STATS_PATH = os.path.join(
        dir, "DAP-F03.4_CH1+2+QC_DA-SER2.01_LibC20Lib02_.stats.tsv"
    )

    data = pd.read_csv(DATA_PATH, sep="\t", index_col="protein")
    obs = pd.read_csv(ANNOTATIONS_PATH, sep="\t")
    stats = pd.read_csv(STATS_PATH, sep="\t")

    obs.drop("Unnamed: 0", axis=1, inplace=True)

    # extract vars
    var_cols = [c for c in data.columns if "JaBa" not in c]
    vars = data[var_cols]
    data.drop(var_cols, axis=1, inplace=True)

    data = data.T

    data["filename"] = [run.split("/")[-1].split(".")[0] for run in data.index]
    data.set_index("filename", drop=True, inplace=True, verify_integrity=True)

    obs["filename"] = [run.split("/")[-1].split(".")[0] for run in obs["Run"]]
    obs.set_index("filename", drop=True, inplace=True, verify_integrity=True)

    stats["filename"] = [run.split("/")[-1].split(".")[0] for run in stats["File.Name"]]
    stats.set_index("filename", drop=True, inplace=True, verify_integrity=True)

    # log normalize intensities and set 0's to nan to be consistent between pilot and main dataset.
    data[data == 0] = np.nan
    data = np.log(data)

    # filter out plate 5 since in the PILOT some samples were measured multiple times. Recommended by Jakob at Manns lab.
    obs = obs[obs["Sample_plate"] != "plate5"]

    # remove more quality control samples
    obs = obs[~obs["MSgroup"].isna()]
    obs = obs[["Pool" not in obs for obs in obs["MSgroup"]]]

    # for some reason, "QCpool_PILOT1" spilled over to "Age".
    obs = obs[["pool" not in obs for obs in obs["Age"]]]

    # remove more quality control samples
    obs = obs[["Pool" not in obs for obs in obs["MSgroup"]]]

    for o in [
        "Leukocyte_count",
        "Albumin_CSF",
        "QAlb",
        "IgG_CSF",
        "QIgG",
        "Total_protein",
    ]:
        obs[o] = [
            np.nan if a in ["n. best.", "n. best. ", "na", "not measured"] else float(a)
            for a in obs[o]
        ]
    obs["Erythrocytes_in_CSF"] = [
        np.nan if a in ["n. best.", "n. best. ", "na", "not measured"] else a
        for a in obs["Erythrocytes_in_CSF"]
    ]

    obs["Total_protein"][obs["Total_protein"] == 0] = np.nan
    obs["Diagnosis_group_subtype"][obs["Diagnosis_group_subtype"] == "unknown"] = np.nan

    obs["Age"] = obs["Age"].astype("float")
    obs["log Qalb"] = np.log(obs["QAlb"])

    obs.rename(
        {
            "Leukocyte_count": "Leukocyte count",
            "Total_protein": "Total protein",
            "IgG_CSF": "IgG CSF",
            "QAlb": "Qalb",
            "Albumin_CSF": "Albumin CSF",
            "Erythrocytes_in_CSF": "Erythrocytes",
            "Sample_plate": "Plate",
            "Sample_preparation_batch": "Preparation day",
        },
        axis=1,
        inplace=True,
    )

    # remove duplicate samples based on ID_main
    ID_main_counts = obs["ID_main"].value_counts()
    ID_main_unique_idx = ID_main_counts[ID_main_counts == 1].index
    obs = obs[obs["ID_main"].isin(ID_main_unique_idx)]

    ## create adata from data, vars, obs
    obs = pd.merge(obs, stats, how="inner", left_index=True, right_index=True)
    obs = pd.merge(
        pd.DataFrame(index=data.index),
        obs,
        how="inner",
        left_index=True,
        right_index=True,
    )

    data = data.loc[obs.index]

    adata = sc.AnnData(data, var=vars, obs=obs)
    adata.obs = adata.obs.set_index("ID_main", drop=True, verify_integrity=True)

    adata.strings_to_categoricals()

    return adata


def filter(adata, min_protein_completeness=0.2):
    # Filtering from Christine.

    # self.adata = self.adata[self.adata.obs["Qalb"] == self.adata.obs["Qalb"]]
    adata = adata[~adata.obs["Qalb"].isna()]

    adata = adata[[e not in ["++", "+++", "bloody"] for e in adata.obs["Erythrocytes"]]]
    adata = adata[(adata.obs[["Erythrocytes"]] == adata.obs[["Erythrocytes"]]).values]

    adata.var["filter"] = 1
    for group in np.unique(adata.obs["Diagnosis_group"]):
        sub = adata[adata.obs["Diagnosis_group"] == group]
        completeness = (sub.X == sub.X).mean(axis=0)
        adata.var["filter"] = adata.var["filter"] * (
            completeness < min_protein_completeness
        ).astype(int)

    adata.var["filter"] = adata.var["filter"].astype(bool)
    adata = adata[:, ~adata.var["filter"]].copy()

    return adata


def preprocess(adata, filter_cells=0):
    print(f"input: {adata.shape}")

    sc.pp.filter_genes(adata, min_cells=1)
    print(f"sc.pp.filter_genes: {adata.shape}")

    sc.pp.filter_cells(adata, min_genes=filter_cells)
    print(f"sc.pp.filter_cells: {adata.shape}")

    adata = filter(adata)
    print(f"filter: {adata.shape}")

    return adata


def combine_PILOT_and_MAIN(pilot_adata, main_adata):
    assert (
        pilot_adata.shape[0] < main_adata.shape[0]
    ), "num patients in pilot data should be smaller than main data. Did you swap the order of the datasets in the function arguments?"

    #  create AnnData object copy
    combined_adata = main_adata.copy()

    # MAIN layer
    combined_adata.layers["MAIN"] = combined_adata.X.copy()

    # PILOT layer
    main_ids = set(main_adata.obs_names)
    pilot_ids = set(pilot_adata.obs_names)
    ids = list(main_ids.intersection(pilot_ids))

    main_proteins = set(main_adata.var_names)
    pilot_proteins = set(pilot_adata.var_names)
    proteins = list(main_proteins.intersection(pilot_proteins))

    empty = pd.DataFrame(
        np.zeros(main_adata.shape),
        index=main_adata.obs_names,
        columns=main_adata.var_names,
    )
    empty[:] = np.nan

    # extract the proteins and samples that are in both datasets from the pilot dataset
    # @IMPORTANT: this will reorder the rows and columns of the pilot dataset... so we need to reorder them back
    pilot = empty.combine_first(pilot_adata[ids, proteins].to_df())
    pilot = pilot.loc[main_adata.obs_names, main_adata.var_names]

    combined_adata.layers["PILOT"] = pilot.values

    print(
        f"Nr. patients | main: {len(main_ids)}, pilot: {len(pilot_ids)}, in both: {len(ids)}"
    )
    print(
        f"Nr. proteins | main: {len(main_proteins)}, pilot: {len(pilot_proteins)}, in both: {len(proteins)}"
    )

    # ALL layer - combine main and pilot data
    # @IMPORTANT: this will reorder the rows and columns of the pilot dataset... so we need to reorder them back
    both = main_adata.to_df().combine_first(pilot_adata[ids, proteins].to_df())
    both = both.loc[main_adata.obs_names, main_adata.var_names]
    combined_adata.layers["combined"] = both.values

    return combined_adata


def print_combined_summary(combined_adata):
    ## PILOT
    pilot_patients_filter = np.any(~np.isnan(combined_adata.layers["PILOT"]), axis=1)
    pilot_protein_filter = np.any(~np.isnan(combined_adata.layers["PILOT"]), axis=0)

    print(
        f"Percentage of patients in both PILOT and MAIN (patients: {np.sum(pilot_patients_filter)}):"
    )

    data = combined_adata[pilot_patients_filter]
    n = np.sum(data.layers["PILOT"] == data.layers["PILOT"])
    n_total = data.shape[0] * data.shape[1]

    print(
        f"  {data.shape[1]} unique proteins (all those in MAIN):      {n / n_total * 100:.2f}%"
    )

    data = combined_adata[pilot_patients_filter, pilot_protein_filter]
    n = np.sum(data.layers["PILOT"] == data.layers["PILOT"])
    n_total = data.shape[0] * data.shape[1]

    print(
        f"  {data.shape[1]} unique proteins (in both MAIN and PILOT): {n / n_total * 100:.2f}%"
    )

    ## MAIN
    n_combined = np.sum(
        combined_adata.layers["combined"] == combined_adata.layers["combined"]
    )
    n_pilot = np.sum(combined_adata.layers["PILOT"] == combined_adata.layers["PILOT"])
    n_main = np.sum(combined_adata.layers["MAIN"] == combined_adata.layers["MAIN"])
    n_total = combined_adata.shape[0] * combined_adata.shape[1]

    print(
        f"\nPercentage of observed intensities using MAIN patient-protein layout (patients: {combined_adata.shape[0]}, proteins: {combined_adata.shape[1]})"
    )
    print(f"  MAIN:     {n_main / n_total * 100:.2f}%")
    print(f"  PILOT:    {n_pilot / n_total * 100:.2f}%")
    print(f"  combined: {n_combined / n_total * 100:.2f}%")


def correct_batch(adata):
    """Corrects batch for anndata.X - keeping the original reference to X"""
    mean_protein = np.nanmean(adata.X, axis=0)

    stds_plates = []
    for plate in np.unique(adata.obs["Plate"]):
        plate_adata = adata[adata.obs["Plate"] == plate]
        std_protein_per_plate = np.nanstd(plate_adata.X, axis=0)
        stds_plates.append(std_protein_per_plate)

    std = np.nanmean(stds_plates)

    for plate in np.unique(adata.obs["Plate"]):
        plate_adata = adata[adata.obs["Plate"] == plate]
        mean_protein_per_plate = np.nanmean(plate_adata.X, axis=0)
        std_protein_per_plate = np.nanstd(plate_adata.X, axis=0)

        # If only 1 cell exists in the plate, std_protein_per_plate will be 0. So we correct this.
        # @TODO: would it be better not to do this correction and thereby get more nan's in the data?
        std_protein_per_plate[std_protein_per_plate == 0] = std

        plate_adata.X = (
            ((plate_adata.X - mean_protein_per_plate) / std_protein_per_plate) * std
        ) + mean_protein

    # result stored in adata.X
