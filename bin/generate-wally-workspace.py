#!/usr/bin/env python3
"""Validate and generate the reduced Wally source-test workspace."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROOT_MANIFEST_PATH = REPOSITORY_ROOT / "rotriever.toml"
WORKSPACE_DIRECTORY = REPOSITORY_ROOT / "tests" / "wally-workspace"
POLICY_PATH = WORKSPACE_DIRECTORY / "workspace.toml"
MANIFEST_PATH = WORKSPACE_DIRECTORY / "wally.toml"
INVENTORY_PATH = WORKSPACE_DIRECTORY / "test-inventory.txt"
PACKAGE_SET_PATH = REPOSITORY_ROOT / "wally-package-set.toml"
TEST_FILE = re.compile(r"\.(?:spec|test)\.(?:lua|luau)$")
WALLY_SPEC = re.compile(
	r"^[a-z0-9-]+/[a-z0-9-]+@=[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$"
)
LUA_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
EXPECTED_DEVELOPER_TOOLS = "github.com/Roblox/developer-tools@=0.2.3"
EXPECTED_BENCHMARK_DEPENDENCY = {
	"git": "https://github.com/Roblox/roact-performance-benchmarks",
	"rev": "main",
}
EXPECTED_JEST_CONFIG_SHA256 = {
	"WorkspaceStatic/jest.config.lua": (
		"c517476d408f83c5bd2f03be857402114e8b989db793146ad69572ecae6d6534"
	),
	"modules/react-devtools-shared/src/jest.config.lua": (
		"f6c5b02885a090fa277212f0b4dd17e0d0ca0ba5e375a1421f36040c85c96e21"
	),
}
EXPECTED_BLOCKER_SHA256 = {
	"modules/react-devtools-extensions/rotriever.toml": (
		"eecdf631ffd0722c44e8b895ec05093c61521e71a33add7bebdc8649d436478a"
	),
	"modules/react-devtools-extensions/src/__tests__/devtools-integration.roblox.spec.lua": (
		"e2ffdefe1c5b636c6a1dc924aa965e0e9632795a237b9157842cb19971c9b5b7"
	),
}


class WorkspaceError(RuntimeError):
	pass


def load_toml(path: Path) -> dict:
	with path.open("rb") as handle:
		return tomllib.load(handle)


def repository_path(path: Path) -> str:
	return path.relative_to(REPOSITORY_ROOT).as_posix()


def require_unique_strings(document: dict, key: str) -> list[str]:
	values = document.get(key)
	if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
		raise WorkspaceError(f"workspace.{key} must be an array of strings")
	if len(values) != len(set(values)):
		raise WorkspaceError(f"workspace.{key} contains duplicates")
	return values


def require_string_table(document: dict, key: str) -> dict[str, str]:
	values = document.get(key)
	if not isinstance(values, dict) or not all(
		isinstance(name, str)
		and bool(name)
		and isinstance(value, str)
		and bool(value)
		for name, value in values.items()
	):
		raise WorkspaceError(f"[{key}] must map nonempty strings to nonempty strings")
	return values


def require_omission_table(document: dict) -> dict[str, list[str]]:
	values = document.get("omitted_dev_dependencies", {})
	if not isinstance(values, dict):
		raise WorkspaceError("[omitted_dev_dependencies] must be a table")
	for name, aliases in values.items():
		if (
			not isinstance(name, str)
			or not isinstance(aliases, list)
			or not all(isinstance(alias, str) and alias for alias in aliases)
			or len(aliases) != len(set(aliases))
		):
			raise WorkspaceError(
				"omitted_dev_dependencies values must be unique string arrays"
			)
	return values


def load_manifests() -> tuple[dict[str, dict], dict[Path, str], dict[str, Path]]:
	manifests: dict[str, dict] = {}
	name_by_directory: dict[Path, str] = {}
	directory_by_name: dict[str, Path] = {}
	for manifest_path in sorted((REPOSITORY_ROOT / "modules").glob("*/rotriever.toml")):
		document = load_toml(manifest_path)
		name = document.get("package", {}).get("name")
		if not isinstance(name, str) or not name:
			raise WorkspaceError(f"{repository_path(manifest_path)} has no package.name")
		if name in manifests:
			raise WorkspaceError(f"duplicate Rotriever package name: {name}")
		directory = manifest_path.parent.resolve()
		manifests[name] = document
		name_by_directory[directory] = name
		directory_by_name[name] = directory
	return manifests, name_by_directory, directory_by_name


def read_inventory() -> list[str]:
	paths = [
		line.strip()
		for line in INVENTORY_PATH.read_text(encoding="utf-8").splitlines()
		if line.strip() and not line.lstrip().startswith("#")
	]
	if len(paths) != len(set(paths)):
		raise WorkspaceError("test-inventory.txt contains duplicates")
	return paths


def discover_test_named_files() -> set[str]:
	paths: set[str] = set()
	for root in (REPOSITORY_ROOT / "modules", REPOSITORY_ROOT / "WorkspaceStatic"):
		for path in root.rglob("*"):
			if path.is_file() and TEST_FILE.search(path.name):
				paths.add(repository_path(path))
	return paths


def format_difference(label: str, values: set[str]) -> str:
	return f"{label}:\n  " + "\n  ".join(sorted(values))


def validate_test_inventory(
	policy: dict,
	included: set[str],
	directory_by_name: dict[str, Path],
) -> None:
	inventory = read_inventory()
	expected_count = policy.get("expected_suite_count")
	if len(inventory) != expected_count:
		raise WorkspaceError(
			f"test inventory has {len(inventory)} suites; expected {expected_count}"
		)

	blocked_suite = policy.get("blocked_suite")
	nonsuite = policy.get("nonsuite_test_module")
	if not isinstance(blocked_suite, str) or not isinstance(nonsuite, str):
		raise WorkspaceError("blocked_suite and nonsuite_test_module must be paths")
	expected_named_files = set(inventory) | {blocked_suite, nonsuite}
	actual_named_files = discover_test_named_files()
	if actual_named_files != expected_named_files:
		parts = []
		if actual_named_files - expected_named_files:
			parts.append(
				format_difference(
					"unclassified test-named files",
					actual_named_files - expected_named_files,
				)
			)
		if expected_named_files - actual_named_files:
			parts.append(
				format_difference(
					"missing classified test-named files",
					expected_named_files - actual_named_files,
				)
			)
		raise WorkspaceError("\n".join(parts))

	module_prefixes = {
		name: repository_path(directory) + "/"
		for name, directory in directory_by_name.items()
	}
	counts: Counter[str] = Counter()
	for relative_path in inventory:
		absolute_path = REPOSITORY_ROOT / relative_path
		if not absolute_path.is_file():
			raise WorkspaceError(f"inventory path does not exist: {relative_path}")
		owner = (
			"WorkspaceStatic"
			if relative_path.startswith("WorkspaceStatic/")
			else next(
				(
					name
					for name, prefix in module_prefixes.items()
					if relative_path.startswith(prefix)
				),
				None,
			)
		)
		if owner not in included and owner != "WorkspaceStatic":
			raise WorkspaceError(f"suite is outside the included workspace: {relative_path}")
		if "/__tests__/" not in relative_path and not relative_path.startswith(
			"modules/react-devtools-shared/"
		):
			raise WorkspaceError(
				f"suite does not match current Jest discovery: {relative_path}"
			)
		counts[owner] += 1

	expected_counts = policy.get("suite_counts")
	if not isinstance(expected_counts, dict):
		raise WorkspaceError("[suite_counts] is required")
	actual_counts = {name: counts[name] for name in expected_counts}
	if actual_counts != expected_counts:
		raise WorkspaceError(
			f"suite ownership counts changed: expected {expected_counts}, "
			f"got {actual_counts}"
		)
	if set(expected_counts) != included | {"WorkspaceStatic"}:
		raise WorkspaceError("suite_counts must classify every included module")

	config_sources: dict[str, str] = {}
	for relative_path, expected_hash in EXPECTED_JEST_CONFIG_SHA256.items():
		source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
		canonical_source = source.replace("\r\n", "\n").replace("\r", "\n")
		actual_hash = hashlib.sha256(canonical_source.encode("utf-8")).hexdigest()
		if actual_hash != expected_hash:
			raise WorkspaceError(
				f"{relative_path} changed; review Jest discovery and refresh "
				"the suite inventory and expected config hash"
			)
		config_sources[relative_path] = canonical_source

	root_config_source = config_sources["WorkspaceStatic/jest.config.lua"]
	devtools_config_source = config_sources[
		"modules/react-devtools-shared/src/jest.config.lua"
	]
	root_config = "\n".join(
		line.split("--", 1)[0] for line in root_config_source.splitlines()
	)
	devtools_config = "\n".join(
		line.split("--", 1)[0] for line in devtools_config_source.splitlines()
	)
	required_root_topology = {
		"root project": r"local\s+allProjects\s*=\s*{\s*Workspace\s*}",
		"ReactDevtoolsShared project": (
			r"projectsWithCustomJestConfig\s*=\s*{\s*"
			r"Workspace\.ReactDevtoolsShared\.ReactDevtoolsShared\s*,?\s*}"
		),
		"custom-project insertion": (
			r"table\.insert\(\s*allProjects\s*,\s*project\s*\)"
		),
		"custom-project ignore": (
			r"table\.insert\(\s*testPathIgnorePatterns\s*,\s*"
			r"tostring\(\s*project\s*\)\s*\)"
		),
		"returned projects": r"projects\s*=\s*allProjects\s*,",
		"returned ignores": (
			r"testPathIgnorePatterns\s*=\s*testPathIgnorePatterns\s*,"
		),
		"root testMatch": re.escape('"**/__tests__/*.(spec|test)"'),
	}
	missing_topology = [
		label
		for label, pattern in required_root_topology.items()
		if re.search(pattern, root_config, re.DOTALL) is None
	]
	if missing_topology:
		raise WorkspaceError(
			"root Jest discovery topology changed: "
			+ ", ".join(missing_topology)
		)
	if re.search(
		re.escape('"**/*.(spec|test)"'), devtools_config
	) is None:
		raise WorkspaceError("ReactDevtoolsShared discovery pattern changed")


def classify_dependencies(
	name: str,
	document: dict,
	*,
	included: set[str],
	name_by_directory: dict[Path, str],
	directory_by_name: dict[str, Path],
	external_dependencies: dict[str, str],
	legacy_external_dependencies: dict[str, str],
	workspace_dependencies: dict[str, str],
	omitted: dict[str, list[str]],
	alias_targets: dict[str, str],
) -> tuple[list[str], list[str], set[str]]:
	sections: dict[str, list[str]] = {
		"dependencies": [],
		"dev_dependencies": [],
	}
	used_alias_targets: set[str] = set()
	for section_name in sections:
		for alias, value in document.get(section_name, {}).items():
			if alias in omitted.get(name, []):
				if not (
					name == "React"
					and section_name == "dev_dependencies"
					and alias == "PerformanceBenchmarks"
					and value == EXPECTED_BENCHMARK_DEPENDENCY
				):
					raise WorkspaceError(
						f"unexpected omitted dependency: {name}.{section_name}.{alias}"
					)
				continue

			target_name: str
			legacy_spec: str | None = None
			if isinstance(value, dict) and isinstance(value.get("path"), str):
				target_directory = (
					directory_by_name[name] / value["path"]
				).resolve()
				target_name = name_by_directory.get(target_directory, "")
				if not target_name:
					raise WorkspaceError(f"{name}.{alias} points outside known modules")
				if target_name not in included:
					raise WorkspaceError(
						f"{name}.{alias} escapes the core closure to {target_name}"
					)
			elif value == {"workspace": True}:
				target_name = alias
				legacy_spec = workspace_dependencies.get(alias)
				if not isinstance(legacy_spec, str):
					raise WorkspaceError(
						f"{name}.{alias} has no root workspace dependency"
					)
			elif isinstance(value, str):
				target_name = alias
				legacy_spec = value
			else:
				raise WorkspaceError(
					f"{name}.{section_name}.{alias} has an unsupported declaration"
				)

			if legacy_spec is not None:
				if alias not in external_dependencies:
					raise WorkspaceError(
						f"{name}.{alias} has no exact Wally replacement"
					)
				expected_legacy_spec = legacy_external_dependencies.get(alias)
				if legacy_spec != expected_legacy_spec:
					raise WorkspaceError(
						f"{name}.{alias} legacy dependency changed: "
						f"expected {expected_legacy_spec!r}, got {legacy_spec!r}"
					)

			if target_name != alias:
				if alias_targets.get(alias) != target_name:
					raise WorkspaceError(
						f"alias target is not declared: {alias} -> {target_name}"
					)
				used_alias_targets.add(alias)
			sections[section_name].append(alias)

	declared_omissions = set(omitted.get(name, []))
	actual_omissions = {
		alias
		for alias in document.get("dev_dependencies", {})
		if alias in declared_omissions
	}
	if actual_omissions != declared_omissions:
		raise WorkspaceError(f"stale omitted dependency policy for {name}")
	return (
		sections["dependencies"],
		sections["dev_dependencies"],
		used_alias_targets,
	)


def render_proxy(
	alias_targets: dict[str, str], source_keys: dict[str, str]
) -> str:
	lines = [
		"--!strict",
		"-- Generated by bin/generate-wally-workspace.py; do not edit by hand.",
		"local aliasTargets = {",
	]
	for alias, target in sorted(alias_targets.items()):
		lines.append(f'\t{alias} = "{target}",')
	lines.extend(
		[
			"}",
			"",
			"local sourceKeys = {",
			*[f'\t{name} = "{key}",' for name, key in sorted(source_keys.items())],
			"}",
			"",
			"local workspace: Instance? = script.Parent",
			'while workspace ~= nil and workspace.Name ~= "_Workspace" do',
			"\tworkspace = workspace.Parent",
			"end",
			"",
			"if workspace == nil then",
			'\terror("Dependency proxy " .. script:GetFullName() .. " is outside _Workspace")',
			"end",
			"",
			"local targetName = aliasTargets[script.Name] or script.Name",
			"local localWrapper = workspace:FindFirstChild(targetName)",
			"local target: Instance?",
			"",
			"if localWrapper ~= nil then",
			"\tlocal sourceName = sourceKeys[targetName] or targetName",
			"\ttarget = localWrapper:FindFirstChild(sourceName)",
			"else",
			"\tlocal packageRoot = workspace.Parent",
			"\tif packageRoot ~= nil then",
			"\t\ttarget = packageRoot:FindFirstChild(targetName)",
			"\tend",
			"end",
			"",
			'if target == nil or not target:IsA("ModuleScript") then',
			'\terror("Dependency proxy " .. script:GetFullName() .. " cannot resolve " .. targetName)',
			"end",
			"",
			"return require(target)",
			"",
		]
	)
	return "\n".join(lines)


def derive_source_keys(
	module_names: list[str],
	manifests: dict[str, dict],
	directory_by_name: dict[str, Path],
) -> dict[str, str]:
	overrides: dict[str, str] = {}
	for name in module_names:
		content_root = manifests[name].get("package", {}).get("content_root")
		if not isinstance(content_root, str):
			raise WorkspaceError(f"{name} has no package.content_root")
		project_path = directory_by_name[name] / "default.project.json"
		project = json.loads(project_path.read_text(encoding="utf-8"))
		tree = project.get("tree")
		if tree == {"$path": content_root}:
			source_key = name
		elif isinstance(tree, dict) and len(tree) == 1:
			source_key, mapping = next(iter(tree.items()))
			if (
				not isinstance(source_key, str)
				or mapping != {"$path": content_root}
			):
				raise WorkspaceError(
					f"{repository_path(project_path)} has an unsupported source tree"
				)
		else:
			raise WorkspaceError(
				f"{repository_path(project_path)} has an unsupported source tree"
			)
		if source_key != name:
			overrides[name] = source_key
	return overrides


def load_root_project_shape() -> tuple[str, str]:
	project_path = REPOSITORY_ROOT / "tests.project.json"
	project = json.loads(project_path.read_text(encoding="utf-8"))
	if set(project) != {"name", "tree"} or not isinstance(project["name"], str):
		raise WorkspaceError("tests.project.json root shape changed")
	tree = project["tree"]
	if (
		not isinstance(tree, dict)
		or set(tree) != {"$path", "_Workspace"}
		or not isinstance(tree["$path"], str)
	):
		raise WorkspaceError("tests.project.json tree shape changed")
	workspace = tree["_Workspace"]
	if (
		not isinstance(workspace, dict)
		or set(workspace) != {"$path"}
		or not isinstance(workspace["$path"], str)
	):
		raise WorkspaceError("tests.project.json _Workspace shape changed")
	return project["name"], workspace["$path"]


def build_project(
	module_names: list[str],
	manifests: dict[str, dict],
	directory_by_name: dict[str, Path],
	dependencies: dict[str, tuple[list[str], list[str]]],
	source_keys: dict[str, str],
	proxy_path: str,
	project_name: str,
	workspace_path: str,
) -> str:
	workspace: dict = {"$path": workspace_path}
	source_owners: dict[Path, str] = {}
	for name in sorted(module_names):
		document = manifests[name]
		content_root = document.get("package", {}).get("content_root")
		if not isinstance(content_root, str):
			raise WorkspaceError(f"{name} has no package.content_root")
		module_directory = directory_by_name[name].resolve()
		source_directory = (module_directory / content_root).resolve()
		if (
			source_directory != module_directory
			and module_directory not in source_directory.parents
		):
			raise WorkspaceError(f"{name} source mapping escapes its module")
		previous_owner = source_owners.get(source_directory)
		if previous_owner is not None:
			raise WorkspaceError(
				f"{name} and {previous_owner} map the same source root"
			)
		source_owners[source_directory] = name
		if not (source_directory / "init.lua").is_file() and not (
			source_directory / "init.luau"
		).is_file():
			raise WorkspaceError(f"{name} source mapping has no init module")

		source_key = source_keys.get(name, name)
		if not LUA_IDENTIFIER.fullmatch(source_key):
			raise WorkspaceError(f"{name} has an invalid source key: {source_key!r}")
		wrapper: dict = {
			"$className": "Folder",
			source_key: {"$path": repository_path(source_directory)},
		}
		runtime_aliases, dev_aliases = dependencies[name]
		if dev_aliases and (source_key == "Dev" or "Dev" in runtime_aliases):
			raise WorkspaceError(f"{name} dependency layout collides with Dev")
		for alias in sorted(runtime_aliases):
			if alias == source_key:
				raise WorkspaceError(
					f"{name} runtime alias collides with its source key"
				)
			wrapper[alias] = {"$path": proxy_path}
		if dev_aliases:
			wrapper["Dev"] = {
				"$className": "Folder",
				**{
					alias: {"$path": proxy_path}
					for alias in sorted(dev_aliases)
				},
			}
		workspace[name] = wrapper

	project = {
		"name": project_name,
		"tree": {
			"$path": "tests/wally-workspace/Packages",
			"_Workspace": workspace,
		},
	}
	return json.dumps(project, indent=2) + "\n"


def write_or_check(path: Path, expected: str, *, check: bool) -> None:
	if check:
		actual = path.read_text(encoding="utf-8") if path.is_file() else None
		if actual != expected:
			raise WorkspaceError(
				f"{repository_path(path)} is stale; run "
				"python bin/generate-wally-workspace.py"
			)
	else:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(expected, encoding="utf-8", newline="\n")


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--check",
		action="store_true",
		help="fail instead of updating generated files",
	)
	arguments = parser.parse_args()

	try:
		document = load_toml(POLICY_PATH)
		policy = document.get("workspace")
		if not isinstance(policy, dict):
			raise WorkspaceError("workspace.toml must contain [workspace]")
		published = require_unique_strings(policy, "published_modules")
		support = require_unique_strings(policy, "support_modules")
		excluded = require_unique_strings(policy, "excluded_modules")
		test_only_external_aliases = require_unique_strings(
			policy, "test_only_external_aliases"
		)
		included_names = published + support
		included = set(included_names)
		if len(included_names) != len(included):
			raise WorkspaceError("published_modules and support_modules overlap")
		if included.intersection(excluded):
			raise WorkspaceError("included and excluded module sets overlap")

		manifests, name_by_directory, directory_by_name = load_manifests()
		if set(manifests) != included | set(excluded):
			raise WorkspaceError(
				"workspace policy does not partition all module manifests"
			)

		package_set = load_toml(PACKAGE_SET_PATH)
		package_members = package_set.get("members")
		if not isinstance(package_members, list) or not all(
			isinstance(member, dict) for member in package_members
		):
			raise WorkspaceError("wally-package-set.toml members are invalid")
		published_aliases = [
			member.get("alias") for member in package_members
		]
		if published_aliases != published:
			raise WorkspaceError(
				"published_modules differs from wally-package-set.toml"
			)
		member_names = {member.get("name") for member in package_members}
		package_runtime_dependencies: dict[str, str] = {}
		for member in package_members:
			dependencies = member.get("dependencies", {})
			if not isinstance(dependencies, dict):
				raise WorkspaceError("package-set member dependencies are invalid")
			for alias, spec in dependencies.items():
				if not isinstance(alias, str) or not isinstance(spec, str):
					raise WorkspaceError("package-set dependencies must be strings")
				if WALLY_SPEC.fullmatch(spec) is None:
					raise WorkspaceError(f"package dependency is not pinned: {spec}")
				if spec.split("@=", 1)[0] not in member_names:
					previous = package_runtime_dependencies.get(alias)
					if previous is not None and previous != spec:
						raise WorkspaceError(
							f"package runtime alias {alias} has conflicting pins"
						)
					package_runtime_dependencies[alias] = spec

		external_dependencies = require_string_table(
			document, "external_dependencies"
		)
		legacy_external_dependencies = require_string_table(
			document, "legacy_external_dependencies"
		)
		alias_targets = require_string_table(document, "alias_targets")
		source_keys = require_string_table(document, "source_keys")
		omitted = require_omission_table(document)
		if set(legacy_external_dependencies) != set(external_dependencies):
			raise WorkspaceError(
				"legacy and Wally external dependency aliases differ"
			)
		for alias, spec in external_dependencies.items():
			if WALLY_SPEC.fullmatch(spec) is None:
				raise WorkspaceError(
					f"external dependency {alias} is not exactly pinned: {spec}"
				)
		actual_test_only_aliases = (
			set(external_dependencies) - set(package_runtime_dependencies)
		)
		if actual_test_only_aliases != set(test_only_external_aliases):
			raise WorkspaceError(
				"test-only external dependency aliases changed"
			)
		expected_runtime_dependencies = {
			alias: external_dependencies[alias]
			for alias in external_dependencies
			if alias not in actual_test_only_aliases
		}
		if package_runtime_dependencies != expected_runtime_dependencies:
			raise WorkspaceError(
				"source-workspace runtime pins differ from the Wally package set"
			)
		for table_name, values in (
			("alias_targets", alias_targets),
			("source_keys", source_keys),
		):
			for key, value in values.items():
				if (
					not LUA_IDENTIFIER.fullmatch(key)
					or not LUA_IDENTIFIER.fullmatch(value)
				):
					raise WorkspaceError(
						f"[{table_name}] must use Luau identifiers"
					)

		root_manifest = load_toml(ROOT_MANIFEST_PATH)
		workspace_dependencies = root_manifest.get("workspace", {}).get(
			"dependencies"
		)
		if not isinstance(workspace_dependencies, dict):
			raise WorkspaceError("root workspace dependencies are missing")

		fixture_manifest = load_toml(MANIFEST_PATH)
		if fixture_manifest.get("package", {}).get("private") is not True:
			raise WorkspaceError(
				"source workspace Wally package must remain private"
			)
		if fixture_manifest.get("dependencies") != external_dependencies:
			raise WorkspaceError(
				"workspace Wally dependencies differ from policy"
			)
		for section in ("dev-dependencies", "server-dependencies"):
			if fixture_manifest.get(section):
				raise WorkspaceError(
					f"workspace Wally manifest must not use [{section}]"
				)

		for relative_path, expected_hash in EXPECTED_BLOCKER_SHA256.items():
			source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
			canonical_source = source.replace("\r\n", "\n").replace("\r", "\n")
			actual_hash = hashlib.sha256(canonical_source.encode("utf-8")).hexdigest()
			if actual_hash != expected_hash:
				raise WorkspaceError(
					f"{relative_path} changed; review the exact DeveloperTools "
					"compatibility blocker and refresh its expected hash"
				)

		blocked_manifest = manifests["ReactDevtoolsExtensions"]
		if (
			blocked_manifest.get("dev_dependencies", {}).get("DeveloperTools")
			!= EXPECTED_DEVELOPER_TOOLS
		):
			raise WorkspaceError(
				"exact DeveloperTools@0.2.3 blocker declaration changed"
			)
		blocked_test = REPOSITORY_ROOT / policy["blocked_suite"]
		if "Packages.Dev.DeveloperTools" not in blocked_test.read_text(
			encoding="utf-8"
		):
			raise WorkspaceError(
				"DeveloperTools integration test no longer exercises its dependency"
			)

		dependency_map: dict[str, tuple[list[str], list[str]]] = {}
		used_external: set[str] = set()
		used_alias_targets: set[str] = set()
		for name in included_names:
			runtime, development, used_overrides = classify_dependencies(
				name,
				manifests[name],
				included=included,
				name_by_directory=name_by_directory,
				directory_by_name=directory_by_name,
				external_dependencies=external_dependencies,
				legacy_external_dependencies=legacy_external_dependencies,
				workspace_dependencies=workspace_dependencies,
				omitted=omitted,
				alias_targets=alias_targets,
			)
			dependency_map[name] = (runtime, development)
			used_alias_targets.update(used_overrides)
			used_external.update(
				alias
				for alias in runtime + development
				if alias in external_dependencies
			)

		if used_external != set(external_dependencies):
			raise WorkspaceError(
				"external Wally dependency policy has unused or missing aliases"
			)
		if used_alias_targets != set(alias_targets):
			raise WorkspaceError(
				"alias_targets contains a stale or unused override"
			)
		derived_source_keys = derive_source_keys(
			included_names, manifests, directory_by_name
		)
		if source_keys != derived_source_keys:
			raise WorkspaceError(
				"source_keys differs from the included module project maps"
			)

		validate_test_inventory(policy, included, directory_by_name)
		project_name, workspace_path = load_root_project_shape()

		proxy_path = policy.get("proxy_path")
		project_path = policy.get("project_path")
		if not isinstance(proxy_path, str) or not isinstance(project_path, str):
			raise WorkspaceError(
				"proxy_path and project_path must be strings"
			)
		write_or_check(
			REPOSITORY_ROOT / proxy_path,
			render_proxy(alias_targets, source_keys),
			check=arguments.check,
		)
		write_or_check(
			REPOSITORY_ROOT / project_path,
			build_project(
				included_names,
				manifests,
				directory_by_name,
				dependency_map,
				source_keys,
				proxy_path,
				project_name,
				workspace_path,
			),
			check=arguments.check,
		)
	except (KeyError, OSError, TypeError, ValueError, WorkspaceError) as error:
		print(f"error: {error}", file=sys.stderr)
		return 1

	verb = "validated" if arguments.check else "generated"
	print(
		f"{verb} Wally source workspace "
		f"({policy['expected_suite_count']} inventoried suites)"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
