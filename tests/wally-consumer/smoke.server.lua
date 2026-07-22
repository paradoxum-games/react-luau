local expectation = _G.REACT_LUAU_SMOKE_EXPECTATION
assert(
	type(expectation) == "string",
	"REACT_LUAU_SMOKE_EXPECTATION must be '<mode>:<artifact marker>'"
)

local separator = string.find(expectation, ":", 1, true)
assert(separator ~= nil, "runtime smoke expectation has no artifact marker")
local mode = string.sub(expectation, 1, separator - 1)
local expectedRuntimeMarker = string.sub(expectation, separator + 1)
assert(
	mode == "dev" or mode == "release",
	"runtime smoke mode must be 'dev' or 'release'"
)
assert(expectedRuntimeMarker ~= "", "runtime smoke artifact marker must not be empty")

local isDev = mode == "dev"
_G.__DEV__ = isDev
_G.__COMPAT_WARNINGS__ = isDev
_G.__ROACT_17_MOCK_SCHEDULER__ = false

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Packages = ReplicatedStorage.Packages

local runtimeMarker = require(ReplicatedStorage.RuntimeMarker)
assert(
	runtimeMarker == expectedRuntimeMarker,
	"Rocale task did not load the exact consumer artifact built by this workflow"
)

local ReactGlobals = require(Packages.ReactGlobals)
local Shared = require(Packages.Shared)
local React = require(Packages.React)
local Scheduler = require(Packages.Scheduler)
local ReactIs = require(Packages.ReactIs)
local ReactReconciler = require(Packages.ReactReconciler)
local ReactRoblox = require(Packages.ReactRoblox)
local ReactTestRenderer = require(Packages.ReactTestRenderer)
local RoactCompat = require(Packages.RoactCompat)

assert(type(ReactGlobals) == "table", "ReactGlobals must load as a table")
assert(type(Shared) == "table", "Shared must load as a table")
assert(type(React) == "table", "React must load as a table")
assert(type(Scheduler) == "table", "Scheduler must load as a table")
assert(type(ReactIs) == "table", "ReactIs must load as a table")
assert(type(ReactReconciler) == "function", "ReactReconciler must load as a function")
assert(type(ReactRoblox) == "table", "ReactRoblox must load as a table")
assert(type(ReactTestRenderer) == "table", "ReactTestRenderer must load as a table")
assert(type(RoactCompat) == "table", "RoactCompat must load as a table")

local expectedVersion = "17.3.10"
assert(ReactGlobals.__DEV__ == isDev, "ReactGlobals must load the requested mode")
assert(
	ReactGlobals.__COMPAT_WARNINGS__ == isDev,
	"compatibility warnings must follow the requested mode"
)
assert(
	Shared.ReactVersion == expectedVersion,
	"Shared must expose the package-set version"
)
assert(React.version == expectedVersion, "React must expose the package-set version")
assert(
	React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED
		== Shared.ReactSharedInternals,
	"React and Shared must resolve one shared-internals instance"
)

local element = React.createElement("Folder")
assert(ReactIs.isElement(element), "ReactIs must recognize elements from React")
assert(
	RoactCompat.Component == React.Component,
	"RoactCompat and React must resolve one Component instance"
)
assert(
	ReactRoblox.version == Shared.ReactVersion,
	"ReactRoblox and Shared must resolve one package family version"
)

local testRenderer = ReactTestRenderer.create(React.createElement("Folder", {
	Name = "ReactLuauTestRendererSmoke",
}))
local testTree = testRenderer.toJSON()
assert(type(testTree) == "table", "ReactTestRenderer must produce a host tree")
assert(testTree.type == "Folder", "ReactTestRenderer must preserve the host type")
assert(
	testTree.props.Name == "ReactLuauTestRendererSmoke",
	"ReactTestRenderer must preserve host props"
)
testRenderer.unmount()
assert(testRenderer.toJSON() == nil, "ReactTestRenderer must unmount its host tree")

local container = Instance.new("Folder")
container.Name = "ReactLuauRuntimeSmokeContainer"
local root = ReactRoblox.createLegacyRoot(container)
root:render(React.createElement("Folder", {
	Name = "ReactLuauRuntimeSmokeChild",
}))

local renderedChild = container:FindFirstChild("ReactLuauRuntimeSmokeChild")
assert(
	renderedChild ~= nil and renderedChild:IsA("Folder"),
	"ReactRoblox must render a Folder host instance"
)

root:unmount()
assert(
	#container:GetChildren() == 0,
	"ReactRoblox must remove host instances during unmount"
)
container:Destroy()

print(
	string.format(
		"[React Luau] %s Wally consumer runtime smoke passed (%s)",
		mode,
		expectedVersion
	)
)
