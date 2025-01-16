import argparse
import os
import shutil
import pycolmap
import hloc.extract_features, hloc.pairs_from_exhaustive, hloc.match_features
import pixsfm.refine_hloc
from pathlib import Path
from typing import List

def pixelsfm_batch(
    input_path : str,
    output_path : str,
    frame_names : List[str]
):
    try:
        os.mkdir(output_path)
    except:
        pass
    # For each frame.
    ambiguous_recon_frames = []
    for frame_folder_name in sorted(os.listdir(input_path)):
        frame_name = frame_folder_name[5:]
        if len(frame_names) > 0 and frame_name not in frame_names:
            continue
        try:
            os.mkdir(os.path.join(output_path, frame_folder_name))
        except:
            pass
        print("============================= Frame {} =============================".format(frame_name))
        image_dir = Path(os.path.join(input_path, frame_folder_name))
        image_list = os.listdir(image_dir)
        feature_path = Path(os.path.join(output_path, frame_folder_name, "features.h5"))
        pair_path = Path(os.path.join(output_path, frame_folder_name, "pairs.txt"))
        match_path = Path(os.path.join(output_path, frame_folder_name, "matches.h5"))
        model_path = Path(os.path.join(output_path, frame_folder_name, "refined"))
        raw_model_path = Path(os.path.join(output_path, frame_folder_name, "raw"))
        try:
            os.mkdir(model_path)
        except:
            pass
        # Feature extractor.
        hloc.extract_features.main(
            conf=hloc.extract_features.confs['superpoint_aachen'], 
            image_dir=image_dir,
            image_list=image_list,
            feature_path=feature_path
        )
        # Exhaustive matcher.
        hloc.pairs_from_exhaustive.main(
            output=pair_path,
            image_list=image_list
        )
        hloc.match_features.main(
            conf=hloc.match_features.confs['superglue'],
            pairs=pair_path,
            features=feature_path,
            matches=match_path
        )
        # Reconstruction
        print("---------------- Refined model ----------------")
        sfm = pixsfm.refine_hloc.PixSfM({"dense_features": {"max_edge": 4096}})
        recon, sfm_outputs = sfm.reconstruction(
            output_dir=model_path,
            image_dir=image_dir,
            pairs_path=pair_path,
            features_path=feature_path,
            matches_path=match_path,
            image_list=image_list,
            camera_mode=pycolmap.CameraMode.PER_IMAGE,
            image_options=pycolmap.ImageReaderOptions(
                camera_model="PINHOLE"
            ),
            mapper_options=pycolmap.IncrementalMapperOptions(
                ba_refine_principal_point=True,
                ba_refine_focal_length=True,
                ba_refine_extra_params=False
            ).todict()
        )
        # Convert binary to text files.
        recon.write_text(str(model_path))
        if False:
            print("---------------- Raw model ----------------")
            sfm = pixsfm.refine_hloc.PixSfM({"KA":{"apply": False}, "BA": {"apply": False}})
            recon, sfm_outputs = sfm.reconstruction(
                output_dir=raw_model_path,
                image_dir=image_dir,
                pairs_path=pair_path,
                features_path=feature_path,
                matches_path=match_path,
                image_list=image_list,
                camera_mode=pycolmap.CameraMode.PER_IMAGE,
                image_options=pycolmap.ImageReaderOptions(
                    camera_model="PINHOLE"
                ),
                mapper_options=pycolmap.IncrementalMapperOptions(
                    ba_refine_principal_point=True,
                    ba_refine_focal_length=True,
                    ba_refine_extra_params=False
                ).todict()
            )
            # Convert binary to text files.
            recon.write_text(str(raw_model_path))
    # Done.
    print("Ambiguous reconstruction frames:")
    print(" ".join(ambiguous_recon_frames))
    print("Please check the reconstruction results of these frames manually.")
    return
        



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="pixelsfm_batch.py",
        description="""
                        Run Pixel-Perfect SfM on the images generated by "gather_images.py".
                        The result of each frame will be placed into a subfolder called 'frame[frame_id]' in the output folder.
                    """,
        allow_abbrev=True
    )
    parser.add_argument("input", help="Path to multiface dataset.")
    parser.add_argument("output", help="Path to output result folder.")
    parser.add_argument("--frame_names", type=str, nargs='*', help="The list of frame names to be processed. If not specified, all frames will be processed.")
    args = parser.parse_args()
    input_path = args.input
    output_path = args.output
    frame_names = args.frame_names if args.frame_names is not None else []
    pixelsfm_batch(input_path, output_path, frame_names)