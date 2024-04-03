#!/usr/bin/env python3

import os
import sys
import cv2
from pyzbar.pyzbar import decode  # type: ignore
from enum import Enum

# mypy imports
from pyzbar.pyzbar import Decoded  # type: ignore
from typing import List
from typing import Tuple


def main() -> None:
    if len(sys.argv) < 3:
        print("To run : python3 renamator.py <images_dir> <extension> <results_file>, ex: ")
        print("python3 renamator.py /tmp/images tif /tmp/res.csv")
    else:
        images_dir: str = sys.argv[1]
        extension: str = sys.argv[2]
        results_file: str = sys.argv[3]

        images: List[str] = [file for file in sorted(os.listdir(
            images_dir)) if file.lower().endswith(f".{extension}")]

        results: List[str] = []
        last_barcode: str = ""
        for i, image in enumerate(images):
            print(f"Process {image}:")
            image_path: str = os.path.join(images_dir, image)
            res, new_image_path, last_barcode = find_barcodes_and_rename_file(
                image_path, last_barcode, i)

            match res:
                case DecodingResult.UNREADABLE:
                    print(f"Unable to read barcode in image '{image_path}'\n")
                case DecodingResult.UNIQUE:
                    print(f"Code found and image '{
                          image_path}' renamed to '{new_image_path}'\n")
                case DecodingResult.MULTIPLE:
                    print(f"Multiple barcodes found: {new_image_path}\n")

            results.append(f"{str(res)}\t{image_path}\t{new_image_path}")

        with open(results_file, "w") as file:
            file.write("\n".join(results))


DecodingResult = Enum("DecodingResult", ["UNREADABLE", "UNIQUE", "MULTIPLE"])


def find_barcodes_and_rename_file(image_path: str, last_barcode: str, i: int) -> Tuple[DecodingResult, str, str]:
    barcodes = [b.data for b in find_barcodes(
        image_path) if b.type == "CODE128" and len(b.data) != 0]
    if len(barcodes) == 0:
        if i == 0:
            return DecodingResult.UNREADABLE, "", ""
        else:
            barcode = make_next_name(last_barcode)
            new_image_path = rename_file(image_path, barcode)
            return DecodingResult.UNREADABLE, new_image_path, barcode
    elif len(barcodes) == 1:
        barcode = barcodes[0].decode("utf-8")
        new_image_path = rename_file(image_path, barcode)
        return DecodingResult.UNIQUE, new_image_path, barcode
    else:
        return DecodingResult.MULTIPLE, str(barcodes), ""


def find_barcodes(image_path: str) -> List[Decoded]:
    # Read image
    image = cv2.imread(image_path)
    # Convert color image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply binary threshold
    _, binary_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
    # Find barcodes in image
    barcodes: List[Decoded] = decode(binary_image)
    return barcodes


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
