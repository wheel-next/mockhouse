# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import zipfile
from pathlib import Path


# ========================= MONKEY PATCHING PACKING ========================= #
"""Packaging needs to be monkey path in order to add `variant` support"""

import packaging.metadata as pmeta  # noqa: E402

pmeta._LIST_FIELDS.add("variants")
pmeta._EMAIL_TO_RAW_MAPPING["variant"] = "variants"
pmeta._RAW_TO_EMAIL_MAPPING["variants"] = "variant"


pmeta.RawMetadata.variants: list[str]  # type: ignore


class MetadataMeta(type):
    def __new__(mcs, name, bases, namespace):
        # for k, v in inspect.getmembers(original_class):
        for k, v in vars(pmeta.Metadata).items():
            if callable(v) or isinstance(v, classmethod) or k.startswith('__'):
                continue
            namespace[k] = v
        return super().__new__(mcs, name, bases, namespace)


# Define the Metadata class with the metaclass
class Metadata(pmeta.Metadata, metaclass=MetadataMeta):
    """Variants-Augmented Metadata Representation."""
    
    # Define additional attributes
    variants: pmeta._Validator[list[str] | None] = pmeta._Validator(added="2.1")


class NoMetadataError(Exception):
    pass


def parse_metadata_file_content(content: bytes | None) -> Metadata:
    # We prefer to parse metadata from the content, which will typically come
    # from extracting a METADATA or PKG-INFO file from an artifact.
    if content is not None:
        return Metadata.from_email(content, validate=True)
    
    # If we don't have contents or form data, then we don't have any metadata
    # and the only thing we can do is error.
    raise NoMetadataError


def wheel_to_metadata_dict(wheelpath: Path) -> dict:
    with zipfile.ZipFile(wheelpath, 'r') as whl:
        # Locate the METADATA file within the wheel package
        metadata_file = next(
            (f for f in whl.namelist() if f.endswith("METADATA")), None
        )

        if metadata_file:
            with whl.open(metadata_file) as f:
                metadata_content = f.read()
                # Parse the content to a dictionary
                return parse_metadata_file_content(metadata_content)._raw
        else:
            raise FileNotFoundError("No METADATA file found in this wheel package.")


if __name__ == "__main__":

    import pprint

    for wheel_file in [
        "dummy_project-0.0.1.dev1-py3-none-any.whl",
        "dummy_project-0.0.1.dev1-1-py3-none-any.whl"
    ]:
        metadata_dict = wheel_to_metadata_dict(wheelpath=Path("artifact_generator/dist") / wheel_file)

        print("\n---------------------------------\n")
        pprint.pprint(metadata_dict)
