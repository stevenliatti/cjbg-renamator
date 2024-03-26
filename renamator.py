#!/usr/bin/env python3

import os
import sys
import cv2
from pyzbar.pyzbar import decode  # type: ignore

# mypy imports
from pyzbar.pyzbar import Decoded  # type: ignore
from typing import List


def main() -> None:
    if len(sys.argv) < 2:
        print("You need to give a correct images directory and files extension, ex: ")
        print("python3 renamator.py /tmp/images tif")
    else:
        images_dir: str = sys.argv[1]
        extension: str = sys.argv[2]
        os.chdir(images_dir)

        images: List[str] = [file for file in os.listdir(
            images_dir) if file.lower().endswith(f".{extension}")]

        for image in images:
            # if "_" not in image:
            print(f"Process {image}:")
            image_path: str = os.path.join(images_dir, image)
            find_barcodes_and_rename_file(image_path)
            print()


def find_barcodes_and_rename_file(image_path: str) -> None:
    barcodes = find_barcodes(image_path)
    if len(barcodes) == 0:
        print(f"Unable to read barcode in the image '{image_path}'")
    elif len(barcodes) == 1:
        barcode = barcodes[0].data.decode("utf-8")
        new_image_path = make_new_name(image_path, barcode)
        compare_names(image_path, barcode)
        # os.rename(image_path, new_image_path)
        print(
            f"Code found and image renamed '{image_path}' to '{new_image_path}'")
    else:
        to_print = [b.data for b in barcodes if b.type == "CODE128"]
        print(f"Multiple barcodes found: {to_print}")


def find_barcodes(image_path: str) -> List[Decoded]:
    # Read image
    image = cv2.imread(image_path)
    # Convert color image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply binary threshold
    _, ad_thr = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
    # Find barcodes in image
    barcodes = decode(ad_thr)
    return barcodes


def make_new_name(image_path: str, barcode: str) -> str:
    base_path, ext = os.path.splitext(image_path)
    new_image_name = f"{barcode}{ext}"
    new_image_path = os.path.join(os.path.dirname(image_path), new_image_name)
    return new_image_path


def compare_names(image_path: str, barcode: str) -> None:
    hierarchy, file = os.path.split(image_path)
    file_name, _ = os.path.splitext(file)
    if file_name != barcode:
        print(f"Image name: {file_name}, barcode value: {barcode}")


if __name__ == "__main__":
    main()
