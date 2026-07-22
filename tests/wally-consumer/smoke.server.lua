local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Packages = ReplicatedStorage.Packages

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
