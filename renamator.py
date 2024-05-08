#!/usr/bin/env python3

import os
import argparse
import cv2
from datetime import datetime
from imohash import hashfile  # type: ignore
from pyzbar.pyzbar import decode as zbar_decode  # type: ignore
from pylibdmtx.pylibdmtx import decode as dm_decode  # type: ignore
from enum import Enum

# mypy imports
from pyzbar.pyzbar import Decoded  # type: ignore
from typing import List
from typing import Tuple
from typing import Dict
from cv2 import UMat
from argparse import Namespace


def main() -> None:
    args = parse_args()
    images: List[str] = [file_name for file_name in sorted(os.listdir(
        args.work_dir)) if file_name.lower().endswith(f".{args.extension}")]
    bin_dups = check_binary_duplicates(args.work_dir, images)
    if len(bin_dups) > 0:
        print("ERROR: there is some binary identical files, here is the list:")
        for d in bin_dups:
            print(d)
    else:
        results: List[str] = process_images_and_rename(args, images)
        now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        with open(os.path.join(args.work_dir, f"{now}_resultats.csv"), "w") as file:
            file.write("\n".join(results))


Place = Enum("Place", ["GENEVE", "SION"])
DecodingResult = Enum(
    "DecodingResult", ["UNREADABLE", "NEED_TO_CHECK", "UNIQUE", "MULTIPLE"])


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        prog="Renamator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Find barcodes and datamatrix in images and rename it to the barcode value.",
        epilog=f"""Examples:
        renamator U:\\user\\images
        renamator U:\\user\\images -p sion -e jpg
        """)
    parser.add_argument("work_dir",
                        help="Directory containing images to rename. The final results are writted here too.")
    parser.add_argument("-p", "--place", required=False, choices=[p.name.lower() for p in Place],
                        default=Place.GENEVE.name.lower(), help="Images provenance (default geneve)")
    parser.add_argument("-e", "--extension", required=False, default="tif",
                        help="Image file extension (default tif)")
    return parser.parse_args()


def check_binary_duplicates(work_dir: str, images: List[str]) -> List[List[str]]:
    hashes = [(image, hashfile(os.path.join(work_dir, image), hexdigest=True))
              for image in images]
    di: Dict[str, List[str]] = {}
    for filename, hash in hashes:
        di.setdefault(hash, []).append(filename)
    return [vs for k, vs in di.items() if len(vs) > 1]


def process_images_and_rename(args: Namespace, images: List[str]) -> List[str]:
    place: Place = Place[args.place.upper()]
    results: List[str] = [f"DecodingResult\tOldName\tNewName\tIsDuplicate"]
    last_barcode: str = ""
    for i, image in enumerate(images):
        print(f"Process '{image}':")
        image_path: str = os.path.join(args.work_dir, image)
        res, last_barcode = process_image(place, image_path, last_barcode, i)
        new_image_path, is_duplicate = make_new_name(image_path, last_barcode)
        os.rename(image_path, new_image_path)
        new_image_name = os.path.basename(new_image_path)

        match res:
            case DecodingResult.UNREADABLE:
                print(f"Unable to decode, rename to '{new_image_name}'\n")
            case DecodingResult.NEED_TO_CHECK:
                print(f"Bad barcode value, rename to '{new_image_name}'\n")
            case DecodingResult.UNIQUE:
                print(f"Code found, rename to '{new_image_name}'\n")
            case DecodingResult.MULTIPLE:
                print(f"Multiple barcodes found: {last_barcode}\n")

        results.append(
            f"{str(res)}\t{image_path}\t{new_image_path}\t{is_duplicate}")
    return results


def process_image(place: Place, image_path: str, last_barcode: str, i: int) -> Tuple[DecodingResult, str]:
    match place:
        case Place.GENEVE:
            barcodes = [b.data for b in find_barcodes(
                image_path) if b.type == "CODE128" and len(b.data) != 0]
        case Place.SION:
            barcodes = [b.data for b in find_datamatrix(
                image_path) if len(b.data) != 0]

    if len(barcodes) == 0:
        if i == 0:
            return DecodingResult.UNREADABLE, "noname"
        else:
            return DecodingResult.UNREADABLE, make_next_name(last_barcode)
    elif len(barcodes) == 1:
        barcode = barcodes[0].decode("utf-8")
        forbidden_chars = ["/", "\\", "<", ">", ":", "|", "?", "*"]
        if any(c in barcode for c in forbidden_chars) or len([c for c in barcode if 0 <= ord(c) <= 31]) != 0:
            return DecodingResult.NEED_TO_CHECK, make_next_name(last_barcode)
        else:
            return DecodingResult.UNIQUE, barcode
    else:
        return DecodingResult.MULTIPLE, str(barcodes)


def find_barcodes(image_path: str) -> List[Decoded]:
    binary_image = to_gray_binary_image(image_path)
    barcodes: List[Decoded] = zbar_decode(binary_image)
    return barcodes


def find_datamatrix(image_path: str) -> List[Decoded]:
    binary_image = to_gray_binary_image(image_path)
    datamatrix: List[Decoded] = dm_decode(
        binary_image, max_count=1, threshold=50, shrink=2)
    return datamatrix


def to_gray_binary_image(image_path: str):
    # Read image
    image = cv2.imread(image_path)
    # Convert color image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply binary threshold
    _, binary_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
    return binary_image


def make_new_name(image_path: str, new_name: str) -> Tuple[str, bool]:
    ext = os.path.splitext(image_path)[1]
    new_image_name = f"{new_name}{ext}"
    new_image_path = os.path.join(os.path.dirname(image_path), new_image_name)
    is_duplicate = os.path.exists(new_image_path)
    while os.path.exists(new_image_path):
        new_image_name = f"copy-{new_image_name}"
        new_image_path = os.path.join(
            os.path.dirname(new_image_path), new_image_name)
    return new_image_path, is_duplicate


def make_next_name(last_barcode: str) -> str:
    if "_" not in last_barcode:
        return f"{last_barcode}_a"
    else:
        base, incr = tuple(last_barcode.split('_'))
        return f"{base}_{chr(ord(incr) + 1)}"


if __name__ == "__main__":
    main()
