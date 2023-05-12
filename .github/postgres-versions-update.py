#
# Copyright The CloudNativePG Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import re
import pprint
import urllib.request
import json
from packaging import version
from subprocess import check_output

min_supported_major = 11

pg_repo_name = "cloudnative-pg/postgresql"
pg_version_re = re.compile(r"^(\d+)(?:\.\d+|beta\d+|rc\d+|alpha\d+)(-\d+)?$")
pg_versions_file = ".github/pg_versions.json"


def get_json(repo_name):
    data = check_output(
        [
            "docker",
            "run",
            "--rm",
            "quay.io/skopeo/stable",
            "list-tags",
            f"docker://ghcr.io/{pg_repo_name}",
        ]
    )
    return json.loads(data.decode("utf-8"))


def is_pre_release(v):
    return version.Version(v).is_prerelease


def write_json(repo_url, version_re, output_file):
    repo_json = get_json(repo_url)
    tags = repo_json["Tags"]

    # Filter out all the tags which do not match the version regexp
    tags = [item for item in tags if version_re.search(item)]

    # Sort the tags according to semantic versioning
    tags.sort(key=version.Version, reverse=True)

    results = {}
    extra_results = {}
    for item in tags:
        match = version_re.search(item)
        if not match:
            continue

        major = match.group(1)

        # Skip too old versions
        if int(major) < min_supported_major:
            continue

        if extra := match.group(2):
            if major not in extra_results:
                extra_results[major] = item

        elif major not in results:
            results[major] = [item]
        elif len(results[major]) < 2:
            results[major].append(item)
    # If there are not enough version without '-` inside we add the one we kept
    for major, value in results.items():
        if len(value) < 2:
            results[major].append(extra_results[major])
        elif is_pre_release(results[major][0]) or is_pre_release(results[major][1]):
            results[major] = [results[major][0], extra_results[major]]

    with open(output_file, "w") as json_file:
        json.dump(results, json_file, indent=2)


if __name__ == "__main__":
    # PostgreSQL JSON file generator with Versions like x.y
    write_json(pg_repo_name, pg_version_re, pg_versions_file)
