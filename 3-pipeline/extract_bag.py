#!/usr/bin/env python3
###############################################################################################################
"""
artificial-agent
09-25-2024
"""
"""
extract_bag.py
"""
"""
DESC:
    - script for extracting rosbags and converting them to hugging face datasets
"""
###############################################################################################################


###############################################################################################################
# Core Imports
import sys
import yaml
import csv
from pathlib import Path
from argparse import ArgumentParser
# External Imports
import rosbag
from tqdm import tqdm
import numpy as np
from datasets import Dataset, IterableDataset, Image
# Internal Imports
from rosbag_preprocess.data_handler import get_msg_cols, process_msg_csv, process_msg_img
###############################################################################################################


# Script setup
###############################################################################################################
def parse_cmd_line() -> dict:
    # Instantiate base argument parser
    parser = ArgumentParser(usage='USAGE: extract_bag.py')

    # Setup args
    parser.add_argument("--bagfile",    type=str,   default=f"canonical.bag",       help="Absolute location of rosbag")
    parser.add_argument("--config",     type=str,   default=f"extract_config.yaml", help="Absolute location of config file")
    parser.add_argument("--output_dir", type=str,   default=f"2-outputs",           help="Directory to ouput data products")

    # Parse args
    args = parser.parse_args()

    # Create output DIR if it does not exist
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Return
    return {
        "bagfile": args.bagfile,
        "config": args.config,
        "output_dir": args.output_dir
    }


###############################################################################################################


# Extraction functions
###############################################################################################################
def extract_single(rosbag_abs_path: str, extraction_config: dict, output_dir: str) -> None:
    #! Setup
    rosbag_topics = [ topic_info["rosbag_topic"] for topic_info in extraction_config["data_schema"] ]
    output_dir_names = [ topic_info["output_dir"] for topic_info in extraction_config["data_schema"] ]
    csv_writers = {} # Dictionary to keep track of open CSV writers by topic type
    img_writers = {}
    topic_msg_counts = {topic: 0 for topic in rosbag_topics} # Dictionary to keep track of the count of each topic
    bag_name = rosbag_abs_path.split("/")[-1][:-4]

    #! Main Loop
    try:
        # Open bag w/ read access
        with rosbag.Bag(rosbag_abs_path, 'r') as bag:
            # Completion bar
            with tqdm(total=bag.get_message_count(), desc="Extracting topics...", file=sys.stdout) as progress_bar:
                # Loop through bag
                for topic, msg, time_stamp in bag.read_messages():
                    msg_type = msg._type

                    # Only extract specified topics
                    if topic in rosbag_topics:
                        topic_idx: int = topic_msg_counts[topic]
                        topic_config: dict = [ topic_info for topic_info in extraction_config["data_schema"] if topic_info["rosbag_topic"] == topic ][0] # do this up front for speedup

                        # Conditionally extract msgs based on start, end, and throttle rate
                        if (topic_idx >= topic_config["start_idx"]) and (topic_idx < topic_config["end_idx"]) and (topic_idx % topic_config["throttle_rate"] == 0):

                            #! Switch based on output type (csv, png, pcd, etc)
                            if topic_config["output_type"] == "csv":
                                if topic not in csv_writers:
                                    # Create a new CSV file for this message type
                                    Path(f"{output_dir}/{bag_name}").mkdir(parents=True, exist_ok=True)
                                    csv_file_path = Path(f'{output_dir}/{bag_name}/{topic_config["output_dir"]}.csv')
                                    csv_file = open(csv_file_path, 'w', newline='')

                                    # Initialize a CSV writer for this file
                                    writer = csv.DictWriter(csv_file, get_msg_cols(msg_type))
                                    writer.writeheader() # Write the header (fields of the message)
                                    csv_writers[topic] = {"file": csv_file, "writer": writer, "msg_type": msg_type}

                                # Process the message and write it to the corresponding CSV
                                processed_data = process_msg_csv(msg_type, msg, time_stamp, topic_config.get("extra_options", None))
                                csv_writers[topic]["writer"].writerow(processed_data)

                            elif topic_config["output_type"] == "dir_of_imgs":
                                if topic not in img_writers:
                                    full_dir = f'{output_dir}/{bag_name}/{topic_config["output_dir"]}'
                                    Path(full_dir).mkdir(parents=True, exist_ok=True)
                                    img_writers[topic] = {"directory": full_dir, "msg_type": msg_type}

                                processed_data = process_msg_img(msg_type, msg, time_stamp, topic_config.get("extra_options", None))
                                processed_data["img"].save(f'{output_dir}/{bag_name}/{topic_config["output_dir"]}/{topic_msg_counts[topic]}.png', pnginfo=processed_data["img_metadata"])

                    # Bookkeeping
                    try:
                        topic_msg_counts[topic] += 1
                    except:
                        topic_msg_counts[topic] = 1

                    progress_bar.update(1)

    finally:
        # Close all open CSV files
        for key, value in csv_writers.items():
            value["file"].close()


def extract_all(rosbag_abs_path: str, extraction_config: dict, output_dir: str) -> None:
    #! Get list of bags
    list_o_bags = [file for file in Path(rosbag_abs_path).glob('*.bag') if not file.name.startswith('.')]
    # Sort the files by file size
    list_o_bags.sort(key=lambda file: file.stat().st_size)
    # Convert to str
    list_o_bags = [str(file) for file in list_o_bags]
    bag_names = [bag.split("/")[-1][:-4] for bag in list_o_bags]

    #! Process each 1 by 1
    for idx, rosbag_path in enumerate(list_o_bags):
        print(f"Extracting bag # {idx}...")
        extract_single(rosbag_path, extraction_config, output_dir)
        print("...Completed!\n\n")


###############################################################################################################


# Main
###############################################################################################################
if __name__ == "__main__":
    # Setup
    args = parse_cmd_line()

    # Load YAML config file
    with open(args["config"]) as stream:
        try:
            extraction_config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Infer end idx
    for topic_info in extraction_config["data_schema"]:
        if topic_info["end_idx"] == -1:
            topic_info["end_idx"] = int(9E15)

    # Infer if single bag or dir of bags & extract data
    if f"{args['bagfile']}"[-4:] == ".bag":
        extract_single(args["bagfile"], extraction_config, args["output_dir"])
    else:
        extract_all(args["bagfile"], extraction_config, args["output_dir"])


###############################################################################################################
# EOF