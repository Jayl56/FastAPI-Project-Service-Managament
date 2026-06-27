from typing import BinaryIO

def get_file_size(file: BinaryIO) -> int:
    current = file.tell()
    file.seek(0, 2)
    size = file.tell()
    file.seek(current)
    return size

