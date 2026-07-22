#!/usr/bin/env python3
"""Validate and consume the unpublished React Luau Wally package family."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unicodedata
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SET_PATH = REPOSITORY_ROOT / "wally-package-set.toml"
MULTIPACK_PATH = REPOSITORY_ROOT / "multipack.toml"
CONSUMER_FIXTURE = REPOSITORY_ROOT / "tests" / "wally-consumer"
POST_PUBLISH_CONSUMER = REPOSITORY_ROOT / "modules" / "example-app" / "wally.toml"
REACT_VERSION_PATH = REPOSITORY_ROOT / "modules" / "shared" / "src" / "ReactVersion.lua"
EXPECTED_MEMBERS = (
	("modules/react-globals", "paradoxum/react-globals", "ReactGlobals"),
	("modules/shared", "paradoxum/react-shared", "Shared"),
	("modules/react", "paradoxum/react", "React"),
	("modules/scheduler", "paradoxum/react-scheduler", "Scheduler"),
	("modules/react-is", "paradoxum/react-is", "ReactIs"),
	("modules/react-reconciler", "paradoxum/react-reconciler", "ReactReconciler"),
	("modules/react-roblox", "paradoxum/react-roblox", "ReactRoblox"),
	("modules/react-test-renderer", "paradoxum/react-test-renderer", "ReactTestRenderer"),
	("modules/roact-compat", "paradoxum/roact-compat", "RoactCompat"),
)
PACKAGE_SPEC = re.compile(
	r"^(?P<scope>[a-z0-9-]+)/(?P<name>[a-z0-9-]+)@=(?P<version>[^\s]+)$"
)
FORBIDDEN_PARTS = {"__tests__", "__snapshots__"}
FORBIDDEN_FILES = {"rotriever.toml", ".robloxrc"}
FORBIDDEN_SUFFIXES = (
	".spec.lua",
	".test.lua",
	".snap.lua",
	".spec.luau",
	".test.luau",
	".snap.luau",
)
REQUIRED_FILES = {
	"default.project.json",
	"LICENSE",
	"README.md",
	"wally.toml",
}
ALLOWED_ROOTS = REQUIRED_FILES | {"src"}
WINDOWS_RESERVED_NAMES = {"con", "prn", "aux", "nul"} | {
	f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


class ValidationError(RuntimeError):
	pass


def load_toml(path: Path) -> dict:
	with path.open("rb") as handle:
		return tomllib.load(handle)


def run(command: list[str], *, cwd: Path = REPOSITORY_ROOT) -> str:
	result = subprocess.run(
		command,
		cwd=cwd,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		check=False,
	)
	if result.returncode != 0:
		details = "\n".join(
			part.rstrip()
			for part in (result.stdout, result.stderr)
			if part.strip()
		)
		raise ValidationError(
			f"Command failed ({result.returncode}): {' '.join(command)}"
			+ (f"\n{details}" if details else "")
		)
	return result.stdout


def normalize_archive_path(raw_path: str) -> str:
	path = raw_path.replace("\\", "/")
	while path.startswith("./"):
		path = path[2:]
	return path.rstrip("/")


def canonical_archive_path(member_name: str, path: str) -> str:
	pure_path = PurePosixPath(path)
	if pure_path.is_absolute() or ".." in pure_path.parts:
		raise ValidationError(f"{member_name} archive has unsafe path: {path}")
	if pure_path.as_posix() != path:
		raise ValidationError(f"{member_name} archive has noncanonical path: {path}")

	canonical_parts: list[str] = []
	for part in pure_path.parts:
		if ":" in part or part.rstrip(" .") != part:
			raise ValidationError(f"{member_name} archive has nonportable path: {path}")
		stem = part.split(".", 1)[0].casefold()
		if stem in WINDOWS_RESERVED_NAMES:
			raise ValidationError(f"{member_name} archive has reserved path: {path}")
		canonical_parts.append(unicodedata.normalize("NFC", part).casefold())
	return "/".join(canonical_parts)


def validate_unique_archive_paths(member_name: str, paths: list[str]) -> None:
	seen: dict[str, str] = {}
	for path in paths:
		canonical = canonical_archive_path(member_name, path)
		previous = seen.get(canonical)
		if previous is not None:
			raise ValidationError(
				f"{member_name} archive has colliding paths: {previous!r}, {path!r}"
			)
		seen[canonical] = path


def is_regular_zip_file(info: zipfile.ZipInfo) -> bool:
	if info.is_dir():
		return False
	if info.create_system != 3:
		return True
	mode = info.external_attr >> 16
	return mode == 0 or stat.S_ISREG(mode)


def parse_spec(spec: str) -> tuple[str, str, str]:
	match = PACKAGE_SPEC.fullmatch(spec)
	if match is None:
		raise ValidationError(f"Dependency is not exactly pinned: {spec}")
	return match.group("scope"), match.group("name"), match.group("version")


def coordinate(scope: str, name: str, version: str) -> str:
	return f"{scope}_{name}@{version}"


def is_forbidden_archive_path(path: str) -> bool:
	parts = PurePosixPath(path).parts
	filename = parts[-1] if parts else ""
	return bool(
		FORBIDDEN_PARTS.intersection(parts)
		or filename in FORBIDDEN_FILES
		or filename.endswith(FORBIDDEN_SUFFIXES)
	)


def validate_archive_paths(
	member_name: str,
	paths: set[str],
	*,
	regular_files: set[str] | None = None,
) -> None:
	required_paths = paths if regular_files is None else regular_files
	missing = REQUIRED_FILES - required_paths
	if missing:
		raise ValidationError(
			f"{member_name} archive is missing: {', '.join(sorted(missing))}"
		)
	if not {"src/init.lua", "src/init.luau"}.intersection(required_paths):
		raise ValidationError(f"{member_name} archive has no runtime entrypoint")

	for path in paths:
		parts = PurePosixPath(path).parts
		if parts and parts[0] not in ALLOWED_ROOTS:
			raise ValidationError(f"{member_name} ships unexpected path: {path}")
		if is_forbidden_archive_path(path):
			raise ValidationError(f"{member_name} ships test/development path: {path}")


def validate_source_inventory(
	member_name: str,
	member_path: Path,
	archive_paths: set[str],
) -> None:
	expected_runtime_files = {
		path.relative_to(member_path).as_posix()
		for path in (member_path / "src").rglob("*")
		if path.is_file()
		and not is_forbidden_archive_path(path.relative_to(member_path).as_posix())
	}
	missing = expected_runtime_files - archive_paths
	if missing:
		raise ValidationError(
			f"{member_name} archive omits runtime source: {', '.join(sorted(missing))}"
		)


def extract_zip_safely(archive: Path, destination: Path) -> set[str]:
	paths: set[str] = set()
	destination_resolved = destination.resolve()
	with zipfile.ZipFile(archive) as package:
		for info in package.infolist():
			path = normalize_archive_path(info.filename)
			if not path:
				continue
			pure_path = PurePosixPath(path)
			if pure_path.is_absolute() or ".." in pure_path.parts:
				raise ValidationError(f"Unsafe archive path: {info.filename}")
			target = (destination / Path(*pure_path.parts)).resolve()
			if target != destination_resolved and destination_resolved not in target.parents:
				raise ValidationError(f"Archive path escapes destination: {info.filename}")
			paths.add(path)
			if info.is_dir():
				target.mkdir(parents=True, exist_ok=True)
			else:
				target.parent.mkdir(parents=True, exist_ok=True)
				with package.open(info) as source, target.open("wb") as output:
					shutil.copyfileobj(source, output)
	return paths


def write_alias(path: Path, source: str) -> None:
	if path.exists():
		raise ValidationError(f"Alias collision: {path}")
	path.write_text(source + "\n", encoding="utf-8", newline="\n")


def validate_manifests() -> tuple[dict, list[dict], dict[str, dict]]:
	package_set_document = load_toml(PACKAGE_SET_PATH)
	package_set = package_set_document["package_set"]
	members = package_set_document["members"]
	member_by_name = {member["name"]: member for member in members}
	member_by_alias = {member["alias"]: member for member in members}
	actual_members = tuple(
		(member["path"], member["name"], member["alias"])
		for member in members
	)

	if actual_members != EXPECTED_MEMBERS:
		raise ValidationError("Package set must contain the approved nine members in order")
	if len(member_by_name) != len(members) or len(member_by_alias) != len(members):
		raise ValidationError("Package-set names and aliases must be unique")
	if package_set.get("private") is not True:
		raise ValidationError("Staged package set must remain private")

	version_source = REACT_VERSION_PATH.read_text(encoding="utf-8")
	version_matches = re.findall(r'^return "([^"]+)"$', version_source, re.MULTILINE)
	if version_matches != [package_set["version"]]:
		raise ValidationError(
			"Shared.ReactVersion must exactly match the Wally package-set version"
		)

	manifests: dict[str, dict] = {}
	order = {member["name"]: index for index, member in enumerate(members)}
	external_dependencies: dict[str, str] = {}
	root_license = (REPOSITORY_ROOT / package_set["license_file"]).read_text(
		encoding="utf-8"
	).replace("\r\n", "\n")

	for member in members:
		member_path = REPOSITORY_ROOT / member["path"]
		manifest_path = member_path / "wally.toml"
		manifest = load_toml(manifest_path)
		manifests[member["name"]] = manifest
		package = manifest["package"]

		expected = {
			"name": member["name"],
			"version": package_set["version"],
			"registry": package_set["registry"],
			"repository": package_set["repository"],
			"realm": "shared",
			"license": "MIT",
			"authors": package_set["authors"],
			"private": True,
		}
		for key, value in expected.items():
			if package.get(key) != value:
				raise ValidationError(
					f"{manifest_path}: package.{key} must be {value!r}"
				)

		license_path = member_path / "LICENSE"
		member_license = (
			license_path.read_text(encoding="utf-8").replace("\r\n", "\n")
			if license_path.exists()
			else None
		)
		if member_license != root_license:
			raise ValidationError(f"{member['name']} LICENSE differs from root LICENSE")

		project = json.loads((member_path / "default.project.json").read_text("utf-8"))
		short_name = member["name"].split("/", 1)[1]
		if project != {"name": short_name, "tree": {"$path": "src"}}:
			raise ValidationError(
				f"{member['name']} project must map {short_name!r} directly to src"
			)

		for section in ("server-dependencies", "dev-dependencies"):
			if manifest.get(section):
				raise ValidationError(
					f"{member['name']} published manifest must not use [{section}]"
				)

		expected_dependencies = member["dependencies"]
		actual_dependencies = manifest.get("dependencies", {})
		if actual_dependencies != expected_dependencies:
			raise ValidationError(
				f"{member['name']} dependencies differ from wally-package-set.toml"
			)

		for alias, spec in actual_dependencies.items():
			scope, dependency_name, version = parse_spec(spec)
			full_name = f"{scope}/{dependency_name}"
			if full_name in member_by_name:
				dependency = member_by_name[full_name]
				if alias != dependency["alias"]:
					raise ValidationError(
						f"{member['name']} aliases {full_name} as {alias}, "
						f"expected {dependency['alias']}"
					)
				if version != package_set["version"]:
					raise ValidationError(
						f"{member['name']} does not lock {full_name} "
						f"to {package_set['version']}"
					)
				if order[full_name] >= order[member["name"]]:
					raise ValidationError(
						f"Package-set order is not topological: "
						f"{member['name']} depends on {full_name}"
					)
			else:
				previous = external_dependencies.get(alias)
				if previous is not None and previous != spec:
					raise ValidationError(
						f"External dependency alias {alias} has conflicting pins"
					)
				external_dependencies[alias] = spec

	consumer_manifest = load_toml(CONSUMER_FIXTURE / "wally.toml")
	consumer_package = consumer_manifest["package"]
	if consumer_package.get("private") is not True:
		raise ValidationError("Unpublished consumer fixture must remain private")
	if consumer_package.get("registry") != package_set["registry"]:
		raise ValidationError("Unpublished consumer fixture uses the wrong registry")
	if consumer_manifest.get("dependencies", {}) != external_dependencies:
		raise ValidationError(
			"Unpublished consumer dependencies must equal all external runtime dependencies"
		)

	expected_post_publish_dependencies = {
		member["alias"]: f"{member['name']}@={package_set['version']}"
		for member in members
	}
	post_publish_manifest = load_toml(POST_PUBLISH_CONSUMER)
	post_publish_package = post_publish_manifest["package"]
	if post_publish_package.get("private") is not True:
		raise ValidationError("Post-publish consumer must remain private")
	if post_publish_package.get("registry") != package_set["registry"]:
		raise ValidationError("Post-publish consumer uses the wrong registry")
	if post_publish_manifest.get("dependencies", {}) != expected_post_publish_dependencies:
		raise ValidationError("Post-publish consumer must pin all nine package members")

	multipack = load_toml(MULTIPACK_PATH)
	for destination in ("rotriever", "rbx_creator_store", "wally"):
		if multipack.get(destination, {}).get("publish_to") is not False:
			raise ValidationError(
				f"Multipack destination {destination} must remain disabled during staging"
			)
	expected_member_paths = [member["path"] for member in members]
	if multipack["wally"].get("members") != expected_member_paths:
		raise ValidationError("Multipack Wally members differ from the package set")

	return package_set, members, manifests


def package_members(
	members: list[dict],
	archives_directory: Path,
) -> dict[str, Path]:
	archives: dict[str, Path] = {}
	for index, member in enumerate(members, start=1):
		member_path = REPOSITORY_ROOT / member["path"]
		listing = run(
			[
				"wally",
				"package",
				"--list",
				"--output",
				os.devnull,
			],
			cwd=member_path,
		)
		listed_path_list = [
			normalize_archive_path(line)
			for line in listing.splitlines()
			if normalize_archive_path(line)
		]
		validate_unique_archive_paths(member["name"], listed_path_list)
		listed_paths = set(listed_path_list)
		validate_archive_paths(member["name"], listed_paths)
		validate_source_inventory(member["name"], member_path, listed_paths)

		archive = archives_directory / f"{index:02d}-{member['alias']}.zip"
		run(
			[
				"wally",
				"package",
				"--output",
				str(archive),
			],
			cwd=member_path,
		)
		with zipfile.ZipFile(archive) as package:
			entries = [
				(info, normalize_archive_path(info.filename))
				for info in package.infolist()
				if normalize_archive_path(info.filename)
			]
		actual_path_list = [path for _, path in entries]
		validate_unique_archive_paths(member["name"], actual_path_list)
		special_files = [
			path
			for info, path in entries
			if not info.is_dir() and not is_regular_zip_file(info)
		]
		if special_files:
			raise ValidationError(f"{member['name']} ships special files: {special_files}")
		actual_paths = set(actual_path_list)
		actual_files = {
			path
			for info, path in entries
			if is_regular_zip_file(info)
		}
		validate_archive_paths(
			member["name"],
			actual_paths,
			regular_files=actual_files,
		)
		validate_source_inventory(member["name"], member_path, actual_files)
		if listed_paths != actual_paths:
			raise ValidationError(
				f"{member['name']} list output differs from packaged ZIP contents"
			)
		archives[member["name"]] = archive
		print(f"validated {member['name']} ({len(actual_paths)} archive paths)")
	return archives


def assemble_consumer(
	package_set: dict,
	members: list[dict],
	manifests: dict[str, dict],
	archives: dict[str, Path],
	working_directory: Path,
	runtime_place_output: Path | None,
	runtime_marker: str | None,
) -> None:
	consumer = working_directory / "consumer"
	shutil.copytree(
		CONSUMER_FIXTURE,
		consumer,
		ignore=shutil.ignore_patterns("Packages", ".staging", ".artifacts"),
	)
	if runtime_marker is not None:
		(consumer / "runtime-marker.lua").write_text(
			f"return {json.dumps(runtime_marker)}\n",
			encoding="utf-8",
		)
	expected_lock = (CONSUMER_FIXTURE / "wally.lock").read_bytes()
	run(["wally", "install", "--project-path", str(consumer)])
	actual_lock = (consumer / "wally.lock").read_bytes()
	if actual_lock != expected_lock:
		raise ValidationError(
			"Consumer wally.lock is stale; run wally install in "
			"tests/wally-consumer and review the lock diff"
		)

	packages = consumer / "Packages"
	index = packages / "_Index"
	index.mkdir(parents=True, exist_ok=True)
	version = package_set["version"]

	for member in members:
		scope, short_name = member["name"].split("/", 1)
		member_coordinate = coordinate(scope, short_name, version)
		coordinate_directory = index / member_coordinate
		package_directory = coordinate_directory / short_name
		package_directory.mkdir(parents=True, exist_ok=False)
		extracted_paths = extract_zip_safely(
			archives[member["name"]],
			package_directory,
		)
		validate_archive_paths(member["name"], extracted_paths)

		manifest = manifests[member["name"]]
		for alias, spec in manifest.get("dependencies", {}).items():
			dependency_scope, dependency_name, dependency_version = parse_spec(spec)
			dependency_coordinate = coordinate(
				dependency_scope,
				dependency_name,
				dependency_version,
			)
			write_alias(
				coordinate_directory / f"{alias}.lua",
				"return require("
				f'script.Parent.Parent["{dependency_coordinate}"]'
				f'["{dependency_name}"])',
			)

		write_alias(
			packages / f"{member['alias']}.lua",
			"return require("
			f'script.Parent._Index["{member_coordinate}"]["{short_name}"])',
		)

	for member in members:
		for alias, spec in manifests[member["name"]].get("dependencies", {}).items():
			dependency_scope, dependency_name, dependency_version = parse_spec(spec)
			dependency_target = (
				index
				/ coordinate(dependency_scope, dependency_name, dependency_version)
				/ dependency_name
			)
			if not dependency_target.exists():
				raise ValidationError(
					f"{member['name']} alias {alias} has no target: {dependency_target}"
				)

		member_scope, member_name = member["name"].split("/", 1)
		member_target = index / coordinate(member_scope, member_name, version) / member_name
		if not member_target.exists():
			raise ValidationError(f"Consumer alias has no target: {member['alias']}")

	sourcemap = working_directory / "consumer-sourcemap.json"
	artifact = (
		runtime_place_output
		if runtime_place_output is not None
		else working_directory / "consumer.rbxm"
	)
	project = consumer / "default.project.json"
	run(
		[
			"rojo",
			"sourcemap",
			str(project),
			"--output",
			str(sourcemap),
		],
	)
	run(
		[
			"rojo",
			"build",
			str(project),
			"--output",
			str(artifact),
		],
	)
	if not artifact.is_file() or artifact.stat().st_size == 0:
		raise ValidationError(f"Rojo did not create a nonempty artifact: {artifact}")
	print("validated unpublished consumer install, sourcemap, and Rojo build")
	if runtime_place_output is not None:
		print(f"built exact unpublished consumer place: {runtime_place_output}")


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--packages-only",
		action="store_true",
		help="validate package manifests and ZIPs without installing the consumer",
	)
	parser.add_argument(
		"--runtime-place-output",
		type=Path,
		help=(
			"build the validated unpublished consumer as a persistent .rbxl "
			"for an external runtime entrypoint"
		),
	)
	parser.add_argument(
		"--runtime-marker",
		help=(
			"embed a unique non-secret marker in --runtime-place-output for "
			"runtime identity attestation"
		),
	)
	arguments = parser.parse_args()

	try:
		if arguments.packages_only and (
			arguments.runtime_place_output is not None
			or arguments.runtime_marker is not None
		):
			raise ValidationError(
				"--packages-only cannot be combined with runtime artifact options"
			)
		runtime_place_output = arguments.runtime_place_output
		runtime_marker = arguments.runtime_marker
		if (runtime_place_output is None) != (runtime_marker is None):
			raise ValidationError(
				"--runtime-place-output and --runtime-marker must be used together"
		)
		if runtime_marker is not None and re.fullmatch(
			r"[A-Za-z0-9._-]{1,160}", runtime_marker
		) is None:
			raise ValidationError(
				"--runtime-marker must be 1-160 safe, non-secret characters"
			)
		if runtime_place_output is not None:
			if not runtime_place_output.is_absolute():
				runtime_place_output = REPOSITORY_ROOT / runtime_place_output
			runtime_place_output = runtime_place_output.resolve()
			if runtime_place_output.suffix.lower() != ".rbxl":
				raise ValidationError("--runtime-place-output must end in .rbxl")
			runtime_place_output.parent.mkdir(parents=True, exist_ok=True)

		package_set, members, manifests = validate_manifests()
		with tempfile.TemporaryDirectory(prefix="react-luau-wally-") as temp:
			working_directory = Path(temp)
			archives_directory = working_directory / "archives"
			archives_directory.mkdir()
			archives = package_members(members, archives_directory)
			if not arguments.packages_only:
				assemble_consumer(
					package_set,
					members,
					manifests,
					archives,
					working_directory,
					runtime_place_output,
					runtime_marker,
				)
	except (OSError, KeyError, ValueError, ValidationError, zipfile.BadZipFile) as error:
		print(f"error: {error}", file=sys.stderr)
		return 1

	print("Wally package family validation passed")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
