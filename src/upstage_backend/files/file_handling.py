import binascii
import os

from base64 import b64decode
import uuid
from graphql import GraphQLError

from upstage_backend.global_config.env import OTHER_MEDIA_MAX_SIZE, VIDEO_MAX_SIZE
from upstage_backend.global_config.helpers.paths import safe_join


def decode_base64_payload(payload: str) -> bytes:
    """
    Decode a data-URL (``data:<mime>;base64,<data>``) or bare base64 string.

    The previous ``payload.split(",")[1]`` raised ``IndexError`` on a payload
    without a comma and accepted garbage silently; both now surface as a
    GraphQL validation error instead of a 500.
    """
    if not isinstance(payload, str) or not payload:
        raise GraphQLError("Malformed upload payload")
    header, sep, data = payload.partition(",")
    raw = data if sep else header
    raw = "".join(raw.split())
    if not raw:
        raise GraphQLError("Malformed upload payload")
    try:
        return b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise GraphQLError("Malformed upload payload") from None


class FileHandling:
    def __init__(self):
        pass

    def convert_KB_to_MB(self, size: int) -> int:
        # Name is historical: the argument is bytes.
        return int(size / (1024 * 1024))

    def validate_file_size(self, file_extension: str, file_size: int) -> bool:
        if file_extension.lower() in [".svg", ".jpg", ".jpeg", ".png", ".gif"]:
            if file_size > OTHER_MEDIA_MAX_SIZE:
                raise GraphQLError(
                    f"Image files must be under {self.convert_KB_to_MB(OTHER_MEDIA_MAX_SIZE)}MB."
                )
        elif file_extension.lower() in [
            ".wav",
            ".mpeg",
            ".mp3",
            ".aac",
            ".aacp",
            ".ogg",
            ".webm",
            ".flac",
            ".m4a",
        ]:
            if file_size > OTHER_MEDIA_MAX_SIZE:
                raise GraphQLError(
                    f"Audio files must be under {self.convert_KB_to_MB(OTHER_MEDIA_MAX_SIZE)}MB."
                )
        elif file_extension.lower() in [".mp4", ".webm", ".opgg", ".3gp", ".flv"]:
            if file_size > VIDEO_MAX_SIZE:
                raise GraphQLError(
                    f"Video files must be under {self.convert_KB_to_MB(VIDEO_MAX_SIZE)}MB."
                )
        else:
            raise GraphQLError("Unsupported file format.")

    def upload_file(
        self,
        base64: str,
        file_name: str,
        absolute_path: str,
        storage_path: str,
        sub_path: str,
    ) -> str:
        filename, file_extension = os.path.splitext(os.path.basename(file_name or ""))
        unique_filename = uuid.uuid4().hex + filename + file_extension
        root = os.path.join(absolute_path, storage_path) if absolute_path else storage_path
        # `sub_path` is the media-type folder and ultimately comes from GraphQL
        # input (validate_asset_type); confine it to the uploads root so it can
        # never create or write directories outside it.
        media_directory = safe_join(root, sub_path)

        # exist_ok, not check-then-create: uploads run concurrently in worker
        # threads, and two first uploads would race between the check and
        # the mkdir (FileExistsError).
        os.makedirs(media_directory, exist_ok=True)
        # Decode once; the old path decoded the same payload a second time in
        # write_file (twice the memory for a 500 MB upload).
        file_data = decode_base64_payload(base64)
        self.validate_file_size(file_extension, len(file_data))

        self.write_bytes(file_data, os.path.join(media_directory, unique_filename))

        return os.path.join(sub_path, unique_filename)

    def write_bytes(self, data: bytes, path: str) -> None:
        with open(path, "wb") as fh:
            fh.write(data)

    def write_file(self, base64: str, path: str):
        self.write_bytes(decode_base64_payload(base64), path)

    def delete_file(self, path):
        # `path` may be None when a caller's safe-join rejected a stored
        # location (see helpers.paths.try_safe_join); nothing to delete then.
        if path and os.path.isfile(path):
            os.remove(path)

    def get_file_size(self, base64: str) -> int:
        return len(decode_base64_payload(base64))
