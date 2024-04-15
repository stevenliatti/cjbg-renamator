#!/usr/bin/env python3

import os
import argparse
import cv2
from datetime import datetime
from pyzbar.pyzbar import decode as zbar_decode  # type: ignore
from pylibdmtx.pylibdmtx import decode as dm_decode  # type: ignore
from enum import Enum

# mypy imports
from pyzbar.pyzbar import Decoded  # type: ignore
from typing import List
from typing import Tuple
from cv2 import UMat
from argparse import Namespace


def main() -> None:
    args = parse_args()
    images: List[str] = [file for file in sorted(os.listdir(
        args.work_dir)) if file.lower().endswith(f".{args.extension}")]
    results: List[str] = process_images(args, images)
    now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(os.path.join(args.work_dir, f"{now}_resultats.csv"), "w") as file:
        file.write("\n".join(results))


Place = Enum("Place", ["GENEVE", "SION"])
DecodingResult = Enum("DecodingResult", ["UNREADABLE", "UNIQUE", "MULTIPLE"])


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


def process_images(args: Namespace, images: List[str]) -> List[str]:
    place: Place = Place[args.place.upper()]
    results: List[str] = []
    last_barcode: str = ""
    for i, image in enumerate(images):
        print(f"Process '{image}':")
        image_path: str = os.path.join(args.work_dir, image)
        res, new_image_path, last_barcode = find_barcodes_and_rename_file(
            place, image_path, last_barcode, i)

        match res:
            case DecodingResult.UNREADABLE:
                print(f"Unable to read barcode in image '{image}'\n")
            case DecodingResult.UNIQUE:
                print(f"Code found: '{last_barcode}'\n")
            case DecodingResult.MULTIPLE:
                print(f"Multiple barcodes found: {last_barcode}\n")

        results.append(f"{str(res)}\t{image_path}\t{new_image_path}")
    return results


def find_barcodes_and_rename_file(place: Place, image_path: str, last_barcode: str, i: int) -> Tuple[DecodingResult, str, str]:
    match place:
        case Place.GENEVE:
            barcodes = [b.data for b in find_barcodes(
                image_path) if b.type == "CODE128" and len(b.data) != 0]
        case Place.SION:
            barcodes = [b.data for b in find_datamatrix(
                image_path) if len(b.data) != 0]

    if len(barcodes) == 0:
        if i == 0:
            barcode = "noname"
            return DecodingResult.UNREADABLE, barcode, barcode
        else:
            barcode = make_next_name(last_barcode)
            new_image_path = rename_file(image_path, barcode)
            return DecodingResult.UNREADABLE, new_image_path, barcode
    elif len(barcodes) == 1:
        barcode = barcodes[0].decode("utf-8")
        new_image_path = rename_file(image_path, barcode)
        return DecodingResult.UNIQUE, new_image_path, barcode
    else:
        return DecodingResult.MULTIPLE, "", str(barcodes)


def find_barcodes(image_path: str) -> List[Decoded]:
    binary_image = to_gray_binary_image(image_path)
    barcodes: List[Decoded] = zbar_decode(binary_image)
    return barcodes


def find_datamatrix(image_path: str) -> List[Decoded]:
    binary_image = to_gray_binary_image(image_path)
    datamatrix: List[Decoded] = dm_decode(
        binary_image, max_count=1, threshold=50, shrink=2)
    return datamatrix


def to_gray_binary_image(image_path: str) -> UMat:
    # Read image
    image = cv2.imread(image_path)
    # Convert color image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply binary threshold
    _, binary_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
    return binary_image


def rename_file(image_path: str, barcode: str) -> str:
    new_image_path = make_new_name(image_path, barcode)
    os.rename(image_path, new_image_path)
    return new_image_path


def make_new_name(image_path: str, barcode: str) -> str:
    base_path, ext = os.path.splitext(image_path)
    new_image_name = f"{barcode}{ext}"
    new_image_path = os.path.join(os.path.dirname(image_path), new_image_name)
    return new_image_path


def make_next_name(last_barcode: str) -> str:
    if "_" not in last_barcode:
        return f"{last_barcode}_a"
    else:
        base, incr = tuple(last_barcode.split('_'))
        return f"{base}_{chr(ord(incr) + 1)}"


if __name__ == "__main__":
    main()
